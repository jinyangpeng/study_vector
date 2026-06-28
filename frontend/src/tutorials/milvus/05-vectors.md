# 05 向量：数据结构与最佳实践

## 1. 单条向量的结构

```json
{
  "id": "doc_001_chunk_007",
  "vector": [0.012, -0.034, 0.056, 0.078, ...],
  "payload": {
    "category": "tech",
    "lang": "zh",
    "title": "Milvus 入门",
    "tags": ["向量", "数据库"]
  }
}
```

- **id**：主键。VARCHAR 类型。建议用业务 ID（如 `doc_hash_chunk_idx`），方便溯源。
- **vector**：向量数组。长度 = 集合 `dimension`。
- **payload**：JSON 对象。存**可过滤**的业务字段。

## 2. 选 id 的策略

| 策略 | 场景 |
|---|---|
| **UUID** | 不关心业务含义，幂等性最简单 |
| **业务 ID**（如 `url_hash`） | 可溯源、去重、去重插入 |
| **auto_id** | 数据库自增，业务无意义 |

> 业务 ID 优于 UUID：你能从日志中直接定位到原始内容。

## 3. 何时用 upsert 代替 insert？

```bash
# upsert：存在则更新，不存在则插入
curl -X POST .../vectors/demo_chunks/upsert -d '[{...}]'
```

**适用**：
- 文档内容变更，需要更新向量
- 数据有重跑逻辑
- ETL 流程

**不适用**：
- 严格只增（用 insert + auto_id 性能更好）
- 频繁单条更新（性能差，Milvus 走 batch）

## 4. 软删除 vs 硬删除

- `delete` API 走**软删除**（标记 tombstone）
- 真正的物理删除在后台 compaction
- 大批量删除后建议手动触发 compaction

```bash
# 删 50% 数据后建议
curl -X POST .../collections/demo_chunks/compact
```

## 5. payload 字段的索引

如果经常按 `category` / `lang` 过滤，建议建标量索引：

```bash
curl -X POST .../collections/demo_chunks/indexes \
  -d '{"field_name": "category", "index_type": "INVERTED"}'
```

不建索引 → 过滤走全扫描，数据量大时慢。

## 6. 维度选择实战

| 嵌入模型 | 维度 | 内存 / 1M 向量 |
|---|---|---|
| BGE-small | 384 | 1.5 GB |
| BGE-base | 768 | 3 GB |
| OpenAI text-embedding-3-small | 1536 | 6 GB |
| OpenAI text-embedding-3-large | 3072 | 12 GB |

**经验**：能选 768 就别选 1536。维度翻倍 = 内存 + 100%，但召回通常只 + 5%。

## 7. 性能陷阱

| 陷阱 | 后果 | 解法 |
|---|---|---|
| 单条 insert | RPC 太多，10x 慢 | 批量 ≥ 100 |
| 大 payload（>10KB） | 内存膨胀 | 移到外部 KV |
| 不归一化 + IP 度量 | 检索结果奇怪 | 先 L2 normalize 再用 IP |
| 频繁 delete + insert | tombstone 堆积 | 定期 compact |

## 8. 接下来

- [分区](06-partitions.md) — 按业务切分
- [别名](07-aliases.md) — 零停机升级
