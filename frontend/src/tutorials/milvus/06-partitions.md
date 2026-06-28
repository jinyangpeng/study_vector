# 06 分区（Partitions）

## 为什么需要分区？

想象一个电商场景：
- 3 年订单数据，每个月都查
- 全表扫描慢，按月切分 = 查 1 月只要扫 1/36

Milvus 的 **partition** 就是这种"集合内切分"。

## 适用场景

| 场景 | 切分方式 |
|---|---|
| **时间序列** | `y2024` / `y2025` / `m202401` |
| **多租户** | `tenant_a` / `tenant_b` |
| **业务类型** | `premium` / `free` |
| **冷热数据** | `hot` / `warm` / `cold` |

## 1. 创建分区

```bash
curl -X POST http://localhost:8000/api/v1/collections/orders/partitions \
  -d '{"name": "y2024"}'
```

每个集合默认有 `_default` 分区。未指定 partition 写入的数据都进 `_default`。

## 2. 列出分区

```bash
curl http://localhost:8000/api/v1/collections/orders/partitions
```

返回：`["_default", "y2024", "y2025"]`

## 3. 检索时限定分区

```bash
curl -X POST .../vectors/orders/search \
  -d '{
    "vector": [...],
    "top_k": 10,
    "partition_names": ["y2024"]
  }'
```

**性能差异**：
- 全分区扫描：1M 向量
- 单分区扫描：300K 向量（按年切 3 年）
- 提速 ~3.3x

## 4. 按分区加载（load）

```bash
curl -X POST http://localhost:8000/api/v1/collections/orders/load \
  -d '{"partition_names": ["y2024"]}'
```

只把热分区加载到内存 → 省内存。

## 5. 写入时标记分区

写入 API 不直接指定 partition，**业务上用 payload 标记**：

```json
{
  "id": "ord_001",
  "vector": [...],
  "payload": {"_partition": "y2024", "date": "2024-03-01"}
}
```

检索时用 `filter_expr` + `partition_names` 联动：
- `partition_names`：物理切分
- `filter_expr`：标量过滤

## 6. 删除分区（高危）

```bash
curl -X DELETE http://localhost:8000/api/v1/collections/orders/partitions/y2023
```

**该分区内所有数据丢失，不可恢复**。生产必须：
1. 先备份
2. 用别名/灰度替代
3. 确认后再删

## 7. 经验

- 切分粒度：不超过 100 个分区（管理成本 < 性能收益）
- 时间分区建议按月/季，不要按天
- 冷数据定期 compact → 释放磁盘

## 8. 接下来

- [别名](07-aliases.md) — 蓝绿部署关键
