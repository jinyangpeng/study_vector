# 02 插入与检索

## 1. 插入单条向量

每条向量 = 1 个 `id`（主键） + 1 个 `vector`（向量数组） + 任意 `payload`（业务元数据）。

```bash
curl -X POST http://localhost:8000/api/v1/vectors/demo_chunks/insert \
  -H "Content-Type: application/json" \
  -d '[
    {
      "id": "doc_001",
      "vector": [0.95, 0.05, 0.0, 0.0],
      "payload": {"category": "tech", "lang": "zh", "source": "news"}
    }
  ]'
```

> **维度必须 = 集合 dimension**（这里是 4）；不一致会 422。

## 2. 批量插入

```bash
curl -X POST http://localhost:8000/api/v1/vectors/demo_chunks/insert \
  -H "Content-Type: application/json" \
  -d '[
    {"id": "doc_002", "vector": [0.1, 0.9, 0.0, 0.0], "payload": {"category": "blog"}},
    {"id": "doc_003", "vector": [0.0, 0.0, 1.0, 0.0], "payload": {"category": "doc"}},
    {"id": "doc_004", "vector": [0.5, 0.5, 0.0, 0.0], "payload": {"category": "tech"}}
  ]'
```

教学点：批量插入走同一 RPC，比单条循环快几个数量级。

## 3. 向量检索

```bash
curl -X POST http://localhost:8000/api/v1/vectors/demo_chunks/search \
  -H "Content-Type: application/json" \
  -d '{
    "vector": [0.95, 0.05, 0.0, 0.0],
    "top_k": 5,
    "filter_expr": {"category": "tech"}
  }'
```

响应：

```json
{
  "code": 0,
  "data": [
    {"id": "doc_001", "score": 1.0,     "payload": {"category": "tech"}},
    {"id": "doc_004", "score": 0.7071,  "payload": {"category": "tech"}}
  ]
}
```

**score 解读**：
- COSINE：1.0 = 完全相同，0 = 正交，-1 = 完全相反
- L2：score = 1/(1+distance)，越大越近
- IP：原始内积，未归一化时可比性差

## 4. 按 id 拉取

```bash
curl -X POST http://localhost:8000/api/v1/vectors/demo_chunks/get \
  -H "Content-Type: application/json" \
  -d '{"ids": ["doc_001", "doc_002"]}'
```

## 5. 删除

```bash
curl -X POST http://localhost:8000/api/v1/vectors/demo_chunks/delete \
  -H "Content-Type: application/json" \
  -d '{"ids": ["doc_001"]}'
```

## 6. 常见错误

| 错误 | 原因 |
|---|---|
| `维度不一致 422` | vector 长度 ≠ 集合 dimension |
| `id 重复 409` | insert 用已存在的 id（用 upsert 可覆盖） |
| `filter 字段不存在` | payload 字段名拼写错 |

## 7. 接下来

- [索引](03-indexes.md) — 加速检索的关键
- [检索进阶](04-search-and-hybrid.md) — filter、混合检索
