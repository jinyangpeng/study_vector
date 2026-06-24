"""向量 CRUD 与检索 API。

- POST /api/v1/vectors/{collection}/insert
- POST /api/v1/vectors/{collection}/upsert
- POST /api/v1/vectors/{collection}/delete
- POST /api/v1/vectors/{collection}/get
- POST /api/v1/vectors/{collection}/search
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import SearchRequest, VectorRecord
from study_vector.exceptions import CollectionNotFoundError
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/vectors", tags=["vectors"])


@router.post("/{collection}/insert", summary="批量插入向量")
async def insert_vectors(
    collection: str = Path(..., min_length=1),
    records: list[VectorRecord] = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    ids = await repo.insert(collection, records)
    return ok({"ids": ids, "count": len(ids)})


@router.post("/{collection}/upsert", summary="存在则更新否则插入")
async def upsert_vectors(
    collection: str = Path(..., min_length=1),
    records: list[VectorRecord] = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    ids = await repo.upsert(collection, records)
    return ok({"ids": ids, "count": len(ids)})


@router.post("/{collection}/delete", summary="按 id 删除向量")
async def delete_vectors(
    collection: str = Path(..., min_length=1),
    ids: list[str] = Body(..., embed=True),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    deleted = await repo.delete(collection, ids)
    return ok({"deleted": deleted})


@router.post("/{collection}/get", summary="按 id 拉取向量")
async def get_vectors(
    collection: str = Path(..., min_length=1),
    ids: list[str] = Body(..., embed=True),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    records = await repo.get(collection, ids)
    return ok([r.model_dump(mode="json") for r in records])


@router.post("/{collection}/search", summary="向量相似度检索")
async def search_vectors(
    collection: str = Path(..., min_length=1),
    request: SearchRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    # 强制 collection 来自 path 而非 body，避免不一致
    request.collection = collection
    if not await repo.has_collection(collection):
        raise CollectionNotFoundError(f"集合不存在 name={collection}")
    results = await repo.search(request)
    return ok([r.model_dump(mode="json") for r in results])
