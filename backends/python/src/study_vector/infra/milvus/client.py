"""Milvus 客户端单例管理。

设计目标：
- 进程内单例，避免请求级反复创建连接（Milvus 推荐复用连接）
- 线程安全
- connect/close 幂等
- 与 pymilvus 同步 API 协同（FastAPI 端 async，但实际工作在后台线程中执行）
"""
from __future__ import annotations

import asyncio
import threading

from loguru import logger
from pymilvus import MilvusException, connections

from study_vector.core.settings import get_settings


class MilvusClientFactory:
    """线程安全的 Milvus 客户端工厂（单例）。"""

    _instance: MilvusClientFactory | None = None
    _lock = threading.Lock()
    _connected = False
    _conn_lock = threading.Lock()  # 串行化 connect/close 避免竞态

    def __new__(cls) -> MilvusClientFactory:
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def _connect_sync(self) -> None:
        settings = get_settings()
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=str(settings.milvus_port),
            user=settings.milvus_user,
            password=settings.milvus_password,
            db_name=settings.milvus_db_name,
            secure=settings.milvus_secure,
        )
        logger.info(
            f"已连接 Milvus host={settings.milvus_host} "
            f"port={settings.milvus_port} db={settings.milvus_db_name}"
        )

    def _disconnect_sync(self) -> None:
        try:
            connections.disconnect(alias="default")
            logger.info("已断开 Milvus 连接")
        except MilvusException:
            logger.exception("断开 Milvus 失败（忽略）")

    def connect(self) -> None:
        """同步建立连接（幂等）。"""
        with self._conn_lock:
            if self._connected:
                return
            self._connect_sync()
            self._connected = True

    def close(self) -> None:
        """同步关闭连接（幂等）。"""
        with self._conn_lock:
            if not self._connected:
                return
            self._disconnect_sync()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected


# 全局辅助函数
_factory_singleton: MilvusClientFactory | None = None


def get_milvus_factory() -> MilvusClientFactory:
    """获取 Milvus 客户端工厂单例。"""
    global _factory_singleton
    if _factory_singleton is None:
        _factory_singleton = MilvusClientFactory()
    return _factory_singleton


async def async_connect() -> None:
    """异步包装：在默认 executor 中执行同步 connect。"""
    await asyncio.to_thread(get_milvus_factory().connect)


async def async_close() -> None:
    """异步包装：关闭连接。"""
    await asyncio.to_thread(get_milvus_factory().close)
