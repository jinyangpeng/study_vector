"""Milvus 核心概念 #8：Alias 零停机切换（Zero-Downtime Migration）。

教学目标：
- 理解"alias"= 集合的命名指针（一个集合可有多个 alias；一个 alias 只指一个集合）
- **零停机切换流程**（最核心教学点）：
  1. 业务代码访问"prod_latest"alias
  2. 创建新集合"docs_v2" + 写双写
  3. 验证 v2 数据齐了
  4. ``alterAlias("prod_latest", docs_v2)`` 原子切换
  5. 删旧集合"docs_v1"
  → 业务**零感知**升级
- 真实 Milvus 提供 ``alterAlias`` 原子操作；本 V1 用 drop + create 模拟
- 业务上始终用 alias 名访问，集合名仅作为内部实现
"""
from __future__ import annotations

# ──────────── 8.1 基本：创建 + 列出 + 删除 ────────────


def test_8_1_create_list_drop_alias(helper):
    """单集合单 alias：增 / 查 / 删。"""
    helper.create_collection("alias_basic")
    helper.create_alias("alias_basic", "v1")

    aliases = helper.list_aliases("alias_basic")
    assert "v1" in aliases

    helper.drop_alias("alias_basic", "v1")
    aliases = helper.list_aliases("alias_basic")
    assert "v1" not in aliases


# ──────────── 8.2 多 alias 指向同一集合 ────────────


def test_8_2_multiple_aliases_same_collection(helper):
    """一个集合可绑多个 alias：例如 ``prod`` / ``staging`` / ``latest``。"""
    helper.create_collection("multi_alias")
    for alias in ("prod", "staging", "latest", "v1"):
        helper.create_alias("multi_alias", alias)

    aliases = helper.list_aliases("multi_alias")
    assert set(aliases) == {"prod", "staging", "latest", "v1"}


# ──────────── 8.3 同一 alias 不可指向多个集合 ────────────


def test_8_3_alias_uniqueness_across_collections(helper):
    """alias 全局唯一：不能绑到第二个集合（否则零停机切换失效）。"""
    helper.create_collection("col_a")
    helper.create_collection("col_b")
    helper.create_alias("col_a", "prod")

    # 尝试把 "prod" 绑到 col_b → 失败
    r = helper.client.post(
        f"/api/v1/collections/{helper.prefix}_col_b/alias",
        json={"alias": "prod"},
    )
    assert r.status_code == 500 or r.status_code == 409  # fake 抛 ValueError → 500
    body = r.json()
    # 错误信息应提到 alias 冲突
    assert "prod" in str(body["message"])


# ──────────── 8.4 同一集合重复绑相同 alias（幂等） ────────────


def test_8_4_repeat_same_alias_idempotent(helper):
    """同集合重复绑相同 alias → 第二次 no-op（fake 实现：不重复添加）。"""
    helper.create_collection("idem_alias")
    helper.create_alias("idem_alias", "v1")
    helper.create_alias("idem_alias", "v1")  # 第二次

    aliases = helper.list_aliases("idem_alias")
    assert aliases.count("v1") == 1


# ──────────── 8.5 零停机切换：核心场景 ────────────


def test_8_5_zero_downtime_switch(helper):
    """蓝绿部署：alias 从 v1 切到 v2，业务代码访问 alias 无感知。"""
    # seed: v1 集合与 alias
    helper.create_collection("docs_v1", dimension=4)
    helper.create_alias("docs_v1", "docs_latest")
    helper.insert(
        "docs_v1",
        [
            {"id": "v1_doc", "vector": [1.0, 0.0, 0.0, 0.0]},
        ],
    )

    # 旧 alias 列表：docs_v1 → [docs_latest]
    assert "docs_latest" in helper.list_aliases("docs_v1")

    # 升级：建 v2，写入新数据
    helper.create_collection("docs_v2", dimension=4)
    helper.insert(
        "docs_v2",
        [
            {"id": "v2_doc", "vector": [0.9, 0.1, 0.0, 0.0]},
        ],
    )

    # 切换 alias：v1 → v2
    helper.reassign_alias("docs_v1", "docs_v2", "docs_latest")

    # verify: alias 现在指向 v2
    assert "docs_latest" in helper.list_aliases("docs_v2")
    assert "docs_latest" not in helper.list_aliases("docs_v1")


# ──────────── 8.6 alias 名与集合名同名校验 ────────────


def test_8_6_alias_with_valid_name(helper):
    """alias 名同样要满足"字母开头 + 字母数字下划线"约束。"""
    helper.create_collection("valid_a")
    helper.create_alias("valid_a", "production")
    helper.create_alias("valid_a", "v1_2024")
    helper.create_alias("valid_a", "ml_alpha")

    aliases = helper.list_aliases("valid_a")
    assert "production" in aliases
    assert "v1_2024" in aliases
    assert "ml_alpha" in aliases


# ──────────── 8.7 不存在的集合 → 绑定 alias 失败 ────────────


def test_8_7_bind_alias_to_nonexistent_collection_fails(helper):
    """给不存在的集合绑 alias → 404。"""

    r = helper.client.post(
        f"/api/v1/collections/{helper.prefix}_ghost/alias",
        json={"alias": "v1"},
    )
    assert r.status_code == 404


# ──────────── 8.8 业务上"用 alias 名"的最佳实践 ────────────


def test_8_8_use_alias_as_indirection_layer(helper):
    """业务用 alias 而不是集合名 → 升级无需改代码。"""
    # 假设应用代码中所有调用都用 "documents" 这个 alias
    helper.create_collection("documents_v1", dimension=4)
    helper.create_collection("documents_v2", dimension=4)
    helper.create_alias("documents_v1", "documents")

    # 业务查 documents alias 实际指 v1
    assert "documents" in helper.list_aliases("documents_v1")

    # 部署 v2 + 切换 alias
    helper.reassign_alias("documents_v1", "documents_v2", "documents")

    # 业务继续查 documents alias（代码不变） → 实际已指向 v2
    assert "documents" in helper.list_aliases("documents_v2")
    assert "documents" not in helper.list_aliases("documents_v1")

    # 后续清理 v1（如果 v2 稳定运行）
    helper.drop_collection("documents_v1")

    # 业务无感知
    assert "documents" in helper.list_aliases("documents_v2")


# ──────────── 8.9 删除集合后 alias 自动失效 ────────────


def test_8_9_drop_collection_clears_aliases(helper):
    """删集合后无法再查 alias（集合不存在 → 404，alias 也消失）。"""
    helper.create_collection("drop_with_alias")
    helper.create_alias("drop_with_alias", "prod")
    helper.create_alias("drop_with_alias", "staging")

    helper.drop_collection("drop_with_alias")

    # 集合没了，再查 alias 返回 404（fake 内部 _aliases 也被清）

    r = helper.client.get(f"/api/v1/collections/{helper.prefix}_drop_with_alias/alias")
    assert r.status_code == 404


# ──────────── 8.10 同一集合多 alias 各自独立管理 ────────────


def test_8_10_delete_one_alias_keeps_others(helper):
    """删一个 alias 不影响其他。"""
    helper.create_collection("multi_drop")
    helper.create_alias("multi_drop", "v1")
    helper.create_alias("multi_drop", "v2")
    helper.create_alias("multi_drop", "v3")

    helper.drop_alias("multi_drop", "v2")

    remaining = set(helper.list_aliases("multi_drop"))
    assert remaining == {"v1", "v3"}
