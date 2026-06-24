# study_vector

> 一个用于系统学习、对比多种**向量数据库**（Vector Database）的研究平台。
> 支持**多语言后端**（Python / Go / Node 等）+ **多向量库**（Milvus / Chroma / Qdrant / Weaviate / pgvector），统一抽象、统一前端展示。

![status](https://img.shields.io/badge/status-v0.1.0-blue)
![python](https://img.shields.io/badge/python-3.11%2B-3776AB)
![vue](https://img.shields.io/badge/vue-3.5-42b883)
![milvus](https://img.shields.io/badge/milvus-2.4-00a1b7)
![license](https://img.shields.io/badge/license-MIT-green)

## 1. 项目定位

- 横向比较 Milvus / Chroma / Qdrant / Weaviate / pgvector 等主流向量库的**功能、API、适用场景**。
- 用同一套业务领域模型（`Collection` / `VectorRecord` / `SearchRequest`）驱动不同的底层实现。
- 后端按语言隔离（`backends/python/` / `backends/go/` / `backends/node/`），前端与具体后端语言解耦，只依赖统一 OpenAPI 契约。
- **企业级实践**：分层架构、配置外部化、依赖注入、可观测性、容器化部署、完整文档（含中文注释）。

## 2. 目录结构

```
study_vector/
├── backends/                    # 多语言后端（按语言隔离）
│   ├── python/                  # 首期交付：FastAPI + uv + pymilvus
│   │   ├── src/study_vector/    # 业务代码（api / domain / infra / repositories）
│   │   ├── tests/               # 单元 + 集成测试
│   │   ├── config/              # dev / test / prod 多环境配置
│   │   └── deploy/Dockerfile
│   ├── go/                      # 未来：Go (Gin / Chi)
│   └── node/                    # 未来：Node (Express / Fastify)
├── frontend/                    # 响应式前端
│   ├── src/                     # Vue 3 + Vite + Element Plus + Pinia
│   ├── e2e/smoke.mjs            # Playwright 端到端冒烟
│   ├── nginx.conf               # 生产部署：API 反代
│   └── Dockerfile
├── deploy/                      # 顶层 Docker Compose 编排
│   ├── docker-compose.yml       # Milvus + API + 前端
│   ├── .env.example
│   └── milvus/                  # Milvus volumes
├── docs/
│   ├── quickstart.md            # 5 分钟跑起来
│   ├── architecture/            # 架构设计文档
│   └── compare/                 # 向量库对比报告
└── README.md
```

## 3. 快速开始

> 项目用 [`just`](https://github.com/casey/just) 编排命令。先安装 just：
> - Windows: `winget install just` 或 `scoop install just`
> - macOS: `brew install just`
> - Linux: `cargo install just` 或 [GitHub Release](https://github.com/casey/just/releases)

参见 [`docs/quickstart.md`](docs/quickstart.md)。核心命令：

```bash
# 0. 一键安装
just init               # 创建 .env + uv sync 安装后端依赖
just init-frontend      # 安装前端依赖

# 1. 启动后端（开发态推荐：跑在宿主，配置最简单）
just dev-api            # 等价于 cd backends/python && just run

# 2. 启动前端
just dev-frontend       # 等价于 cd frontend && npm run dev

# 3. 验收
just status             # 一屏看：Docker / API / 集合列表 / 前端
just verify             # 跑完整验收：lint + test + e2e
```

### 不喜欢 just？

每个子项目里都有 `package.json` / `pyproject.toml`，直接：

```bash
# 后端
cd backends/python
uv sync
uv run uvicorn study_vector.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

## 4. 端到端验收

```bash
# Python 测试
cd backends/python
uv sync
uv run pytest -v

# 前端 E2E（需要先启动 dev server 和 API）
cd ../../frontend
node e2e/smoke.mjs    # 8 步全部 [OK]，并产出截图
```

## 5. 路线图

- [x] 阶段 0：仓库与目录骨架
- [x] 阶段 1：Python 后端（FastAPI + uv + pymilvus）
- [x] 阶段 2：Repository 抽象层（业务与向量库解耦）
- [x] 阶段 3：业务 API（集合管理 / 向量 CRUD / 检索）
- [x] 阶段 4：测试（单元 + 集成 + E2E）
- [x] 阶段 5：Docker 化与编排
- [x] 阶段 6：响应式前端（Vue 3 + Element Plus）
- [x] 阶段 7：文档（quickstart / architecture / compare）
- [ ] 阶段 8：多向量库（Chroma / Qdrant / Weaviate / pgvector）
- [ ] 阶段 9：多语言后端（Go / Node）

## 6. 文档导航

| 文档                                                            | 作用                                  |
| --------------------------------------------------------------- | ------------------------------------- |
| [docs/quickstart.md](docs/quickstart.md)                         | 5 分钟快速跑起来                      |
| [docs/architecture/overview.md](docs/architecture/overview.md)   | 整体架构图 + 分层职责 + 扩展点        |
| [docs/architecture/repository-pattern.md](docs/architecture/repository-pattern.md) | Repository 模式 + 新增向量库步骤 |
| [docs/architecture/multi-backend.md](docs/architecture/multi-backend.md)           | 多语言后端 + 前端解耦机制       |
| [docs/compare/milvus.md](docs/compare/milvus.md)               | Milvus 特性 + 踩坑笔记 + 性能粗观察   |

## 7. 贡献

欢迎 PR。新增向量库时只需：
1. 在 `backends/python/src/study_vector/infra/<新库>/repository.py` 实现 `VectorRepository` 协议
2. 在 `dependencies.py` 注册 builder
3. 补单测 / 集成测试 + `docs/compare/<新库>.md`

业务代码、API 路由、领域模型、前端**完全不需要改动**。

## 8. License

MIT
