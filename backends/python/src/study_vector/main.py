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
from loguru import logger

from study_vector.api.exception_handlers import register_exception_handlers
from study_vector.api.v1 import collections, health, vectors
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


def create_app() -> FastAPI:
    """工厂函数：构造并配置 FastAPI 应用。"""
    settings = get_settings()
    app = FastAPI(
        title="study_vector API",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
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
