"""领域模型：业务层统一数据结构。

设计原则：
- 不引用任何具体向量库 SDK
- 所有数据结构与具体库解耦，由 Repository 实现层完成翻译
- 字段类型尽量宽松（id 允许 str/int/UUID），以兼容不同向量库的主键约定
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

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


class IndexType(str, Enum):
    """索引类型枚举（覆盖主流选项）。"""

    FLAT = "FLAT"
    IVF_FLAT = "IVF_FLAT"
    IVF_SQ8 = "IVF_SQ8"
    IVF_PQ = "IVF_PQ"
    HNSW = "HNSW"
    ANNOY = "ANNOY"
    AUTOINDEX = "AUTOINDEX"  # Milvus / Qdrant 等支持的"自动"索引


# ------------------------- 集合 -------------------------

class CollectionSchema(BaseModel):
    """业务层集合（表）Schema 定义。"""

    name: str = Field(..., min_length=1, max_length=255, description="集合名称")
    dimension: int = Field(..., gt=0, le=65536, description="向量维度")
    metric: DistanceMetric = Field(
        default=DistanceMetric.COSINE, description="距离/相似度度量"
    )
    primary_field: str = Field(default="id", description="主键字段名")
    vector_field: str = Field(default="vector", description="向量字段名")
    description: str | None = Field(default=None, description="集合描述")
    index_type: IndexType = Field(
        default=IndexType.AUTOINDEX, description="索引类型（实现层可能忽略）"
    )


class CollectionInfo(BaseModel):
    """集合元信息。"""

    name: str
    dimension: int
    metric: DistanceMetric
    row_count: int = 0
    created_at: datetime | None = None


# ------------------------- 向量记录 -------------------------

class VectorRecord(BaseModel):
    """单条向量记录。"""

    id: str | int | UUID = Field(default_factory=lambda: uuid4())
    vector: list[float] = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None  # 仅在检索结果中填充


# ------------------------- 检索 -------------------------

class SearchRequest(BaseModel):
    """向量检索请求。"""

    # collection 由 path 参数注入；保留为可选以便纯业务调用
    collection: str | None = Field(default=None, description="集合名（由 path 注入）")
    vector: list[float] = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=1000)
    # 通用过滤表达式：业务层只传 dict，实现层翻译为原生表达式
    # 格式： {"field": "value", "active": true, "count": 3}
    filter_expr: dict[str, Any] | None = None
    output_fields: list[str] | None = None


class SearchResult(BaseModel):
    """检索命中。"""

    id: str | int | UUID
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)
