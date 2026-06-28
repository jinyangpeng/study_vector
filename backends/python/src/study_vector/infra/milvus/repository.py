"""Milvus Repository 实现。

将业务层 DTO 与 pymilvus 模型互相翻译。

约定（业务层视角的统一 schema）：
- 主键字段：VARCHAR(128)
- 向量字段：FLOAT_VECTOR(dim=schema.dimension)
- 负载字段：JSON 类型，名为 `payload`，存储业务层 dict

实现要点：
- pymilvus 是同步 API，所有方法用 `asyncio.to_thread` 包装
- 过滤条件：业务层 dict -> Milvus `expr`，支持 ==（基础版）
- 用户/数据库：Milvus 2.4 的 RBAC API（`utility.list_user` / `user.create`）
"""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from pymilvus import (
    Collection,
    DataType,
    FieldSchema,
    MilvusException,
    utility,
)
from pymilvus import (
    CollectionSchema as MilvusCollectionSchema,
)

from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    CreateIndexRequest,
    CreatePartitionRequest,
    DistanceMetric,
    HybridSearchRequest,
    IndexInfo,
    IndexType,
    LoadRequest,
    PartitionInfo,
    QueryRequest,
    SearchRequest,
    SearchResult,
    UserInfo,
    VectorRecord,
)
from study_vector.exceptions import (
    CollectionNotFoundError,
    IndexNotFoundError,
    PartitionNotFoundError,
)
from study_vector.infra.milvus.client import get_milvus_factory

# 业务层统一 schema 字段名
_PRIMARY_FIELD = "id"
_VECTOR_FIELD = "vector"
_PAYLOAD_FIELD = "payload"

# Milvus RBAC 操作（pymilvus 2.4+ 用 `utility` 或 `connections` 提供的 API）
# 不同版本有差异，下面封装一层容错


