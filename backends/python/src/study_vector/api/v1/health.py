"""健康检查端点：用于 K8s / Docker 的探针。

提供：
- /health        liveness probe（应用进程是否存活）
- /health/ready  readiness probe（依赖服务是否就绪，含 Milvus 健康）
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from study_vector.dependencies import get_vector_repository
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="存活探针")
async def liveness() -> dict:
    """存活探针：进程在就跑。

    不检查任何依赖（避免级联失败）。K8s 用它决定是否重启 Pod。
    """
    return {"code": 0, "message": "ok", "data": {"status": "ok"}}


@router.get("/ready", summary="就绪探针（含 Milvus 健康）")
async def readiness(
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    """就绪探针：含 Milvus 健康状态。

    教学点：
    - 与 liveness 不同，readiness 用于决定是否把流量分过来
    - Milvus 暂时不可用时返回 200 + degraded，前端会显示"降级模式"
    - Milvus 完全无法连通时返回 503，让 K8s 把流量切走
    """
    milvus_ok = await repo.healthcheck()
    if not milvus_ok:
        # Milvus 不可用 → 503；前端在 K8s 中会把流量切到其他 Pod
        return {
            "code": 503,
            "message": "milvus down",
            "data": {
                "status": "not_ready",
                "checks": {"milvus": "down"},
            },
        }
    return {
        "code": 0,
        "message": "ready",
        "data": {
            "status": "ready",
            "checks": {"milvus": "ok"},
        },
    }
