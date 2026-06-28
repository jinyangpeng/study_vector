# 快速开始（Quick Start）

> 5 分钟内把 **study_vector** 跑起来：Python API + Milvus + 前端。

---

## 1. 前置条件

| 工具       | 版本           | 用途                          |
| ---------- | -------------- | ----------------------------- |
| Docker     | 24+            | 容器化部署（最简路径，推荐）  |
| Node.js    | 20+（仅前端）  | 宿主开发 / 启动 dev server    |
| Python     | 3.11+（仅后端）| 宿主二次开发 / 跑测试         |
| uv         | 最新           | Python 依赖管理（可选）       |

> 端口占用：`8000`（API）、`5173`（前端）、`19530`（Milvus gRPC）、`9091`（Milvus 管理）、`9001`（MinIO 控制台，仅内置模式）。

---

## 2. Docker 一键部署（推荐，最简）

> 前提：已安装 Docker 24+。**无需安装 Python / Node 即可跑起全套**，适合体验、演示、CI。

```bash
cd docker
cp .env.example .env
docker compose up -d --build
```

### 2.1 选择 Milvus 部署模式

通过 `.env` 的 `COMPOSE_PROFILES` 一键切换（改完重新 `docker compose up -d` 即可）：

**内置模式（默认，开箱即用）** — 启动项目自带的 etcd+minio+milvus+api+前端：

```env
COMPOSE_PROFILES=milvus
MILVUS_HOST=milvus
```

**外部模式（复用你已部署的 Milvus）** — 仅启动 api+前端，连接已有的 Milvus，省资源：

```env
COMPOSE_PROFILES=                      # 留空，禁用内置 milvus 套件
MILVUS_HOST=host.docker.internal       # 改为你的 Milvus 地址
                                       # （Milvus 在同宿主用此，跨机用 IP/域名）
```

### 2.2 验证

```bash
docker compose ps
curl http://localhost:8000/api/v1/health    # {"code":0,...,"status":"ok"}
# 浏览器：http://localhost:5173 （前端）
# 内置模式另可访问 MinIO 控制台 http://localhost:9001 (minioadmin / minioadmin)
```

### 2.3 常用命令

```bash
docker compose ps                 # 查看状态
docker compose logs -f api        # 跟踪 API 日志
docker compose restart api        # 重启单个服务
docker compose up -d --build api  # 代码变更后重新构建
docker compose down               # 停止并删容器（保留数据卷）
```

> 完整部署文档（多环境覆盖、资源限制、接入外部 Milvus、故障排查）见 [`docker/README.md`](../docker/README.md)。

---

## 3. 宿主开发模式（热重载，日常开发）

适合二次开发：API 和前端跑在宿主，支持热重载；Milvus 仍用 Docker。

### 3.1 启动 Milvus

```bash
cd docker
cp .env.example .env                         # 保持 COMPOSE_PROFILES=milvus
docker compose up -d milvus etcd minio       # 仅起依赖服务
```

等待 `study_vector_milvus` 容器变 `healthy`（约 30s）：

```bash
docker ps --filter name=study_vector_milvus
```

### 3.2 启动 API（FastAPI，热重载）

```bash
cd backends/python
cp config/dev.env .env       # 已默认 MILVUS_HOST=localhost:19530
uv sync
uv run uvicorn study_vector.main:app --reload --host 0.0.0.0 --port 8000
```

> 验证：浏览器开 <http://127.0.0.1:8000/api/v1/health> → `{"code":0,"data":{"status":"ok"}}`。

**Windows Docker Desktop 上，宿主访问 `127.0.0.1:19530` 完全可以连上容器里的 Milvus**（与 `9091` / `2379` 同理）。
直接用 `localhost` / `127.0.0.1`，不需要 `docker network connect` 或容器名。

### 3.3 启动前端（Vite，热更新）

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

打开 <http://127.0.0.1:5173> 即可。

### 3.4 MILVUS_HOST 怎么填

