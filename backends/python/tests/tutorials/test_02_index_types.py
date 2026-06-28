"""Milvus 核心概念 #2：索引类型对比。

教学目标：
- 理解索引 = 把向量按某种数据结构组织，**用时间换精度**
- 5 大主流索引的适用场景与权衡：
  - **FLAT**：暴力搜索；100% 召回；适合 < 1k 条数据 / 基准测试
  - **IVF_FLAT**：倒排 + 聚类；适合中等规模（百万级）
  - **IVF_PQ**：倒排 + 乘积量化；内存省 10-100x；召回略降
  - **HNSW**：图结构；高召回 / 内存允许；延迟低
  - **DISKANN**：磁盘索引；超大规模（亿级）但延迟高
  - **AUTOINDEX**：Milvus 自适应；**生产推荐**（黑盒）
- 索引**可重建**（先 drop 再 create），**与数据共存**（索引建好后才能检索）
- 索引参数可调（IVF nlist、HNSW M/efConstruction）
"""
from __future__ import annotations

import pytest

# ──────────── 2.1 索引元信息 ────────────


def test_2_1_default_index(helper):
    """默认 AUTOINDEX。"""
    helper.create_collection("default_idx")
    indexes = helper.list_indexes("default_idx")
    assert len(indexes) == 1
    idx = indexes[0]
    assert idx["index_type"] == "AUTOINDEX"
    assert idx["field_name"] == "vector"


@pytest.mark.parametrize(
    "idx_type,scenario",
    [
        ("FLAT", "暴力 / 基准测试"),
        ("IVF_FLAT", "倒排 + FLAT / 百万级"),
        ("IVF_SQ8", "标量量化 / 内存省"),
        ("IVF_PQ", "乘积量化 / 超省内存"),
        ("HNSW", "图 / 低延迟"),
        ("ANNOY", "树 / Spotify 开源"),
        ("DISKANN", "磁盘 / 亿级"),
        ("AUTOINDEX", "Milvus 自适应 / 生产推荐"),
    ],
)
def test_2_2_all_index_types(helper, idx_type, scenario):
    """8 种索引类型全部可建。"""
    helper.create_collection(f"idx_{idx_type}")
    helper.create_index(
        f"idx_{idx_type}",
        field_name="vector",
        index_type=idx_type,
        metric_type="COSINE",
    )

    indexes = helper.list_indexes(f"idx_{idx_type}")
    assert len(indexes) == 1
    assert indexes[0]["index_type"] == idx_type


# ──────────── 2.3 索引参数调优 ────────────


def test_2_3_hnsw_parameters(helper):
    """HNSW 参数：M（每节点邻居数）+ efConstruction（构建期搜索宽度）。"""
    helper.create_collection("hnsw_demo")
    helper.create_index(
        "hnsw_demo",
        field_name="vector",
        index_type="HNSW",
        metric_type="L2",
        params={"M": 16, "efConstruction": 64},
    )

    indexes = helper.list_indexes("hnsw_demo")
    assert indexes[0]["index_type"] == "HNSW"
    assert indexes[0]["metric_type"] == "L2"
    # params 在 fake repo 中保留
    assert indexes[0]["params"]["M"] == 16
    assert indexes[0]["params"]["efConstruction"] == 64


def test_2_4_ivf_parameters(helper):
    """IVF_FLAT 参数：nlist（聚类数）。"""
    helper.create_collection("ivf_demo")
    helper.create_index(
        "ivf_demo",
        field_name="vector",
        index_type="IVF_FLAT",
        metric_type="L2",
        params={"nlist": 1024},
    )

    indexes = helper.list_indexes("ivf_demo")
    assert indexes[0]["params"]["nlist"] == 1024


# ──────────── 2.5 重建索引（drop + create） ────────────


def test_2_5_rebuild_index(helper):
    """同字段可重建：先 drop 再 create（不需要删数据）。"""
    helper.create_collection("rebuild")
    helper.create_index("rebuild", field_name="vector", index_type="FLAT")

    # seed: 插几条数据
    helper.insert(
        "rebuild",
        [
            {"id": "v1", "vector": [0.1, 0.2, 0.3, 0.4]},
            {"id": "v2", "vector": [0.5, 0.6, 0.7, 0.8]},
        ],
    )

    # run: drop FLAT
    helper.drop_index("rebuild", "vector")
    assert helper.list_indexes("rebuild") == []

    # run: 重建为 HNSW
    helper.create_index("rebuild", field_name="vector", index_type="HNSW")

    indexes = helper.list_indexes("rebuild")
    assert len(indexes) == 1
    assert indexes[0]["index_type"] == "HNSW"

    # verify: 数据仍存在
    info = helper.get_collection("rebuild")
    assert info["row_count"] == 2


# ──────────── 2.6 多字段多索引（V1 限制：V1 简化版只支持向量字段索引） ────────────


def test_2_6_replace_same_field_index(helper):
    """同字段再建索引会自动替换旧的。"""
    helper.create_collection("replace_idx")
    helper.create_index(
        "replace_idx",
        field_name="vector",
        index_type="FLAT",
    )
    helper.create_index(
        "replace_idx",
        field_name="vector",
        index_type="HNSW",
    )

    # verify: 旧 FLAT 被替换为 HNSW
    indexes = helper.list_indexes("replace_idx")
    assert len(indexes) == 1
    assert indexes[0]["index_type"] == "HNSW"


# ──────────── 2.7 索引 vs 度量 ────────────


@pytest.mark.parametrize("metric", ["COSINE", "L2", "IP"])
def test_2_7_index_with_metric(helper, metric):
    """不同度量都可建索引（但生产应保持集合 metric 与索引 metric 一致）。"""
    helper.create_collection(f"idx_{metric}", metric=metric)
    helper.create_index(
        f"idx_{metric}",
        field_name="vector",
        index_type="HNSW",
        metric_type=metric,
    )

    indexes = helper.list_indexes(f"idx_{metric}")
    assert indexes[0]["metric_type"] == metric
