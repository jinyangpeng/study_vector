"""领域模型：业务层统一数据结构。

设计原则：
- 不引用任何具体向量库 SDK
- 所有数据结构与具体库解耦，由 Repository 实现层完成翻译
- 字段类型尽量宽松（id 允许 str/int/UUID），以兼容不同向量库的主键约定
- ``extra="forbid"``：契约严格 —— OpenAPI 之外的字段直接 422，便于教学平台
  把"乱传字段"暴露为可见错误
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

# ------------------------- 枚举 -------------------------

class DistanceMetric(str, Enum):
    """距离 / 相似度度量。

    跨库常用映射：
    - COSINE / IP / L2 / HAMMING / JACCARD
    """

    COSINE = "COSINE"
    EUCLIDEAN = "L2"
    INNER_PRODUCT = "IP"
    HAMMING = "HAMMING"
    JACCARD = "JACCARD"


class VectorType(str, Enum):
    """向量数据类型。

    教学点：选错向量类型 = 维度/度量/索引/距离全错。

    | 类型 | 内存 | 适用 | 支持的距离 |
    |---|---|---|---|
    | **FloatVector**（默认）| 4×D bytes | 通用 embedding | COSINE / L2 / IP |
    | **BinaryVector** | D/8 bytes | 哈希特征/图像 | HAMMING / JACCARD |
    | **Float16Vector** | 2×D bytes | 显存省 | COSINE / L2 / IP |
    | **BFloat16Vector** | 2×D bytes | 训练 | COSINE / L2 / IP |
    | **SparseFloatVector** | 4×NNZ bytes | 关键词 / SPLADE | IP |
    | **Int8Vector** | D bytes | 量化 | L2 |
    """

    FLOAT_VECTOR = "FloatVector"
    BINARY_VECTOR = "BinaryVector"
    FLOAT16_VECTOR = "Float16Vector"
    BFLOAT16_VECTOR = "BFloat16Vector"
    SPARSE_FLOAT_VECTOR = "SparseFloatVector"
    INT8_VECTOR = "Int8Vector"


class IndexType(str, Enum):
    """索引类型枚举（覆盖主流选项）。"""

    FLAT = "FLAT"
    IVF_FLAT = "IVF_FLAT"
    IVF_SQ8 = "IVF_SQ8"
    IVF_PQ = "IVF_PQ"
    HNSW = "HNSW"
    ANNOY = "ANNOY"
    AUTOINDEX = "AUTOINDEX"  # Milvus / Qdrant 等支持的"自动"索引
    DISKANN = "DISKANN"  # Milvus 2.4+ 内存+磁盘混合索引


class ConsistencyLevel(str, Enum):
    """Milvus 一致性等级。

    教学点：CAP 三角在 Milvus 中的体现。
    """

    STRONG = "Strong"
    SESSION = "Session"
    BOUNDED = "Bounded"
    EVENTUALLY = "Eventually"


# ------------------------- 基础配置 -------------------------

# 业务层统一 Pydantic 配置：禁止未声明字段
_CONTRACT_CONFIG = ConfigDict(extra="forbid", str_strip_whitespace=True)


# ------------------------- 集合 -------------------------

class CollectionSchema(BaseModel):
    """业务层集合（表）Schema 定义。"""

    model_config = _CONTRACT_CONFIG

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="集合名称（字母开头 + 字母数字下划线）",
    )
    dimension: int = Field(..., gt=0, le=65536, description="向量维度")
    metric: DistanceMetric = Field(
        default=DistanceMetric.COSINE, description="距离/相似度度量"
    )
    vector_type: VectorType = Field(
        default=VectorType.FLOAT_VECTOR,
        description=(
            "向量数据类型。"
            "BinaryVector 维度需为 8 的倍数；"
            "SparseFloatVector 的 dimension 表示 NNZ 上限，"
            "实际向量以 dict {idx: value} 形式存储。"
        ),
    )
    primary_field: str = Field(
        default="id",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="主键字段名（字母开头 + 字母数字下划线）",
    )
    vector_field: str = Field(
        default="vector",
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="向量字段名（字母开头 + 字母数字下划线）",
    )
    description: str | None = Field(default=None, description="集合描述")
    index_type: IndexType = Field(
        default=IndexType.AUTOINDEX, description="索引类型（实现层可能忽略）"
    )
    consistency_level: ConsistencyLevel = Field(
        default=ConsistencyLevel.SESSION,
        description="Milvus 一致性等级（CAP 三角取舍）",
    )

    @model_validator(mode="after")
    def _validate_vector_type_metric(self) -> CollectionSchema:
        """向量类型与距离度量的兼容性校验。"""
        binary_metrics = {DistanceMetric.HAMMING, DistanceMetric.JACCARD}
        float_only_metrics = {
            DistanceMetric.COSINE,
            DistanceMetric.EUCLIDEAN,
            DistanceMetric.INNER_PRODUCT,
        }
        if self.vector_type == VectorType.BINARY_VECTOR:
            if self.metric not in binary_metrics:
                raise ValueError(
                    f"BinaryVector 只能配 HAMMING / JACCARD，当前 {self.metric.value} 不兼容"
                )
            if self.dimension % 8 != 0:
                raise ValueError(
                    f"BinaryVector 维度必须是 8 的倍数（按位打包），当前 {self.dimension}"
                )
        elif self.vector_type == VectorType.SPARSE_FLOAT_VECTOR:
            if self.metric != DistanceMetric.INNER_PRODUCT:
                raise ValueError(
                    f"SparseFloatVector 配 IP 度量（标准实践），当前 {self.metric.value} 不推荐"
                )
        elif self.vector_type in {
            VectorType.FLOAT_VECTOR,
            VectorType.FLOAT16_VECTOR,
            VectorType.BFLOAT16_VECTOR,
        }:
            if self.metric not in float_only_metrics:
                raise ValueError(
                    f"{self.vector_type.value} 配 COSINE / L2 / IP，当前 {self.metric.value} 不兼容"
                )
        elif self.vector_type == VectorType.INT8_VECTOR:
            if self.metric != DistanceMetric.EUCLIDEAN:
                raise ValueError(
                    f"Int8Vector 配 L2 度量，当前 {self.metric.value} 不兼容"
                )
        return self


class CollectionInfo(BaseModel):
    """集合元信息。"""

    model_config = _CONTRACT_CONFIG

    name: str
    dimension: int
    metric: DistanceMetric
    vector_type: VectorType = VectorType.FLOAT_VECTOR
    row_count: int = 0
    loaded: bool = False
    consistency_level: ConsistencyLevel = ConsistencyLevel.SESSION
    created_at: datetime | None = None
    indexes: list[IndexInfo] = Field(default_factory=list)


# ------------------------- 向量记录 -------------------------

class VectorRecord(BaseModel):
    """单条向量记录。"""

    model_config = _CONTRACT_CONFIG

    id: str | int | UUID = Field(default_factory=lambda: uuid4())
    vector: list[float] = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None  # 仅在检索结果中填充


# ------------------------- 检索 -------------------------

class SearchRequest(BaseModel):
    """向量检索请求。"""

    model_config = _CONTRACT_CONFIG

    # collection 由 path 参数注入；保留为可选以便纯业务调用
    collection: str | None = Field(default=None, description="集合名（由 path 注入）")
    vector: list[float] = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=1000)
    # 通用过滤表达式：业务层只传 dict，实现层翻译为原生表达式
    # 格式： {"field": "value", "active": true, "count": 3}
    filter_expr: dict[str, Any] | None = None
    output_fields: list[str] | None = None
    # 限定扫描的分区（不指定则扫描全部分区）
    partition_names: list[str] | None = None
    # 检索参数（IVF nprobe / HNSW ef 等）
    search_params: dict[str, Any] | None = None


class SearchResult(BaseModel):
    """检索命中。"""

    model_config = _CONTRACT_CONFIG

    id: str | int | UUID
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)


# ------------------------- 其它业务对象（供 Phase 1.3+ 使用） -------------------------


class LoadRequest(BaseModel):
    """加载集合请求。"""

    model_config = _CONTRACT_CONFIG

    replica_number: int = Field(default=1, ge=1, le=16)
    partition_names: list[str] | None = None


class DeleteRequest(BaseModel):
    """删除请求：按 id 或按 filter（二选一）。"""

    model_config = _CONTRACT_CONFIG

    ids: list[str] | None = None
    filter: dict[str, Any] | None = None

    @model_validator(mode="after")
    def _exactly_one(self) -> DeleteRequest:
        """契约：`oneOf [ids, filter]` —— 必须二选一，不能都不传也不能都传。"""
        has_ids = self.ids is not None
        has_filter = self.filter is not None
        if has_ids == has_filter:  # 同时为 True 或同时为 False
            raise ValueError("ids 与 filter 必须二选一（不能同时为 None / 不能同时存在）")
        if has_ids and len(self.ids or []) < 1:
            raise ValueError("ids 非空时至少 1 个")
        return self


class QueryRequest(BaseModel):
    """标量检索 / 计数请求。"""

    model_config = _CONTRACT_CONFIG

    filter: dict[str, Any] | None = None
    output_fields: list[str] | None = None
    limit: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)
    count_only: bool = False


class IndexInfo(BaseModel):
    """索引信息。"""

    model_config = _CONTRACT_CONFIG

    field_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )
    index_type: IndexType
    metric_type: DistanceMetric
    params: dict[str, Any] = Field(default_factory=dict)


class CreateIndexRequest(BaseModel):
    """建索引请求。"""

    model_config = _CONTRACT_CONFIG

    field_name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="要建索引的字段名（一般是向量字段，字母开头 + 字母数字下划线）",
    )
    index_type: IndexType
    metric_type: DistanceMetric = Field(default=DistanceMetric.COSINE)
    params: dict[str, Any] = Field(default_factory=dict)


class PartitionInfo(BaseModel):
    """分区信息。"""

    model_config = _CONTRACT_CONFIG

    name: str
    row_count: int = 0
    created_at: datetime | None = None


class CreatePartitionRequest(BaseModel):
    """建分区请求。"""

    model_config = _CONTRACT_CONFIG

    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="分区名（字母开头 + 字母数字下划线）",
    )


# ------------------------- Alias -------------------------

class CreateAliasRequest(BaseModel):
    """创建 alias 请求。"""

    model_config = _CONTRACT_CONFIG

    alias: str = Field(
        ...,
        min_length=1,
        max_length=255,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="alias 名（字母开头 + 字母数字下划线）",
    )


# ------------------------- Hybrid Search -------------------------

class HybridSearchRequest(BaseModel):
    """混合检索请求：dense + sparse 多路召回 + RRF 重排。

    教学点：
    - 真实生产场景下，常常 dense（语义）+ sparse（关键词）联合检索
    - 各自走自己的 ANN 索引；后用 RRF（Reciprocal Rank Fusion）合并排序
    """

    model_config = _CONTRACT_CONFIG

    collection: str | None = Field(default=None, description="集合名（path 注入）")
    # 稠密向量（语义召回）
    dense: list[float] | None = Field(default=None, description="稠密向量（语义）")
    dense_weight: float = Field(default=1.0, description="稠密路权重（RRF 系数）")
    # 稀疏向量（关键词召回；用 dict {idx: value} 表示）
    sparse: dict[str, float] | None = Field(default=None, description="稀疏向量（关键词）")
    sparse_weight: float = Field(default=1.0, description="稀疏路权重（RRF 系数）")
    top_k: int = Field(default=10, ge=1, le=1000)
    filter_expr: dict[str, Any] | None = None
    output_fields: list[str] | None = None
    # RRF 公式中的 k 平滑项（避免分母为 0）
    rrf_k: int = Field(default=60, ge=1, le=1000, description="RRF 平滑项 k")


# ------------------------- Database / User -------------------------

class CreateDatabaseRequest(BaseModel):
    """创建数据库请求。"""

    model_config = _CONTRACT_CONFIG

    name: str = Field(..., min_length=1, max_length=255, pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$")


class CreateUserRequest(BaseModel):
    """创建用户请求（教学辅助；Milvus RBAC）。"""

    model_config = _CONTRACT_CONFIG

    user_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
        description="用户名（字母开头 + 字母数字下划线）",
    )
    password: str = Field(..., min_length=1, max_length=256)


class UserInfo(BaseModel):
    """用户信息。"""

    model_config = _CONTRACT_CONFIG

    user_name: str = Field(
        ...,
        min_length=1,
        max_length=128,
        pattern=r"^[a-zA-Z][a-zA-Z0-9_]*$",
    )
    created_at: datetime | None = None


# ------------------------- Health -------------------------

class HealthCheck(BaseModel):
    """健康检查响应。"""

    model_config = _CONTRACT_CONFIG

    status: str
    checks: dict[str, str] = Field(default_factory=dict)
