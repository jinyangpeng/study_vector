"""基于 OpenAPI 契约的自动化测试（schemathesis 4.x）。

设计目标：
- **单一事实源**：测试用例从 contracts/openapi.yaml 派生，不手写
- **后端真实**（vs fake）：跑的是真 FastAPI app，但 Milvus 用 FakeRepo 替换
- **覆盖范围**：每次运行都遍历 OpenAPI 里所有 path × method × payload 组合
- **回归保护**：任何端点改了 schema，契约测试会立刻发现

策略：
- **黑名单**用反向 exclude：默认测 OpenAPI 所有端点；只 exclude 尚未实现的
- 端点实现一个，从 NOT_IMPLEMENTED 删一个
- **状态隔离**：每次 case 跑前重置 fake_repo（module-level app 是共享的）

## 用法
```bash
uv run pytest tests/contract -v
```

## schemathesis + in-process ASGI 的坑
schemathesis 4.x 的 ``RequestsTransport`` 把 ``session`` 当 ``requests.Session``
使用，会调 ``session.request(method, url, **kwargs)``（kwargs 里有 ``verify``
/ ``cert`` 等 requests 风格参数）。

直接 in-process 走 httpx + ASGITransport 有两个拦路虎：

1. httpx 0.28 的 ``Client``（同步）调 ``transport.handle_request``，
   但 ``ASGITransport`` 只提供 ``handle_async_request``，sync 路径不通。
2. schemathesis 还会读/写 ``session.headers``、``session.auth``、设
   ``session.max_redirects``，需要 adapter 满足这些接口。

解决方案：模块级起一个 uvicorn 服务器在后台线程（127.0.0.1:随机空闲端口），
:class:`ASGISessionAdapter` 继承 ``requests.Session``，把请求剥掉
httpx 不认识的参数后转给 ``httpx.Client``，后者发到 127.0.0.1。
这样既满足 schemathesis 的 requests.Session 约定，又零侵入业务代码。
"""
from __future__ import annotations

import socket
import threading
from pathlib import Path

import requests
import schemathesis
import uvicorn
import yaml
from hypothesis import HealthCheck, settings
from schemathesis import openapi as schemathesis_openapi
from tests.integration._fake_repo import FakeVectorRepository

from study_vector.dependencies import get_vector_repository
from study_vector.main import create_app

# ──────────── 加载 OpenAPI spec（module-level，parametrize 阶段需要） ────────────
# __file__ = backends/python/tests/contract/test_openapi_compliance.py
# parents[0] = contract/, [1] = tests/, [2] = python/, [3] = backends/, [4] = REPO_ROOT
REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACTS_FILE = REPO_ROOT / "contracts" / "openapi.yaml"


