# 多语言后端

> 前端只依赖统一 OpenAPI 契约，未来加 Go / Node / Rust 后端无需改前端。

## 1. 为什么需要多语言

研究向量库时，业务逻辑（CRUD / 检索）通常非常薄。
不同语言**生态不同**：
- **Python**：pymilvus / chromadb / qdrant-client / weaviate-client；ML / 嵌入模型最丰富。
- **Go**：milvus-sdk-go / weaviate-go-client；性能好，适合高并发 / 边车。
- **Node.js**：@zilliz/milvus2-sdk-node / chromadb-js；适合全栈 / Serverless。

把"多语言"作为平台的一等公民，可以**对比同一组业务 API 在不同语言上的开发体验与性能**。

## 2. 隔离原则

```
backends/
├── python/            # FastAPI
│   ├── pyproject.toml
│   ├── src/study_vector/...
│   ├── tests/
│   ├── config/{dev,test,prod}.env
│   └── deploy/Dockerfile
├── go/                # 未来
│   ├── go.mod
│   ├── cmd/api/main.go
│   └── deploy/Dockerfile
└── node/              # 未来
    ├── package.json
    ├── src/...
    └── Dockerfile
```

每个语言子项目：
- 独立依赖管理（uv / go mod / npm）
- 独立 Dockerfile
- 独立端口（python 8000 / go 8001 / node 8002）
- 独立测试 + CI

## 3. 统一 OpenAPI 契约

所有后端实现同一组端点：

| Method | Path                                  | 作用           |
| ------ | ------------------------------------- | -------------- |
| GET    | /api/v1/health                        | 存活探针       |
| GET    | /api/v1/health/ready                  | 就绪探针       |
| GET    | /api/v1/collections                   | 列出集合       |
| POST   | /api/v1/collections                   | 创建集合       |
| GET    | /api/v1/collections/{name}            | 集合详情       |
| DELETE | /api/v1/collections/{name}            | 删除集合       |
| POST   | /api/v1/vectors/{coll}/insert         | 插入           |
| POST   | /api/v1/vectors/{coll}/upsert         | 存在则更新     |
| POST   | /api/v1/vectors/{coll}/delete         | 按 id 删除     |
| POST   | /api/v1/vectors/{coll}/get            | 按 id 拉取     |
| POST   | /api/v1/vectors/{coll}/search         | 向量检索       |

**统一响应**：

```json
{ "code": 0, "message": "success", "data": ... }
```

`code = 0` 表示成功；非 0 是业务 / 校验 / 后端错误码（与 HTTP status code 区分）。

## 4. 前端如何与后端解耦

`frontend/src/stores/backend.ts`：

```ts
export const useBackendStore = defineStore('backend', () => {
  const backends: Backend[] = [
    { name: 'Python FastAPI', baseUrl: 'http://127.0.0.1:8000', language: 'python' },
    // { name: 'Go Gin',        baseUrl: 'http://127.0.0.1:8001', language: 'go' },
    // { name: 'Node Express',  baseUrl: 'http://127.0.0.1:8002', language: 'node' },
  ]
  const current = ref<Backend>(backends[0])
  return { backends, current, select }
})
```

`frontend/src/api/client.ts`：

```ts
export function getClient() {
  return axios.create({
    baseURL: useBackendStore().current.baseUrl,
    timeout: 30000,
  })
}
```

切换后端 = 顶栏下拉切换 → 重建 axios 实例 → 路由回首页 + 刷新页面。

后端语言的差异（同步 / 异步 / 类型）**完全由后端自己消化**；前端只看 JSON。

## 5. 顶层编排

`deploy/docker-compose.yml`：

```yaml
services:
  milvus-standalone: ...   # 用户已有 / compose 内置

  python-api:
    build: ../backends/python
    network: study_vector_study_vector_net
    ports: ["8000:8000"]
    environment:
      MILVUS_HOST: milvus-standalone   # 同网络用容器名

  # 未来
  # go-api:
  #   build: ../backends/go
  #   network: study_vector_study_vector_net
  #   ports: ["8001:8000"]
  #   environment:
  #     MILVUS_HOST: milvus-standalone

  frontend:
    build: ../frontend
    network: study_vector_study_vector_net
    ports: ["5173:80"]
```

**关键**：所有后端与前端都进 `study_vector_study_vector_net`，用容器名互访。

## 6. 新增一门语言（以 Go 为例）的步骤

1. `mkdir -p backends/go/{cmd/api,internal,deploy}`
2. 选框架：`gin`（社区主流，文档丰富）或 `chi`（更轻量）
3. 复制本仓库的 `core/settings.py` 思路 → `internal/config/config.go`
4. 复制 `domain/models.py` → `internal/domain/models.go`（Pydantic 等价物可用 `go-playground/validator`）
5. 在 `internal/repository/milvus.go` 调 milvus-sdk-go 实现 `VectorRepository` 接口（Go 用 interface）
6. `cmd/api/main.go` 装配路由（与 Python 对齐）
7. `deploy/Dockerfile` 多阶段构建（golang:1.22-alpine → alpine）
8. `deploy/docker-compose.yml` 加 `go-api` 服务
9. `frontend/src/stores/backend.ts` 加 `{ name: 'Go Gin', baseUrl: 'http://127.0.0.1:8001', language: 'go' }`
10. E2E：`FRONTEND_URL=... API_URL=http://127.0.0.1:8001 node e2e/smoke.mjs`

## 7. 跨语言一致性保障

- **契约测试**：用 `schemathesis` / `dredd` 对每种语言后端跑同一份 OpenAPI。
- **基准测试**：相同 collection + 相同数据 + 相同 query，对比 5/50/95/99 延迟。
- **CI**：GitHub Actions 矩阵（`language ∈ {python, go, node}`）跑同一组端到端用例。
