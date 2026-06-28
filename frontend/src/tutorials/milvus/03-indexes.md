# 03 索引

## 为什么需要索引？

暴力搜索（FLAT）的时间复杂度是 O(N×D)。百万向量就要 10^9 次距离计算。
**索引 = 用空间换时间**，让搜索变成 O(log N) 量级。

## Milvus 8 种索引

| 索引 | 算法 | 适用 | 关键参数 |
|---|---|---|---|
| **AUTOINDEX** | Milvus 自适应 | 生产首选 | 无 |
| **HNSW** | 图索引 | 高召回 / 内存允许 | `M`, `efConstruction` |
| **IVF_FLAT** | 倒排 + FLAT | 大数据 / 速度优先 | `nlist` |
| **IVF_SQ8** | 标量量化 | 4× 压缩 | `nlist` |
| **IVF_PQ** | 乘积量化 | 极大压缩 | `nlist`, `m`, `nbits` |
| **FLAT** | 暴力 | 精确 / 小数据 | 无 |
| **ANNOY** | 树 | 只读 | `n_trees` |
| **DISKANN** | 磁盘 | 内存不够 | — |

## 1. 建 HNSW 索引

```bash
curl -X POST http://localhost:8000/api/v1/collections/demo_chunks/indexes \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "vector",
    "index_type": "HNSW",
    "metric_type": "COSINE",
    "params": {"M": 16, "efConstruction": 64}
  }'
```

- `M` = 每个节点的边数（16-64，越大召回越高越慢）
- `efConstruction` = 构建时搜索深度（越大越慢但索引质量高）

## 2. 建 IVF_PQ（极大压缩）

```bash
curl -X POST http://localhost:8000/api/v1/collections/demo_chunks/indexes \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "vector",
    "index_type": "IVF_PQ",
    "metric_type": "L2",
    "params": {"nlist": 1024, "m": 8, "nbits": 8}
  }'
```

- `nlist` = 聚类数（经验值：4√N ~ 16√N）
- `m` = 子量化器数（必须整除 dimension）
- `nbits` = 每子量化器位数（8 = 256 桶）

## 3. 查询索引

```bash
curl http://localhost:8000/api/v1/collections/demo_chunks/indexes
```

## 4. 删除索引

```bash
curl -X DELETE http://localhost:8000/api/v1/collections/demo_chunks/indexes/vector
```

> **删索引会失去检索能力**（要重建）。生产环境慎用。

## 5. 选错会怎样？

| 错误 | 后果 |
|---|---|
| 索引 metric ≠ 集合 metric | 检索报错 |
| IVF_PQ 的 m 不整除 dimension | 建索引失败 |
| nlist > 数据量 | 检索召回低（聚类太空） |
| nlist 太小 | 检索慢（每聚类向量太多） |

## 6. 经验值

| 数据量 | 推荐 |
|---|---|
| < 10万 | FLAT（精确） |
| 10万 - 100万 | HNSW / IVF_FLAT |
| 100万 - 1亿 | IVF_PQ / AUTOINDEX |
| > 1亿 | DISKANN / 分片 |

## 7. 接下来

- [检索进阶](04-search-and-hybrid.md) — 检索参数调优
