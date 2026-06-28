"""Milvus 核心概念 #7：分区策略（Partition Strategy）。

教学目标：
- 理解"分区"= 集合内的物理隔离单位
- 三大典型用法：
  1. **时间分区**（按年/季/月/日）：日志、事件、订单
  2. **租户分区**（按 tenant_id）：SaaS 多租户
  3. **类别分区**（按业务类别）：内容、商品
- 检索时配 ``partition_names`` 限定扫描范围 → **性能/成本优化**
- 默认 ``_default`` 分区永远存在（且不可删）
- 现代替代：``PartitionKey`` 自动按 hash 路由（不需手动建）

本节用 fake + payload._partition 模拟分区数据（真实 Milvus 需 insert 时指定 partition_name）。
"""
from __future__ import annotations

import pytest

# ──────────── 7.1 默认分区自动创建 ────────────


def test_7_1_default_partition_exists(helper):
    """新集合创建后必有 ``_default`` 分区。"""
    helper.create_collection("part_default")
    partitions = helper.list_partitions("part_default")
    names = [p["name"] for p in partitions]
    assert "_default" in names


# ──────────── 7.2 自定义分区（时间维度） ────────────


def test_7_2_create_time_partitions(helper):
    """时间维度分区：按季度切分（命名加 ``y`` 前缀以符合"字母开头"约束）。"""
    helper.create_collection("time_part")
    for q in ("y2024_q1", "y2024_q2", "y2024_q3", "y2024_q4"):
        helper.create_partition("time_part", q)

    parts = helper.list_partitions("time_part")
    names = {p["name"] for p in parts}
    assert names == {
        "_default",
        "y2024_q1",
        "y2024_q2",
        "y2024_q3",
        "y2024_q4",
    }


# ──────────── 7.3 租户分区（多租户场景） ────────────


def test_7_3_tenant_partitions(helper):
    """多租户 SaaS 场景：每租户一个分区（隔离 + 各自 load）。"""
    helper.create_collection("tenants")
    for tid in ("tenant_a", "tenant_b", "tenant_c"):
        helper.create_partition("tenants", tid)

    parts = helper.list_partitions("tenants")
    assert len(parts) == 4  # 3 租户 + _default


# ──────────── 7.4 重复创建同名分区（幂等） ────────────


def test_7_4_partition_idempotent(helper):
    """同名分区重复创建 → 第二次是 no-op（不应报错也不应重复添加）。"""
    helper.create_collection("idem_part")
    helper.create_partition("idem_part", "p1")
    helper.create_partition("idem_part", "p1")  # 第二次

    parts = helper.list_partitions("idem_part")
    p1_count = sum(1 for p in parts if p["name"] == "p1")
    assert p1_count == 1


# ──────────── 7.5 删除自定义分区 ────────────


def test_7_5_drop_custom_partition(helper):
    """可删自定义分区。"""
    helper.create_collection("drop_part")
    helper.create_partition("drop_part", "old_data")
    helper.create_partition("drop_part", "new_data")

    helper.drop_partition("drop_part", "old_data")

    names = {p["name"] for p in helper.list_partitions("drop_part")}
    assert "old_data" not in names
    assert "new_data" in names


# ──────────── 7.6 _default 分区不可删（保护） ────────────


def test_7_6_default_partition_protected(helper):
    """``_default`` 不能删（fake 实现：删除是 no-op）。"""
    helper.create_collection("protect_default")
    helper.create_partition("protect_default", "user_part")

    # 尝试删 _default（fake 静默忽略）
    helper.drop_partition("protect_default", "_default")

    # _default 仍在
    names = {p["name"] for p in helper.list_partitions("protect_default")}
    assert "_default" in names


# ──────────── 7.7 检索限定分区（性能优化） ────────────


