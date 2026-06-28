"""集合（Collection）管理 API。

端点（V1 全部）：
- POST   /api/v1/collections              创建
- GET    /api/v1/collections              列出
- GET    /api/v1/collections/{name}       详情
- DELETE /api/v1/collections/{name}       删除
- POST   /api/v1/collections/{name}/load    加载到内存
- POST   /api/v1/collections/{name}/release 从内存释放
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import CollectionInfo, CollectionSchema, LoadRequest
from study_vector.exceptions import (
    CollectionAlreadyExistsError,
    CollectionNotFoundError,
)
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", summary="创建集合")
async def create_collection(
    schema: CollectionSchema,
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    # 业务：重复创建同名集合应 409（与 Milvus 原生行为一致）
    if await repo.has_collection(schema.name):
        raise CollectionAlreadyExistsError(
            f"集合已存在: {schema.name}"
        )
    await repo.create_collection(schema)
    return ok({"name": schema.name})


@router.get("", summary="列出所有集合")
async def list_collections(
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    names = await repo.list_collections()
    return ok(names)


@router.get("/{name}", summary="查看集合详情")
async def get_collection(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    info: CollectionInfo = await repo.get_collection_info(name)
    return ok(info.model_dump(mode="json"))


@router.delete("/{name}", summary="删除集合")
async def delete_collection(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.drop_collection(name)
    return ok({"name": name})


@router.post("/{name}/load", summary="加载集合到内存")
async def load_collection(
    name: str = Path(..., min_length=1),
    body: LoadRequest | None = Body(default=None),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.load_collection(name, body)
    loaded = await repo.is_loaded(name)
    return ok({"name": name, "loaded": loaded})


@router.post("/{name}/release", summary="从内存释放集合")
async def release_collection(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.release_collection(name)
    return ok({"name": name, "loaded": False})
