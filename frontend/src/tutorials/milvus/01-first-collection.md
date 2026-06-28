# 01 第一个集合

## 概念

Milvus 中"集合（Collection）"类比 MySQL 的"表"——是组织向量数据的容器。

一个集合 = **schema**（字段定义）+ **索引**（加速搜索的数据结构）+ **数据**（向量行）。

## 1. 创建集合

```bash
curl -X POST http://localhost:8000/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "demo_chunks",
    "dimension": 768,
    "vector_type": "FloatVector",
    "metric": "COSINE",
    "index_type": "AUTOINDEX",
    "consistency_level": "Session",
    "description": "BGE-base 嵌入的教学集合"
  }'
```

## 2. 参数解释

| 字段 | 必填 | 说明 |
|---|---|---|
| `name` | ✅ | 集合名（字母开头 + 字母数字下划线） |
| `dimension` | ✅ | 向量维度（与嵌入模型输出一致） |
| `vector_type` |  | `FloatVector`（默认）/`BinaryVector`/`Float16`/`SparseFloat` 等 |
| `metric` |  | `COSINE`（推荐）/`L2`/`IP`/`HAMMING`/`JACCARD` |
| `index_type` |  | `AUTOINDEX`（推荐）/`HNSW`/`IVF_FLAT` 等 |
| `consistency_level` |  | `Session`（默认）/`Strong`/`Bounded`/`Eventually` |

## 3. 期望响应

```json
{
  "code": 0,
  "message": "success",
  "data": { "name": "demo_chunks" }
}
```

## 4. 选错度量会怎样？

- **COSINE** 看方向不看模长（最常用）
- **L2** 看直线距离（对模长敏感）
- **IP** 看"对齐度"，归一化后等价 COSINE

**生产经验**：文本嵌入基本用 COSINE；图像/坐标用 L2；推荐系统归一化后用 IP。

## 5. 接下来

- [插入向量](02-insert-and-search.md)
- [索引](03-indexes.md)
- [检索](04-search-and-hybrid.md)