class MilvusRepository:
    """基于 pymilvus 的 VectorRepository 实现。"""

    def __init__(self) -> None:
        self._factory = get_milvus_factory()

    # ============= 生命周期 =============

    async def connect(self) -> None:
        await asyncio.to_thread(self._factory.connect)

    async def close(self) -> None:
        await asyncio.to_thread(self._factory.close)

    async def healthcheck(self) -> bool:
        def _check() -> bool:
            try:
                ver = utility.get_server_version()
                return bool(ver)
            except MilvusException:
                logger.exception("Milvus 健康检查失败")
                return False

        return await asyncio.to_thread(_check)

    # ============= 集合管理 =============

    def _build_milvus_schema(self, schema: CollectionSchema) -> MilvusCollectionSchema:
        """业务 schema -> pymilvus schema。"""
        fields = [
            FieldSchema(
                name=schema.primary_field,
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=128,
            ),
            FieldSchema(
                name=schema.vector_field,
                dtype=DataType.FLOAT_VECTOR,
                dim=schema.dimension,
            ),
            FieldSchema(name=_PAYLOAD_FIELD, dtype=DataType.JSON),
        ]
        return MilvusCollectionSchema(
            fields=fields,
            description=schema.description or "",
            enable_dynamic_field=False,
        )

    def _ensure_collection(self, name: str) -> Collection:
        if not utility.has_collection(name):
            raise CollectionNotFoundError(f"集合不存在 name={name}")
        return Collection(name=name)

    async def create_collection(self, schema: CollectionSchema) -> None:
        def _create() -> None:
            if utility.has_collection(schema.name):
                logger.info(f"集合已存在，跳过创建 name={schema.name}")
                return
            milvus_schema = self._build_milvus_schema(schema)
            coll = Collection(name=schema.name, schema=milvus_schema)
            index_params = {
                "metric_type": schema.metric.value,
                "index_type": schema.index_type.value,
                "params": {},
            }
            coll.create_index(
                field_name=schema.vector_field, index_params=index_params
            )
            coll.load()
            logger.info(
                f"已创建集合 name={schema.name} dim={schema.dimension} "
                f"metric={schema.metric.value} index={schema.index_type.value}"
            )

        await asyncio.to_thread(_create)

    async def drop_collection(self, name: str) -> None:
        def _drop() -> None:
            if not utility.has_collection(name):
                return
            utility.drop_collection(name)
            logger.info(f"已删除集合 name={name}")

        await asyncio.to_thread(_drop)

    async def has_collection(self, name: str) -> bool:
        return await asyncio.to_thread(utility.has_collection, name)

    async def list_collections(self) -> list[str]:
        return await asyncio.to_thread(utility.list_collections)

    async def get_collection_info(self, name: str) -> CollectionInfo:
        def _info() -> CollectionInfo:
            coll = self._ensure_collection(name)
            # 找到 FLOAT_VECTOR 字段的 dim
            vector_field = next(
                (f for f in coll.schema.fields if f.dtype == DataType.FLOAT_VECTOR),
                None,
            )
            dim = vector_field.dim if vector_field else 0
            try:
                coll.flush()
            except MilvusException:
                logger.warning("集合 flush 失败（可忽略）")
            # 尝试读取加载状态
            loaded = False
            try:
                progress = utility.loading_progress(name)
                loaded = progress == 100
            except Exception:  # noqa: BLE001
                loaded = False
            # 读取 metric / index（从第一个索引推断）
            metric = DistanceMetric.COSINE
            index_list: list[IndexInfo] = []
            try:
                for idx in coll.indexes:
                    params = dict(idx.params or {})
                    metric_str = params.get("metric_type", "COSINE")
                    try:
                        metric = DistanceMetric(metric_str)
                    except ValueError:
                        pass
                    index_type_str = params.get("index_type", "AUTOINDEX")
                    try:
                        index_list.append(
                            IndexInfo(
                                field_name=idx.field_name,
                                index_type=IndexType(index_type_str),
                                metric_type=metric,
                                params=params,
                            )
                        )
                    except ValueError:
                        # 未知索引类型
                        pass
            except MilvusException:
                pass
            return CollectionInfo(
                name=name,
                dimension=dim or 0,
                metric=metric,
                row_count=coll.num_entities,
                loaded=loaded,
                indexes=index_list,
                created_at=datetime.now(UTC),
            )

        return await asyncio.to_thread(_info)

    # ============= 集合内存：load / release =============

    async def load_collection(
        self, name: str, request: LoadRequest | None = None
    ) -> None:
        def _load() -> None:
            coll = self._ensure_collection(name)
            kwargs: dict[str, Any] = {}
            if request is not None:
                if request.replica_number and request.replica_number > 1:
                    kwargs["replica_number"] = request.replica_number
                if request.partition_names:
                    kwargs["partition_names"] = request.partition_names
            coll.load(**kwargs)
            logger.info(f"已加载集合 name={name} kwargs={kwargs}")

        await asyncio.to_thread(_load)

    async def release_collection(self, name: str) -> None:
        def _release() -> None:
            coll = self._ensure_collection(name)
            coll.release()
            logger.info(f"已释放集合 name={name}")

        await asyncio.to_thread(_release)

    async def is_loaded(self, name: str) -> bool:
        def _is_loaded() -> bool:
            if not utility.has_collection(name):
                return False
            try:
                return utility.loading_progress(name) == 100
            except MilvusException:
                return False

        return await asyncio.to_thread(_is_loaded)

    # ============= 索引 =============

    async def create_index(
        self, name: str, request: CreateIndexRequest
    ) -> None:
        def _create() -> None:
            coll = self._ensure_collection(name)
            index_params = {
                "metric_type": request.metric_type.value,
                "index_type": request.index_type.value,
                "params": dict(request.params or {}),
            }
            coll.create_index(
                field_name=request.field_name, index_params=index_params
            )
            logger.info(
                f"已建索引 name={name} field={request.field_name} "
                f"type={request.index_type.value}"
            )

        await asyncio.to_thread(_create)

    async def list_indexes(self, name: str) -> list[IndexInfo]:
        def _list() -> list[IndexInfo]:
            coll = self._ensure_collection(name)
            out: list[IndexInfo] = []
            for idx in coll.indexes:
                # idx.field_name, idx.index_name, idx.params
                params = dict(idx.params or {})
                index_type_str = params.get("index_type", "AUTOINDEX")
                metric_type_str = params.get("metric_type", "COSINE")
                out.append(
                    IndexInfo(
                        field_name=idx.field_name,
                        index_type=IndexType(index_type_str),
                        metric_type=metric_type_str,
                        params=params,
                    )
                )
            return out

        return await asyncio.to_thread(_list)

    async def drop_index(self, name: str, field_name: str) -> None:
        def _drop() -> None:
            coll = self._ensure_collection(name)
            try:
                coll.drop_index(field_name=field_name)
            except MilvusException as e:
                raise IndexNotFoundError(
                    f"索引不存在 name={name} field={field_name}"
                ) from e
            logger.info(f"已删索引 name={name} field={field_name}")

        await asyncio.to_thread(_drop)

    # ============= 分区 =============

    async def create_partition(
        self, name: str, request: CreatePartitionRequest
    ) -> None:
        def _create() -> None:
            coll = self._ensure_collection(name)
            if request.name in [p.name for p in coll.partitions]:
                logger.info(f"分区已存在 name={name}/{request.name}")
                return
            coll.create_partition(request.name)
            logger.info(f"已建分区 name={name}/{request.name}")

        await asyncio.to_thread(_create)

    async def list_partitions(self, name: str) -> list[PartitionInfo]:
        def _list() -> list[PartitionInfo]:
            coll = self._ensure_collection(name)
            return [
                PartitionInfo(
                    name=p.name,
                    row_count=p.num_entities,
                    created_at=None,
                )
                for p in coll.partitions
            ]

        return await asyncio.to_thread(_list)

    async def drop_partition(self, name: str, partition: str) -> None:
        def _drop() -> None:
            coll = self._ensure_collection(name)
            names = [p.name for p in coll.partitions]
            if partition not in names:
                raise PartitionNotFoundError(
                    f"分区不存在 name={name}/{partition}"
                )
            coll.drop_partition(partition)
            logger.info(f"已删分区 name={name}/{partition}")

        await asyncio.to_thread(_drop)

    # ============= Alias =============

    async def create_alias(self, name: str, alias: str) -> None:
        def _create() -> None:
            self._ensure_collection(name)
            try:
                utility.create_alias(collection_name=name, alias=alias)
            except MilvusException as e:
                # alias 已存在时不算错
                if "already exists" in str(e).lower():
                    logger.info(f"alias 已存在 collection={name} alias={alias}")
                    return
                raise
            logger.info(f"已建 alias collection={name} alias={alias}")

        await asyncio.to_thread(_create)

    async def list_aliases(self, name: str) -> list[str]:
        def _list() -> list[str]:
            self._ensure_collection(name)
            try:
                return list(utility.list_aliases(collection_name=name) or [])
            except MilvusException:
                # 老版本 Milvus 不支持 collection_name 参数
                return list(utility.list_aliases() or [])

        return await asyncio.to_thread(_list)

    async def drop_alias(self, name: str, alias: str) -> None:
        def _drop() -> None:
            try:
                utility.drop_alias(alias=alias)
            except MilvusException as e:
                if "not exists" in str(e).lower():
                    logger.info(f"alias 不存在 alias={alias}")
                    return
                raise
            logger.info(f"已删 alias collection={name} alias={alias}")

        await asyncio.to_thread(_drop)

    # ============= 数据库 =============

    async def list_databases(self) -> list[str]:
        return await asyncio.to_thread(utility.list_database)

    async def create_database(self, name: str) -> None:
        def _create() -> None:
            try:
                utility.create_database(db_name=name)
            except MilvusException as e:
                if "already exists" in str(e).lower():
                    logger.info(f"db 已存在 name={name}")
                    return
                raise
            logger.info(f"已建数据库 name={name}")

        await asyncio.to_thread(_create)

    async def drop_database(self, name: str) -> None:
        def _drop() -> None:
            try:
                utility.drop_database(db_name=name)
            except MilvusException as e:
                if "not exists" in str(e).lower():
                    logger.info(f"db 不存在 name={name}")
                    return
                raise
            logger.info(f"已删数据库 name={name}")

        await asyncio.to_thread(_drop)

    # ============= 用户（RBAC 教学辅助） =============

    async def list_users(self) -> list[UserInfo]:
        def _list() -> list[UserInfo]:
            try:
                # pymilvus 2.4+ 提供 utility.list_user
                users = utility.list_user() or []
                return [UserInfo(user_name=str(u)) for u in users]
            except (MilvusException, AttributeError):
                return []

        return await asyncio.to_thread(_list)

    async def create_user(self, user_name: str, password: str) -> UserInfo:
        def _create() -> None:
            try:
                utility.create_user(user_name=user_name, password=password)
            except MilvusException as e:
                if "already exists" in str(e).lower():
                    logger.info(f"user 已存在 name={user_name}")
                    return
                raise
            logger.info(f"已建用户 name={user_name}")

        await asyncio.to_thread(_create)
        return UserInfo(user_name=user_name, created_at=datetime.now(UTC))

    async def drop_user(self, user_name: str) -> None:
        def _drop() -> None:
            try:
                utility.delete_user(user_name=user_name)
            except MilvusException as e:
                if "not exists" in str(e).lower():
                    logger.info(f"user 不存在 name={user_name}")
                    return
                raise
            logger.info(f"已删用户 name={user_name}")

        await asyncio.to_thread(_drop)

    # ============= 写入 =============

    @staticmethod
    def _to_milvus_rows(records: list[VectorRecord]) -> list[list[Any]]:
        """业务 records -> pymilvus 列式数据。"""
        return [
            [str(r.id) for r in records],
            [r.vector for r in records],
            [r.payload for r in records],
        ]

    async def insert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        if not records:
            return []

        def _insert() -> list[str | int]:
            coll = self._ensure_collection(collection)
            rows = self._to_milvus_rows(records)
            coll.insert(rows)
            coll.flush()
            return [str(r.id) for r in records]

        return await asyncio.to_thread(_insert)

    async def upsert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        if not records:
            return []

        def _upsert() -> list[str | int]:
            coll = self._ensure_collection(collection)
            rows = self._to_milvus_rows(records)
            coll.upsert(rows)
            coll.flush()
            return [str(r.id) for r in records]

        return await asyncio.to_thread(_upsert)

    async def delete(self, collection: str, ids: list[str | int]) -> int:
        if not ids:
            return 0

        def _delete() -> int:
            coll = self._ensure_collection(collection)
            str_ids = [str(i) for i in ids]
            # 用引号包裹字符串主键
            quoted = ",".join(f'"{i}"' for i in str_ids)
            expr = f"{_PRIMARY_FIELD} in [{quoted}]"
            mut = coll.delete(expr)
            coll.flush()
            return mut.delete_count

        return await asyncio.to_thread(_delete)

    # ============= 检索 =============

    @staticmethod
    def _build_filter_expr(filter_expr: dict[str, Any] | None) -> str | None:
        """业务 dict -> Milvus expr（极简版：仅支持 ==，AND 连接）。

        支持的 value 类型：str / bool / 数字
        字段读取自 `payload` JSON 字段。
        """
        if not filter_expr:
            return None
        parts: list[str] = []
        for k, v in filter_expr.items():
            if isinstance(v, str):
                parts.append(f'{_PAYLOAD_FIELD}["{k}"] == "{v}"')
            elif isinstance(v, bool):
                parts.append(f'{_PAYLOAD_FIELD}["{k}"] == {str(v).lower()}')
            elif isinstance(v, (int, float)):
                parts.append(f'{_PAYLOAD_FIELD}["{k}"] == {v}')
            else:
                raise ValueError(
                    f"过滤值类型不支持（仅 str/bool/number）：{k}={v!r}"
                )
        return " and ".join(parts) if parts else None

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        def _search() -> list[SearchResult]:
            coll = self._ensure_collection(request.collection or "")
            # 检索时如果未 load，自动 load（教学体验更好）
            try:
                if utility.loading_progress(coll.name) < 100:
                    coll.load()
            except MilvusException:
                coll.load()
            expr = self._build_filter_expr(request.filter_expr)
            output_fields = list(request.output_fields or [])
            if _PAYLOAD_FIELD not in output_fields:
                output_fields.append(_PAYLOAD_FIELD)

            results = coll.search(
                data=[request.vector],
                anns_field=_VECTOR_FIELD,
                param={"metric_type": "COSINE"},
                limit=request.top_k,
                expr=expr,
                output_fields=output_fields,
            )

            out: list[SearchResult] = []
            for hit in results[0]:
                out.append(
                    SearchResult(
                        id=hit.id if isinstance(hit.id, (str, int)) else str(hit.id),
                        score=float(hit.score),
                        payload=dict(hit.entity.get(_PAYLOAD_FIELD) or {}),
                    )
                )
            return out

        return await asyncio.to_thread(_search)

    async def get(
        self, collection: str, ids: list[str | int]
    ) -> list[VectorRecord]:
        if not ids:
            return []

        def _get() -> list[VectorRecord]:
            coll = self._ensure_collection(collection)
            str_ids = [str(i) for i in ids]
            quoted = ",".join(f'"{i}"' for i in str_ids)
            expr = f"{_PRIMARY_FIELD} in [{quoted}]"
            rows = coll.query(
                expr=expr, output_fields=[_PRIMARY_FIELD, _VECTOR_FIELD, _PAYLOAD_FIELD]
            )
            return [
                VectorRecord(
                    id=row[_PRIMARY_FIELD],
                    vector=row[_VECTOR_FIELD],
                    payload=row.get(_PAYLOAD_FIELD) or {},
                )
                for row in rows
            ]

        return await asyncio.to_thread(_get)

    # ============= Query（标量检索 / count） =============

    async def query(
        self, collection: str, request: QueryRequest
    ) -> list[VectorRecord] | int:
        def _do() -> list[VectorRecord] | int:
            coll = self._ensure_collection(collection)
            expr = self._build_filter_expr(request.filter)
            output_fields = list(request.output_fields or [])
            if _PAYLOAD_FIELD not in output_fields:
                output_fields.append(_PAYLOAD_FIELD)
            if _VECTOR_FIELD not in output_fields and not request.count_only:
                output_fields.append(_VECTOR_FIELD)

            if request.count_only:
                # 直接走 num_entities 风格的快速计数（前提：没有 delete）
                # 真实场景应走 query(expr=expr, output_fields=["count(*)"])
                rows = coll.query(
                    expr=expr or "id != \"\"",
                    output_fields=["count(*)"],
                )
                if rows and "count(*)" in rows[0]:
                    return int(rows[0]["count(*)"])
                return 0

            rows = coll.query(
                expr=expr or "id != \"\"",
                output_fields=output_fields,
                limit=request.limit,
                offset=request.offset,
            )
            out: list[VectorRecord] = []
            for row in rows:
                out.append(
                    VectorRecord(
                        id=row.get(_PRIMARY_FIELD, ""),
                        vector=row.get(_VECTOR_FIELD, []) or [],
                        payload=row.get(_PAYLOAD_FIELD) or {},
                    )
                )
            return out

        return await asyncio.to_thread(_do)

    # ============= Hybrid Search（dense + sparse + RRF） =============

    async def hybrid_search(
        self, request: HybridSearchRequest
    ) -> list[SearchResult]:
        """混合检索实现（教学版）。

        策略：
        1. 稠密路：直接用 request.dense 向量走 search
        2. 稀疏路：把 dict[int,float] 转成 dense 向量（Milvus 2.4 教学用）；
           真实生产用 SPARSE_FLOAT_VECTOR 字段
        3. 用 RRF（Reciprocal Rank Fusion）合并排序
           score(d) = sum_{rank in hits} weight / (k + rank)
        """
        if not request.dense and not request.sparse:
            return []

        def _search_dense() -> list[SearchResult]:
            if not request.dense:
                return []
            coll = self._ensure_collection(request.collection or "")
            expr = self._build_filter_expr(request.filter_expr)
            output_fields = [_PRIMARY_FIELD, _PAYLOAD_FIELD]
            try:
                results = coll.search(
                    data=[request.dense],
                    anns_field=_VECTOR_FIELD,
                    param={"metric_type": "COSINE"},
                    limit=request.top_k * 2,  # 拿多一些给 RRF 用
                    expr=expr,
                    output_fields=output_fields,
                )
            except MilvusException:
                return []
            out: list[SearchResult] = []
            for hit in results[0]:
                out.append(
                    SearchResult(
                        id=str(hit.id),
                        score=float(hit.score),
                        payload=dict(hit.entity.get(_PAYLOAD_FIELD) or {}),
                    )
                )
            return out

        # 稀疏路：把 dict 散点转成 dense 向量（仅供教学演示 RRF 流程）
        def _search_sparse() -> list[SearchResult]:
            if not request.sparse:
                return []
            # 教学实现：用 sparse 词频向量代替密集向量（业务里要建 SPARSE_FLOAT_VECTOR 字段）
            coll = self._ensure_collection(request.collection or "")
            expr = self._build_filter_expr(request.filter_expr)
            # 把 dict -> list（与 schema 的 dim 等长）
            dim = 0
            for f in coll.schema.fields:
                if f.dtype == DataType.FLOAT_VECTOR:
                    dim = f.dim
                    break
            if not dim:
                return []
            vec = [0.0] * dim
            for k, v in request.sparse.items():
                try:
                    idx = int(k)
                    if 0 <= idx < dim:
                        vec[idx] = float(v)
                except (ValueError, TypeError):
                    continue
            try:
                results = coll.search(
                    data=[vec],
                    anns_field=_VECTOR_FIELD,
                    param={"metric_type": "COSINE"},
                    limit=request.top_k * 2,
                    expr=expr,
                    output_fields=[_PRIMARY_FIELD, _PAYLOAD_FIELD],
                )
            except MilvusException:
                return []
            out: list[SearchResult] = []
            for hit in results[0]:
                out.append(
                    SearchResult(
                        id=str(hit.id),
                        score=float(hit.score),
                        payload=dict(hit.entity.get(_PAYLOAD_FIELD) or {}),
                    )
                )
            return out

        dense_hits, sparse_hits = await asyncio.gather(
            asyncio.to_thread(_search_dense),
            asyncio.to_thread(_search_sparse),
        )

        # RRF 合并
        k = request.rrf_k
        score_map: dict[str, float] = {}
        # dense 路
        for rank, hit in enumerate(dense_hits, start=1):
            score_map[hit.id] = score_map.get(hit.id, 0.0) + (
                request.dense_weight / (k + rank)
            )
        # sparse 路
        for rank, hit in enumerate(sparse_hits, start=1):
            score_map[hit.id] = score_map.get(hit.id, 0.0) + (
                request.sparse_weight / (k + rank)
            )

        # 拿到原 payload
        payload_map: dict[str, dict[str, Any]] = {}
        for hit in dense_hits + sparse_hits:
            payload_map[hit.id] = hit.payload

        # 按 RRF 分数排序
        ranked = sorted(score_map.items(), key=lambda kv: kv[1], reverse=True)
        return [
            SearchResult(
                id=_id,
                score=float(_score),
                payload=payload_map.get(_id, {}),
            )
            for _id, _score in ranked[: request.top_k]
        ]
