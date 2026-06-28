"""Milvus 核心概念 #4：标量过滤表达式（Scalar Filter）。

教学目标：
- 理解"向量相似度 + 标量过滤"是向量库的杀手锏
- 学会 MongoDB 风格过滤语法（与 Milvus 表达式等价）
- 运算符一览：

  | 语法 | Milvus 等价 | 含义 |
  |---|---|---|
  | ``{"k": v}`` | ``k == v`` | 等于（最常用） |
  | ``{"k": {"$ne": v}}`` | ``k != v`` | 不等于 |
  | ``{"k": {"$gt": 5}}`` | ``k > 5`` | 数值/时间比较 |
  | ``{"k": {"$gte": 5}}`` | ``k >= 5`` | |
  | ``{"k": {"$lt": 5}}`` | ``k < 5`` | |
  | ``{"k": {"$lte": 5}}`` | ``k <= 5`` | |
  | ``{"k": {"$in": [1,2]}}`` | ``k in [1,2]`` | 成员 |
  | ``{"k": {"$nin": [1,2]}}`` | ``k not in [1,2]`` | 非成员 |

- 顶层多 key → AND；``$or`` / ``$and`` → 显式逻辑
- 过滤在**向量召回后**应用：先取 top_k 候选，再过滤 → 结果数 ≤ top_k
"""
from __future__ import annotations

# ──────────── 4.1 基础：等于过滤 ────────────


def test_4_1_equality_filter(helper):
    """``{"category": "news"}`` 只返回 payload.category == "news" 的记录。"""
    helper.create_collection("news_blog")
    helper.insert(
        "news_blog",
        [
            {"id": "n1", "vector": [0.1, 0.0, 0.0, 0.0], "payload": {"category": "news"}},
            {"id": "n2", "vector": [0.2, 0.0, 0.0, 0.0], "payload": {"category": "news"}},
            {"id": "b1", "vector": [0.3, 0.0, 0.0, 0.0], "payload": {"category": "blog"}},
        ],
    )

    # 查最相似 1 条
    results = helper.search(
        "news_blog",
        vector=[1.0, 0.0, 0.0, 0.0],
        top_k=3,
        filter_expr={"category": "news"},
    )

    assert len(results) == 2
    assert all(r["payload"]["category"] == "news" for r in results)
    assert {r["id"] for r in results} == {"n1", "n2"}


def test_4_2_explicit_eq_operator(helper):
    """``$eq`` 显式等于（与裸值等价）。"""
    helper.create_collection("eq_demo")
    helper.insert(
        "eq_demo",
        [
            {"id": "a", "vector": [0.1, 0.0], "payload": {"x": 5}},
            {"id": "b", "vector": [0.0, 0.1], "payload": {"x": 10}},
        ],
    )

    results = helper.search(
        "eq_demo",
        vector=[1.0, 0.0],
        top_k=2,
        filter_expr={"x": {"$eq": 5}},
    )
    assert len(results) == 1
    assert results[0]["id"] == "a"


# ──────────── 4.2 数值范围 ────────────


def test_4_3_numeric_range(helper):
    """``{"price": {"$gte": 10, "$lte": 100}}`` = 10 <= price <= 100。"""
    helper.create_collection("price_demo")
    helper.insert(
        "price_demo",
        [
            {"id": "p1", "vector": [0.1, 0.0], "payload": {"price": 5}},
            {"id": "p2", "vector": [0.2, 0.0], "payload": {"price": 50}},
            {"id": "p3", "vector": [0.3, 0.0], "payload": {"price": 150}},
            {"id": "p4", "vector": [0.4, 0.0], "payload": {"price": 100}},
        ],
    )

    results = helper.search(
        "price_demo",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"price": {"$gte": 10, "$lte": 100}},
    )
    ids = {r["id"] for r in results}
    assert ids == {"p2", "p4"}  # 50 与 100 命中，5 与 150 排除


def test_4_4_gt_lt_open_interval(helper):
    """``$gt`` / ``$lt`` 是开区间。"""
    helper.create_collection("open_interval")
    helper.insert(
        "open_interval",
        [
            {"id": "a", "vector": [0.1, 0.0], "payload": {"v": 5}},
            {"id": "b", "vector": [0.2, 0.0], "payload": {"v": 10}},
            {"id": "c", "vector": [0.3, 0.0], "payload": {"v": 15}},
        ],
    )

    # 5 < v < 15
    results = helper.search(
        "open_interval",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"v": {"$gt": 5, "$lt": 15}},
    )
    ids = {r["id"] for r in results}
    assert ids == {"b"}  # 仅 10


# ──────────── 4.3 成员（$in / $nin）────────────


def test_4_5_in_operator(helper):
    """``$in``：字段值在候选集合内。"""
    helper.create_collection("in_demo")
    helper.insert(
        "in_demo",
        [
            {"id": "a", "vector": [0.1, 0.0], "payload": {"tag": "ai"}},
            {"id": "b", "vector": [0.2, 0.0], "payload": {"tag": "ml"}},
            {"id": "c", "vector": [0.3, 0.0], "payload": {"tag": "db"}},
            {"id": "d", "vector": [0.4, 0.0], "payload": {"tag": "ai"}},
        ],
    )

    results = helper.search(
        "in_demo",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"tag": {"$in": ["ai", "ml"]}},
    )
    ids = {r["id"] for r in results}
    assert ids == {"a", "b", "d"}


