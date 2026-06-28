"""FastAPI 应用入口。

使用 create_app 工厂模式便于：
- 测试时创建独立 app 实例
- 多环境装配（如关闭某些中间件）
- 未来多 Worker / 蓝绿部署

启动流程：
1. 初始化日志
2. 缓存 settings 至 app.state
3. 启动时建立 Milvus 连接（失败进入降级模式，仅健康检查受影响）
4. 关闭时断开 Milvus 连接
"""
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from study_vector.api.exception_handlers import register_exception_handlers
from study_vector.api.v1 import (
    alias,
    collections,
    databases,
    health,
    hybrid_search,
    indexes,
    partitions,
    query,
    users,
    vectors,
)
from study_vector.core.logging import setup_logging
from study_vector.core.settings import Settings, get_settings
from study_vector.infra.milvus.client import async_close, async_connect


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """应用生命周期：启动 / 关闭钩子。"""
    setup_logging()
    settings = get_settings()
    app.state.settings = settings
    logger.info(
        f"启动 study_vector app={settings.app_name} v{settings.app_version} "
        f"env={settings.app_env}"
    )
    # 启动时建立 Milvus 连接（失败不阻塞 API 启动，进入降级模式）
    try:
        await async_connect()
    except Exception as e:  # noqa: BLE001
        logger.exception(f"启动时连接 Milvus 失败，进入降级模式：{e}")
    yield
    # 关闭时断开 Milvus 连接
    try:
        await async_close()
    except Exception:  # noqa: BLE001
        logger.exception("关闭 Milvus 连接失败（忽略）")


