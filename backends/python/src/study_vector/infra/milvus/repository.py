"""Milvus Repository 实现。

将业务层 DTO 与 pymilvus 模型互相翻译。

约定（业务层视角的统一 schema）：
- 主键字段：VARCHAR(128)
- 向量字段：FLOAT_VECTOR(dim=schema.dimension)
- 负载字段：JSON 类型，名为 `payload`，存储业务层 dict

实现要点：
- pymilvus 是同步 API，所有方法用 `asyncio.to_thread` 包装
- 过滤条件：业务层 dict -> Milvus `expr`，支持 ==（基础版）
"""
from __future__ import annotations

import asyncio
from datetime import datetime
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
    DistanceMetric,
    SearchRequest,
    SearchResult,
    VectorRecord,
)
from study_vector.infra.milvus.client import get_milvus_factory

# 主键字段名（与业务层 CollectionSchema.primary_field 保持一致）
_PRIMARY_FIELD = "id"
_VECTOR_FIELD = "vector"
_PAYLOAD_FIELD = "payload"


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
            coll = Collection(name=name)
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
            return CollectionInfo(
                name=name,
                dimension=dim or 0,
                metric=DistanceMetric.COSINE,  # 简化：实际可读索引参数
                row_count=coll.num_entities,
                created_at=datetime.utcnow(),
            )

        return await asyncio.to_thread(_info)

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
            coll = Collection(collection)
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
            coll = Collection(collection)
            rows = self._to_milvus_rows(records)
            coll.upsert(rows)
            coll.flush()
            return [str(r.id) for r in records]

        return await asyncio.to_thread(_upsert)

    async def delete(self, collection: str, ids: list[str | int]) -> int:
        if not ids:
            return 0

        def _delete() -> int:
            coll = Collection(collection)
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
            coll = Collection(request.collection)
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
            coll = Collection(collection)
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
