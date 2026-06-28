"""自定义业务异常。

所有业务异常应继承 `StudyVectorError`，
并定义 `code`（业务错误码，整数，与 OpenAPI 契约的 ErrorCode 对齐）
与 `http_status`（HTTP 状态码）。
由全局异常处理器统一转为统一响应格式。
"""
from __future__ import annotations

# 业务错误码常量（与 study_vector.api.responses 同步）
ERR_COLLECTION_NOT_FOUND = 1404
ERR_COLLECTION_ALREADY_EXISTS = 1409
ERR_PARTITION_NOT_FOUND = 2404
ERR_INDEX_NOT_FOUND = 3404
ERR_ALIAS_ALREADY_EXISTS = 4409
ERR_VECTOR_DIMENSION_MISMATCH = 1422
ERR_VALIDATION_ERROR = 1422
ERR_VECTOR_BACKEND_ERROR = 1502
ERR_INTERNAL_ERROR = 1500


class StudyVectorError(Exception):
    """业务异常基类。"""

    code: int = ERR_INTERNAL_ERROR
    http_status: int = 500

    def __init__(self, message: str = "", *, code: int | None = None) -> None:
        super().__init__(message or self.__class__.__doc__ or "业务异常")
        if code is not None:
            self.code = code


class CollectionNotFoundError(StudyVectorError):
    """集合不存在。"""

    code = ERR_COLLECTION_NOT_FOUND
    http_status = 404


class CollectionAlreadyExistsError(StudyVectorError):
    """集合已存在（创建时强制要求不存在时使用）。"""

    code = ERR_COLLECTION_ALREADY_EXISTS
    http_status = 409


class PartitionNotFoundError(StudyVectorError):
    """分区不存在。"""

    code = ERR_PARTITION_NOT_FOUND
    http_status = 404


class IndexNotFoundError(StudyVectorError):
    """索引不存在。"""

    code = ERR_INDEX_NOT_FOUND
    http_status = 404


class AliasAlreadyExistsError(StudyVectorError):
    """Alias 已被其他集合占用（alias 全局唯一）。"""

    code = ERR_ALIAS_ALREADY_EXISTS
    http_status = 409


class VectorDimensionError(StudyVectorError):
    """向量维度不匹配。"""

    code = ERR_VECTOR_DIMENSION_MISMATCH
    http_status = 422


class VectorBackendError(StudyVectorError):
    """向量库后端错误（连接失败、SDK 异常等）。"""

    code = ERR_VECTOR_BACKEND_ERROR
    http_status = 502
