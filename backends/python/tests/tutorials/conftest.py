"""Tutorials 公共 fixtures 与 helpers。

设计：
- 启动后台 uvicorn（fake repo 后端）—— 复用 contract test 的 ``_BackgroundUvicorn``
- 暴露 ``api_client`` fixture（httpx 客户端）和 ``base_url``（base URL）
- 状态隔离：每个 test 用唯一 collection 前缀，避免相互污染
- ``TutorialHelper`` 提供 seed / run / verify 三步式辅助
"""
from __future__ import annotations

import socket
import threading
import time
import uuid
from collections.abc import Iterator
from typing import Any

import httpx
import pytest
import uvicorn

from study_vector.dependencies import get_vector_repository
from study_vector.main import create_app
from tests.integration._fake_repo import FakeVectorRepository

# ──────────── 后台 uvicorn（与 contract test 共享设计） ────────────


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _BackgroundUvicorn:
    """在后台线程跑一个 uvicorn.Server，供 tutorial 走真实 HTTP。"""

    def __init__(self, app, *, host: str = "127.0.0.1", port: int) -> None:
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="warning",
            lifespan="off",  # tutorial 跑 fake repo，不要 lifespan 试图连 Milvus
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self.base_url = f"http://{host}:{port}"

    def start(self) -> None:
        self._thread.start()
        for _ in range(50):
            if self._server.started:
                return
            time.sleep(0.1)
        raise RuntimeError("uvicorn 启动超时")

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5)


# ──────────── module-level 共享 app + server ────────────
# 注意：与 contract test 不同，tutorials 需要在每个 test 间**重置 fake repo 状态**
# 所以 fake_repo + app 都是 module-level（避免重复启动），但每次 test 通过
# ``_reset_fake_repo()`` 显式清空。

_fake_repo = FakeVectorRepository()
_app = create_app()
_app.dependency_overrides[get_vector_repository] = lambda: _fake_repo

_port = _find_free_port()
_server = _BackgroundUvicorn(_app, port=_port)
_server.start()


def _reset_fake_repo() -> None:
    """每个 test 前清空 fake repo 状态。"""
    _fake_repo._cols.clear()  # type: ignore[attr-defined]
    _fake_repo._recs.clear()  # type: ignore[attr-defined]
    _fake_repo._indexes.clear()  # type: ignore[attr-defined]
    _fake_repo._partitions.clear()  # type: ignore[attr-defined]
    _fake_repo._aliases.clear()  # type: ignore[attr-defined]
    _fake_repo._loaded.clear()  # type: ignore[attr-defined]
    _fake_repo._dbs = ["default"]  # type: ignore[attr-defined]
    _fake_repo._users.clear()  # type: ignore[attr-defined]


# ──────────── Fixtures ────────────


@pytest.fixture(scope="session")
def base_url() -> str:
    """Tutorial API base URL。"""
    return _server.base_url


@pytest.fixture
def api_client(base_url: str) -> Iterator[httpx.Client]:
    """HTTP 客户端 + 自动重置 fake repo。"""
    _reset_fake_repo()
    with httpx.Client(base_url=base_url, timeout=10.0) as client:
        yield client


@pytest.fixture
def unique_name() -> str:
    """生成唯一 collection 名前缀（避免 tutorial 之间的 state 污染）。"""
    return f"t_{uuid.uuid4().hex[:8]}"


# ──────────── TutorialHelper ────────────


