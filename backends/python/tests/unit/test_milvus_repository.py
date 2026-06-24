"""Milvus Repository 单元测试。

注意：只测纯函数（如过滤表达式构建），不连接真实 Milvus。
真实环境测试参见 `tests/integration/` 下的 testcontainers 套件。
"""
from __future__ import annotations

import pytest

from study_vector.infra.milvus.repository import MilvusRepository


def test_build_filter_expr_none():
    """空过滤应返回 None。"""
    assert MilvusRepository._build_filter_expr(None) is None
    assert MilvusRepository._build_filter_expr({}) is None


def test_build_filter_expr_string():
    """字符串值应被引号包裹。"""
    out = MilvusRepository._build_filter_expr({"tag": "x"})
    assert out == 'payload["tag"] == "x"'


def test_build_filter_expr_bool():
    """布尔值应用小写字面量。"""
    out = MilvusRepository._build_filter_expr({"active": True, "tag": "a"})
    assert 'payload["active"] == true' in out
    assert 'payload["tag"] == "a"' in out
    assert " and " in out


def test_build_filter_expr_numbers():
    """数值保持原样。"""
    out = MilvusRepository._build_filter_expr({"count": 3, "ratio": 0.5})
    assert 'payload["count"] == 3' in out
    assert 'payload["ratio"] == 0.5' in out


def test_build_filter_expr_unsupported_value():
    """不支持的值类型应抛 ValueError。"""
    with pytest.raises(ValueError, match="过滤值类型不支持"):
        MilvusRepository._build_filter_expr({"tags": ["a", "b"]})
