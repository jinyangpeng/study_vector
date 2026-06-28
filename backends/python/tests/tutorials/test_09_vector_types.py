"""Milvus 核心概念 #9：向量数据类型（Vector Type）。

教学目标：
- 理解 Milvus 6 种向量类型的设计目的与存储差异
- 不同向量类型对应不同的内存占用、距离度量、索引选项
- 选错类型 = 维度/度量/索引/距离全错

## 6 种向量类型对比

| 类型 | 内存 | 维度约束 | 支持的距离 | 典型场景 |
|---|---|---|---|---|
| **FloatVector**（默认）| 4×D bytes | 1-65536 | COSINE / L2 / IP | 通用 embedding（BGE/OpenAI）|
| **BinaryVector** | D/8 bytes | 8 的倍数 | HAMMING / JACCARD | 哈希特征/图像指纹 |
| **Float16Vector** | 2×D bytes | 1-65536 | COSINE / L2 / IP | 显存省一半 |
| **BFloat16Vector** | 2×D bytes | 1-65536 | COSINE / L2 / IP | 训练推理（保留 8-bit 指数）|
| **SparseFloatVector** | 4×NNZ bytes | NNZ 上限 | IP | 关键词/SPLADE 检索 |
| **Int8Vector** | D bytes | 1-65536 | L2 | 量化/边缘设备 |

## 关键原则

1. **维度是固定值**：选什么 embedding 模型 → 维度跟着定 → 集合创建时锁定
2. **类型决定度量**：Binary 配 Hamming；Sparse 配 IP；Int8 配 L2；Float 系都能配
3. **类型决定存储**：D=768 的 FloatVector ≈ 3KB/向量；D=768 的 Float16 ≈ 1.5KB；BinaryVector(D=768) ≈ 96B
4. **类型决定索引**：IVF_PQ 不支持 BinaryVector；BIN_FLAT 仅 BinaryVector 支持
5. **Sparse 走 hybrid_search**：向量以 dict {idx: value} 形式传入，单独接口

## 三步式：seed → run → verify
"""
from __future__ import annotations

import pytest

from study_vector.domain.models import VectorType

# ──────────── 9.1 6 种向量类型枚举值正确 ────────────


def test_9_0_vector_type_enum_values():
    """枚举值与 Milvus 官方 SDK 字符串完全一致。"""
    assert VectorType.FLOAT_VECTOR.value == "FloatVector"
    assert VectorType.BINARY_VECTOR.value == "BinaryVector"
    assert VectorType.FLOAT16_VECTOR.value == "Float16Vector"
    assert VectorType.BFLOAT16_VECTOR.value == "BFloat16Vector"
    assert VectorType.SPARSE_FLOAT_VECTOR.value == "SparseFloatVector"
    assert VectorType.INT8_VECTOR.value == "Int8Vector"


# ──────────── 9.2 默认是 FloatVector ────────────


def test_9_1_default_vector_type_is_float(helper):
    """不指定 vector_type → 默认 FloatVector。"""
    helper.create_collection("default_vt", dimension=4)

    info = helper.get_collection("default_vt")
    assert info["vector_type"] == "FloatVector"


def test_9_2_explicit_float_vector(helper):
    """显式指定 FloatVector 与默认行为一致。"""
    helper.create_collection("explicit_float", dimension=4, vector_type="FloatVector")

    info = helper.get_collection("explicit_float")
    assert info["vector_type"] == "FloatVector"


# ──────────── 9.3 FloatVector 端到端 ────────────


def test_9_3_float_vector_end_to_end(helper):
    """FloatVector 完整流程：建集合 → 插数据 → COSINE 检索。"""
    helper.create_collection("fv_e2e", dimension=4, vector_type="FloatVector")

    helper.insert(
        "fv_e2e",
        [
            {"id": "a", "vector": [1.0, 0.0, 0.0, 0.0]},
            {"id": "b", "vector": [0.0, 1.0, 0.0, 0.0]},
            {"id": "c", "vector": [0.9, 0.1, 0.0, 0.0]},
        ],
    )

    # COSINE 检索：与 a 最接近的应是 a 和 c
    results = helper.search("fv_e2e", vector=[1.0, 0.0, 0.0, 0.0], top_k=3)
    ids = [r["id"] for r in results]
    assert "a" in ids
    assert "c" in ids
    # 距离最远的是 b（与 query 正交）
    assert ids[-1] == "b"


