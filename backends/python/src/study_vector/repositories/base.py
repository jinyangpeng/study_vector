"""向量库 Repository 协议定义。

业务层只依赖此协议，不依赖任何具体向量库 SDK。
任何向量库只需提供 `VectorRepository` 的实现即可无缝接入。

使用 `Protocol` + `runtime_checkable` 以支持结构化子类型（鸭子类型），
无需显式继承即可被 FastAPI Depends 注入。
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    SearchRequest,
    SearchResult,
    VectorRecord,
)


@runtime_checkable
class VectorRepository(Protocol):
    """向量库统一接口。

    所有方法均为 async，与 FastAPI 异步生态保持一致。
    同步 SDK 在实现层用 `asyncio.to_thread` 包装。
    """

    # ----- 连接生命周期 -----
    async def connect(self) -> None:
        """建立与向量库的连接。"""
        ...

    async def close(self) -> None:
        """关闭连接。"""
        ...

    async def healthcheck(self) -> bool:
        """健康检查。"""
        ...

    # ----- 集合管理 -----
    async def create_collection(self, schema: CollectionSchema) -> None:
        """创建集合。集合已存在时应保持幂等（不抛异常）。"""
        ...

    async def drop_collection(self, name: str) -> None:
        """删除集合。集合不存在时保持幂等。"""
        ...

    async def has_collection(self, name: str) -> bool:
        """判断集合是否存在。"""
        ...

    async def list_collections(self) -> list[str]:
        """列出全部集合名称。"""
        ...

    async def get_collection_info(self, name: str) -> CollectionInfo:
        """获取集合元信息。"""
        ...

    # ----- 向量写入 -----
    async def insert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        """批量插入向量，返回所有主键。"""
        ...

    async def upsert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        """存在则更新否则插入，返回所有主键。"""
        ...

    async def delete(self, collection: str, ids: list[str | int]) -> int:
        """按主键删除，返回删除条数。"""
        ...

    # ----- 向量检索 -----
    async def search(self, request: SearchRequest) -> list[SearchResult]:
        """向量相似度检索。"""
        ...

    async def get(
        self, collection: str, ids: list[str | int]
    ) -> list[VectorRecord]:
        """按主键拉取完整记录。"""
        ...
