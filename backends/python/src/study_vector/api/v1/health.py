"""健康检查端点：用于 K8s / Docker 的探针。

提供：
- /health：liveness probe（应用进程是否存活）
- /health/ready：readiness probe（依赖服务是否就绪，阶段 2 后接 Milvus）
"""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="存活探针")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="就绪探针")
async def readiness() -> dict[str, str]:
    # TODO（阶段 2）：调用 Milvus healthcheck 后返回真实状态
    return {"status": "ready"}
