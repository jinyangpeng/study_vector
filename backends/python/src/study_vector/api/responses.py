"""
约定格式：
{
    "code": 0,            # 0 表示成功；非 0 为业务错误码（与 HTTP 状态码正交）
    "message": "success", # 人类可读信息
    "data": <payload>     # 业务数据
}
"""
from __future__ import annotations

from typing import Any

# 业务错误码：与 OpenAPI 契约中的 ErrorCode enum 对齐
# 数字编码：HTTP 状态码 * 100 + 序号，便于一眼看出错误类别
ERR_COLLECTION_NOT_FOUND = 1404
ERR_COLLECTION_ALREADY_EXISTS = 1409
ERR_PARTITION_NOT_FOUND = 2404
ERR_INDEX_NOT_FOUND = 3404
ERR_VECTOR_DIMENSION_MISMATCH = 1422
ERR_VALIDATION_ERROR = 1422  # Pydantic 422
ERR_VECTOR_BACKEND_ERROR = 1502
ERR_INTERNAL_ERROR = 1500


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    """构造成功响应。"""
    return {"code": 0, "message": message, "data": data}


def fail(code: int, message: str, http_status: int = 400) -> dict[str, Any]:
    """构造失败响应（通常由异常处理器调用）。

    `code` 必须是整数（与 OpenAPI 契约一致），与 HTTP 状态码正交。
    """
    return {"code": code, "message": message, "data": None}
