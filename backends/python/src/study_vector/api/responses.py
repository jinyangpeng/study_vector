"""统一响应封装。

约定格式：
{
    "code": 0,            # 0 表示成功；非 0 为业务错误码
    "message": "success", # 人类可读信息
    "data": <payload>     # 业务数据
}
"""
from __future__ import annotations

from typing import Any


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    """构造成功响应。"""
    return {"code": 0, "message": message, "data": data}


def fail(code: str, message: str, http_status: int = 400) -> dict[str, Any]:
    """构造失败响应（通常由异常处理器调用）。"""
    return {"code": code, "message": message, "data": None}