class TutorialHelper:
    """三步式 helper：seed → run → verify。

    用法：
    >>> helper = TutorialHelper(api_client, unique_name)
    >>> helper.create_collection("demo", dimension=4, metric="COSINE")
    >>> helper.insert("demo", records=[...])
    >>> helper.search("demo", vector=[...], top_k=3)
    """

    def __init__(self, client: httpx.Client, prefix: str) -> None:
        self.client = client
        self.prefix = prefix

    # ---------- 集合 ----------

    def create_collection(
        self,
        name: str,
        *,
        dimension: int = 4,
        metric: str = "COSINE",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """创建集合。返回 ApiResponse.data。"""
        body = {
            "name": f"{self.prefix}_{name}",
            "dimension": dimension,
            "metric": metric,
            **kwargs,
        }
        r = self.client.post("/api/v1/collections", json=body)
        r.raise_for_status()
        return r.json()["data"]

    def get_collection(self, name: str) -> dict[str, Any]:
        """获取集合信息。"""
        r = self.client.get(f"/api/v1/collections/{self.prefix}_{name}")
        r.raise_for_status()
        return r.json()["data"]

    def list_collections(self) -> list[str]:
        r = self.client.get("/api/v1/collections")
        r.raise_for_status()
        return r.json()["data"]

    def drop_collection(self, name: str) -> None:
        self.client.delete(f"/api/v1/collections/{self.prefix}_{name}").raise_for_status()

    # ---------- 向量 ----------

    def insert(self, name: str, records: list[dict[str, Any]]) -> list[str]:
        r = self.client.post(
            f"/api/v1/vectors/{self.prefix}_{name}/insert", json=records
        )
        r.raise_for_status()
        return r.json()["data"]["ids"]

    def upsert(self, name: str, records: list[dict[str, Any]]) -> list[str]:
        r = self.client.post(
            f"/api/v1/vectors/{self.prefix}_{name}/upsert", json=records
        )
        r.raise_for_status()
        return r.json()["data"]["ids"]

    def delete(self, name: str, ids: list[str]) -> int:
        r = self.client.post(
            f"/api/v1/vectors/{self.prefix}_{name}/delete", json={"ids": ids}
        )
        r.raise_for_status()
        return r.json()["data"].get("count", 0)

    def get(self, name: str, ids: list[str]) -> list[dict[str, Any]]:
        r = self.client.post(
            f"/api/v1/vectors/{self.prefix}_{name}/get", json={"ids": ids}
        )
        r.raise_for_status()
        return r.json()["data"]

    # ---------- 检索 ----------

    def search(
        self, name: str, vector: list[float], top_k: int = 10, **kwargs: Any
    ) -> list[dict[str, Any]]:
        body = {"vector": vector, "top_k": top_k, **kwargs}
        r = self.client.post(
            f"/api/v1/vectors/{self.prefix}_{name}/search", json=body
        )
        r.raise_for_status()
        return r.json()["data"]

    def query(self, name: str, **kwargs: Any) -> list[dict[str, Any]] | int:
        r = self.client.post(
            f"/api/v1/vectors/{self.prefix}_{name}/query", json=kwargs
        )
        r.raise_for_status()
        return r.json()["data"]

    def hybrid_search(
        self,
        name: str,
        *,
        dense: list[float] | None = None,
        dense_weight: float = 1.0,
        sparse: dict[str, float] | None = None,
        sparse_weight: float = 1.0,
        top_k: int = 10,
        rrf_k: int = 60,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """混合检索：dense + sparse + RRF。"""
        body = {
            "dense": dense,
            "dense_weight": dense_weight,
            "sparse": sparse,
            "sparse_weight": sparse_weight,
            "top_k": top_k,
            "rrf_k": rrf_k,
            **kwargs,
        }
        # 去掉 None 值，避免 422
        body = {k: v for k, v in body.items() if v is not None}
        r = self.client.post(
            f"/api/v1/vectors/{self.prefix}_{name}/hybrid_search", json=body
        )
        r.raise_for_status()
        return r.json()["data"]

    # ---------- 索引 ----------

    def create_index(self, name: str, **kwargs: Any) -> None:
        r = self.client.post(
            f"/api/v1/collections/{self.prefix}_{name}/indexes", json=kwargs
        )
        r.raise_for_status()

    def list_indexes(self, name: str) -> list[dict[str, Any]]:
        r = self.client.get(f"/api/v1/collections/{self.prefix}_{name}/indexes")
        r.raise_for_status()
        return r.json()["data"]

    def drop_index(self, name: str, field_name: str) -> None:
        r = self.client.delete(
            f"/api/v1/collections/{self.prefix}_{name}/indexes/{field_name}"
        )
        r.raise_for_status()

    # ---------- 分区 ----------

    def create_partition(self, name: str, partition: str) -> None:
        r = self.client.post(
            f"/api/v1/collections/{self.prefix}_{name}/partitions",
            json={"name": partition},
        )
        r.raise_for_status()

    def list_partitions(self, name: str) -> list[dict[str, Any]]:
        r = self.client.get(f"/api/v1/collections/{self.prefix}_{name}/partitions")
        r.raise_for_status()
        return r.json()["data"]

    def drop_partition(self, name: str, partition: str) -> None:
        r = self.client.delete(
            f"/api/v1/collections/{self.prefix}_{name}/partitions/{partition}"
        )
        r.raise_for_status()

    # ---------- Alias ----------

    def create_alias(self, name: str, alias: str) -> None:
        r = self.client.post(
            f"/api/v1/collections/{self.prefix}_{name}/alias", json={"alias": alias}
        )
        r.raise_for_status()

    def list_aliases(self, name: str) -> list[str]:
        r = self.client.get(f"/api/v1/collections/{self.prefix}_{name}/alias")
        r.raise_for_status()
        return r.json()["data"]

    def drop_alias(self, name: str, alias: str) -> None:
        r = self.client.delete(
            f"/api/v1/collections/{self.prefix}_{name}/alias/{alias}"
        )
        r.raise_for_status()

    def reassign_alias(self, from_name: str, to_name: str, alias: str) -> None:
        """零停机切换：把 alias 从 from 集合迁到 to 集合。

        业务流程：
        1. drop alias from old collection
        2. create alias on new collection
        （真实 Milvus 提供 alterAlias 原子操作）
        """
        self.drop_alias(from_name, alias)
        self.create_alias(to_name, alias)


@pytest.fixture
def helper(api_client: httpx.Client, unique_name: str) -> TutorialHelper:
    """三步式 helper fixture。"""
    return TutorialHelper(api_client, unique_name)
