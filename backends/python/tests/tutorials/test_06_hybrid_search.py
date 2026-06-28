"""Milvus 核心概念 #6：混合检索（Hybrid Search）+ RRF 合并。

教学目标：
- 真实生产中常需要 **dense（语义）+ sparse（关键词）** 联合检索
  - 语义：找"意思相近"（"猫"和"kitty"）
  - 关键词：找"词面匹配"（"猫"只匹配含"猫"的）
  - 两者互补
- **RRF（Reciprocal Rank Fusion）**：把多路召回结果按名次合并
  - 公式：``score(d) = Σ_route  weight / (k + rank_d)``
  - k 是平滑项（默认 60，越大越接近线性合并）
- 适用：电商搜索、文档检索、RAG 增强召回

本节使用 **fake 简化版**：
- dense 路走 COSINE
- sparse 路把 ``sparse`` 字段当 keyword 字典，与 payload 的 ``kw_<id>`` 字段点积
"""
from __future__ import annotations

# ──────────── 6.1 Dense only：等价于普通 search ────────────


def test_6_1_dense_only_hybrid(helper):
    """只传 dense → 退化为普通向量检索。"""
    helper.create_collection("dense_only", dimension=4)
    helper.insert(
        "dense_only",
        [
            {"id": "a", "vector": [1.0, 0.0, 0.0, 0.0]},
            {"id": "b", "vector": [0.0, 1.0, 0.0, 0.0]},
            {"id": "c", "vector": [0.7071, 0.7071, 0.0, 0.0]},
        ],
    )

    results = helper.hybrid_search(
        "dense_only",
        dense=[1.0, 0.0, 0.0, 0.0],
        top_k=3,
    )
    # 与 test_3_2 普通 search 一致
    assert [r["id"] for r in results] == ["a", "c", "b"]


# ──────────── 6.2 Sparse only：纯关键词 ────────────


def test_6_2_sparse_only_hybrid(helper):
    """只传 sparse → 纯关键词检索（fake 用 ``kw_<id>`` payload 字段打分）。"""
    helper.create_collection("sparse_only", dimension=4)
    # 3 条数据，每条 payload 带不同的关键词命中
    helper.insert(
        "sparse_only",
        [
            {
                "id": "doc1",
                "vector": [0.0, 0.0, 0.0, 0.0],  # dense 没用
                "payload": {"kw_ml": 0.9, "kw_ai": 0.5},
            },
            {
                "id": "doc2",
                "vector": [0.0, 0.0, 0.0, 0.0],
                "payload": {"kw_ml": 0.3},
            },
            {
                "id": "doc3",
                "vector": [0.0, 0.0, 0.0, 0.0],
                "payload": {"kw_db": 1.0},  # 完全不相关
            },
        ],
    )

    # 查询关键词 ml + ai
    results = helper.hybrid_search(
        "sparse_only",
        sparse={"ml": 1.0, "ai": 1.0},
        top_k=3,
    )

    # doc3 不命中（没有 ml/ai 关键词），应被排除
    assert [r["id"] for r in results] == ["doc1", "doc2"]
    # doc1 分值高（kw_ml=0.9 + kw_ai=0.5 = 1.4）
    # doc2 分值低（kw_ml=0.3）
    assert results[0]["id"] == "doc1"
    assert results[1]["id"] == "doc2"


# ──────────── 6.3 Dense + Sparse：RRF 合并 ────────────


def test_6_3_dense_and_sparse_rrf_merge(helper):
    """dense + sparse 同时给 → RRF 合并名次。"""
    helper.create_collection("rrf_demo", dimension=4)
    helper.insert(
        "rrf_demo",
        [
            {
                "id": "semantic_match",  # dense 第一
                "vector": [1.0, 0.0, 0.0, 0.0],
                "payload": {"kw_kw1": 0.0},  # sparse 没分
            },
            {
                "id": "keyword_match",  # sparse 第一
                "vector": [0.0, 1.0, 0.0, 0.0],  # dense 第二
                "payload": {"kw_kw1": 1.0},
            },
            {
                "id": "both_match",  # dense+sparse 都在
                "vector": [0.8, 0.2, 0.0, 0.0],  # dense 第三
                "payload": {"kw_kw1": 0.5},  # sparse 第二
            },
        ],
    )

    # dense 查 [1,0,0,0]，sparse 查 kw1=1.0
    results = helper.hybrid_search(
        "rrf_demo",
        dense=[1.0, 0.0, 0.0, 0.0],
        sparse={"kw1": 1.0},
        top_k=3,
    )

    # both_match 应排第一：dense rank=3 + sparse rank=2 都贡献
    # 公式（k=60, weight=1.0）：score = 1/63 + 1/62 = 0.0317
    # semantic_match：dense rank=1 + sparse 不在 → score = 1/61 = 0.0164
    # keyword_match：dense rank=2 + sparse rank=1 → score = 1/62 + 1/61 = 0.0325
    # 实际：keyword_match 略高（rank 1+2 vs 1+3）
    # 但 both_match 的 sum 也接近；只验证 both_match / keyword_match 排前两位
    top2 = {r["id"] for r in results[:2]}
    assert "both_match" in top2
    assert "keyword_match" in top2
    # semantic_match 排最后（只 dense 1 分）
    assert results[-1]["id"] == "semantic_match"


