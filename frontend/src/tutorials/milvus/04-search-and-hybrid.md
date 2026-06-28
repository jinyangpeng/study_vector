# 04 检索进阶：标量过滤 + 混合检索

## 1. 基础检索回顾

```bash
curl -X POST http://localhost:8000/api/v1/vectors/demo_chunks/search \
  -d '{"vector": [...], "top_k": 5}'
```

## 2. 标量过滤（filter_expr）

先按 payload 字段过滤，再做向量检索。**速度提升显著**（数据集大时几个数量级）。

### 简单等值

```json
{"filter_expr": {"category": "tech"}}
```

### 数值范围

```json
{"filter_expr": {"price": {"$gt": 100}}}
```

### 多条件 AND

```json
{"filter_expr": {"category": "tech", "lang": "zh"}}
```

### $or / $in / $ne

```json
{"filter_expr": {"$or": [{"category": "news"}, {"category": "blog"}]}}
```

```json
{"filter_expr": {"category": {"$in": ["news", "blog"]}}}
```

```json
{"filter_expr": {"category": {"$ne": "spam"}}}
```

### 嵌套对象

```json
{"filter_expr": {"meta.lang": "zh"}}
```

## 3. 输出字段控制

```json
{
  "vector": [...],
  "top_k": 5,
  "output_fields": ["title", "url", "meta.lang"]
}
```

不写则只返回 `id` + `score` + `payload`。

## 4. 限定分区

```json
{
  "vector": [...],
  "top_k": 5,
  "partition_names": ["y2024", "y2025"]
}
```

## 5. 混合检索（Hybrid / RRF）

**场景**：dense（语义）拿语义匹配，sparse（关键词）拿字面匹配，两路互补。

```bash
curl -X POST http://localhost:8000/api/v1/vectors/docs/hybrid_search \
  -H "Content-Type: application/json" \
  -d '{
    "dense": [0.1, 0.2, 0.3, 0.4],
    "dense_weight": 1.0,
    "sparse": {"milvus": 1.0, "search": 0.5, "engine": 0.3},
    "sparse_weight": 0.5,
    "rrf_k": 60,
    "top_k": 10
  }'
```

### RRF (Reciprocal Rank Fusion) 公式

```
score(d) = Σ_i  weight_i / (k + rank_i(d))
```

- `k` 越大各路贡献越平均（默认 60）
- `weight` 控制该路在总分中的占比
- 排名 1 的项加分最多

### 何时用混合检索？

- 关键词必须命中（如"Milvus 教程"）
- 还想理解语义（如"向量数据库入门"）
- 单一检索召回率不够

## 6. 检索参数调优

### HNSW

```json
{"search_params": {"ef": 64}}
```

`ef` 越大召回越高越慢（搜索时动态参数）。

### IVF

```json
{"search_params": {"nprobe": 16}}
```

`nprobe` 越大召回越高越慢（探测的聚类数）。

## 7. 接下来

- [向量](05-vectors.md) — 数据结构详解
- [分区](06-partitions.md) — 按业务切分数据
