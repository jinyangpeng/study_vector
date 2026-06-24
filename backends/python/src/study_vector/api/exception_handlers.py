"""全局异常处理：捕获所有未处理异常，转为统一响应格式。

注册的处理器（按优先级从高到低）：
1. StudyVectorError：业务异常，按 code/http_status 返回
2. MilvusException：Milvus SDK 错误，统一 502
3. RequestValidationError：参数校验错误，422
4. Exception：兜底，500
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger

# 尝试导入 Milvus 异常类型，pymilvus 可能不可用时降级
try:
    from pymilvus import MilvusException  # type: ignore
except ImportError:  # pragma: no cover
    MilvusException = None  # type: ignore

from study_vector.exceptions import StudyVectorError


def _error_response(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": None},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StudyVectorError)
    async def handle_business(request: Request, exc: StudyVectorError):  # type: ignore[unused-ignore]
        logger.warning(f"业务异常 code={exc.code} msg={exc}")
        return _error_response(exc.code, str(exc), exc.http_status)

    if MilvusException is not None:
        @app.exception_handler(MilvusException)
        async def handle_milvus(request: Request, exc: MilvusException):
            logger.exception("Milvus 错误")
            return _error_response("VECTOR_BACKEND_ERROR", str(exc), 502)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        # 把校验错误结构化到 message 中便于前端排查
        return _error_response(
            "VALIDATION_ERROR",
            "参数校验失败: " + str(jsonable_encoder(exc.errors())),
            422,
        )

    @app.exception_handler(Exception)
    async def handle_unknown(request: Request, exc: Exception):
        logger.exception("未捕获异常")
        return _error_response("INTERNAL_ERROR", "服务器内部错误", 500)
