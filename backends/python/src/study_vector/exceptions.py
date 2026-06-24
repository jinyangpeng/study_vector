"""自定义业务异常。

所有业务异常应继承 `StudyVectorError`，
并定义 `code`（业务错误码）与 `http_status`（HTTP 状态码）。
由全局异常处理器统一转为统一响应格式。
"""
from __future__ import annotations


class StudyVectorError(Exception):
    """业务异常基类。"""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message or self.__class__.__doc__ or self.code)
        if code:
            self.code = code


class CollectionNotFoundError(StudyVectorError):
    """集合不存在。"""

    code = "COLLECTION_NOT_FOUND"
    http_status = 404


class CollectionAlreadyExistsError(StudyVectorError):
    """集合已存在（创建时强制要求不存在时使用）。"""

    code = "COLLECTION_ALREADY_EXISTS"
    http_status = 409


class VectorDimensionError(StudyVectorError):
    """向量维度不匹配。"""

    code = "VECTOR_DIMENSION_MISMATCH"
    http_status = 422


class VectorBackendError(StudyVectorError):
    """向量库后端错误（连接失败、SDK 异常等）。"""

    code = "VECTOR_BACKEND_ERROR"
    http_status = 502
