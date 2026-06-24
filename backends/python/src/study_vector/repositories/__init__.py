"""Repository 协议层入口。

业务层只依赖此包暴露的 `VectorRepository` 协议；
具体实现位于 `study_vector.infra.*`。
"""
from study_vector.repositories.base import VectorRepository

__all__ = ["VectorRepository"]
