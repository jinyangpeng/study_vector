# 整体架构

> study_vector 是一个**多语言 / 多向量库**的研究平台。
> 第一阶段交付：Python + FastAPI + Milvus + Vue 3 前端。

## 1. 系统组成图

```
┌──────────────────────────────────────────────────────────────────────┐
│                       浏览器（桌面 / 移动）                             │
│  Vue 3 + Vite + Element Plus + Pinia（无后端语言依赖）                  │
└──────────────┬───────────────────────────────────────────────────────┘
               │  HTTP / JSON （OpenAPI 契约）
               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  Python API（FastAPI + Uvicorn）                       │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────────┐    │
│  │  api/v1      │  │  domain      │  │  repositories              │    │
│  │ collections  │→ │ Collection   │← │ VectorRepository (Protocol)│    │
│  │ vectors      │  │ VectorRecord │  └─────────────┬──────────────┘    │
│  │ health       │  │ Search*      │                │                  │
│  └──────┬───────┘  └──────────────┘  ┌────────────▼───────────────┐   │
│         │  Depends(get_vector_repository)        │  infra/milvus       │   │
│         ▼                                        │  pymilvus 包装      │   │
│  ┌──────────────────────────────────────┐        └─────────┬──────────┘   │
│  │  core/ 配置 + 日志                      │                 │              │
│  │  exceptions + exception_handlers      │                 │              │
│  └──────────────────────────────────────┘                 │              │
└────────────────────────────────────────────────────────────┼──────────────┘
                                                             │  gRPC :19530
                                                             ▼
                                                ┌────────────────────────┐
                                                │  Milvus Standalone      │
                                                │  （etcd + minio）        │
                                                └────────────────────────┘
```

## 2. 进程与网络拓扑（Docker Compose）

```
[ study_vector_study_vector_net ]  (bridge 网络)
    ├── milvus-standalone          (用户已有 / compose 内置)
    ├── api (study-vector-api)     8000  → 用容器名 milvus-standalone 连 Milvus
    └── frontend (nginx)           5173  →  /api/*  反代到 api:8000
```

**为什么容器内的 API 要用容器名？**
容器内的 `localhost` 是它自己；宿主上的 `127.0.0.1` 在容器内不可达。
唯一稳定的方式是用容器名（Docker 内置 DNS 服务名解析）。
**而宿主上的 API 跑 Python 进程时，`localhost` 就是宿主自己的回环，能直接连上容器端口映射的 `127.0.0.1:19530`**，这点在 Windows Docker Desktop 上同样成立。

## 3. 数据流（典型请求：检索）

```
1. 前端  POST /api/v1/vectors/{coll}/search  { vector, top_k }
2. FastAPI 路由 vectors.search_vectors 注入 VectorRepository
3. repo.search(SearchRequest)  → MilvusRepository.search()
4. asyncio.to_thread( coll.search(...) )  → 同步 pymilvus
5. pymilvus gRPC :19530 → Milvus Standalone
6. Milvus 返回 SearchResult → 转 SearchResult 业务模型
7. 统一响应 { code:0, message, data }
8. axios 拦截器解包 data  → Vue store / 组件
```

## 4. 分层职责

| 层                | 关注点                             | 例子                                           |
| ----------------- | ---------------------------------- | ---------------------------------------------- |
| `api/v1`          | 路由、参数校验、统一响应、HTTP 状态 | `POST /collections`                            |
| `domain`          | 业务模型（不依赖任何 SDK）          | `CollectionSchema`, `VectorRecord`             |
| `repositories`    | 抽象接口（`Protocol`）             | `VectorRepository`                             |
| `infra/<db>`      | 具体向量库 SDK 翻译层              | `MilvusRepository`, `client.py`                |
| `core`            | 配置、日志、生命周期               | `Settings`, `setup_logging`                    |
| `dependencies.py` | FastAPI 依赖注入（DI 容器）         | `get_vector_repository`                        |
| `exceptions`      | 业务异常体系                        | `CollectionNotFoundError`                      |

## 5. 关键设计原则

1. **业务层零依赖**：API 路由与 domain 模型都不知道 Milvus 存在。
   切换向量库 = 改 `dependencies.py` 一行，业务代码不动。
2. **依赖倒置**：`VectorRepository` 是 `Protocol`，pymilvus 实现 duck-type 满足即可。
3. **多环境配置**：pydantic-settings + `.env.{APP_ENV}` 切换 dev / test / prod。
4. **可观测性**：loguru 结构化日志；全局异常拦截 → 统一响应；`/health/ready` 探针。
5. **多语言隔离**：`backends/<lang>/` 独立 `pyproject.toml` / `Dockerfile` / 端口。
6. **前后端解耦**：前端只调 OpenAPI，未来加 Go / Node 后端无需改前端。

## 6. 扩展点

### 6.1 新增向量库（以 Chroma 为例）

```
infra/chroma/
    __init__.py
    client.py        # chromadb 客户端单例
    repository.py    # class ChromaRepository: 满足 VectorRepository
```

```python
# dependencies.py
_BUILDERS = {
    "milvus": lambda: MilvusRepository(),
    "chroma": lambda: ChromaRepository(),
}
```

### 6.2 新增语言（以 Go 为例）

```
backends/go/
    go.mod
    cmd/api/main.go
    internal/
        repository/        # 实现 VectorRepository 协议
        api/               # gin/chi 路由
        config/            # 多环境配置
```

顶层 `docker/docker-compose.yml` 加 `go-api` 服务；前端 `stores/backend.ts` 加 Go 后端选项。

## 7. 验收检查（首期）

参见 [quickstart.md §5](quickstart.md#5-一键验收清单)。
