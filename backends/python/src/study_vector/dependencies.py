"""FastAPI 依赖注入：按配置返回具体 Repository。

业务层只通过 `get_vector_repository` 拿到 Repository 协议实例，
不直接依赖 Milvus，便于未来切换 / 扩展。
"""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from study_vector.core.settings import Settings, get_settings
from study_vector.infra.milvus import MilvusRepository
from study_vector.repositories.base import VectorRepository

# 未来扩展点：新增向量库时在此注册
_BUILDERS: dict[str, callable] = {
    "milvus": lambda: MilvusRepository(),
    # "chroma": lambda: ChromaRepository(),
    # "qdrant": lambda: QdrantRepository(),
    # "weaviate": lambda: WeaviateRepository(),
}


@lru_cache
def _build_repository(backend: str) -> VectorRepository:
    """根据 backend 类型构造 Repository 实例（单例缓存）。"""
    if backend not in _BUILDERS:
        raise ValueError(
            f"不支持的向量库 backend={backend}，"
            f"可选：{sorted(_BUILDERS.keys())}"
        )
    return _BUILDERS[backend]()


def get_vector_repository(
    settings: Settings = Depends(get_settings),
) -> VectorRepository:
    """FastAPI 依赖：返回当前配置的 Repository。

    首期固定为 milvus；后续可在 Settings 中增加
    `vector_backend` 字段并改写此处。
    """
    # TODO：改为 settings.vector_backend 默认 "milvus"
    return _build_repository("milvus")
