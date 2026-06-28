"""混合检索（Hybrid Search）API。

端点：
- POST /api/v1/vectors/{collection}/hybrid_search

教学点：
- 真实生产场景下，常常 dense（语义）+ sparse（关键词）联合检索
- 各自走自己的 ANN 索引；后用 RRF（Reciprocal Rank Fusion）合并排序
- 公式：score(d) = Σ_routes [ weight / (k + rank) ]
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import HybridSearchRequest
from study_vector.exceptions import CollectionNotFoundError
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/vectors", tags=["search"])


@router.post(
    "/{collection}/hybrid_search", summary="混合检索（dense+sparse+RRF）"
)
async def hybrid_search(
    collection: str = Path(..., min_length=1),
    body: HybridSearchRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(collection):
        raise CollectionNotFoundError(f"集合不存在 name={collection}")
    body.collection = collection
    results = await repo.hybrid_search(body)
    return ok([r.model_dump(mode="json") for r in results])