def test_7_7_search_within_partition(helper):
    """``partition_names`` 限定扫描范围 → 只查该分区内的记录。

    教学：业务上常用此隔离租户 / 限定时间窗，避免全表扫描。
    """
    helper.create_collection("part_search")
    helper.create_partition("part_search", "y2024")
    helper.create_partition("part_search", "y2025")

    # 用 payload._partition 标记数据所属分区（fake 简化）
    helper.insert(
        "part_search",
        [
            {
                "id": "old1",
                "vector": [1.0, 0.0, 0.0, 0.0],
                "payload": {"_partition": "y2024"},
            },
            {
                "id": "old2",
                "vector": [0.9, 0.1, 0.0, 0.0],
                "payload": {"_partition": "y2024"},
            },
            {
                "id": "new1",
                "vector": [0.8, 0.2, 0.0, 0.0],
                "payload": {"_partition": "y2025"},
            },
        ],
    )

    # 限定 y2024 分区：应只返回 old1, old2
    r_2024 = helper.search(
        "part_search",
        vector=[1.0, 0.0, 0.0, 0.0],
        top_k=10,
        partition_names=["y2024"],
    )
    assert {r["id"] for r in r_2024} == {"old1", "old2"}

    # 限定 y2025 分区：应只返回 new1
    r_2025 = helper.search(
        "part_search",
        vector=[1.0, 0.0, 0.0, 0.0],
        top_k=10,
        partition_names=["y2025"],
    )
    assert {r["id"] for r in r_2025} == {"new1"}

    # 不指定分区 → 全部分区都查
    r_all = helper.search(
        "part_search", vector=[1.0, 0.0, 0.0, 0.0], top_k=10
    )
    assert {r["id"] for r in r_all} == {"old1", "old2", "new1"}


# ──────────── 7.8 限定多个分区（多租户批量） ────────────


def test_7_8_search_multi_partitions(helper):
    """partition_names 支持多值：union 查询多个分区。"""
    helper.create_collection("multi_p")
    for p in ("p1", "p2", "p3"):
        helper.create_partition("multi_p", p)

    helper.insert(
        "multi_p",
        [
            {"id": "a", "vector": [1.0, 0.0, 0.0, 0.0], "payload": {"_partition": "p1"}},
            {"id": "b", "vector": [0.9, 0.1, 0.0, 0.0], "payload": {"_partition": "p2"}},
            {"id": "c", "vector": [0.8, 0.2, 0.0, 0.0], "payload": {"_partition": "p3"}},
        ],
    )

    # 限定 p1 + p2（排除 p3）
    r = helper.search(
        "multi_p", vector=[1.0, 0.0, 0.0, 0.0], top_k=10, partition_names=["p1", "p2"]
    )
    assert {r["id"] for r in r} == {"a", "b"}


# ──────────── 7.9 不存在的分区 → 空结果 ────────────


def test_7_9_nonexistent_partition_returns_empty(helper):
    """查询不存在的分区 → 空结果（不抛错）。"""
    helper.create_collection("no_such_part")
    helper.insert("no_such_part", [{"id": "x", "vector": [0.1, 0.0, 0.0, 0.0]}])

    results = helper.search(
        "no_such_part",
        vector=[0.1, 0.0, 0.0, 0.0],
        top_k=10,
        partition_names=["ghost"],
    )
    assert results == []


# ──────────── 7.10 分区命名规范 ────────────


@pytest.mark.parametrize(
    "name",
    ["p1", "tenant_a", "y2024_q1", "q1_2024"],
)
def test_7_10_valid_partition_names(helper, name):
    """合法分区名：字母开头 + 字母数字下划线。"""
    helper.create_collection("valid_pn")
    helper.create_partition("valid_pn", name)
    parts = helper.list_partitions("valid_pn")
    assert name in {p["name"] for p in parts}


def test_7_11_invalid_partition_name_rejected(helper):
    """分区名以数字开头 → 422（契约约束）。"""

    helper.create_collection("bad_pn")
    r = helper.client.post(
        f"/api/v1/collections/{helper.prefix}_bad_pn/partitions",
        json={"name": "2024_q1"},  # 数字开头
    )
    assert r.status_code == 422
    body = r.json()
    assert "name" in str(body["message"]).lower() or "分区" in str(body["message"])