class ContractComplianceMiddleware:
    """纯 ASGI 中间件：补 ``Allow`` 头（405）与 ``Content-Type`` 头（缺省时）。

    为什么不用 ``BaseHTTPMiddleware``：
    - 对 405 / 304 / streaming 响应，``BaseHTTPMiddleware`` 在某些 Starlette
      版本上有 race condition 或直接不触发。
    - 纯 ASGI 中间件对所有响应（成功 / 4xx / 5xx / 异常路径）都生效。

    行为：
    1. 405 响应补 ``Allow`` 头（RFC 9110 §15.5.6）—— schemathesis 强制
    2. 任何响应若无 ``Content-Type`` 但有 body，补 ``application/json; charset=utf-8``
    3. 缺失的 ``content-length`` 也按 body 长度补上
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # 拦截 start：补 headers
        async def _send(message: Message) -> None:
            if message["type"] == "http.response.start":
                # 修改 message["headers"]：补 Allow / Content-Type
                raw = list(message.get("headers", []))
                new_headers = _augment_headers(
                    status=message["status"],
                    raw_headers=raw,
                    path=path,
                )
                message["headers"] = new_headers
            await send(message)

        await self.app(scope, receive, _send)


def _augment_headers(  # type: ignore[no-untyped-def]
    status: int, raw_headers: list[tuple[bytes, bytes]], path: str
) -> list[tuple[bytes, bytes]]:
    """在 start 消息发出前，补缺的头。返回新 headers 列表。"""
    lname_to_idx: dict[str, int] = {}
    for i, (n, _v) in enumerate(raw_headers):
        lname_to_idx[n.decode("latin-1").lower()] = i
    new_headers = list(raw_headers)

    def _set(name: bytes, value: bytes) -> None:
        lname = name.decode("latin-1").lower()
        if lname in lname_to_idx:
            new_headers[lname_to_idx[lname]] = (name, value)
        else:
            new_headers.append((name, value))
            lname_to_idx[lname] = len(new_headers) - 1

    # 405 补 Allow
    if status == 405 and "allow" not in lname_to_idx:
        allowed = _get_allowed_methods_from_path(path)
        if allowed:
            _set(b"allow", ", ".join(sorted(allowed)).encode("latin-1"))

    return new_headers


# 路由表缓存：app 创建后扫描一次
# 格式：path_format → {methods}
# 含 ``{param}`` 的 path_format 不展开，只在查找时用正则匹配
# 包含 FastAPI 顶层 Route + 嵌套 _IncludedRouter（router）里的 Route
_ALLOWED_METHODS_CACHE: list[tuple[str, set[str]]] = []  # [(path_format, {methods})]


def _build_allowed_methods_cache(app) -> None:  # type: ignore[no-untyped-def]
    """扫描 app 路由，构建 (path_format, {methods}) 列表。

    FastAPI 把 ``include_router`` 后的路由包成 ``_IncludedRouter``，其结构：
    - ``_IncludedRouter.include_context.prefix`` = include_router 时的 prefix（如 ``/api/v1``）
    - ``_IncludedRouter.original_router.prefix`` = router 自己定义时的 prefix（如 ``/health``）
    - ``_IncludedRouter.original_router.routes[].path`` = 已经包含 router_prefix 的完整子路径（如 ``/health`` 或 ``/health/ready``）

    完整 path = include_prefix + sub_route.path（不需要再加 router_prefix）
    """
    global _ALLOWED_METHODS_CACHE
    cache: list[tuple[str, set[str]]] = []
    for route in getattr(app, "routes", []):
        cls_name = type(route).__name__
        if cls_name == "_IncludedRouter":
            include_ctx = getattr(route, "include_context", None)
            include_prefix = getattr(include_ctx, "prefix", "") or ""
            orig = getattr(route, "original_router", None)
            sub_routes = getattr(orig, "routes", []) if orig is not None else []
            for sub_route in sub_routes:
                methods = getattr(sub_route, "methods", None)
                path_format = getattr(sub_route, "path", None)
                # path_format 可能是 ""（router 根路径），不能直接用 truthy 判断
                if not methods or path_format is None:
                    continue
                full_path = include_prefix + path_format
                ms = {m.upper() for m in methods if m not in {"HEAD"}}
                cache.append((full_path, ms))
            continue
        # 顶层 Route（如 /openapi.json, /docs）
        methods = getattr(route, "methods", None)
        path_format = getattr(route, "path", None)
        if not methods or path_format is None:
            continue
        ms = {m.upper() for m in methods if m not in {"HEAD"}}
        cache.append((path_format, ms))
    _ALLOWED_METHODS_CACHE = cache


def _get_allowed_methods_from_path(request_path: str) -> set[str]:
    """从缓存里找 path 匹配的路由，返回 {methods}。"""
    import re

    allowed: set[str] = set()
    for path_format, methods in _ALLOWED_METHODS_CACHE:
        if path_format == request_path:
            allowed.update(methods)
        elif "{" in path_format:
            # 参数化路径：用 regex 匹配
            pattern = re.sub(r"\{[^}]+\}", r"[^/]+", path_format)
            if re.fullmatch(pattern, request_path):
                allowed.update(methods)
    return allowed


def create_app() -> FastAPI:
    """工厂函数：构造并配置 FastAPI 应用。"""
    settings = get_settings()
    app = FastAPI(
        title="study_vector API",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        default_response_class=JSONResponse,
        # OpenAPI 文档元数据
        description=(
            "study_vector：向量数据库学习平台 API。\n\n"
            "- 多语言后端：当前为 Python（FastAPI），未来支持 Go / Node\n"
            "- 多向量库：通过 Repository 协议切换 Milvus / Chroma / Qdrant 等\n"
            "- 统一响应：`{code, message, data}`，code=0 为成功"
        ),
    )
    # 全局异常处理
    register_exception_handlers(app)
    # 契约合规中间件（405 Allow 头 / Content-Type 头）—— 必须最先注册，
    # 这样它在最外层，能包住所有响应（包括 405 / 路由层异常）。
    app.add_middleware(ContractComplianceMiddleware)
    # CORS：开发态允许前端 dev server / 生产态 nginx 通过同源反代
    # 生产部署时前端与 API 同源（nginx 反代），CORS 不必放开；
    # 此处仍配置为开发态便利（前端可用绝对 URL 调 API）。
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # 路由聚合
    app.include_router(health.router, prefix="/api/v1")
    app.include_router(collections.router, prefix="/api/v1")
    app.include_router(vectors.router, prefix="/api/v1")
    app.include_router(indexes.router, prefix="/api/v1")
    app.include_router(partitions.router, prefix="/api/v1")
    app.include_router(alias.router, prefix="/api/v1")
    app.include_router(query.router, prefix="/api/v1")
    app.include_router(hybrid_search.router, prefix="/api/v1")
    app.include_router(databases.router, prefix="/api/v1")
    app.include_router(users.router, prefix="/api/v1")
    # 路由注册完后，建一次 Allow 头缓存
    _build_allowed_methods_cache(app)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings: Settings = get_settings()
    uvicorn.run(
        "study_vector.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
