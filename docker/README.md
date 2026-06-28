# Docker 部署

study_vector 的容器化部署方案，采用 **Compose Override 模式** 区分开发/生产环境，所有配置参数化。

> 本目录是项目唯一的容器化部署方案（原 `deploy/` 已于 2026-06 合并迁移至此）。

---

## 目录结构

```
docker/
├── README.md                    # 本文档
├── .env.example                 # 环境变量模板（拷贝为 .env）
├── docker-compose.yml           # 基础编排（所有服务定义）
├── docker-compose.dev.yml       # 开发覆盖：仅依赖服务
├── docker-compose.prod.yml      # 生产覆盖：资源限制 + 日志轮转
├── api/
│   └── Dockerfile               # 后端 API 镜像（多阶段，非 root）
├── frontend/
│   ├── Dockerfile               # 前端镜像（node 构建 → nginx 运行）
│   └── nginx.conf               # nginx：静态服务 + API 反代 + SPA 回退
└── volumes/                     # 数据持久化（.gitignore，不入版本控制）
    ├── etcd/
    ├── minio/
    └── milvus/
```

---

## 服务架构

```
                ┌─────────────────────────────────────────────┐
   浏览器 ──►   │ frontend (nginx:80)                          │
   :5173       │   ├─ 静态文件 (Vue dist)                      │
               │   └─ /api/* ──► proxy ──► api (uvicorn:8000)  │
               └────────────────────┬────────────────────────┘
                                     │ pymilvus
                                     ▼
                ┌─────────────────────────────────────────────┐
                │ milvus (standalone:19530)                    │
                │   ├─ etcd  (元数据)                          │
                │   └─ minio (对象存储, 控制台 :9001)           │
                └─────────────────────────────────────────────┘
                          （study_vector_net 桥接网络）
```

| 服务      | 镜像                                   | 容器端口 | 宿主端口（可配置）       | 职责              |
| --------- | -------------------------------------- | -------- | ------------------------ | ----------------- |
| etcd      | `quay.io/coreos/etcd:v3.5.16`          | 2379     | -                        | Milvus 元数据     |
| minio     | `minio/minio:RELEASE.2024-09-13...`    | 9000/9001| 9001（控制台）           | Milvus 对象存储   |
| milvus    | `milvusdb/milvus:v2.4.10`              | 19530/9091| 19530 / 9091            | 向量数据库        |
| api       | `study_vector/api:latest`（本地构建）  | 8000     | 8000                     | FastAPI 后端      |
| frontend  | `study_vector/frontend:latest`（本地） | 80       | 5173                     | Vue 前端 + 反代   |

---

## 快速开始

### 1. 准备环境变量

```bash
cd docker
cp .env.example .env
# 按需编辑 .env（关键：COMPOSE_PROFILES 决定 Milvus 部署模式）
```

### 2. 启动

```bash
docker compose up -d --build
```

> `.env` 里 `COMPOSE_PROFILES=milvus`（默认）即为内置模式，开箱即用。
> 见下文「Milvus 部署模式」选择适合自己的方式。

验证：

```bash
docker compose ps
curl http://localhost:8000/api/v1/health      # {"status":"healthy"}
# 浏览器打开 http://localhost:5173
# 内置模式下 MinIO 控制台 http://localhost:9001  (minioadmin / minioadmin)
```

---

## Milvus 部署模式

通过 `.env` 的 **`COMPOSE_PROFILES`** 一键切换，命令统一为 `docker compose up -d`。

| 模式     | `COMPOSE_PROFILES` | 启动服务                            | 适用场景                     |
| -------- | ------------------ | ----------------------------------- | ---------------------------- |
| 内置模式 | `milvus`（默认）   | etcd + minio + milvus + api + 前端 | 首次使用 / 无现成 Milvus     |
| 外部模式 | （留空）           | api + 前端                          | 已有自建 Milvus，省资源      |

### 模式 A — 内置 Milvus（开箱即用，默认）

启动项目自带的 etcd + minio + milvus + api + 前端，全套容器化。

`.env` 保持默认：
```env
COMPOSE_PROFILES=milvus
MILVUS_HOST=milvus          # 指向 compose 内的 milvus service
```

```bash
docker compose up -d --build
```

### 模式 B — 外部 Milvus（复用已部署实例）

仅启动 api + 前端，连接你已部署的 Milvus（不启动 etcd/minio/milvus，省资源）。

编辑 `.env`：
```env
COMPOSE_PROFILES=                 # 留空，禁用内置 milvus 套件
MILVUS_HOST=192.168.1.100         # 改为你的外部 Milvus 地址
MILVUS_PORT=19530
MILVUS_SECURE=false
```

```bash
docker compose up -d --build
```

