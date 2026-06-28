"""数据库（DB）管理 API。

端点：
- GET    /api/v1/databases   列出数据库
- POST   /api/v1/databases   创建数据库
- DELETE /api/v1/databases/{name}  删除数据库

教学点：
- Milvus 支持多数据库隔离；类似 MySQL 的"database"
- 默认连接到 `default` db；要切到其它 db，需在 Settings 配置
  `MILVUS_DB_NAME=xxx` 重启服务（或未来支持多连接）
- 不同 db 之间的集合名独立
"""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import CreateDatabaseRequest
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/databases", tags=["databases"])


@router.get("", summary="列出数据库")
async def list_databases(
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    return ok(await repo.list_databases())


@router.post("", summary="创建数据库")
async def create_database(
    body: CreateDatabaseRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    await repo.create_database(body.name)
    return ok({"name": body.name})


@router.delete("/{name}", summary="删除数据库")
async def drop_database(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    await repo.drop_database(name)
    return ok({"name": name})
