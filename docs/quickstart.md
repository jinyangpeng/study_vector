# 快速开始（Quick Start）

> 5 分钟内把 **study_vector** 跑起来：Python API + Milvus + 前端。

---

## 1. 前置条件

| 工具       | 版本           | 用途                          |
| ---------- | -------------- | ----------------------------- |
| Docker     | 24+            | 容器化 Milvus / API / 前端    |
| Node.js    | 20+（仅前端）  | 前端构建 / 启动 dev server    |
| Python     | 3.11+（仅后端）| 二次开发 / 跑测试             |
| uv         | 最新           | Python 依赖管理（可选）       |

> 端口占用：`8000`（API）、`5173`（前端）、`19530`（Milvus gRPC）、`9091`（Milvus 管理）、`9001`（MinIO 控制台）。

---

## 2. 启动 Milvus（任选其一）

### 方式 A：复用你已部署的 Milvus

直接跳到 §3，只需要在 API 容器里把 `MILVUS_HOST` 指向你的 Milvus 即可。
如果 Milvus 在 Docker 中且和 API 不在同一网络，按 §3.1 调整。

### 方式 B：用本仓库 compose 自带一套

```bash
cd deploy
cp .env.example .env
docker compose up -d milvus etcd minio
```

等待 `study_vector_milvus` 容器变 `healthy`（约 30s）：

```bash
docker ps --filter name=study_vector_milvus
```

---

## 3. 启动 API（FastAPI）

### 3.1 宿主开发模式（推荐用于日常开发）⭐

```bash
cd backends/python
cp config/dev.env .env       # 已默认 MILVUS_HOST=localhost:19530
uv sync
uv run uvicorn study_vector.main:app --reload --host 0.0.0.0 --port 8000
```

> 验证：浏览器开 <http://127.0.0.1:8000/api/v1/health> → `{"code":0,"data":{"status":"ok"}}`。

**Windows Docker Desktop 上，宿主访问 `127.0.0.1:19530` 完全可以连上容器里的 Milvus**（与 `9091` / `2379` 同理）。
直接用 `localhost` / `127.0.0.1`，不需要 `docker network connect` 或容器名。

### 3.2 Docker 启动（与 Milvus 同网络 / 生产环境）

```bash
cd backends/python
docker build -f deploy/Dockerfile -t study-vector-api:dev .

docker run -d --name study_vector_api \
  --network study_vector_study_vector_net \
  -p 8000:8000 \
  -e APP_ENV=dev \
  -e MILVUS_HOST=milvus-standalone \
  -e MILVUS_PORT=19530 \
  -e MILVUS_USER=root \
  -e MILVUS_PASSWORD=Milvus \
  -e MILVUS_DB_NAME=default \
  study-vector-api:dev
```

> 这里之所以用 `milvus-standalone`（容器名）是因为 API **跑在容器内**，
> 容器内的 `localhost` 指的是自己、宿主上的 `127.0.0.1` 不通，
> **唯一稳定方式是用容器名**（依赖 Docker 内置 DNS）。

### 3.3 一键选择

| 场景                          | API 跑在哪   | MILVUS_HOST             |
| ----------------------------- | ------------ | ----------------------- |
| 日常开发（推荐）              | 宿主 Python  | `localhost`             |
| 多服务联调 / 沙箱             | Docker       | `milvus-standalone`     |
| 跨主机 / 远程 Milvus          | 任意         | `<host IP>` 或域名      |

---

## 4. 启动前端

### 4.1 dev server（开发态，热更新）

```bash
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5173
```

打开 <http://127.0.0.1:5173> 即可。

### 4.2 Docker 启动（生产态，nginx 反代）

```bash
cd frontend
docker build -t study-vector-frontend:dev .
docker run -d --name study_vector_frontend \
  --network study_vector_study_vector_net \
  -p 5173:80 study-vector-frontend:dev
```

---

## 5. 一键验收清单

| 步骤 | 命令 / 路径                                                            | 期望                                                              |
| ---- | ---------------------------------------------------------------------- | ----------------------------------------------------------------- |
| 1    | 浏览器访问 <http://127.0.0.1:8000/api/v1/health>                       | `{"code":0,"message":"success","data":{"status":"ok"}}`           |
| 2    | 浏览器访问 <http://127.0.0.1:8000/docs>                                | 看到 OpenAPI Swagger UI                                           |
| 3    | 浏览器访问 <http://127.0.0.1:5173>                                     | 看到「集合管理」页面、集合列表                                    |
| 4    | 前端新建集合 `demo4`，插入向量，检索                                   | 命中按相似度排序                                                  |
| 5    | `cd backends/python && uv run pytest`                                  | 单元 + 集成测试全部通过                                           |
| 6    | `cd frontend && node e2e/smoke.mjs`                                    | 8 步 E2E 全部 `[OK]`，并产出截图 `e2e/screenshot-*.png`           |

---

## 6. 常见问题（FAQ）

**Q1：浏览器能打开前端，但「集合列表」为空 / 接口报网络错误？**
A：多半是 API 跨域或后端不通。前端默认走 `http://127.0.0.1:8000`（绝对地址），后端必须监听 `0.0.0.0:8000`。在顶栏切换后端为「Python FastAPI (本机直接)」即可。

**Q2：API 报 `VECTOR_BACKEND_ERROR ... failed to connect to ... 19530`？**
A：API 找不到 Milvus。检查：
- Milvus 容器是否 healthy（`docker ps`）
- `MILVUS_HOST` 是否正确（宿主跑用 `localhost`，容器跑用容器名）
- 端口映射是否生效：`Invoke-WebRequest http://127.0.0.1:9091/` 应返回 404（说明 Milvus HTTP 在听）

**Q3：Windows 宿主上 `127.0.0.1:19530` 不通？**
A：极少见。先用 `python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1',19530)); print('ok')"` 验证；
若 Python 能连而 pymilvus 不能，多半是 SDK 版本问题；若都不能，检查 Milvus 端口映射。
**不要用 `Test-NetConnection`，它在某些 PowerShell 版本会给出假阴性**。

**Q4：检索返回 0 条？**
A：插入后 Milvus 默认 1s 索引刷盘，搜索前等几秒或调高 `top_k`；也可在请求里把 `top_k` 调到 `100`。

**Q5：删除后 `row_count` 不变？**
A：Milvus 缓存行数，强制刷盘（容器内）或调用 `coll.flush()` 后再读。
