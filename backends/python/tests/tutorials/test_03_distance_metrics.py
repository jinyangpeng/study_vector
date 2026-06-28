"""Milvus 核心概念 #3：距离度量对比（COSINE / IP / L2）。

教学目标：
- 理解距离度量 = 决定"两个向量怎么算近"
- 三大主流度量：
  - **COSINE（余弦相似度）**：只看方向，不看大小；范围 [-1, 1]
    - 用法：文本/embedding（句子长短不一致时也公平）
  - **IP / Inner Product（内积）**：原始点积 `Σaᵢbᵢ`
    - 用法：归一化向量后等价于 COSINE；推荐系统原始打分
  - **L2 / Euclidean（欧氏距离）**：sqrt(Σ(aᵢ-bᵢ)²)，距离值越小越近
    - 用法：图像/坐标；score 通常转成 ``1/(1+dist)``（越大越相关）
- 选择度量是**工程决策**（不是数学决定）：
  - 文本语义 → COSINE（最常用）
  - 评分/排序 → IP
  - 坐标/物理距离 → L2

与索引的关系：
- 集合 metric 与索引 metric_type 必须一致（否则 Milvus 报 schema 不匹配）
- 本节用 fake repo：metric 存在 collection schema 中
"""
from __future__ import annotations

import pytest

# ──────────── 3.1 三种度量都可建集合 ────────────


@pytest.mark.parametrize(
    "metric,scenario",
    [
        ("COSINE", "文本 / embedding / 语义检索"),
        ("IP", "推荐系统 / 原始评分"),
        ("L2", "图像 / 坐标 / 物理距离"),
    ],
)
def test_3_1_create_collection_with_metric(helper, metric, scenario):
    """三种度量都能创建集合，并在 CollectionInfo 中正确反映。"""
    helper.create_collection(f"m_{metric}", metric=metric)

    info = helper.get_collection(f"m_{metric}")
    assert info["metric"] == metric
    assert info["name"].endswith(f"m_{metric}")


# ──────────── 3.2 几何含义：同数据不同度量 → 不同排序 ────────────


def test_3_2_cosine_vs_ip_on_normalized(helper):
    """归一化向量：COSINE 与 IP 排序完全一致，分值仅差一个常数缩放。"""
    helper.create_collection("norm_demo", metric="COSINE", dimension=3)
    # 全部是单位向量（已 L2 归一化）
    records = [
        {"id": "a", "vector": [1.0, 0.0, 0.0]},
        {"id": "b", "vector": [0.0, 1.0, 0.0]},
        {"id": "c", "vector": [0.7071, 0.7071, 0.0]},  # 45°，与 a cos=0.7071
    ]
    helper.insert("norm_demo", records)

    # 查 a
    results = helper.search("norm_demo", vector=[1.0, 0.0, 0.0], top_k=3)
    # 排序：a (1.0) > c (~0.7071) > b (0.0)
    assert [r["id"] for r in results] == ["a", "c", "b"]
    assert results[0]["score"] == pytest.approx(1.0, abs=1e-4)
    assert results[1]["score"] == pytest.approx(0.7071, abs=1e-3)
    assert results[2]["score"] == pytest.approx(0.0, abs=1e-4)


def test_3_3_cosine_is_scale_invariant(helper):
    """COSINE 不受向量缩放影响：``[1,0]`` 与 ``[10,0]`` 视为同方向。"""
    helper.create_collection("cos_scale", metric="COSINE", dimension=2)
    helper.insert(
        "cos_scale",
        [
            {"id": "unit", "vector": [1.0, 0.0]},
            {"id": "scaled", "vector": [10.0, 0.0]},  # 同方向，不同大小
        ],
    )

    results = helper.search("cos_scale", vector=[2.0, 0.0], top_k=2)
    # 两个应都得 1.0（COSINE 看方向）
    scores = {r["id"]: r["score"] for r in results}
    assert scores["unit"] == pytest.approx(1.0, abs=1e-4)
    assert scores["scaled"] == pytest.approx(1.0, abs=1e-4)


