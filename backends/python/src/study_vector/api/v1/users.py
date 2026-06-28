"""用户管理 API（Milvus RBAC 教学辅助）。

端点：
- GET    /api/v1/users      列出用户
- POST   /api/v1/users      创建用户
- DELETE /api/v1/users/{name}  删除用户

教学点：
- Milvus 2.4+ 完整支持 RBAC：用户 / 角色 / 权限
- 本平台做的是教学辅助：仅暴露最基础的用户管理
- 完整的角色 / 权限 API 留给 V1.x
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import CreateUserRequest
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", summary="列出用户")
async def list_users(
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    items = await repo.list_users()
    return ok([u.model_dump(mode="json") for u in items])


@router.post("", summary="创建用户")
async def create_user(
    body: CreateUserRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    user = await repo.create_user(body.user_name, body.password)
    return ok(user.model_dump(mode="json"))


@router.delete("/{user_name}", summary="删除用户")
async def drop_user(
    user_name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    await repo.drop_user(user_name)
    return ok({"user_name": user_name})
