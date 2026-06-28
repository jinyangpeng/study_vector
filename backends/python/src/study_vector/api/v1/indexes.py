"""索引管理 API。

端点：
- GET    /api/v1/collections/{name}/indexes           列出索引
- POST   /api/v1/collections/{name}/indexes           建索引
- DELETE /api/v1/collections/{name}/indexes/{field}   删索引
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import CreateIndexRequest
from study_vector.exceptions import CollectionNotFoundError
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/collections", tags=["indexes"])


@router.get("/{name}/indexes", summary="列出索引")
async def list_indexes(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    items = await repo.list_indexes(name)
    return ok([i.model_dump(mode="json") for i in items])


@router.post("/{name}/indexes", summary="建索引")
async def create_index(
    name: str = Path(..., min_length=1),
    body: CreateIndexRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.create_index(name, body)
    return ok(
        {
            "name": name,
            "field_name": body.field_name,
            "index_type": body.index_type.value,
        }
    )


@router.delete(
    "/{name}/indexes/{field_name}", summary="删除指定字段的索引"
)
async def drop_index(
    name: str = Path(..., min_length=1),
    field_name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.drop_index(name, field_name)
    return ok({"name": name, "field_name": field_name})
