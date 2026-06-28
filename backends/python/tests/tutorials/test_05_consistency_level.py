"""Milvus 核心概念 #5：一致性等级（Consistency Level）。

教学目标：
- 理解"一致性"= 写入后多久能读到
- Milvus 提供 4 个等级（CAP 三角取舍）：

  | 等级 | 一致性 | 延迟 | 适用场景 |
  |---|---|---|---|
  | **Strong** | 强（读必见最新写） | 高 | 金融/订单 |
  | **Session** | 单会话内一致 | 中 | **默认**，通用 |
  | **Bounded** | 时间窗内一致 | 较低 | 推荐/容忍旧数据 |
  | **Eventually** | 最终一致 | 最低 | 离线分析/聚合 |

- **不可变**：集合创建时设定，运行时不能改
- 这是 **CAP** 在 Milvus 中的体现：C（一致性）vs A（可用性）vs P（分区容忍）
  - Milvus 选 AP（牺牲 C 换取可用性与扩展性），但通过 4 档等级让用户调节
"""
from __future__ import annotations

import pytest

from study_vector.domain.models import ConsistencyLevel

# ──────────── 5.1 四种等级都可创建 ────────────


@pytest.mark.parametrize(
    "level,scenario",
    [
        (ConsistencyLevel.STRONG, "强一致：金融/订单，读必见最新写"),
        (ConsistencyLevel.SESSION, "默认：单会话内一致，通用业务"),
        (ConsistencyLevel.BOUNDED, "有界：容忍短时间旧数据，推荐系统"),
        (ConsistencyLevel.EVENTUALLY, "最终一致：延迟最低，离线分析"),
    ],
)
def test_5_1_create_with_each_level(helper, level, scenario):
    """4 种一致性等级都能在创建集合时设置。"""
    helper.create_collection(
        f"cl_{level.value.lower()}",
        dimension=4,
        consistency_level=level,
    )

    info = helper.get_collection(f"cl_{level.value.lower()}")
    assert info["consistency_level"] == level.value


# ──────────── 5.2 默认 Session ────────────


def test_5_2_default_is_session(helper):
    """不指定 consistency_level → 默认 Session。"""
    helper.create_collection("default_cl")
    info = helper.get_collection("default_cl")
    assert info["consistency_level"] == "Session"


# ──────────── 5.3 不可变：创建后改不动 ────────────


def test_5_3_consistency_level_immutable(helper):
    """一致性等级在 Milvus 中不可改；本测试验证"再创建一个同名集合会失败"。

    教学：想换等级只能 drop 后重建（会丢数据），所以选对等级很关键。
    """
    helper.create_collection("immutable_cl", consistency_level=ConsistencyLevel.STRONG)
    info = helper.get_collection("immutable_cl")
    assert info["consistency_level"] == "Strong"

    # 同名集合已存在 → 409

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + "_immutable_cl",
            "dimension": 4,
            "consistency_level": "Eventually",
        },
    )
    assert r.status_code == 409


# ──────────── 5.4 4 档可同时存在（不同集合可不同等级） ────────────


def test_5_4_different_collections_can_have_different_levels(helper):
    """不同集合可设不同一致性等级，独立生效。"""
    for level in ConsistencyLevel:
        helper.create_collection(
            f"multi_{level.value.lower()}", consistency_level=level
        )

    for level in ConsistencyLevel:
        info = helper.get_collection(f"multi_{level.value.lower()}")
        assert info["consistency_level"] == level.value


# ──────────── 5.5 强 vs 最终一致：CAP 演示 ────────────


def test_5_5_cap_tradeoff_demo(helper):
    """演示 CAP 三角：Strong（高 C）与 Eventually（高 A）的取舍。

    教学：fake repo 总是强一致（单进程），但等级已记录到元数据；
    真实 Milvus 中：
    - Strong 写入后立即可读（最慢）
    - Eventually 写入后可能短暂读不到（最快）
    """
    helper.create_collection("cap_strong", consistency_level=ConsistencyLevel.STRONG)
    helper.create_collection(
        "cap_eventually", consistency_level=ConsistencyLevel.EVENTUALLY
    )

    # 都立刻可查
    s = helper.get_collection("cap_strong")
    e = helper.get_collection("cap_eventually")
    assert s["consistency_level"] == "Strong"
    assert e["consistency_level"] == "Eventually"

    # 写入数据（强 vs 最终 在 fake 中表现一致）
    helper.insert(
        "cap_strong",
        [
            {"id": "v1", "vector": [0.1, 0.2, 0.3, 0.4]},
        ],
    )
    helper.insert(
        "cap_eventually",
        [
            {"id": "v1", "vector": [0.1, 0.2, 0.3, 0.4]},
        ],
    )

    # 两个集合都能查出来
    s_results = helper.search("cap_strong", vector=[0.1, 0.2, 0.3, 0.4], top_k=1)
    e_results = helper.search(
        "cap_eventually", vector=[0.1, 0.2, 0.3, 0.4], top_k=1
    )
    assert len(s_results) == 1
    assert len(e_results) == 1


# ──────────── 5.6 非法值 422 ────────────


def test_5_6_invalid_consistency_level_returns_422(helper):
    """非法等级名 → 参数校验失败 422。"""

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + "_bad_cl",
            "dimension": 4,
            "consistency_level": "InvalidLevel",
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] != 0
    assert "consistency_level" in str(body["message"])


# ──────────── 5.7 默认等级写入后立即可读（Session 语义） ────────────


def test_5_7_session_visibility_default(helper):
    """Session 是默认等级；写入后立即可在 search 看到（fake 总是一致）。"""
    helper.create_collection("session_vis", dimension=4)  # 默认 Session

    helper.insert(
        "session_vis",
        [
            {"id": "v1", "vector": [0.1, 0.2, 0.3, 0.4]},
        ],
    )

    results = helper.search("session_vis", vector=[0.1, 0.2, 0.3, 0.4], top_k=1)
    assert len(results) == 1
    assert results[0]["id"] == "v1"

    info = helper.get_collection("session_vis")
    assert info["consistency_level"] == "Session"
    assert info["row_count"] == 1
