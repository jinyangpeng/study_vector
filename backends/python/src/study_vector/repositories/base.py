"""向量库 Repository 协议定义。

业务层只依赖此协议，不依赖任何具体向量库 SDK。
任何向量库只需提供 `VectorRepository` 的实现即可无缝接入。

使用 `Protocol` + `runtime_checkable` 以支持结构化子类型（鸭子类型），
无需显式继承即可被 FastAPI Depends 注入。

方法分组（按教学功能划分）：
- 生命周期：connect / close / healthcheck
- 集合管理：create / drop / list / has / get_info
- 集合内存：load / release
- 索引：create_index / list_indexes / drop_index
- 分区：create_partition / list_partitions / drop_partition
- Alias：create_alias / list_aliases / drop_alias
- 数据库：list_databases / create_database / drop_database
- 用户（RBAC）：list_users / create_user / drop_user
- 数据：insert / upsert / delete / get
- 检索：search / query / hybrid_search
"""
from __future__ import annotations

from typing import Protocol, runtime_checkable

from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    CreateIndexRequest,
    CreatePartitionRequest,
    HybridSearchRequest,
    IndexInfo,
    LoadRequest,
    PartitionInfo,
    QueryRequest,
    SearchRequest,
    SearchResult,
    UserInfo,
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

    # ----- 集合内存（load / release） -----
    async def load_collection(
        self, name: str, request: LoadRequest | None = None
    ) -> None:
        """把集合索引加载到查询节点内存。"""
        ...

    async def release_collection(self, name: str) -> None:
        """从内存卸载集合。"""
        ...

    async def is_loaded(self, name: str) -> bool:
        """判断集合是否已加载。"""
        ...

    # ----- 索引 -----
    async def create_index(
        self, name: str, request: CreateIndexRequest
    ) -> None:
        """为指定字段建索引。"""
        ...

    async def list_indexes(self, name: str) -> list[IndexInfo]:
        """列出集合所有索引。"""
        ...

    async def drop_index(self, name: str, field_name: str) -> None:
        """删除指定字段的索引。"""
        ...

    # ----- 分区 -----
    async def create_partition(
        self, name: str, request: CreatePartitionRequest
    ) -> None:
        """创建分区。"""
        ...

    async def list_partitions(self, name: str) -> list[PartitionInfo]:
        """列出集合所有分区。"""
        ...

    async def drop_partition(self, name: str, partition: str) -> None:
        """删除指定分区。"""
        ...

    # ----- Alias -----
    async def create_alias(self, name: str, alias: str) -> None:
        """给集合绑定 alias。"""
        ...

    async def list_aliases(self, name: str) -> list[str]:
        """列出集合的所有 alias。"""
        ...

    async def drop_alias(self, name: str, alias: str) -> None:
        """解绑 alias。"""
        ...

    # ----- 数据库 -----
    async def list_databases(self) -> list[str]:
        """列出所有数据库。"""
        ...

    async def create_database(self, name: str) -> None:
        """创建数据库。"""
        ...

    async def drop_database(self, name: str) -> None:
        """删除数据库。"""
        ...

    # ----- 用户（RBAC 教学辅助） -----
    async def list_users(self) -> list[UserInfo]:
        """列出所有用户。"""
        ...

    async def create_user(self, user_name: str, password: str) -> UserInfo:
        """创建用户。"""
        ...

    async def drop_user(self, user_name: str) -> None:
        """删除用户。"""
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

    # ----- 检索 -----
    async def search(self, request: SearchRequest) -> list[SearchResult]:
        """向量相似度检索。"""
        ...

    async def query(
        self, collection: str, request: QueryRequest
    ) -> list[VectorRecord] | int:
        """标量检索或 count(*)。返回 list 时是数据；返回 int 时是计数。"""
        ...

    async def hybrid_search(
        self, request: HybridSearchRequest
    ) -> list[SearchResult]:
        """混合检索：dense + sparse + RRF 重排。"""
        ...

    async def get(
        self, collection: str, ids: list[str | int]
    ) -> list[VectorRecord]:
        """按主键拉取完整记录。"""
        ...
