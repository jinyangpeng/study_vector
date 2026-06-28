# 09 用户（Users）与 RBAC

## 为什么需要 RBAC？

生产环境**绝对不要**用 `root` 跑业务：
- `root` 删集合 = 全公司宕机
- 业务代码泄露 = 全库被拖

RBAC = **Role-Based Access Control**：
- **用户（User）**= 身份
- **角色（Role）**= 权限的集合
- **权限（Privilege）**= 具体的操作

## 1. 列出用户

```bash
curl http://localhost:8000/api/v1/users
```

返回：
```json
{
  "code": 0,
  "data": [
    {"user_name": "root", "roles": ["admin"]},
    {"user_name": "reader_01", "roles": ["readonly"]}
  ]
}
```

## 2. 创建用户

```bash
curl -X POST http://localhost:8000/api/v1/users \
  -d '{
    "user_name": "reader_01",
    "password": "P@ssw0rd!"
  }'
```

## 3. 角色 vs 用户

Milvus 内置 3 个角色：

| 角色 | 权限 |
|---|---|
| `admin` | 所有权限（含删除） |
| `readonly` | 仅查询（Query/Search） |
| `readwrite` | 读写（不含管理） |

## 4. 删除用户

```bash
curl -X DELETE http://localhost:8000/api/v1/users/reader_01
```

## 5. 生产 RBAC 实践

```
应用服务
  ├── search-service     → role: readonly
  ├── indexer-service    → role: readwrite
  ├── admin-ops          → role: admin
  └── etl-batch          → role: readwrite (限流)
```

最小权限原则：
- 检索服务 = readonly
- 写入服务 = readwrite
- 管理操作 = admin（人工触发，不用服务账号）

## 6. 凭据管理

- 密码不进代码 / Git
- 用环境变量 / 密钥管理（K8s Secret / Vault）
- 定期轮换（90 天）
- 启用 TLS（防止明文传输）

## 7. 审计

- 开启 Milvus audit log
- 关键操作（delete / drop）必须留痕
- 异常登录告警

## 8. 接下来

你已经掌握了 Milvus 的**全功能点**！可以回到 [集合管理](01-first-collection.md) 把整个流程串起来跑一遍。
