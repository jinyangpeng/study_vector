"""内存版 Repository 替身：仅测试用。

实现 `VectorRepository` 协议的全部方法，
使用朴素 cosine 计算相似度，验证业务层逻辑。
"""
from __future__ import annotations

import math
from typing import Any

from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    SearchRequest,
    SearchResult,
    VectorRecord,
)
from study_vector.repositories.base import VectorRepository


class FakeVectorRepository(VectorRepository):
    """基于内存 dict + list 的极简实现。"""

    def __init__(self) -> None:
        self._cols: dict[str, dict[str, Any]] = {}
        self._recs: dict[str, list[VectorRecord]] = {}

    async def connect(self) -> None:
        pass

    async def close(self) -> None:
        pass

    async def healthcheck(self) -> bool:
        return True

    async def create_collection(self, schema: CollectionSchema) -> None:
        self._cols[schema.name] = schema.model_dump()
        self._recs.setdefault(schema.name, [])

    async def drop_collection(self, name: str) -> None:
        self._cols.pop(name, None)
        self._recs.pop(name, None)

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
            row_count=len(self._recs[name]),
        )

    async def insert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        self._recs[collection].extend(records)
        return [str(r.id) for r in records]

    async def upsert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        return await self.insert(collection, records)

    async def delete(self, collection: str, ids: list[str | int]) -> int:
        idset = {str(i) for i in ids}
        before = len(self._recs[collection])
        self._recs[collection] = [
            r for r in self._recs[collection] if str(r.id) not in idset
        ]
        return before - len(self._recs[collection])

    async def search(self, request: SearchRequest) -> list[SearchResult]:
        recs = self._recs[request.collection]

        def cos(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b, strict=False))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb + 1e-12)

        scored = [(cos(request.vector, r.vector), r) for r in recs]
        scored.sort(key=lambda x: x[0], reverse=True)
        # 过滤：只支持 ==，与 Milvus 实现保持一致
        if request.filter_expr:
            scored = [
                (s, r)
                for s, r in scored
                if all(r.payload.get(k) == v for k, v in request.filter_expr.items())
            ]
        return [
            SearchResult(id=r.id, score=round(s, 6), payload=r.payload)
            for s, r in scored[: request.top_k]
        ]

    async def get(
        self, collection: str, ids: list[str | int]
    ) -> list[VectorRecord]:
        idset = {str(i) for i in ids}
        return [r for r in self._recs[collection] if str(r.id) in idset]
