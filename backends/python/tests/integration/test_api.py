"""API 集成测试。

使用 `FakeVectorRepository` 替换真实 Milvus，验证：
1. create -> insert -> search 完整流程
2. 错误码（404 / 422）正确返回
3. Repository 协议依赖注入可被覆盖
"""
from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from study_vector.dependencies import get_vector_repository
from study_vector.main import create_app
from tests.integration._fake_repo import FakeVectorRepository


@pytest.fixture
def fake_repo() -> FakeVectorRepository:
    return FakeVectorRepository()


@pytest.fixture
async def client(fake_repo: FakeVectorRepository):
    """构造测试用 ASGI 客户端，并把 Repository 依赖覆盖为 fake。"""
    app = create_app()
    app.dependency_overrides[get_vector_repository] = lambda: fake_repo
    # 关闭 lifespan 中连接 Milvus 的尝试
    app.router.lifespan_context = None  # type: ignore[assignment]
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c


@pytest.mark.asyncio
async def test_health(client: AsyncClient):
    r = await client.get("/api/v1/health")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_create_and_search_flow(client: AsyncClient):
    # 1) 创建集合
    r = await client.post(
        "/api/v1/collections",
        json={"name": "demo", "dimension": 4, "metric": "COSINE"},
    )
    assert r.status_code == 200
    assert r.json()["code"] == 0

    # 2) 列出
    r = await client.get("/api/v1/collections")
    assert r.json()["data"] == ["demo"]

    # 3) 详情
    r = await client.get("/api/v1/collections/demo")
    info = r.json()["data"]
    assert info["name"] == "demo"
    assert info["dimension"] == 4

    # 4) 插入
    r = await client.post(
        "/api/v1/vectors/demo/insert",
        json=[
            {"id": "a", "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"tag": "x"}},
            {"id": "b", "vector": [0.2, 0.1, 0.4, 0.3], "payload": {"tag": "y"}},
        ],
    )
    assert r.status_code == 200
    assert r.json()["data"]["count"] == 2

    # 5) 检索：最相似应该是 a
    r = await client.post(
        "/api/v1/vectors/demo/search",
        json={"collection": "demo", "vector": [0.1, 0.2, 0.3, 0.4], "top_k": 2},
    )
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]) == 2
    assert body["data"][0]["id"] == "a"
    assert body["data"][0]["score"] > body["data"][1]["score"]

    # 6) 过滤检索
    r = await client.post(
        "/api/v1/vectors/demo/search",
        json={
            "collection": "demo",
            "vector": [0.1, 0.2, 0.3, 0.4],
            "top_k": 5,
            "filter_expr": {"tag": "y"},
        },
    )
    body = r.json()
    assert len(body["data"]) == 1
    assert body["data"][0]["id"] == "b"

    # 7) get
    r = await client.post(
        "/api/v1/vectors/demo/get", json={"ids": ["a"]}
    )
    body = r.json()
    assert body["data"][0]["id"] == "a"
    assert body["data"][0]["payload"] == {"tag": "x"}

    # 8) delete
    r = await client.post(
        "/api/v1/vectors/demo/delete", json={"ids": ["a"]}
    )
    assert r.json()["data"]["deleted"] == 1


@pytest.mark.asyncio
async def test_collection_not_found_returns_404(client: AsyncClient):
    r = await client.get("/api/v1/collections/missing")
    assert r.status_code == 404
    body = r.json()
    assert body["code"] == 1404
    assert "missing" in body["message"]


@pytest.mark.asyncio
async def test_validation_error_returns_422(client: AsyncClient):
    # dimension 必须为正整数
    r = await client.post(
        "/api/v1/collections",
        json={"name": "bad", "dimension": 0, "metric": "COSINE"},
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] == 1422


@pytest.mark.asyncio
async def test_drop_collection(client: AsyncClient):
    await client.post(
        "/api/v1/collections",
        json={"name": "tmp", "dimension": 8, "metric": "L2"},
    )
    r = await client.delete("/api/v1/collections/tmp")
    assert r.json()["code"] == 0
    r = await client.get("/api/v1/collections")
    assert "tmp" not in r.json()["data"]
