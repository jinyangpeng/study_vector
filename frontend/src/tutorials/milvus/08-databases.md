# 08 数据库（Databases）— 多租户隔离

## 为什么需要多 DB？

Milvus 默认有 `default` 数据库。多租户场景下：
- 不同客户的数据**不能混在一起**
- 需要物理 / 逻辑隔离
- 不同业务线独立管理

## Database vs Collection

| 维度 | Collection | Database |
|---|---|---|
| 数量 | 多（业务表） | 少（业务域） |
| 隔离粒度 | 同 DB 内可见 | 跨 DB 不可见 |
| 适用 | 同一类数据细分 | 不同业务/租户 |

## 1. 列出数据库

```bash
curl http://localhost:8000/api/v1/databases
```

返回：`["default"]`

## 2. 创建数据库

```bash
curl -X POST http://localhost:8000/api/v1/databases \
  -d '{"name": "tenant_a"}'
```

## 3. 在指定 DB 下创建集合

V1 简化：业务 DB 切换通过 backend 配置（MILVUS_DB_NAME）。

真实 Milvus：

```python
from pymilvus import connections, db

conn = connections.connect(host="...", port="19530")
db.using_database("tenant_a")

# 后续 collection 操作都在 tenant_a 下
```

## 4. 删除数据库

```bash
curl -X DELETE http://localhost:8000/api/v1/databases/tenant_a
```

**该 DB 下所有集合会被一起删除！** 生产慎用。

## 5. 多租户架构

```
Milvus
├── default (系统)
│   └── system_collections
├── tenant_a
│   ├── docs
│   └── vectors
├── tenant_b
│   ├── docs
│   └── vectors
└── tenant_c
    ├── docs
    └── vectors
```

每个租户：
- 集合名可相同（互不影响）
- 资源（内存/CPU）独立
- 权限可独立控制

## 6. 经验

- 简单业务用 collection 内的 `tenant_id` 字段隔离即可
- **真物理隔离**才用多 DB（合规、审计场景）
- DB 数量 < 10（管理成本）

## 7. 接下来

- [用户](09-users.md) — RBAC 权限控制