def test_4_6_nin_operator(helper):
    """``$nin``：字段值不在候选集合内。"""
    helper.create_collection("nin_demo")
    helper.insert(
        "nin_demo",
        [
            {"id": "a", "vector": [0.1, 0.0], "payload": {"tag": "ai"}},
            {"id": "b", "vector": [0.2, 0.0], "payload": {"tag": "spam"}},
            {"id": "c", "vector": [0.3, 0.0], "payload": {"tag": "ml"}},
        ],
    )

    results = helper.search(
        "nin_demo",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"tag": {"$nin": ["spam"]}},
    )
    ids = {r["id"] for r in results}
    assert ids == {"a", "c"}


# ──────────── 4.4 不等于 ────────────


def test_4_7_ne_operator(helper):
    """``$ne``：排除特定值。"""
    helper.create_collection("ne_demo")
    helper.insert(
        "ne_demo",
        [
            {"id": "active", "vector": [0.1, 0.0], "payload": {"status": "active"}},
            {"id": "banned", "vector": [0.2, 0.0], "payload": {"status": "banned"}},
            {"id": "active2", "vector": [0.3, 0.0], "payload": {"status": "active"}},
        ],
    )

    results = helper.search(
        "ne_demo",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"status": {"$ne": "banned"}},
    )
    ids = {r["id"] for r in results}
    assert ids == {"active", "active2"}


# ──────────── 4.5 多字段 AND ────────────


def test_4_8_multi_field_and(helper):
    """顶层多 key 自动 AND。"""
    helper.create_collection("and_demo")
    helper.insert(
        "and_demo",
        [
            {
                "id": "p1",
                "vector": [0.1, 0.0],
                "payload": {"category": "news", "lang": "zh"},
            },
            {
                "id": "p2",
                "vector": [0.2, 0.0],
                "payload": {"category": "news", "lang": "en"},
            },
            {
                "id": "p3",
                "vector": [0.3, 0.0],
                "payload": {"category": "blog", "lang": "zh"},
            },
        ],
    )

    # category=news AND lang=zh
    results = helper.search(
        "and_demo",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"category": "news", "lang": "zh"},
    )
    assert len(results) == 1
    assert results[0]["id"] == "p1"


# ──────────── 4.6 顶层 $or ────────────


def test_4_9_top_level_or(helper):
    """``$or``：多个子表达式取并集。"""
    helper.create_collection("or_demo")
    helper.insert(
        "or_demo",
        [
            {"id": "a", "vector": [0.1, 0.0], "payload": {"cat": "news"}},
            {"id": "b", "vector": [0.2, 0.0], "payload": {"cat": "blog"}},
            {"id": "c", "vector": [0.3, 0.0], "payload": {"cat": "doc"}},
            {"id": "d", "vector": [0.4, 0.0], "payload": {"cat": "news"}},
        ],
    )

    # cat=news OR cat=blog
    results = helper.search(
        "or_demo",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"$or": [{"cat": "news"}, {"cat": "blog"}]},
    )
    ids = {r["id"] for r in results}
    assert ids == {"a", "b", "d"}


# ──────────── 4.7 组合：过滤 + top_k ────────────


def test_4_10_filter_with_topk(helper):
    """过滤后仍受 top_k 限制：先取 top_k 候选再过滤。"""
    helper.create_collection("topk_filter")
    helper.insert(
        "topk_filter",
        [
            {"id": "news_1", "vector": [0.9, 0.0], "payload": {"type": "news"}},
            {"id": "news_2", "vector": [0.8, 0.0], "payload": {"type": "news"}},
            {"id": "blog_1", "vector": [0.7, 0.0], "payload": {"type": "blog"}},
            {"id": "blog_2", "vector": [0.6, 0.0], "payload": {"type": "blog"}},
            {"id": "blog_3", "vector": [0.5, 0.0], "payload": {"type": "blog"}},
        ],
    )

    # 候选前 2 中只有 1 个 news
    results = helper.search(
        "topk_filter",
        vector=[1.0, 0.0],
        top_k=2,
        filter_expr={"type": "news"},
    )
    assert len(results) == 2
    assert all(r["payload"]["type"] == "news" for r in results)
    assert {r["id"] for r in results} == {"news_1", "news_2"}


# ──────────── 4.8 过滤命中为空 ────────────


def test_4_11_filter_no_match_returns_empty(helper):
    """过滤掉所有数据时返回空列表。"""
    helper.create_collection("no_match")
    helper.insert(
        "no_match",
        [
            {"id": "a", "vector": [0.1, 0.0], "payload": {"tag": "x"}},
            {"id": "b", "vector": [0.2, 0.0], "payload": {"tag": "y"}},
        ],
    )

    results = helper.search(
        "no_match",
        vector=[1.0, 0.0],
        top_k=10,
        filter_expr={"tag": "z"},
    )
    assert results == []


# ──────────── 4.9 空过滤 vs 无过滤 ────────────


def test_4_12_no_filter_returns_all(helper):
    """无 filter_expr / 空 filter_expr → 不过滤，全部返回。"""
    helper.create_collection("no_filter")
    helper.insert(
        "no_filter",
        [
            {"id": "a", "vector": [0.1, 0.0]},
            {"id": "b", "vector": [0.2, 0.0]},
            {"id": "c", "vector": [0.3, 0.0]},
        ],
    )

    # 不传 filter
    r1 = helper.search("no_filter", vector=[1.0, 0.0], top_k=10)
    assert len(r1) == 3

    # 传空 dict
    r2 = helper.search("no_filter", vector=[1.0, 0.0], top_k=10, filter_expr={})
    assert len(r2) == 3