# ──────────── 6.4 权重调节：dense_weight vs sparse_weight ────────────


def test_6_4_dense_weight_dominates(helper):
    """dense_weight >> sparse_weight → 倾向 dense 排序。"""
    helper.create_collection("weight_dense", dimension=4)
    helper.insert(
        "weight_dense",
        [
            {
                "id": "dense_winner",  # dense 命中
                "vector": [1.0, 0.0, 0.0, 0.0],
                "payload": {"kw_kw1": 0.0},  # sparse 没分
            },
            {
                "id": "sparse_winner",  # sparse 命中
                "vector": [0.0, 1.0, 0.0, 0.0],  # dense 不近
                "payload": {"kw_kw1": 1.0},
            },
        ],
    )

    # dense_weight=100, sparse_weight=1 → dense 主导
    results = helper.hybrid_search(
        "weight_dense",
        dense=[1.0, 0.0, 0.0, 0.0],
        sparse={"kw1": 1.0},
        dense_weight=100.0,
        sparse_weight=1.0,
        top_k=2,
    )
    # dense_winner dense rank=1, sparse 不在 → 100/61
    # sparse_winner dense rank=2, sparse rank=1 → 100/62 + 1/61
    # dense_winner 仍赢
    assert results[0]["id"] == "dense_winner"


def test_6_5_sparse_weight_dominates(helper):
    """sparse_weight >> dense_weight → 倾向 sparse 排序。"""
    helper.create_collection("weight_sparse", dimension=4)
    helper.insert(
        "weight_sparse",
        [
            {
                "id": "dense_winner",
                "vector": [1.0, 0.0, 0.0, 0.0],
                "payload": {"kw_kw1": 0.0},
            },
            {
                "id": "sparse_winner",
                "vector": [0.0, 1.0, 0.0, 0.0],
                "payload": {"kw_kw1": 1.0},
            },
        ],
    )

    # sparse_weight=100, dense_weight=1 → sparse 主导
    results = helper.hybrid_search(
        "weight_sparse",
        dense=[1.0, 0.0, 0.0, 0.0],
        sparse={"kw1": 1.0},
        dense_weight=1.0,
        sparse_weight=100.0,
        top_k=2,
    )
    # dense_winner: 1/61 (dense rank=1) + 0 (sparse 不在) = 0.0164
    # sparse_winner: 1/62 (dense rank=2) + 100/61 (sparse rank=1) = 1.655
    assert results[0]["id"] == "sparse_winner"


# ──────────── 6.6 RRF k 参数的平滑作用 ────────────


def test_6_6_rrf_k_smoothing(helper):
    """k 越大 → 名次差对分值影响越小（更平滑，分数差异更小）。"""
    helper.create_collection("rrf_k", dimension=4)
    # 3 条数据，dense 与 sparse 给出不同的相对排名
    helper.insert(
        "rrf_k",
        [
            {
                "id": "A",
                "vector": [1.0, 0.0, 0.0, 0.0],  # dense rank 1
                "payload": {"kw_kw1": 0.1},  # sparse rank 3
            },
            {
                "id": "B",
                "vector": [0.9, 0.1, 0.0, 0.0],  # dense rank 2
                "payload": {"kw_kw1": 1.0},  # sparse rank 1
            },
            {
                "id": "C",
                "vector": [0.8, 0.2, 0.0, 0.0],  # dense rank 3
                "payload": {"kw_kw1": 0.5},  # sparse rank 2
            },
        ],
    )

    # k=1（强平滑）：名次差对分值影响大
    small_k = helper.hybrid_search(
        "rrf_k",
        dense=[1.0, 0.0, 0.0, 0.0],
        sparse={"kw1": 1.0},
        rrf_k=1,
        top_k=3,
    )
    # k=1000（弱平滑）：趋近于线性合并
    big_k = helper.hybrid_search(
        "rrf_k",
        dense=[1.0, 0.0, 0.0, 0.0],
        sparse={"kw1": 1.0},
        rrf_k=1000,
        top_k=3,
    )

    # 两种 k 下 top-1 都是 B（dense rank 2 + sparse rank 1）
    assert small_k[0]["id"] == "B"
    assert big_k[0]["id"] == "B"

    # top-1 与 top-2 的分值差：k 越大差距越小
    diff_small = small_k[0]["score"] - small_k[1]["score"]
    diff_big = big_k[0]["score"] - big_k[1]["score"]
    assert diff_small > diff_big  # 小 k 时差距更大（更不平滑）


# ──────────── 6.7 dense + sparse 都为空 ────────────


def test_6_7_empty_inputs_returns_empty(helper):
    """dense + sparse 都不传 → 无候选可召 → 空结果（不抛错）。"""
    helper.create_collection("empty_hybrid", dimension=4)
    helper.insert("empty_hybrid", [{"id": "x", "vector": [0.1, 0.0, 0.0, 0.0]}])

    results = helper.hybrid_search("empty_hybrid", top_k=10)
    assert results == []