def test_3_4_ip_is_not_scale_invariant(helper):
    """IP 受缩放影响：``[10,0]`` 的 IP = ``[1,0]`` 的 10 倍。"""
    helper.create_collection("ip_scale", metric="IP", dimension=2)
    helper.insert(
        "ip_scale",
        [
            {"id": "unit", "vector": [1.0, 0.0]},
            {"id": "scaled", "vector": [10.0, 0.0]},
        ],
    )

    results = helper.search("ip_scale", vector=[1.0, 0.0], top_k=2)
    scores = {r["id"]: r["score"] for r in results}
    # IP：scaled = 10 * unit
    assert scores["scaled"] == pytest.approx(10.0, abs=1e-4)
    assert scores["unit"] == pytest.approx(1.0, abs=1e-4)


# ──────────── 3.5 L2 度量：距离越大分值越小 ────────────


def test_3_5_l2_zero_distance_gives_top_score(helper):
    """L2：相同向量距离 = 0，score = 1/(1+0) = 1。"""
    helper.create_collection("l2_zero", metric="L2", dimension=3)
    helper.insert(
        "l2_zero",
        [
            {"id": "near", "vector": [0.1, 0.1, 0.1]},
            {"id": "exact", "vector": [0.5, 0.5, 0.5]},  # 与查询完全一致
            {"id": "far", "vector": [1.0, 1.0, 1.0]},
        ],
    )

    results = helper.search("l2_zero", vector=[0.5, 0.5, 0.5], top_k=3)
    # exact 距离 0，score = 1.0；最近应是它
    assert results[0]["id"] == "exact"
    assert results[0]["score"] == pytest.approx(1.0, abs=1e-4)
    # 距离排序：exact < near < far
    assert results[1]["id"] == "near"
    assert results[2]["id"] == "far"
    # 分值单调递减
    assert results[0]["score"] > results[1]["score"] > results[2]["score"]


def test_3_6_l2_score_equals_reciprocal(helper):
    """L2 转换公式：``score = 1 / (1 + dist)``。"""
    helper.create_collection("l2_formula", metric="L2", dimension=2)
    helper.insert("l2_formula", [{"id": "x", "vector": [3.0, 4.0]}])

    # 查询 [0,0]：距离 = 5
    results = helper.search("l2_formula", vector=[0.0, 0.0], top_k=1)
    assert results[0]["score"] == pytest.approx(1.0 / 6.0, abs=1e-4)


# ──────────── 3.7 度量影响 top-1 ────────────


def test_3_7_metric_changes_top1(helper):
    """同一组向量，不同度量会得到不同的 top-1（说明选错度量 = 检索失败）。"""
    # 数据：a 在 (1,0)，b 在 (10,0)，c 在 (0,10)
    helper.create_collection("metric_diff", metric="COSINE", dimension=2)
    helper.insert(
        "metric_diff",
        [
            {"id": "a", "vector": [1.0, 0.0]},
            {"id": "b", "vector": [10.0, 0.0]},  # 与 a 同方向，模长更大
            {"id": "c", "vector": [0.0, 10.0]},  # 与 a 正交
        ],
    )

    # COSINE 看方向：a 和 b 一样近
    cos_results = helper.search("metric_diff", vector=[1.0, 0.0], top_k=3)
    assert cos_results[0]["score"] == cos_results[1]["score"]  # a == b
    assert cos_results[2]["id"] == "c"

    # IP 看大小：b 分数是 a 的 10 倍，b 应排第一
    helper.create_collection("metric_ip", metric="IP", dimension=2)
    helper.insert(
        "metric_ip",
        [
            {"id": "a", "vector": [1.0, 0.0]},
            {"id": "b", "vector": [10.0, 0.0]},
            {"id": "c", "vector": [0.0, 10.0]},
        ],
    )
    ip_results = helper.search("metric_ip", vector=[1.0, 0.0], top_k=3)
    assert ip_results[0]["id"] == "b"  # IP 下 b 赢
    assert ip_results[0]["score"] == pytest.approx(10.0, abs=1e-4)


# ──────────── 3.8 集合与索引的 metric 必须一致（业务约束演示） ────────────


@pytest.mark.parametrize("metric", ["COSINE", "IP", "L2"])
def test_3_8_index_metric_must_match_collection(helper, metric):
    """建索引时 metric_type 应与集合 metric 保持一致（Milvus 强约束）。"""
    helper.create_collection(f"match_{metric}", metric=metric)
    # 教学 fake：不强校验，但本测试演示"正确做法"
    helper.create_index(
        f"match_{metric}",
        field_name="vector",
        index_type="HNSW",
        metric_type=metric,  # 与集合一致
    )

    info = helper.get_collection(f"match_{metric}")
    assert info["metric"] == metric
    assert info["indexes"][0]["metric_type"] == metric
