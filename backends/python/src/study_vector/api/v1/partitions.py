"""分区（Partition）管理 API。

端点：
- GET    /api/v1/collections/{name}/partitions          列出分区
- POST   /api/v1/collections/{name}/partitions          创建分区
- DELETE /api/v1/collections/{name}/partitions/{part}   删除分区

教学点：
- 分区是集合内的物理隔离单位（按时间 / 业务维度切分）
- 检索时配 `partition_names` 限定扫描范围
- 加载时配 `partition_names` 节省内存
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import CreatePartitionRequest
from study_vector.exceptions import CollectionNotFoundError
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/collections", tags=["partitions"])


@router.get("/{name}/partitions", summary="列出分区")
async def list_partitions(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    items = await repo.list_partitions(name)
    return ok([p.model_dump(mode="json") for p in items])


@router.post("/{name}/partitions", summary="创建分区")
async def create_partition(
    name: str = Path(..., min_length=1),
    body: CreatePartitionRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.create_partition(name, body)
    return ok({"name": name, "partition": body.name})


@router.delete(
    "/{name}/partitions/{partition}", summary="删除分区"
)
async def drop_partition(
    name: str = Path(..., min_length=1),
    partition: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.drop_partition(name, partition)
    return ok({"name": name, "partition": partition})