| 场景                          | API 跑在哪   | MILVUS_HOST             |
| ----------------------------- | ------------ | ----------------------- |
| 日常开发（推荐）              | 宿主 Python  | `localhost`             |
| Docker 全量部署（compose）    | Docker       | `milvus`（service 名）  |
| 跨主机 / 远程 Milvus          | 任意         | `<host IP>` 或域名      |

> 关键：API **跑在容器内**时，`localhost` 指容器自己，必须用 service 名（`milvus`）或外部地址；
> API **跑在宿主**时，用 `localhost` 即可（Docker Desktop 已把容器端口映射到宿主）。

---

## 4. 一键验收清单

| 步骤 | 命令 / 路径                                                            | 期望                                                              |
| ---- | ---------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 1    | 浏览器访问 <http://127.0.0.1:8000/api/v1/health>                       | `{"code":0,"message":"success","data":{"status":"ok"}}`           |
| 2    | 浏览器访问 <http://127.0.0.1:8000/docs>                                | 看到 OpenAPI Swagger UI                                           |
| 3    | 浏览器访问 <http://127.0.0.1:5173>                                     | 看到「集合管理」页面、集合列表                                    |
| 4    | 前端新建集合 `demo4`，插入向量，检索                                   | 命中按相似度排序                                                  |
| 5    | `cd backends/python && uv run pytest`                                  | 单元 + 集成测试全部通过                                           |
| 6    | `cd frontend && node e2e/smoke.mjs`                                    | 8 步 E2E 全部 `[OK]`，并产出截图 `e2e/screenshot-*.png`           |

---

## 5. 常见问题（FAQ）

**Q1：浏览器能打开前端，但「集合列表」为空 / 接口报网络错误？**
A：多半是 API 不通或跨域。
- **Docker 部署**：前端 nginx 已反代 `/api/*` 到 api 容器，无需额外配置；检查 `docker compose ps` 里 api 是否健康、`docker compose logs api` 是否报连不上 Milvus。
- **宿主开发**：前端默认走 `http://127.0.0.1:8000`（绝对地址），后端必须监听 `0.0.0.0:8000`。在顶栏切换后端为「Python FastAPI (本机直接)」即可。

**Q2：API 报 `VECTOR_BACKEND_ERROR ... failed to connect to ... 19530`？**
A：API 找不到 Milvus。检查：
- Milvus 容器是否 healthy（`docker ps`）
- `MILVUS_HOST` 是否正确（宿主跑用 `localhost`，容器跑用 service 名 `milvus`，外部实例用其地址）
- 端口映射是否生效：`Invoke-WebRequest http://127.0.0.1:9091/` 应返回 404（说明 Milvus HTTP 在听）

**Q3：Windows 宿主上 `127.0.0.1:19530` 不通？**
A：极少见。先用 `python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1',19530)); print('ok')"` 验证；
若 Python 能连而 pymilvus 不能，多半是 SDK 版本问题；若都不能，检查 Milvus 端口映射。
**不要用 `Test-NetConnection`，它在某些 PowerShell 版本会给出假阴性**。

**Q4：容器名冲突 `The container name "/study_vector_api" is already in use`？**
A：之前用旧编排启动过同名容器。清理后重启：`docker compose down`（在新 `docker/` 目录），或 `docker rm -f study_vector_api study_vector_frontend study_vector_milvus study_vector_etcd study_vector_minio`。

**Q5：端口 9001 / 19530 已被占用？**
A：宿主上已有另一套 Milvus 在跑。改用「外部模式」（`.env` 设 `COMPOSE_PROFILES=` 留空 + `MILVUS_HOST=host.docker.internal`）复用已有 Milvus，或修改 `.env` 里 `MILVUS_HOST_PORT` / `MINIO_CONSOLE_PORT` 避开冲突。

**Q6：检索返回 0 条？**
A：插入后 Milvus 默认 1s 索引刷盘，搜索前等几秒或调高 `top_k`；也可在请求里把 `top_k` 调到 `100`。

**Q7：删除后 `row_count` 不变？**
A：Milvus 缓存行数，强制刷盘（容器内）或调用 `coll.flush()` 后再读。
