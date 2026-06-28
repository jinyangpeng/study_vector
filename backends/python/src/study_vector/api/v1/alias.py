"""Alias 管理 API。

端点：
- POST   /api/v1/collections/{name}/alias            给集合绑定 alias
- GET    /api/v1/collections/{name}/alias            列出集合的 alias
- DELETE /api/v1/collections/{name}/alias/{alias}    解绑 alias

教学点：
- 一个集合可以有多个 alias；一个 alias 只能指向一个集合
- 用于零停机切换：建新集合 → 写双写 → alias 切换 → 删旧集合
- 业务上 alias 是访问入口；用 alias 而不是集合名访问 → 平滑升级
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import CreateAliasRequest
from study_vector.exceptions import AliasAlreadyExistsError, CollectionNotFoundError
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/collections", tags=["alias"])


@router.get("/{name}/alias", summary="列出集合的 alias")
async def list_aliases(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    items = await repo.list_aliases(name)
    return ok(items)


@router.post("/{name}/alias", summary="给集合绑定 alias")
async def create_alias(
    name: str = Path(..., min_length=1),
    body: CreateAliasRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    try:
        await repo.create_alias(name, body.alias)
    except ValueError as e:
        # fake repo 抛 ValueError 表示 alias 冲突；翻译成业务异常
        raise AliasAlreadyExistsError(str(e)) from e
    return ok({"name": name, "alias": body.alias})


@router.delete("/{name}/alias/{alias}", summary="解绑 alias")
async def drop_alias(
    name: str = Path(..., min_length=1),
    alias: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    await repo.drop_alias(name, alias)
    return ok({"name": name, "alias": alias})