# ──────────── 9.4 BinaryVector 维度必须是 8 的倍数 ────────────


def test_9_4_binary_vector_dim_must_be_multiple_of_8(helper):
    """BinaryVector 按位打包 → 维度必须 8 的倍数，否则 422。"""

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + "_bin_bad",
            "dimension": 7,  # 不是 8 的倍数
            "vector_type": "BinaryVector",
            "metric": "HAMMING",
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] != 0
    assert "8" in str(body["message"])


@pytest.mark.parametrize("dim", [8, 16, 64, 128, 512])
def test_9_5_binary_vector_dim_8_aligned_ok(helper, dim):
    """维度是 8 的倍数都能建。"""
    helper.create_collection(
        f"bin_{dim}",
        dimension=dim,
        vector_type="BinaryVector",
        metric="HAMMING",
    )

    info = helper.get_collection(f"bin_{dim}")
    assert info["vector_type"] == "BinaryVector"
    assert info["dimension"] == dim


# ──────────── 9.6 BinaryVector 度量必须 HAMMING/JACCARD ────────────


@pytest.mark.parametrize(
    "metric",
    ["HAMMING", "JACCARD"],
)
def test_9_6_binary_vector_supported_metrics(helper, metric):
    """BinaryVector 配 HAMMING/JACCARD 都能建。"""
    helper.create_collection(
        f"bin_{metric.lower()}",
        dimension=8,
        vector_type="BinaryVector",
        metric=metric,
    )
    info = helper.get_collection(f"bin_{metric.lower()}")
    assert info["metric"] == metric
    assert info["vector_type"] == "BinaryVector"


@pytest.mark.parametrize("metric", ["COSINE", "L2", "IP"])
def test_9_7_binary_vector_rejects_float_metrics(helper, metric):
    """BinaryVector 配 COSINE/L2/IP → 422。"""

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + f"_bin_bad_{metric}",
            "dimension": 8,
            "vector_type": "BinaryVector",
            "metric": metric,
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] != 0
    assert "BinaryVector" in str(body["message"])


# ──────────── 9.8 BinaryVector 端到端（汉明距离）────────────


def test_9_8_binary_vector_hamming_search(helper):
    """BinaryVector 检索：查询 [1,0,1,0,1,0,1,0]，按位差最少者胜出。

    教学：
    - 真 Milvus 内部按字节位存储，8 个 bit 打 1 字节
    - 距离 = 不同 bit 数；越少越相似
    - fake 端用 list[float] (0/1) 形式 + 元素级 != 计算
    """
    helper.create_collection(
        "bin_search",
        dimension=8,
        vector_type="BinaryVector",
        metric="HAMMING",
    )

    helper.insert(
        "bin_search",
        [
            {"id": "exact", "vector": [1, 0, 1, 0, 1, 0, 1, 0]},  # 距离 0
            {"id": "1off", "vector": [1, 0, 1, 0, 1, 0, 1, 1]},  # 距离 1
            {"id": "4off", "vector": [0, 0, 1, 0, 1, 0, 1, 0]},  # 距离 2（但实际不同位更少）
            {"id": "ortho", "vector": [0, 1, 0, 1, 0, 1, 0, 1]},  # 距离 8
        ],
    )

    results = helper.search(
        "bin_search", vector=[1, 0, 1, 0, 1, 0, 1, 0], top_k=4
    )
    # exact 必然第一
    assert results[0]["id"] == "exact"
    # ortho 必然最后
    assert results[-1]["id"] == "ortho"


# ──────────── 9.9 Float16 / BFloat16 ────────────


