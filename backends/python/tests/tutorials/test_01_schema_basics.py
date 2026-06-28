"""Milvus 核心概念 #1：集合 Schema 详解。

教学目标：
- 理解集合 = 表 + schema + 索引
- 主键、向量字段、payload 三个固定字段
- 维度（dimension）一旦创建不可修改
- 不同距离度量的选择（先用 COSINE 演示）
- 集合元信息（loaded / row_count / indexes / created_at）
- 重复创建同名集合会返回 409
- 删除集合不可逆

## 三步式：seed → run → verify
每个 test 都遵循：
1. seed: 准备数据（创建集合、插入向量）
2. run: 演示某个 Milvus API 的用法
3. verify: 验证操作生效（GET、query、search）
"""
from __future__ import annotations

import pytest

# ──────────── 1.1 创建集合 ────────────


def test_1_1_create_minimal_collection(helper):
    """最小可用集合：4 维向量 + COSINE 距离。"""
    # run: 创建集合
    data = helper.create_collection("minimal", dimension=4, metric="COSINE")

    # verify: 返回值含集合名
    assert data["name"] == f"{helper.prefix}_minimal"

    # verify: GET /collections/{name} 拿完整元信息
    info = helper.get_collection("minimal")
    assert info["dimension"] == 4
    assert info["metric"] == "COSINE"
    assert info["row_count"] == 0
    assert info["loaded"] is True  # 教学 fake：创建即标记为已加载
    assert isinstance(info["indexes"], list)
    assert info["created_at"] is not None


def test_1_2_create_collection_with_description(helper):
    """创建带描述的集合。"""
    helper.create_collection(
        "described",
        dimension=8,
        metric="L2",
        description="用于 Phase 2.3 教学示例",
    )

    info = helper.get_collection("described")
    assert info["dimension"] == 8
    assert info["metric"] == "L2"
    # description 是创建时的输入，目前 GET 暂不返回（属于元数据高级功能）


# ──────────── 1.3 不同 dimension 选型 ────────────


@pytest.mark.parametrize(
    "dim,scenario",
    [
        (4, "教学示例（最快）"),
        (384, "BGE-small"),
        (768, "BGE-base / m3e-base"),
        (1536, "OpenAI text-embedding-3-small"),
        (3072, "OpenAI text-embedding-3-large"),
    ],
)
def test_1_3_different_dimensions(helper, dim, scenario):
    """不同 dimension 对应不同嵌入模型。

    教学点：dimension 必须在创建集合时就确定（因为向量索引结构依赖维度），
    一旦创建不可修改 —— 这就是为什么 schema 设计要先选好 embedding 模型。
    """
    helper.create_collection(f"dim_{dim}", dimension=dim)

    info = helper.get_collection(f"dim_{dim}")
    assert info["dimension"] == dim, f"dim={dim} scenario={scenario}"


# ──────────── 1.4 集合元信息 / 列表 / 重复创建 / 删除 ────────────


def test_1_4_list_and_drop_collection(helper):
    """列出集合 + 重复创建返回 409 + 删除不可逆。"""
    helper.create_collection("a")
    helper.create_collection("b")

    # verify: 列表里能找到
    cols = helper.list_collections()
    assert f"{helper.prefix}_a" in cols
    assert f"{helper.prefix}_b" in cols

    # run: 重复创建同名集合应 409

    r = helper.client.post(
        "/api/v1/collections",
        json={"name": f"{helper.prefix}_a", "dimension": 4},
    )
    assert r.status_code == 409
    body = r.json()
    assert body["code"] != 0  # 业务错误码非 0
    assert "exists" in body["message"].lower() or "已存在" in body["message"]

    # run: 删除
    helper.drop_collection("a")

    # verify: 列表里不再有 a
    cols = helper.list_collections()
    assert f"{helper.prefix}_a" not in cols
    assert f"{helper.prefix}_b" in cols


# ──────────── 1.5 集合与向量的关系 ────────────


def test_1_5_row_count_reflects_inserts(helper):
    """row_count 随插入更新。"""
    helper.create_collection("counter", dimension=4)

    info1 = helper.get_collection("counter")
    assert info1["row_count"] == 0

    # seed: 插入 3 条
    helper.insert(
        "counter",
        [
            {"id": "v1", "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"tag": "a"}},
            {"id": "v2", "vector": [0.5, 0.6, 0.7, 0.8], "payload": {"tag": "b"}},
            {"id": "v3", "vector": [0.9, 0.0, 0.1, 0.2], "payload": {"tag": "a"}},
        ],
    )

    # verify: row_count = 3
    info2 = helper.get_collection("counter")
    assert info2["row_count"] == 3

    # run: 按 id 删除
    helper.delete("counter", ["v1"])

    # verify: row_count = 2
    info3 = helper.get_collection("counter")
    assert info3["row_count"] == 2


# ──────────── 1.6 default 系统分区 ────────────


def test_1_6_default_partition_auto_created(helper):
    """创建集合时自动建一个 _default 分区。"""
    helper.create_collection("with_default_part")

    # verify: 列表里有 _default
    parts = helper.list_partitions("with_default_part")
    names = [p["name"] for p in parts]
    assert "_default" in names


# ──────────── 1.7 AUTOINDEX 默认索引 ────────────


def test_1_7_default_index_on_create(helper):
    """创建集合时自动建一个 AUTOINDEX。"""
    helper.create_collection("with_auto_idx", index_type="AUTOINDEX")

    indexes = helper.list_indexes("with_auto_idx")
    assert len(indexes) == 1
    assert indexes[0]["index_type"] == "AUTOINDEX"
    assert indexes[0]["field_name"] == "vector"
    assert indexes[0]["metric_type"] == "COSINE"
