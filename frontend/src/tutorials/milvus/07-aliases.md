# 07 别名（Aliases）— 零停机升级

## 业务痛点

场景：你的搜索服务写死了 `docs` 集合名。
要升级 schema（换 dimension、改 metric）怎么办？

- 直接改 `docs` 集合？→ 业务中断
- 用 `docs_v2` 替换？→ 业务代码全改

**Alias 解法**：业务代码访问 `docs_latest`（alias），底层切集合，业务无感。

## 概念

- **alias** = 集合的"逻辑名"
- 一个 alias 可指向**一个**集合（互斥）
- 业务代码 → alias → 实际集合

```
docs_latest → docs_v2   (切换)
docs_latest → docs_v1   (回滚)
```

## 1. 创建 alias

```bash
curl -X POST http://localhost:8000/api/v1/collections/docs_v1/alias \
  -d '{"alias": "docs_latest"}'
```

## 2. 业务代码访问 alias

业务代码检索时直接用 alias 代替集合名：

```bash
curl -X POST http://localhost:8000/api/v1/vectors/docs_latest/search \
  -d '{"vector": [...], "top_k": 5}'
```

> V1 简化版：alias 在 API 路径中与集合名等价。

## 3. 列出集合的 aliases

```bash
curl http://localhost:8000/api/v1/collections/docs_v1/alias
```

返回：`["docs_latest"]`

## 4. 零停机切换

```bash
# 1. 新集合写入数据
curl -X POST .../collections -d '{"name": "docs_v2", ...}'
# ... 灌入数据 ...

# 2. 切换：drop 旧 alias + create 到新集合
curl -X DELETE .../collections/docs_v1/alias/docs_latest
curl -X POST .../collections/docs_v2/alias -d '{"alias": "docs_latest"}'

# 3. 验证
curl http://localhost:8000/api/v1/collections/docs_v2/alias
# → ["docs_latest"]
```

> 真 Milvus 提供 `alterAlias` 原子操作；V1 简化版走两步。

## 5. 经典用法

### 蓝绿部署

```
docs_latest  →  docs_blue
docs_canary  →  docs_green  (1% 流量)
```

切 1% → 100% 全量，全过程业务不感知。

### 灰度发布

```
old_version  →  docs_v1
new_version  →  docs_v2
```

新版本用 alias 验证，对比质量后再切。

### 版本回滚

发现 v2 召回率下降？一行命令切回 v1。

## 6. 经验

- 业务代码**永远**写 alias，不写死集合名
- alias 命名规范：`<业务>_<环境>`（如 `docs_prod`、`docs_staging`）
- 多 alias 可以指向同一集合（用于"读/写分离"等）

## 7. 接下来

- [数据库](08-databases.md) — 多租户隔离
- [用户](09-users.md) — RBAC 权限
