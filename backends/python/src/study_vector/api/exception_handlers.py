"""全局异常处理：捕获所有未处理异常，转为统一响应格式。

注册的处理器（按优先级从高到低）：
1. StudyVectorError：业务异常，按 code/http_status 返回
2. MilvusException：Milvus SDK 错误，统一 502
3. RequestValidationError：参数校验错误，422
4. HTTPException（含 400 body 解析失败 / 405 / 404）：按 FastAPI 内置语义返回 + 补 Allow 头
5. Exception：兜底，500

业务错误码全部为整数（与 OpenAPI 契约一致）。
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from starlette.exceptions import HTTPException as StarletteHTTPException

# 尝试导入 Milvus 异常类型，pymilvus 可能不可用时降级
try:
    from pymilvus import MilvusException  # type: ignore
except ImportError:  # pragma: no cover
    MilvusException = None  # type: ignore

from study_vector.exceptions import (
    ERR_INTERNAL_ERROR,
    ERR_VALIDATION_ERROR,
    ERR_VECTOR_BACKEND_ERROR,
    StudyVectorError,
)


def _error_response(code: int, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": None},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StudyVectorError)
    async def handle_business(request: Request, exc: StudyVectorError):  # type: ignore[unused-ignore]
        logger.warning(f"业务异常 code={exc.code} msg={exc}")
        return _error_response(int(exc.code), str(exc), int(exc.http_status))

    if MilvusException is not None:
        @app.exception_handler(MilvusException)
        async def handle_milvus(request: Request, exc: MilvusException):
            logger.exception("Milvus 错误")
            return _error_response(ERR_VECTOR_BACKEND_ERROR, str(exc), 502)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        # 把校验错误结构化到 message 中便于前端排查
        return _error_response(
            ERR_VALIDATION_ERROR,
            "参数校验失败: " + str(jsonable_encoder(exc.errors())),
            422,
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_exception(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """把 FastAPI/Starlette 抛出的 HTTPException 也转成统一格式。

        典型场景：body 解析失败时 FastAPI 抛 ``HTTPException(400, "There was an error parsing the body")``，
        默认响应是 ``{"detail": "..."}``，与契约 ``{code, message, data}`` 不一致。
        这里把所有 HTTPException 都转成契约格式，业务码用 ``http_status * 100 + 0``。
        """
        # 业务码：与 ERR_VALIDATION_ERROR 一致地编码
        code = exc.status_code * 100
        # detail 可能是字符串或 list/dict；统一转字符串便于 message 字段
        detail = exc.detail
        if isinstance(detail, (list, dict)):
            message = f"HTTP {exc.status_code}: {jsonable_encoder(detail)}"
        else:
            message = f"HTTP {exc.status_code}: {detail}"
        return _error_response(code, message, exc.status_code)

    @app.exception_handler(Exception)
    async def handle_unknown(request: Request, exc: Exception):
        logger.exception("未捕获异常")
        return _error_response(ERR_INTERNAL_ERROR, "服务器内部错误", 500)
