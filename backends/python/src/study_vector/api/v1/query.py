"""标量检索 / 计数 API。

端点：
- POST /api/v1/vectors/{collection}/query

两种用途：
1. 标量过滤：`{"filter": {"category": "news"}, "limit": 100}`
2. 计数：`{"filter": {}, "count_only": true}` → `data: 1024`

教学点：
- 不走向量相似度，只按标量条件查询
- `count_only=true` 走的是 Milvus 内置 row_count，比 query limit 大快很多
- 配合 `output_fields` 可指定返回字段
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import QueryRequest
from study_vector.exceptions import CollectionNotFoundError
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/vectors", tags=["search"])


@router.post("/{collection}/query", summary="标量检索 / 计数")
async def query_vectors(
    collection: str = Path(..., min_length=1),
    body: QueryRequest = Body(default_factory=QueryRequest),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(collection):
        raise CollectionNotFoundError(f"集合不存在 name={collection}")
    result = await repo.query(collection, body)
    if isinstance(result, int):
        return ok(result)
    return ok([r.model_dump(mode="json") for r in result])