@pytest.mark.parametrize("vt", ["Float16Vector", "BFloat16Vector"])
def test_9_9_half_precision_create(helper, vt):
    """Float16/BFloat16 都能建；度量都用 COSINE/L2/IP。

    教学：
    - 内存省一半（2 字节/元素 vs 4 字节）
    - 距离计算逻辑同 FloatVector
    - 训练推理阶段常用 Float16（省显存）
    """
    helper.create_collection(
        f"hp_{vt.lower()}",
        dimension=4,
        vector_type=vt,
        metric="COSINE",
    )
    info = helper.get_collection(f"hp_{vt.lower()}")
    assert info["vector_type"] == vt


@pytest.mark.parametrize("vt", ["Float16Vector", "BFloat16Vector"])
def test_9_10_half_precision_rejects_binary_metrics(helper, vt):
    """Float16/BFloat16 不能配 HAMMING/JACCARD。"""

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + f"_{vt.lower()}_bad",
            "dimension": 4,
            "vector_type": vt,
            "metric": "HAMMING",
        },
    )
    assert r.status_code == 422


# ──────────── 9.11 Int8Vector ────────────


def test_9_11_int8_create_with_l2(helper):
    """Int8Vector 配 L2。"""
    helper.create_collection(
        "int8_l2",
        dimension=4,
        vector_type="Int8Vector",
        metric="L2",
    )
    info = helper.get_collection("int8_l2")
    assert info["vector_type"] == "Int8Vector"
    assert info["metric"] == "L2"


@pytest.mark.parametrize("metric", ["COSINE", "IP", "HAMMING", "JACCARD"])
def test_9_12_int8_rejects_other_metrics(helper, metric):
    """Int8Vector 只能配 L2。"""

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + f"_int8_bad_{metric}",
            "dimension": 4,
            "vector_type": "Int8Vector",
            "metric": metric,
        },
    )
    assert r.status_code == 422


def test_9_13_int8_end_to_end(helper):
    """Int8Vector 端到端：值是整数 0-255。"""
    helper.create_collection(
        "int8_e2e",
        dimension=4,
        vector_type="Int8Vector",
        metric="L2",
    )
    helper.insert(
        "int8_e2e",
        [
            {"id": "a", "vector": [1, 2, 3, 4]},
            {"id": "b", "vector": [5, 6, 7, 8]},
            {"id": "c", "vector": [1, 2, 3, 4]},  # 与 a 完全相同
        ],
    )

    results = helper.search("int8_e2e", vector=[1, 2, 3, 4], top_k=3)
    # a 和 c 与 query 完全相同 → 距离 0 → score 1
    assert results[0]["score"] == 1.0
    # b 距离最远
    assert results[-1]["id"] == "b"


# ──────────── 9.14 SparseFloatVector ────────────


def test_9_14_sparse_create_with_ip(helper):
    """SparseFloatVector 配 IP（标准实践）。"""
    helper.create_collection(
        "sparse_ip",
        dimension=100,  # NNZ 上限
        vector_type="SparseFloatVector",
        metric="IP",
    )
    info = helper.get_collection("sparse_ip")
    assert info["vector_type"] == "SparseFloatVector"
    assert info["metric"] == "IP"
    assert info["dimension"] == 100


@pytest.mark.parametrize("metric", ["COSINE", "L2", "HAMMING", "JACCARD"])
def test_9_15_sparse_warns_for_non_ip(helper, metric):
    """SparseFloatVector 配非 IP 会被拒绝（标准实践是 IP）。

    教学：稀疏向量的几何意义是关键词权重，IP 直接累加关键词命中分数。
    """

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + f"_sparse_{metric}",
            "dimension": 10,
            "vector_type": "SparseFloatVector",
            "metric": metric,
        },
    )
    # 模型层抛 ValueError → FastAPI 转 422
    assert r.status_code == 422
    body = r.json()
    assert body["code"] != 0
    assert "SparseFloatVector" in str(body["message"])


