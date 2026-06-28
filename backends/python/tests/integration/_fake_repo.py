"""内存版 Repository 替身：仅测试用。

实现 `VectorRepository` 协议的全部方法，
使用朴素 cosine 计算相似度，验证业务层逻辑。
"""
from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    CreateIndexRequest,
    CreatePartitionRequest,
    HybridSearchRequest,
    IndexInfo,
    LoadRequest,
    PartitionInfo,
    QueryRequest,
    SearchRequest,
    SearchResult,
    UserInfo,
    VectorRecord,
)
from study_vector.repositories.base import VectorRepository


class FakeVectorRepository(VectorRepository):
    """基于内存 dict + list 的极简实现。"""

    def __init__(self) -> None:
        self._cols: dict[str, dict[str, Any]] = {}
        self._recs: dict[str, list[VectorRecord]] = {}
        # 额外状态：索引 / 分区 / alias / db / user
        self._indexes: dict[str, list[IndexInfo]] = {}
        self._partitions: dict[str, list[PartitionInfo]] = {}
        self._aliases: dict[str, list[str]] = {}
        self._dbs: list[str] = ["default"]
        self._users: dict[str, UserInfo] = {}
        self._loaded: set[str] = set()

    # ============= 生命周期 =============

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def healthcheck(self) -> bool:
        return True

    # ============= 集合管理 =============

    async def create_collection(self, schema: CollectionSchema) -> None:
        self._cols[schema.name] = schema.model_dump()
        self._recs.setdefault(schema.name, [])
        self._indexes.setdefault(schema.name, [])
        self._partitions.setdefault(schema.name, [
            PartitionInfo(name="_default", row_count=0)
        ])
        self._aliases.setdefault(schema.name, [])
        # 默认建一个 AUTOINDEX
        self._indexes[schema.name].append(
            IndexInfo(
                field_name=schema.vector_field,
                index_type=schema.index_type,
                metric_type=schema.metric,
                params={},
            )
        )
        # 默认标记为已加载
        self._loaded.add(schema.name)

    async def drop_collection(self, name: str) -> None:
        self._cols.pop(name, None)
        self._recs.pop(name, None)
        self._indexes.pop(name, None)
        self._partitions.pop(name, None)
        self._aliases.pop(name, None)
        self._loaded.discard(name)

    async def has_collection(self, name: str) -> bool:
        return name in self._cols

    async def list_collections(self) -> list[str]:
        return list(self._cols.keys())

    async def get_collection_info(self, name: str) -> CollectionInfo:
        s = self._cols[name]
        return CollectionInfo(
            name=name,
            dimension=s["dimension"],
            metric=s["metric"],
            vector_type=s.get("vector_type", "FloatVector"),
            row_count=len(self._recs[name]),
            loaded=name in self._loaded,
            consistency_level=s.get("consistency_level", "Session"),
            indexes=list(self._indexes.get(name, [])),
            created_at=datetime.now(UTC),
        )

    # ============= 集合内存 =============

    async def load_collection(
        self, name: str, request: LoadRequest | None = None
    ) -> None:
        if name in self._cols:
            self._loaded.add(name)

    async def release_collection(self, name: str) -> None:
        self._loaded.discard(name)

    async def is_loaded(self, name: str) -> bool:
        return name in self._loaded

    # ============= 索引 =============

    async def create_index(
        self, name: str, request: CreateIndexRequest
    ) -> None:
        if name not in self._cols:
            return  # 教学 fake：忽略
        # 删除同字段旧索引再加
        self._indexes[name] = [
            i for i in self._indexes[name] if i.field_name != request.field_name
        ]
        self._indexes[name].append(
            IndexInfo(
                field_name=request.field_name,
                index_type=request.index_type,
                metric_type=request.metric_type,
                params=dict(request.params or {}),
            )
        )

    async def list_indexes(self, name: str) -> list[IndexInfo]:
        return list(self._indexes.get(name, []))

    async def drop_index(self, name: str, field_name: str) -> None:
        self._indexes[name] = [
            i for i in self._indexes.get(name, []) if i.field_name != field_name
        ]

    # ============= 分区 =============

    async def create_partition(
        self, name: str, request: CreatePartitionRequest
    ) -> None:
        if name not in self._cols:
            return
        existing = [p.name for p in self._partitions[name]]
        if request.name not in existing:
            self._partitions[name].append(PartitionInfo(name=request.name))

    async def list_partitions(self, name: str) -> list[PartitionInfo]:
        return list(self._partitions.get(name, []))

    async def drop_partition(self, name: str, partition: str) -> None:
        # 不允许删 _default
        if partition == "_default":
            return
        self._partitions[name] = [
            p for p in self._partitions.get(name, []) if p.name != partition
        ]

    # ============= Alias =============

    async def create_alias(self, name: str, alias: str) -> None:
        if name not in self._cols:
            return
        # 教学 fake：alias 全局唯一 → 一旦被其他集合占用就拒绝
        for existing_name, aliases in self._aliases.items():
            if alias in aliases and existing_name != name:
                # 真实 Milvus 会抛 "alias already exists"
                raise ValueError(
                    f"alias 已被集合 {existing_name} 占用: {alias}"
                )
        if alias not in self._aliases[name]:
            self._aliases[name].append(alias)

    async def list_aliases(self, name: str) -> list[str]:
        return list(self._aliases.get(name, []))

    async def drop_alias(self, name: str, alias: str) -> None:
        self._aliases[name] = [
            a for a in self._aliases.get(name, []) if a != alias
        ]

    # ============= 数据库 =============

    async def list_databases(self) -> list[str]:
        return list(self._dbs)

    async def create_database(self, name: str) -> None:
        if name not in self._dbs:
            self._dbs.append(name)

    async def drop_database(self, name: str) -> None:
        if name == "default":
            return  # 保护 default
        self._dbs = [d for d in self._dbs if d != name]

    # ============= 用户（RBAC 教学辅助） =============

    async def list_users(self) -> list[UserInfo]:
        return list(self._users.values())

    async def create_user(self, user_name: str, password: str) -> UserInfo:
        if user_name not in self._users:
            self._users[user_name] = UserInfo(
                user_name=user_name, created_at=datetime.now(UTC)
            )
        return self._users[user_name]

    async def drop_user(self, user_name: str) -> None:
        self._users.pop(user_name, None)

    # ============= 写入 =============

    async def insert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        self._recs[collection].extend(records)
        return [str(r.id) for r in records]

    async def upsert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        # 简化：按 id 去重后插入
        ids = {str(r.id) for r in records}
        self._recs[collection] = [
            r for r in self._recs[collection] if str(r.id) not in ids
        ]
        self._recs[collection].extend(records)
        return [str(r.id) for r in records]

    async def delete(self, collection: str, ids: list[str | int]) -> int:
        idset = {str(i) for i in ids}
        before = len(self._recs[collection])
        self._recs[collection] = [
            r for r in self._recs[collection] if str(r.id) not in idset
        ]
        return before - len(self._recs[collection])

    # ============= 检索 =============

    @staticmethod
    def _cos(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        return dot / (na * nb + 1e-12)

    @staticmethod
    def _ip(a: list[float], b: list[float]) -> float:
        """Inner Product：原始点积。向量化前 L2 归一则与 COSINE 等价。"""
        return sum(x * y for x, y in zip(a, b, strict=False))

    @staticmethod
    def _l2_dist(a: list[float], b: list[float]) -> float:
        """欧氏距离。score 转成 ``1 / (1 + dist)`` 让分值越大越相关。"""
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b, strict=False)))

    @staticmethod
    def _l2_score(a: list[float], b: list[float]) -> float:
        return 1.0 / (1.0 + FakeVectorRepository._l2_dist(a, b))

    @staticmethod
    def _hamming_dist(a: list[float], b: list[float]) -> int:
        """二进制向量汉明距离：按位比较，统计不同的 bit 数。

        输入：0/1 序列（float 形式存储以兼容通用序列化）
        教学：BinaryVector 在 Milvus 内部按字节位存储，D=8 时 8 个 bit 打成 1 字节；
        距离定义为不同 bit 数，越小越相似。
        """
        return sum(1 for x, y in zip(a, b, strict=False) if x != y)

    # ============= 过滤表达式（MongoDB 风格） =============

    @staticmethod
    def _match_field_condition(actual: Any, condition: Any) -> bool:
        """单字段 vs 单条件。"""
        # 标量值 = 等于
        if not isinstance(condition, dict):
            return actual == condition
        # 运算符 dict：所有 op 必须满足（AND）
        for op, expected in condition.items():
            if op == "$eq":
                if actual != expected:
                    return False
            elif op == "$ne":
                if actual == expected:
                    return False
            elif op == "$gt":
                if actual is None or not (actual > expected):
                    return False
            elif op == "$gte":
                if actual is None or not (actual >= expected):
                    return False
            elif op == "$lt":
                if actual is None or not (actual < expected):
                    return False
            elif op == "$lte":
                if actual is None or not (actual <= expected):
                    return False
            elif op == "$in":
                if actual not in expected:
                    return False
            elif op == "$nin":
                if actual in expected:
                    return False
            else:
                return False  # 未知运算符
        return True

    @staticmethod
    def _match_filter(payload: dict[str, Any], expr: dict[str, Any] | None) -> bool:
        """评估 MongoDB 风格过滤表达式（与 Milvus 表达式等价）。

        支持：
        - 顶层多 key → AND
        - ``$or`` / ``$and`` → 逻辑组合
        - 字段值 = 标量 → 等于
        - 字段值 = ``{"$op": v, ...}`` → 运算符 dict
        """
        if not expr:
            return True
        # 顶层 $or
        if "$or" in expr:
            return any(
                FakeVectorRepository._match_filter(payload, sub) for sub in expr["$or"]
            )
        # 顶层 $and
        if "$and" in expr:
            return all(
                FakeVectorRepository._match_filter(payload, sub) for sub in expr["$and"]
            )
        # 字段条件
        for field, condition in expr.items():
            if field.startswith("$"):
                continue  # 跳过未知顶层运算符
            actual = payload.get(field)
            if not FakeVectorRepository._match_field_condition(actual, condition):
                return False
        return True

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        recs = self._recs[request.collection]
        # 从 collection schema 取度量与向量类型（与 OpenAPI/DistanceMetric 对齐）
        metric = self._cols.get(request.collection, {}).get("metric", "COSINE")
        vector_type = self._cols.get(request.collection, {}).get("vector_type", "FloatVector")
        if vector_type == "BinaryVector":
            # 二进制向量：按位汉明距离。distance 越小越相似 → score 越大
            # 教学：BinaryVector 在 Milvus 内部按字节位存储
            def _bin_score(a: list[float], b: list[float]) -> float:
                return 1.0 / (1.0 + FakeVectorRepository._hamming_dist(a, b))

            score_fn: Any = _bin_score
            reverse = True  # score 越大越相关
        elif metric in ("COSINE",):
            score_fn = self._cos
            reverse = True
        elif metric in ("IP", "INNER_PRODUCT"):
            score_fn = self._ip
            reverse = True
        elif metric in ("L2", "EUCLIDEAN"):
            score_fn = self._l2_score
            reverse = True  # score 已经是 1/(1+dist)
        elif metric == "HAMMING":
            # 浮点向量 + HAMMING 度量（理论可配 binary metric 但教学 fake 简化）
            score_fn = self._hamming_dist
            reverse = False  # 距离越小越相关
        elif metric == "JACCARD":
            # Jaccard = 1 - |A∩B| / |A∪B|；教学 fake 简化成 cos 作为占位
            score_fn = self._cos
            reverse = True
        else:
            # 未识别度量降级为 COSINE
            score_fn = self._cos
            reverse = True
        # 分区过滤：先按 partition_names 筛；空 = 全部分区
        if request.partition_names:
            allowed = set(request.partition_names)
            recs = [
                r
                for r in recs
                if r.payload.get("_partition", "_default") in allowed
            ]
        scored = [(score_fn(request.vector, r.vector), r) for r in recs]
        scored.sort(key=lambda x: x[0], reverse=reverse)
        # MongoDB 风格过滤
        if request.filter_expr:
            scored = [
                (s, r)
                for s, r in scored
                if self._match_filter(r.payload, request.filter_expr)
            ]
        return [
            SearchResult(id=r.id, score=round(s, 6), payload=r.payload)
            for s, r in scored[: request.top_k]
        ]

    async def query(
        self, collection: str, request: QueryRequest
    ) -> list[VectorRecord] | int:
        recs = self._recs[collection]
        # 分区过滤
        if request.partition_names:
            allowed = set(request.partition_names)
            recs = [
                r
                for r in recs
                if r.payload.get("_partition", "_default") in allowed
            ]
        if request.filter:
            recs = [r for r in recs if self._match_filter(r.payload, request.filter)]
        if request.count_only:
            return len(recs)
        # 简单分页
        start = request.offset
        end = start + request.limit
        return recs[start:end]

    async def hybrid_search(
        self, request: HybridSearchRequest
    ) -> list[SearchResult]:
        """教学版 hybrid：dense + sparse 各自检索后用 RRF 合并。"""
        recs = self._recs[request.collection or ""]
        k = request.rrf_k
        score_map: dict[str, float] = {}

        # dense 路
        if request.dense:
            dense_scored = [
                (self._cos(request.dense, r.vector), r) for r in recs
            ]
            dense_scored.sort(key=lambda x: x[0], reverse=True)
            for rank, (_s, r) in enumerate(dense_scored[: request.top_k * 2], start=1):
                _id = str(r.id)
                score_map[_id] = score_map.get(_id, 0.0) + (
                    request.dense_weight / (k + rank)
                )

        # sparse 路：把 dict 当成 top-k 关键词打分
        if request.sparse:
            sparse_scored = []
            for r in recs:
                score = sum(
                    float(v) * float(r.payload.get(f"kw_{kid}", 0) or 0)
                    for kid, v in request.sparse.items()
                )
                if score > 0:
                    sparse_scored.append((score, r))
            sparse_scored.sort(key=lambda x: x[0], reverse=True)
            for rank, (_s, r) in enumerate(sparse_scored[: request.top_k * 2], start=1):
                _id = str(r.id)
                score_map[_id] = score_map.get(_id, 0.0) + (
                    request.sparse_weight / (k + rank)
                )

        # 收集 payload
        payload_map = {str(r.id): r.payload for r in recs}
        ranked = sorted(score_map.items(), key=lambda kv: kv[1], reverse=True)
        return [
            SearchResult(
                id=_id,
                score=float(_score),
                payload=payload_map.get(_id, {}),
            )
            for _id, _score in ranked[: request.top_k]
        ]

    async def get(
        self, collection: str, ids: list[str | int]
    ) -> list[VectorRecord]:
        idset = {str(i) for i in ids}
        return [r for r in self._recs[collection] if str(r.id) in idset]