> 外部 Milvus 无需与本项目容器同网络——api 从容器内通过 `MILVUS_HOST` 连接，
> 只要该地址从容器网络可达即可（同宿主用宿主 IP，跨主机用对应 IP/域名）。

---

## 其他场景

### 场景 C — 仅依赖服务（本地开发）

只启动 Milvus 及其依赖，**API 和前端在宿主本地运行**（支持热重载调试）：

```bash
# 前提：.env 里 COMPOSE_PROFILES=milvus
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# 本地跑后端
cd ../backends/python && uv run uvicorn study_vector.main:app --reload --port 8000

# 本地跑前端（另开终端）
cd ../frontend && npm run dev -- --host 127.0.0.1 --port 5173
```

> 原理：dev 覆盖文件给 `api`/`frontend` 打上 `disabled` profile，默认 `up` 不启动它们。

### 场景 D — 生产部署

叠加生产覆盖：资源限制 + 日志轮转 + `always` 重启 + 强制 JSON 日志。

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

---

## 常用命令

```bash
# 查看状态 / 日志
docker compose ps
docker compose logs -f api
docker compose logs -f --tail=100 milvus

# 重启单个服务
docker compose restart api

# 重新构建（代码变更后）
docker compose up -d --build api

# 停止 / 清理
docker compose down                    # 停止并删容器（保留数据卷）
docker compose down -v                 # 同时删命名卷（慎用，清空 Milvus 数据）
docker compose down --rmi local        # 同时删本地构建的镜像
```

---

## 环境变量说明

完整列表见 [`.env.example`](.env.example)，关键项：

| 变量                | 默认值            | 说明                                                  |
| ------------------- | ----------------- | ----------------------------------------------------- |
| `COMPOSE_PROFILES`  | `milvus`          | **Milvus 模式开关**：`milvus`=内置，留空=外部         |
| `APP_ENV`           | `prod`            | 应用环境：dev / test / prod                           |
| `MILVUS_HOST`       | `milvus`          | API 连接的 Milvus 地址（内置=`milvus`，外部=IP/域名） |
| `MILVUS_USER`       | `root`            | Milvus 用户名                                         |
| `MILVUS_PASSWORD`   | `Milvus`          | Milvus 密码                                           |
| `API_PORT`          | `8000`            | API 宿主映射端口                                      |
| `FRONTEND_PORT`     | `5173`            | 前端宿主映射端口                                      |
| `LOG_LEVEL`         | `INFO`            | 日志级别                                              |
| `LOG_JSON`          | `true`            | 是否输出 JSON 日志                                    |
| `MINIO_ACCESS_KEY`  | `minioadmin`      | MinIO 凭据（内置模式，**生产务必修改**）              |
| `MINIO_SECRET_KEY`  | `minioadmin`      | MinIO 凭据（内置模式，**生产务必修改**）              |

> 容器内通信端口固定（Milvus 19530、API 8000、前端 80），仅宿主映射端口可配。
> `MINIO_*` / `MILVUS_HOST_PORT` 等仅在内置模式（`COMPOSE_PROFILES=milvus`）生效。

---

## 构建优化

- **多阶段构建**：builder 阶段装编译依赖，runtime 阶段仅含运行时，镜像更小更安全。
- **非 root 用户**：API 以 `app`（UID 1001）运行；`tini` 作为 PID 1 正确处理信号。
- **层缓存**：先复制 `pyproject.toml`/`package.json`，依赖不变时跳过重装。
- **`.dockerignore`**：项目根的 [.dockerignore](../.dockerignore) 排除 `node_modules`、`__pycache__`、`.git`、数据卷、密钥，加速构建且避免泄露。
- **固定版本**：所有基础镜像与 `uv` 均锁版本号，避免 `latest` 漂移。

---

## 故障排查

| 现象                          | 排查                                                                 |
| ----------------------------- | -------------------------------------------------------------------- |
| API 启动失败连不上 Milvus     | `docker compose ps` 确认 milvus 健康；检查 `MILVUS_HOST` 是否为 `milvus` |
| 前端 502 Bad Gateway          | API 未就绪，`docker compose logs api` 查看；前端依赖 `api` 服务      |
| Milvus 健康检查一直 starting  | 首次启动较慢（>30s），加大 `start_period` 或等待；查看 `milvus` 日志 |
| 端口冲突                      | 修改 `.env` 中 `API_PORT` / `FRONTEND_PORT` 等                       |
| 数据丢失                      | 确认 `docker/volumes/` 目录权限；勿用 `down -v`                       |
| 构建慢 / 上下文过大           | 确认项目根 `.dockerignore` 生效；`docker compose build --no-cache`  |

---

## 历史

原 `deploy/` 目录（早期方案，Dockerfile 分散在 `backends/python/deploy/` 与 `frontend/`）
已于 2026-06 合并至本目录并删除。Milvus 数据卷已迁移到 `docker/volumes/`，原有数据完整保留。