def test_9_16_sparse_via_hybrid_search(helper):
    """SparseFloatVector 走 hybrid_search：dense + sparse 一起查。

    教学：稀疏向量不通过 /insert 接口（要传 dict），而是通过 /hybrid_search
    的 ``sparse`` 字段以 ``{关键词: 权重}`` 形式传入。
    """
    helper.create_collection(
        "sparse_hybrid",
        dimension=4,  # dense 维度
        vector_type="SparseFloatVector",
        metric="IP",
    )

    # dense 端插 3 条
    helper.insert(
        "sparse_hybrid",
        [
            {"id": "semantic", "vector": [1.0, 0.0, 0.0, 0.0], "payload": {}},
            {"id": "other", "vector": [0.0, 1.0, 0.0, 0.0], "payload": {}},
        ],
    )

    # hybrid_search：sparse 用 "kw_keyword" 字段加权
    # 真实场景 sparse payload 里应有 ``kw_xxx`` 字段；fake 通过 payload 模拟
    # 这里只验证能跑通 + 至少能拿到 1 条结果
    results = helper.hybrid_search(
        "sparse_hybrid",
        dense=[1.0, 0.0, 0.0, 0.0],
        dense_weight=1.0,
        sparse={"kw_keyword": 0.0},  # 无关键词命中
        sparse_weight=1.0,
        top_k=2,
    )
    # 至少能搜到 dense 部分
    assert len(results) >= 1


# ──────────── 9.17 内存占用对比（教学演示）────────────


def test_9_17_memory_footprint_comparison(helper):
    """同维度 D=768 下 6 种类型的理论内存（教学注释）。

    教学点：选 BinaryVector 可以把内存压到 FloatVector 的 1/32。
    本测试不直接测内存（fake 是 dict 存储），只演示创建对比。
    """
    cases = [
        ("FloatVector", 768, "COSINE", 4 * 768),  # 3072 bytes
        ("Float16Vector", 768, "COSINE", 2 * 768),  # 1536 bytes
        ("BFloat16Vector", 768, "COSINE", 2 * 768),  # 1536 bytes
        ("Int8Vector", 768, "L2", 768),  # 768 bytes
        ("BinaryVector", 768, "HAMMING", 768 // 8),  # 96 bytes
    ]
    for vt, dim, metric, _expected_bytes in cases:
        helper.create_collection(
            f"mem_{vt}",
            dimension=dim,
            vector_type=vt,
            metric=metric,
        )
        info = helper.get_collection(f"mem_{vt}")
        assert info["vector_type"] == vt
        assert info["dimension"] == dim


# ──────────── 9.18 非法 vector_type 值 422 ────────────


def test_9_18_invalid_vector_type_returns_422(helper):
    """非枚举值 → Pydantic 422。"""

    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + "_bad_vt",
            "dimension": 4,
            "vector_type": "NotAVectorType",
            "metric": "COSINE",
        },
    )
    assert r.status_code == 422
    body = r.json()
    assert body["code"] != 0
    assert "vector_type" in str(body["message"])


# ──────────── 9.19 集合信息暴露 vector_type ────────────


def test_9_19_collection_info_exposes_vector_type(helper):
    """GET /collections/{name} 必须返回 vector_type 字段。"""
    helper.create_collection(
        "info_vt",
        dimension=8,
        vector_type="BinaryVector",
        metric="HAMMING",
    )

    info = helper.get_collection("info_vt")
    assert "vector_type" in info
    assert info["vector_type"] == "BinaryVector"


# ──────────── 9.20 一旦创建不可改 ────────────


def test_9_20_vector_type_immutable(helper):
    """向量类型一旦创建不可改（与 dimension 一样属于不可变字段）。

    教学：想换类型只能 drop + rebuild → 数据会丢 → 设计 schema 时要想清楚。
    """
    helper.create_collection("immutable_vt", dimension=4, vector_type="FloatVector")
    info1 = helper.get_collection("immutable_vt")
    assert info1["vector_type"] == "FloatVector"

    # 重复创建同名集合应 409（同名 + 同 metric 仍能走完校验到 duplicate 检查）
    r = helper.client.post(
        "/api/v1/collections",
        json={
            "name": helper.prefix + "_immutable_vt",
            "dimension": 4,
            "vector_type": "FloatVector",  # 保持一致 → 跳过模型校验
            "metric": "COSINE",
        },
    )
    assert r.status_code == 409