def _load_spec() -> dict:
    with open(CONTRACTS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ──────────── 尚未实现的端点黑名单 ────────────
# 端点实现后，从这里删掉对应行
# 格式：(path, method)
# Phase 1.3-1.9 全部实现后，这里是空的
NOT_IMPLEMENTED: list[tuple[str, str]] = []


# ──────────── 找空闲端口 ────────────
def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ──────────── 后台 uvicorn 服务器 ────────────
class _BackgroundUvicorn:
    """在后台线程跑一个 uvicorn.Server，供 contract test 走真实 HTTP。"""

    def __init__(self, app, *, host: str = "127.0.0.1", port: int) -> None:
        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="warning",
            lifespan="off",  # 测试里手工管依赖覆盖，不要 lifespan 试图连 Milvus
            access_log=False,
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self.base_url = f"http://{host}:{port}"

    def start(self) -> None:
        self._thread.start()
        # 等服务器就绪（最长 5 秒）
        for _ in range(50):
            if self._server.started:
                return
            import time

            time.sleep(0.1)
        raise RuntimeError("uvicorn 启动超时")

    def stop(self) -> None:
        self._server.should_exit = True
        self._thread.join(timeout=5)


# ──────────── ASGI 适配层 ────────────
# schemathesis 期望一个 requests.Session 风格的 session 对象；
# 我们继承 requests.Session，只重写 request 方法，剥掉 requests-only 参数后走 httpx。
class ASGISessionAdapter(requests.Session):
    """``requests.Session`` 子类，把请求转发到本地 uvicorn。

    - 读/写 ``session.headers``：用 ``requests.Session`` 原生行为
    - 读/写 ``session.auth`` / ``session.max_redirects``：用原生属性
    - 调 ``session.request(method, url, **kwargs)``：剥掉 requests 风格
      参数（``verify`` / ``cert`` / ``trust_env`` / ``proxies``），
      转给 ``httpx.Client`` 发出

    返回 :class:`requests.Response`，满足 schemathesis 后续处理。
    """

    # requests 风格、httpx 不支持的 kwargs
    _DROP_KWARGS = frozenset({"verify", "cert", "trust_env", "proxies"})

    def __init__(self, base_url: str) -> None:  # type: ignore[no-untyped-def]
        super().__init__()
        from httpx import Client

        self._client = Client(base_url=base_url, timeout=10.0)
        self.headers: dict[str, str] = {}  # schemathesis 会读/写
        # 标记，避免 schemathesis 走 ``if close_session`` 分支
        self._asgi_session = True

    def request(  # type: ignore[override]
        self,
        method: str,
        url: str,
        params=None,  # type: ignore[no-untyped-def]
        data=None,  # type: ignore[no-untyped-def]
        headers=None,  # type: ignore[no-untyped-def]
        cookies=None,  # type: ignore[no-untyped-def]
        files=None,  # type: ignore[no-untyped-def]
        auth=None,  # type: ignore[no-untyped-def]
        timeout=None,  # type: ignore[no-untyped-def]
        allow_redirects: bool = True,
        json=None,  # type: ignore[no-untyped-def]
        **kwargs,  # type: ignore[no-untyped-def]
    ) -> requests.Response:
        """剥掉 requests-only kwargs，转给 httpx，再包成 ``Response``。"""
        for k in self._DROP_KWARGS:
            kwargs.pop(k, None)

        httpx_resp = self._client.request(
            method=method,
            url=url,
            params=params,
            data=data,
            headers=headers,
            cookies=cookies,
            files=files,
            timeout=timeout,
            follow_redirects=allow_redirects,
            json=json,
            **kwargs,
        )
        return _to_requests_response(httpx_resp, request_url=str(httpx_resp.url), method=method)

    def close(self) -> None:  # type: ignore[override]
        try:
            self._client.close()
        finally:
            super().close()


def _to_requests_response(httpx_resp, *, request_url: str, method: str) -> requests.Response:  # type: ignore[no-untyped-def]
    """把 :class:`httpx.Response` 包装成 :class:`requests.Response`。

    schemathesis 后续会读 ``.status_code`` / ``.headers`` / ``.content`` /
    ``.text`` / ``.json()``，还会通过 ``response.request.method`` 拿到请求方法。
    关键陷阱：schemathesis 内部走 :func:`Response.from_requests`，会读
    ``response.raw.headers.getlist(name)`` —— ``raw`` 不能是 None，
    且 ``headers`` 必须支持 ``.getlist(name)``（urllib3 HTTPHeaderDict 接口），
    否则 Allow / Content-Type 都被丢成空。
    这里用 :class:`urllib3.HTTPHeaderDict` 替身把 headers 暴露出去。
    """
    from requests import PreparedRequest
    from urllib3 import HTTPHeaderDict

    resp = requests.Response()
    resp.status_code = httpx_resp.status_code
    resp.headers.update({k: v for k, v in httpx_resp.headers.items()})
    resp._content = httpx_resp.content
    resp.url = request_url
    resp.encoding = httpx_resp.encoding or "utf-8"

    # schemathesis 通过 response.request.method 判定请求方法
    prepped = PreparedRequest()
    prepped.method = method
    prepped.url = request_url
    prepped.headers = dict(httpx_resp.request.headers) if httpx_resp.request else {}
    resp.request = prepped

    # 最小 raw 替身：必须支持 .headers.getlist(name) + .version
    # 用 HTTPHeaderDict：和 urllib3 接口一致
    raw_headers = HTTPHeaderDict()
    for k, v in httpx_resp.headers.items():
        raw_headers.add(k, v)
    # NOTE: requests.Response 的 .raw 是 property，对应 ._raw 是另一个 slot；
    # 设 .raw 才能让 schemathesis 读到 .raw.headers
    resp.raw = _FakeRaw(raw_headers, version=11)  # type: ignore[assignment]
    return resp


class _FakeRaw:
    """``urllib3.HTTPResponse`` 替身：schemathesis 只用 ``.headers`` 和 ``.version``。

    ``.headers`` 必须是 :class:`urllib3.HTTPHeaderDict`（支持 ``getlist``）。
    """

    def __init__(self, headers, *, version: int = 11) -> None:  # type: ignore[no-untyped-def]
        self.headers = headers
        self.version = version


# ──────────── 构造 module-level app + fake_repo + uvicorn ────────────
# 必须 module-level 因为 @schema.parametrize() 在 import 时展开
_fake_repo = FakeVectorRepository()
_app = create_app()
_app.dependency_overrides[get_vector_repository] = lambda: _fake_repo

_port = _find_free_port()
_server = _BackgroundUvicorn(_app, port=_port)
_server.start()


# ──────────── 构造 schemathesis schema ────────────
# 用 from_dict：自己读 spec，case 跑时传 transport
schema = schemathesis_openapi.from_dict(_load_spec())

# 应用黑名单
for path, method in NOT_IMPLEMENTED:
    schema = schema.exclude(path=path, method=method.lower())


# ──────────── 状态隔离：每个 case 跑前重置 fake_repo ────────────
@schemathesis.hook
def before_call(context, case, **kwargs) -> None:  # type: ignore[no-untyped-def]
    """每个 case 跑前重置 fake repo 状态（避免状态污染）。

    全局 hook（必须 global scope，不能在 schema scope 注册）。
    """
    _fake_repo._cols.clear()  # type: ignore[attr-defined]
    _fake_repo._recs.clear()  # type: ignore[attr-defined]


# ──────────── 契约测试主用例 ────────────
@schema.parametrize()  # type: ignore[misc]
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[
        HealthCheck.function_scoped_fixture,
        HealthCheck.too_slow,
        # schemathesis 4.x 在 strict-mode 下对带 additionalProperties: false
        # + 嵌套 enum / object 的 schema 容易触发 filter_too_much；
        # 这是 hypothesis 的健康检查，不是 schema 本身的 bug。
        HealthCheck.filter_too_much,
    ],
)
def test_api_matches_openapi(case):
    """对 OpenAPI 派生的每个 case，验证响应符合契约。

    schemathesis 4.x 需要 ``requests.Session`` 风格的 session；
    :class:`ASGISessionAdapter` 把请求剥掉 requests-only kwargs 后通过
    httpx 转到本地 uvicorn。
    """
    session = ASGISessionAdapter(_server.base_url)
    try:
        case.call_and_validate(session=session)
    finally:
        session.close()
