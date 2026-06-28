# study_vector v0.2 实施计划 — Milvus 向量数据库实战教学平台

> **For agentic workers:** 本计划**取代** [2026-06-23-study-vector-initial.md](./2026-06-23-study-vector-initial.md)。v0.1 计划（多语言后端优先）已部分实施；v0.2 重新调整优先级——**Milvus 深度教学优先**，多向量库与多语言后端降为 V1.x 可选扩展。步骤使用 checkbox (`- [ ]`) 语法跟踪。
>
> **v0.2 校准（2026-06-24 第二次）**：
> 1. V1 范围锁定为 **Milvus 一个库做透**（Qdrant/Weaviate/Chroma/pgvector 推到 V1.x）
> 2. 多语言后端（Go/Node）推到 V2+（V1 只做 Python，OpenAPI 契约先行）
> 3. 教学深度升级到 **三层**（OpenAPI 字段说明 ⓘ + Markdown 教程 + 一键运行）
> 4. **教学闭环**：每个操作后必须能"查询验证"（QueryPanel 自动展示）
> 5. 前端栈保持 Vue 3 + Element Plus

## 0. 需求变更（相对 v0.1）

| 维度 | v0.1（旧） | v0.2 校准（新，本计划） |
|---|---|---|
| 多语言后端（Python/Go/Node） | 一等公民 | **延后**为 V2+，V1 只做 Python，但 OpenAPI 契约先行写好 |
| 多向量库（Milvus/Qdrant/Weaviate/Chroma） | 可选扩展 | **V1.x 增量**，V1 只做 Milvus 深度 |
| UI 主导航 | 按"功能"（集合/向量/检索） | **按"向量库"** → 库内按"功能"（V1 只有 Milvus 一组） |
| 教学维度 | 无 | **核心三层**：ⓘ 字段说明 + Markdown 教程 + 一键运行；**每个操作后必须能查询验证** |
| API 契约 | 隐式（FastAPI 自动生成） | **显式** OpenAPI 作为单一事实源（为 V2+ 多语言铺路） |
| 知识点覆盖 | 仅 CRUD | **全面 Milvus 知识点**：集合/Schema/索引/CRUD/检索/分区/一致性/内存/Alias/数据库 |

## 1. 目标

构建一个 **Milvus 向量数据库实战教学平台**：

- 同一套 REST API（OpenAPI 单一事实源）服务 Milvus 全知识点
- 前端按 "Milvus → 功能" 二级导航（V1.x 扩展 Qdrant/Weaviate/Chroma 时复用同一套 UI 组件）
- 每个 API 字段都有 `description`（教学说明），UI 端 hover 即看（ⓘ 组件）
- 每个功能点提供"试一下就跑通"的可运行示例（Markdown 教程 + 一键填充示例数据 + 一键调用）
- **教学闭环**：每个操作成功后自动展示 QueryPanel，验证数据已落库 / 已生效
- 后端 Python 实现（V1），多语言后端（Go/Node）作为 V2+ 扩展位（OpenAPI 契约已就绪）
- 多向量库扩展（Qdrant/Weaviate/Chroma）作为 V1.x 扩展位（Repository 协议已就绪）

## 2. 总体架构

```
study_vector/
├── contracts/                              # ★ NEW: OpenAPI 单一事实源
│   └── openapi.yaml                        # 整个 API 的源；后端实现 + 前端类型都从这来
│
├── backends/python/                        # Python 后端（V1 唯一一等公民）
│   ├── src/study_vector/
│   │   ├── api/                            # HTTP 层（只做 HTTP 转换）
│   │   │   └── v1/
│   │   │       ├── collections.py
│   │   │       ├── vectors.py
│   │   │       ├── indexes.py              # ★ NEW: 索引教学
│   │   │       ├── search.py               # ★ NEW: 检索教学（混合检索等）
│   │   │       ├── partitions.py           # ★ NEW: 分区教学
│   │   │       └── health.py
│   │   ├── application/                    # ★ NEW: 应用服务层（用例编排）
│   │   │   ├── collection_service.py
│   │   │   └── ...
│   │   ├── domain/                         # 领域模型（无框架依赖）
│   │   ├── repositories/                   # VectorRepository 协议（已有）
│   │   ├── infra/
│   │   │   ├── milvus/                     # Milvus 适配器（已有）
│   │   │   └── base.py                     # ★ NEW: 适配器基类（公共逻辑）
│   │   ├── core/
│   │   ├── exceptions.py
│   │   ├── dependencies.py
│   │   └── main.py
│   ├── tests/                              # 单元 + 集成 + 契约测试
│   ├── deploy/Dockerfile
│   └── config/{dev,test,prod}.env
│
├── frontend/                               # 教学 UI（Vite + React/Vue 3）
│   ├── src/
│   │   ├── api/                            # 从 openapi.yaml 自动生成
│   │   ├── lib/
│   │   │   └── docs/                       # ★ NEW: 参数说明元数据
│   │   │       └── milvus/
│   │   │           ├── collections.md      # 每个字段的详细说明（Markdown）
│   │   │           ├── vectors.md
│   │   │           └── ...
│   │   ├── components/
│   │   │   ├── Layout.tsx                  # 侧边栏：一级=向量库，二级=功能
│   │   │   ├── ParamHelp.tsx               # ★ NEW: hover 显示字段说明
│   │   │   ├── ApiResponseViewer.tsx       # ★ NEW: 显示 API 原始响应
│   │   │   └── ...
│   │   ├── pages/
│   │   │   ├── Home.tsx
│   │   │   └── milvus/                     # 一级菜单：Milvus
│   │   │       ├── Collections.tsx         # 二级菜单
│   │   │       ├── Vectors.tsx
│   │   │       ├── Indexes.tsx
│   │   │       ├── Search.tsx
│   │   │       └── ...
│   │   └── tutorials/                      # ★ NEW: 教学示例（运行即得结果）
│   │       └── milvus/
│   │           ├── 01-first-collection.md
│   │           └── ...
│   └── e2e/
│
├── deploy/
│   ├── docker-compose.yml                  # Milvus + API + Frontend
│   └── milvus/                             # Milvus 官方 standalone compose（引用）
│
├── docs/
│   ├── architecture/
│   │   ├── overview.md                     # 更新：突出多向量库
│   │   ├── repository-pattern.md           # 更新：增加"为新向量库加 driver"步骤
│   │   └── multi-vector-db.md              # ★ NEW: 多向量库扩展指南
│   ├── tutorials/                          # ★ NEW: 教学文档
│   │   └── milvus/
│   ├── superpowers/plans/
│   │   ├── 2026-06-23-study-vector-initial.md  # v0.1（已完成部分）
│   │   └── 2026-06-24-vector-db-learning-platform.md  # ← 本文件 v0.2
│   └── quickstart.md                       # 更新
│
├── justfile
└── README.md
```

## 2.5 Milvus 知识点清单（V1 必须全覆盖）

> **教学原则**：每个知识点对应一个 API 端点（group），前端一个二级菜单页，附带 ⓘ 字段说明 + Markdown 教程 + 一键运行 + 操作后 QueryPanel 验证。

### 2.5.1 集合生命周期（Collection Lifecycle）

| # | 知识点 | API 端点 | 教学要点 |
|---|---|---|---|
| 1 | 集合 Schema 设计 | `POST /collections` | 主键 / 向量字段 / 标量字段 / 动态字段；字段类型选择 |
| 2 | 集合列表 | `GET /collections` | 列出当前 DB 下所有集合 |
| 3 | 集合详情 | `GET /collections/{name}` | schema 完整信息 + 加载状态 + 索引列表 |
| 4 | 删除集合 | `DELETE /collections/{name}` | 不可逆；生产应先 release + 备份 |
| 5 | 加载到内存 | `POST /collections/{name}/load` | 检索前必须；副本数 replica_number |
| 6 | 从内存释放 | `POST /collections/{name}/release` | 释放内存；不影响数据 |
| 7 | Alias 管理 | `POST/DELETE /collections/{name}/alias` | 多对一 / 一对多映射；零停机切换 |

### 2.5.2 Schema 与字段类型（Field Types）

> **教学点**：Milvus 支持丰富的字段类型；选错会性能/正确性问题。

| 字段类型 | 适用场景 | 教学示例 |
|---|---|---|
| `INT64` 主键 | 自增 ID | `id INT64 AUTO_INCREMENT PRIMARY KEY` |
| `VARCHAR` 主键 | 业务 ID（如文档 hash） | `id VARCHAR(256) PRIMARY KEY` |
| `FLOAT_VECTOR` | 文本/图像嵌入 | `vector FLOAT_VECTOR(1536)` |
| `BINARY_VECTOR` | 指纹 / 哈希嵌入 | `vector BINARY_VECTOR(1024)` |
| `SPARSE_FLOAT_VECTOR` | BM25 / SPLADE 稀疏嵌入 | `vector SPARSE_FLOAT_VECTOR` |
| `BOOL` / `INT8/16/32/64` / `FLOAT/DOUBLE` | 标量特征 | `category VARCHAR / price FLOAT` |
| `JSON` | 半结构化元数据 | `meta JSON` |
| `ARRAY` | 列表型标量 | `tags ARRAY<VARCHAR>` |
| 动态字段（`enable_dynamic_field=true`） | 灵活扩展 | 插入时任意字段自动入库 |

### 2.5.3 索引（Index）

| # | 索引类型 | 适用场景 | 关键参数 |
|---|---|---|---|
| 1 | `AUTOINDEX`（生产推荐） | Milvus 自动选最优 | 无 |
| 2 | `HNSW` | 高召回 / 内存允许 | `M`, `efConstruction` |
| 3 | `IVF_FLAT` | 大数据 / 速度优先 | `nlist` |
| 4 | `IVF_SQ8` | 压缩 4× | `nlist` |
| 5 | `IVF_PQ` | 极大压缩 | `nlist`, `m`, `nbits` |
| 6 | `FLAT` | 精确 / 小数据 | 无（暴力） |
| 7 | `ANNOY` | 只读场景 | `n_trees` |
| 8 | `DiskANN` | 内存不够 / 大规模 | — |
| 9 | `SCANN` | IVF_PQ 升级版 | — |

操作端点：
- `POST /collections/{name}/indexes` 建索引
- `GET /collections/{name}/indexes` 查看
- `DELETE /collections/{name}/indexes` 删除

### 2.5.4 数据 CRUD

| # | 操作 | 端点 | 教学要点 |
|---|---|---|---|
| 1 | Insert | `POST /collections/{name}/insert` | 批量；auto_id；返回主键 |
| 2 | Upsert | `POST /collections/{name}/upsert` | 存在则更新 |
| 3 | Delete by ids | `POST /collections/{name}/delete` | 软删除；后台 compaction 才真删 |
| 4 | Delete by filter | 同上带 `filter` | 标量条件删除 |
| 5 | Get by ids | `POST /collections/{name}/get` | 按主键精确取 |
| 6 | Query（标量检索） | `POST /collections/{name}/query` | 表达式过滤；`output_fields` |
| 7 | Count | `POST /collections/{name}/query` 配 `count(*)` | 行数统计 |

### 2.5.5 向量检索（Search / Hybrid）

| # | 检索类型 | 端点 | 教学要点 |
|---|---|---|---|
| 1 | 基础向量检索 | `POST /collections/{name}/search` | `top_k`, `metric_type` |
| 2 | 带 filter 的向量检索 | 同上 | `filter` 标量过滤加速 |
| 3 | 输出字段控制 | 同上 `output_fields` | 不返回 vector 节省带宽 |
| 4 | 检索参数调优 | `search_params` | IVF：`nprobe`；HNSW：`ef` |
| 5 | 范围检索 | `radius` + `range_filter` | 距离区间过滤 |
| 6 | 批量检索（多 query） | `vectors: List[List[float>]]` | 一次检索 N 个 query |
| 7 | 混合检索（Hybrid） | `POST /collections/{name}/hybrid_search` | dense + sparse 多路召回 + RRF 重排 |
| 8 | 迭代检索（Iterator） | `POST /collections/{name}/search_iterator` | 全量遍历 / 分页 |
| 9 | 标量检索 | `POST /collections/{name}/query` | 非向量查询 |

### 2.5.6 分区（Partition）

| # | 知识点 | 端点 | 教学要点 |
|---|---|---|---|
| 1 | 创建分区 | `POST /collections/{name}/partitions` | 按业务维度切分 |
| 2 | 列出分区 | `GET /collections/{name}/partitions` | — |
| 3 | 删除分区 | `DELETE /collections/{name}/partitions/{partition}` | 不可逆 |
| 4 | 按分区检索 | `search` 配 `partition_names` | 缩小扫描范围 |
| 5 | 按分区加载 | `load` 配 `partition_names` | 节省内存 |

### 2.5.7 一致性等级（Consistency Level）

| 等级 | 行为 | 适用场景 |
|---|---|---|
| `Strong` | 强一致（最高延迟） | 金融 / 库存 |
| `Session` | 单会话内一致（默认） | 通用 |
| `Bounded` | 可容忍旧数据 | 监控 |
| `Eventually` | 最终一致（最快） | 日志聚合 |

端点：`POST /collections/{name}` 配 `consistency_level`；运行时：`X-Milvus-Consistency-Level` header。

### 2.5.8 数据库与用户（Database & User）

| # | 知识点 | 端点 |
|---|---|---|
| 1 | 列出数据库 | `GET /databases` |
| 2 | 创建 / 删除数据库 | `POST/DELETE /databases` |
| 3 | 使用某数据库（连接） | 设置 `MILVUS_DB_NAME` |
| 4 | 用户管理 | `GET/POST/DELETE /users` |
| 5 | 角色 / 权限 | `GET/POST /roles` |

### 2.5.9 系统与监控

| # | 知识点 | 端点 |
|---|---|---|
| 1 | 健康探针 | `GET /health`, `GET /health/ready` |
| 2 | 集合统计 | `GET /collections/{name}/stats` |
| 3 | 全局 query | `GET /version` |

### 2.5.10 教学闭环（核心 UX 模式）

> **每个操作按钮的 UX 流程**：
>
> 1. 用户填表（每个字段右侧 ⓘ 弹出 OpenAPI description 文字说明）
> 2. 左侧有"📋 一键填充示例"按钮（自动填入该功能的典型示例数据）
> 3. 用户点击"调用" → 触发 API
> 4. **右侧自动出现 QueryPanel**（操作验证）：
>    - 写操作（insert/delete/upsert）：自动展示"立即 query 验证"——调用 `POST /collections/{name}/query` 拉回前 10 条
>    - 改 schema / 索引：自动调用 `GET /collections/{name}` 拉回最新状态
>    - 检索：检索结果直接展示在 ResultPanel（已含结果）
> 5. 下方有 Markdown 教程区（react-markdown 渲染）
> 6. 教程里有"复制 curl"按钮——粘贴到终端也能跑

**QueryPanel 组件要求**：
- 自动轮询（轮询可关）
- 支持"按 ID 查"、"按 filter 查"、"count"、"导出为 JSON"按钮
- 标红显示本次操作影响的记录数（"本次 insert 影响 5 条 / 集合总 1024 条"）

## 3. 技术栈

| 类别 | 选型 |
|---|---|
| API 契约 | **OpenAPI 3.1**（手写 + 工具校验） |
| 后端 | Python 3.11+ / FastAPI / pydantic v2 / loguru / uv |
| 向量库 SDK | pymilvus 2.4+（其他库 V1 不做，但保留接口） |
| 前端 | Vite + React 18 + TypeScript + Ant Design（或保持现有 Vue 3 + Element Plus） |
| API 客户端生成 | `openapi-typescript`（前端 TS 类型）+ `openapi-python-client`（后端不直接生成，但做契约校验） |
| 契约测试 | `schemathesis`（从 OpenAPI 派生测试用例） |
| 文档站 | VitePress 或 Docusaurus（教学文档站） |
| 可观测性 | loguru + OpenTelemetry（接口预留） |
| 容器化 | Docker + docker compose |

## 4. 关键设计原则（"最佳实践"落地）

1. **契约先行**：`contracts/openapi.yaml` 是 API 的唯一事实源
   - 后端 FastAPI 的 Pydantic 模型从 OpenAPI schema 导出
   - 前端 TS 类型从 OpenAPI 自动生成
   - 契约测试用 schemathesis 自动跑
2. **领域驱动**：业务逻辑在 `application/` 层，只依赖 `domain/` + `repositories/` 接口，不依赖任何 SDK
3. **依赖倒置**：`VectorRepository` 是 Protocol；新增向量库 = 新增 `infra/<库>/repository.py`，不动业务
4. **响应即文档**：每个 Pydantic 字段都有 `description=` 和 `examples=`，自动出现在 `/docs` 上
5. **可观测**：结构化日志 + 异常统一拦截 + 关键操作 span
6. **TDD**：每个 task 先写测试（红），再实现（绿），再重构

---

# 阶段 0：环境稳定化（必须先做，否则后面没法验证）

**目标**：让现有 `backends/python` 能在本机跑通、能连上 Milvus、curl `/api/v1/collections` 拿到 200。

### Task 0.1：修复 Milvus 启动配置

**问题诊断**（已知）：
- etcd command 里的反引号 `\`http://etcd:2379\`` 是 shell 命令替换语法，导致 advertise URL 为空
- `depends_on` 没加 `condition: service_healthy`，milvus 启动时 etcd 还没选主
- milvus 镜像用 v3.0-beta 与 pymilvus 2.4 不兼容

**文件**：用户自有 `docker-compose.yml`（项目外）

- [ ] **Step 1：去掉 etcd command 的反引号**

```yaml
etcd:
  command: etcd -advertise-client-urls=http://etcd:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd
```

- [ ] **Step 2：depends_on 加 health 等待**

```yaml
standalone:
  depends_on:
    etcd:
      condition: service_healthy
    minio:
      condition: service_healthy
```

- [ ] **Step 3：milvus 镜像降到 v2.4.10（与 pymilvus 2.4+ 兼容）**

```yaml
standalone:
  image: milvusdb/milvus:v2.4.10
```

- [ ] **Step 4：清旧数据并重启**

```bash
docker rm -f milvus-standalone milvus-etcd milvus-minio
rm -rf ./volumes
docker compose up -d
```

- [ ] **Step 5：验证 19530 监听**

```bash
# 等 30-60s
Get-NetTCPConnection -LocalPort 19530 -State Listen
docker logs milvus-standalone --tail 30
# 期望：看到 "Proxy successfully started" 等健康日志
```

- [ ] **Step 6：commit（如项目内有 compose 改动）**

### Task 0.2：让后端连上 Milvus 并返回 200

**文件**：`backends/python/config/dev.env`、`backends/python/src/study_vector/main.py`（lifespan）

- [ ] **Step 1：写失败的契约测试**（红）

```python
# backends/python/tests/integration/test_api_smoke.py
import pytest
from httpx import ASGITransport, AsyncClient
from study_vector.dependencies import get_vector_repository
from study_vector.main import create_app
from tests.integration._fake_repo import FakeVectorRepository


@pytest.mark.asyncio
async def test_collections_list_returns_200():
    app = create_app()
    app.dependency_overrides[get_vector_repository] = lambda: FakeVectorRepository()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/collections")
    assert r.status_code == 200
    assert r.json()["code"] == 0
```

- [ ] **Step 2：跑测试**——期望 PASS（用 FakeRepo，Milvus 还没接上）

```bash
cd backends/python
uv run pytest tests/integration/test_api_smoke.py -v
```

- [ ] **Step 3：写失败的健康端点测试**（红）

```python
@pytest.mark.asyncio
async def test_health_ready_reports_milvus_status():
    app = create_app()
    app.dependency_overrides[get_vector_repository] = lambda: FakeVectorRepository(healthy=True)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/health/ready")
    assert r.status_code == 200
    body = r.json()["data"]
    assert body["status"] == "ready"
    assert body["checks"]["milvus"] == "ok"
```

- [ ] **Step 4：实现 `/health/ready` 调用 repo.healthcheck()**

```python
# backends/python/src/study_vector/api/v1/health.py
from fastapi import APIRouter, Depends
from study_vector.dependencies import get_vector_repository
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="存活探针")
async def liveness() -> dict:
    return {"code": 0, "message": "ok", "data": {"status": "ok"}}


@router.get("/ready", summary="就绪探针（含 Milvus 健康）")
async def readiness(repo: VectorRepository = Depends(get_vector_repository)) -> dict:
    milvus_ok = await repo.healthcheck()
    return {
        "code": 0,
        "message": "ready",
        "data": {
            "status": "ready" if milvus_ok else "degraded",
            "checks": {"milvus": "ok" if milvus_ok else "down"},
        },
    }
```

- [ ] **Step 5：跑测试**——期望 PASS

- [ ] **Step 6：在 lifespan 中连接 Milvus（生产逻辑）**

```python
# backends/python/src/study_vector/main.py  (修改 lifespan)
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    factory = get_milvus_factory()
    try:
        await asyncio.to_thread(factory.connect)
        logger.info("Milvus 连接已建立")
    except Exception:
        logger.exception("Milvus 连接失败，进入 degraded 模式")
    yield
    await asyncio.to_thread(factory.close)
```

- [ ] **Step 7：手动 curl 验证 200**

```bash
cd backends/python
uv run uvicorn study_vector.main:app --reload --port 8000
# 另开终端：
curl http://127.0.0.1:8000/api/v1/health
# 期望：{"code":0,"message":"ok","data":{"status":"ok"}}

curl http://127.0.0.1:8000/api/v1/health/ready
# 期望：{"code":0,"message":"ready","data":{"status":"ready","checks":{"milvus":"ok"}}}

curl http://127.0.0.1:8000/api/v1/collections
# 期望：{"code":0,"message":"success","data":[]}
```

- [ ] **Step 8：commit**

```bash
git add backends/python
git commit -m "feat(python): /health/ready 含 Milvus 健康 + 启动连接"
```

---

# 阶段 1：OpenAPI 单一事实源

**目标**：`contracts/openapi.yaml` 是 API 的唯一权威；后端实现 / 前端类型 / 契约测试都从这里派生。

### Task 1.1：建立 contracts 目录与 OpenAPI 骨架

**文件**：
- 创建：`contracts/.gitkeep`、`contracts/openapi.yaml`

- [ ] **Step 1：写 openapi.yaml 头部**

```yaml
openapi: 3.1.0
info:
  title: study_vector API
  version: 0.2.0
  description: |
    向量数据库实战教学平台 — 统一 REST API。

    ## 设计目标
    1. **多向量库适配**：通过 `VectorRepository` 抽象支持多种向量库（V1: Milvus）
    2. **教学友好**：每个字段都有 description 和 examples，可直接作为教学示例
    3. **契约稳定**：本文件是 API 的唯一事实源，后端实现 / 前端类型 / 契约测试都从这里派生

    ## 通用约定
    - 所有响应统一格式：`{ code, message, data }`
    - `code = 0` 表示业务成功；非 0 是错误码（与 HTTP 状态码正交）
    - 业务异常用 `4xx`，后端错误用 `5xx`，向量库后端错误统一 `502`

  contact:
    name: study_vector contributors
  license:
    name: MIT

servers:
  - url: http://localhost:8000
    description: 本地开发（Python FastAPI）
  # 未来扩展：Go / Node 后端
  # - url: http://localhost:8001
  #   description: 本地开发（Go Gin）

tags:
  - name: collections
    description: |
      ## 集合（Collection）管理
      向量集合是组织向量数据的容器，对应传统数据库的"表"。
      本节演示：创建 / 列出 / 查看 / 删除 / 加载到内存 / 从内存释放。
  - name: vectors
    description: |
      ## 向量（Entity）CRUD
      单条向量记录的插入 / 更新 / 查询 / 删除。
  - name: search
    description: |
      ## 向量检索
      相似度检索（ANN），是向量数据库的核心能力。
  - name: indexes
    description: |
      ## 索引管理
      加速检索的索引结构（FLAT / IVF / HNSW / AUTOINDEX 等）。
  - name: partitions
    description: |
      ## 分区
      将集合按业务维度切分，提升检索效率。
  - name: health
    description: 探针端点（k8s / 监控系统用）

paths: {}
components:
  schemas: {}
  responses: {}
  parameters: {}
```

- [ ] **Step 2：commit**

```bash
git add contracts/openapi.yaml
git commit -m "docs(contracts): OpenAPI 骨架与全局约定"
```

### Task 1.2：定义通用响应 / 错误模型

**文件**：`contracts/openapi.yaml`（追加）

- [ ] **Step 1：在 components.schemas 增加通用响应**

```yaml
components:
  schemas:

    # ========== 通用响应包装 ==========
    ApiResponse:
      type: object
      description: |
        **统一响应格式**：所有业务接口都包成这个形状。
        - `code = 0` 表示成功
        - `code ≠ 0` 表示错误（业务 / 校验 / 后端），对应 HTTP 状态码见 error codes 表
      required: [code, message, data]
      properties:
        code:
          type: integer
          description: 业务码。0=成功；非 0=错误（见错误码表）
          example: 0
        message:
          type: string
          description: 人类可读消息
          example: success
        data:
          description: 业务负载；类型由具体端点决定
          oneOf:
            - type: object
            - type: array
            - type: string
            - type: number
            - type: boolean
            - type: 'null'

    # ========== 错误码 ==========
    ErrorCode:
      type: string
      enum:
        - COLLECTION_NOT_FOUND      # 404
        - COLLECTION_ALREADY_EXISTS # 409
        - VECTOR_DIMENSION_MISMATCH # 422
        - VALIDATION_ERROR          # 422
        - VECTOR_BACKEND_ERROR      # 502
        - INTERNAL_ERROR            # 500
      description: |
        业务错误码常量。
        - `COLLECTION_NOT_FOUND`: 操作的集合不存在
        - `COLLECTION_ALREADY_EXISTS`: 集合名重复
        - `VECTOR_DIMENSION_MISMATCH`: 向量维度与集合 schema 不符
        - `VALIDATION_ERROR`: 请求参数校验失败
        - `VECTOR_BACKEND_ERROR`: 向量库后端（如 Milvus）出错
        - `INTERNAL_ERROR`: 未预期的服务器内部错误

    ErrorResponse:
      type: object
      description: 错误响应（与 ApiResponse 同构，但 code 一定非 0）
      required: [code, message, data]
      properties:
        code:
          $ref: '#/components/schemas/ErrorCode'
        message:
          type: string
          example: 集合不存在 name=demo
        data:
          type: 'null'
          example: null

  responses:
    NotFound:
      description: 资源不存在
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    BadRequest:
      description: 参数校验失败
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
    BackendError:
      description: 向量库后端错误
      content:
        application/json:
          schema:
            $ref: '#/components/schemas/ErrorResponse'
```

- [ ] **Step 2：用 Redocly 校验语法**

```bash
# 安装一次
npm install -g @redocly/cli
redocly lint contracts/openapi.yaml
```

期望：0 errors。

- [ ] **Step 3：commit**

```bash
git add contracts/openapi.yaml
git commit -m "docs(contracts): 通用响应与错误码模型"
```

### Task 1.3：定义 collections 端点

**文件**：`contracts/openapi.yaml`（追加 paths/components）

- [ ] **Step 1：增加 DistanceMetric 枚举**

```yaml
components:
  schemas:
    DistanceMetric:
      type: string
      enum: [COSINE, L2, IP, HAMMING, JACCARD]
      description: |
        相似度度量方式。
        - **COSINE**（余弦相似度）：只看方向不看模长，最常用；归一化向量等价于内积
        - **L2**（欧氏距离）：两点直线距离；对向量模长敏感
        - **IP**（内积）：未归一化向量的"对齐度"
        - **HAMMING / JACCARD**：用于二值向量
      example: COSINE
```

- [ ] **Step 2：增加 CollectionSchema**

```yaml
    CollectionSchema:
      type: object
      description: |
        向量集合的 schema 定义。
        业务约定：所有集合自动包含三个字段——
          - `<primary_field>` (VARCHAR, 主键)
          - `<vector_field>` (FLOAT_VECTOR, 维度 = dimension)
          - `payload` (JSON, 业务元数据，可检索)
      required: [name, dimension]
      properties:
        name:
          type: string
          minLength: 1
          maxLength: 255
          pattern: '^[a-zA-Z][a-zA-Z0-9_]*$'
          description: |
            集合名。命名规则：
            - 以字母开头
            - 后续字符：字母 / 数字 / 下划线
            - 长度 1-255
          example: demo_collection
        dimension:
          type: integer
          minimum: 1
          maximum: 65536
          description: |
            向量维度。
            - 与使用的嵌入模型输出一致（如 OpenAI text-embedding-3-small=1536，BGE-base=768）
            - 一旦创建不可修改
          example: 1536
        metric:
          $ref: '#/components/schemas/DistanceMetric'
        primary_field:
          type: string
          default: id
          maxLength: 128
          description: 主键字段名。V1 固定为 VARCHAR 类型。
          example: id
        vector_field:
          type: string
          default: vector
          maxLength: 128
          description: 向量字段名。
          example: vector
        description:
          type: string
          nullable: true
          maxLength: 1024
          description: 集合描述（人类可读）。
          example: "Demo collection for tutorial"
```

- [ ] **Step 3：增加 CollectionInfo**

```yaml
    CollectionInfo:
      type: object
      description: 集合运行时信息
      required: [name, dimension, metric, row_count]
      properties:
        name:
          type: string
          example: demo_collection
        dimension:
          type: integer
          example: 1536
        metric:
          $ref: '#/components/schemas/DistanceMetric'
        row_count:
          type: integer
          description: 当前集合内向量条数
          example: 1024
        loaded:
          type: boolean
          description: 是否已加载到内存（已加载才能检索）
          example: true
        created_at:
          type: string
          format: date-time
          nullable: true
          example: "2026-06-24T08:00:00Z"
```

- [ ] **Step 4：增加 collection 端点**

```yaml
paths:
  /api/v1/collections:
    get:
      tags: [collections]
      summary: 列出所有集合
      description: |
        返回当前 Milvus 中所有集合的名字。
        教学点：Milvus 用 etcd 存元数据；列集合是元数据查询，不会扫数据。
      operationId: listCollections
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items: {type: string}
                        example: ["demo_collection", "tutorial_index"]

    post:
      tags: [collections]
      summary: 创建集合
      description: |
        根据 schema 创建一个空集合，并自动建好 AUTOINDEX 索引 + 加载到内存。
        教学点：
        - 集合 = 表 + schema + 索引 的组合
        - 索引建好才能检索
        - AUTOINDEX 是 Milvus 的"自动选最优索引"机制
      operationId: createCollection
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/CollectionSchema'
            examples:
              default:
                summary: 最小可用 schema
                value:
                  name: demo_collection
                  dimension: 4
              openai_1536:
                summary: OpenAI 嵌入模型
                value:
                  name: openai_chunks
                  dimension: 1536
                  metric: COSINE
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: object
                        properties:
                          name: {type: string}
        '409':
          $ref: '#/components/responses/NotFound'
        '502':
          $ref: '#/components/responses/BackendError'

  /api/v1/collections/{name}:
    parameters:
      - name: name
        in: path
        required: true
        schema: {type: string}
        description: 集合名

    get:
      tags: [collections]
      summary: 查看集合详情
      operationId: getCollection
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        $ref: '#/components/schemas/CollectionInfo'
        '404':
          $ref: '#/components/responses/NotFound'

    delete:
      tags: [collections]
      summary: 删除集合
      description: |
        删除集合及其所有数据。**不可恢复**。
        教学点：生产环境删除前应先 release + 备份。
      operationId: dropCollection
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: object
                        properties:
                          name: {type: string}
```

- [ ] **Step 5：lint + commit**

```bash
redocly lint contracts/openapi.yaml
git add contracts/openapi.yaml
git commit -m "docs(contracts): collections 端点完整定义"
```

### Task 1.4：定义 vectors 端点

> **说明**：此 task 的步骤结构同 1.3，鉴于篇幅这里只列 endpoint 摘要。具体字段描述在 `contracts/openapi.yaml` 中按 Pydantic 字段一一对应。

**文件**：`contracts/openapi.yaml`

- [ ] **Step 1：定义 VectorRecord 端点模型**

```yaml
    VectorRecord:
      type: object
      required: [vector]
      properties:
        id:
          type: string
          maxLength: 128
          description: |
            主键值。留空时后端自动生成 UUID。
            业务上常用"内容 hash"或外部业务 ID。
          example: "doc-001-chunk-007"
        vector:
          type: array
          items: {type: number, format: float}
          minItems: 1
          description: |
            向量数组。
            - 长度必须 = 集合的 `dimension`
            - 服务端不会校验语义（是否为有效嵌入），由调用方保证
          example: [0.012, -0.034, 0.056, 0.078]

    SearchRequest:
      type: object
      required: [vector]
      properties:
        vector:
          type: array
          items: {type: number, format: float}
          minItems: 1
        top_k:
          type: integer
          default: 10
          minimum: 1
          maximum: 1000
          description: 返回最相似的 K 条
        filter:
          type: object
          additionalProperties: true
          description: |
            标量过滤条件（key 为 payload 字段名，value 为匹配值）。
            简化实现只支持 == 与 AND。
          example: {"category": "news", "lang": "zh"}
        output_fields:
          type: array
          items: {type: string}
          description: 返回结果中要包含的 payload 字段
          example: ["title", "url"]

    SearchResult:
      type: object
      properties:
        id: {type: string}
        score: {type: number, format: float, description: 相似度分数}
        payload:
          type: object
          additionalProperties: true
```

- [ ] **Step 2：定义 5 个端点**

```yaml
paths:
  /api/v1/collections/{name}/vectors:
    parameters:
      - {name: name, in: path, required: true, schema: {type: string}}
    post:
      tags: [vectors]
      summary: 批量插入
      operationId: insertVectors
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: array
              items: {$ref: '#/components/schemas/VectorRecord'}
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: object
                        properties:
                          ids: {type: array, items: {type: string}}
                          count: {type: integer}

    put:
      tags: [vectors]
      summary: 存在则更新否则插入
      operationId: upsertVectors
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: array
              items: {$ref: '#/components/schemas/VectorRecord'}
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: object
                        properties:
                          ids: {type: array, items: {type: string}}
                          count: {type: integer}

  /api/v1/collections/{name}/vectors:delete:
    parameters:
      - {name: name, in: path, required: true, schema: {type: string}}
    post:
      tags: [vectors]
      summary: 按 id 批量删除
      operationId: deleteVectors
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [ids]
              properties:
                ids: {type: array, items: {type: string}}
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: object
                        properties:
                          deleted: {type: integer, description: 实际删除条数}

  /api/v1/collections/{name}/vectors:get:
    parameters:
      - {name: name, in: path, required: true, schema: {type: string}}
    post:
      tags: [vectors]
      summary: 按 id 拉取
      operationId: getVectors
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [ids]
              properties:
                ids: {type: array, items: {type: string}}
      responses:
        '200':
          description: 成功

  /api/v1/collections/{name}/search:
    parameters:
      - {name: name, in: path, required: true, schema: {type: string}}
    post:
      tags: [search]
      summary: 向量相似度检索（ANN）
      description: |
        给定 query 向量，返回集合内最相似的 top_k 条记录。
        教学点：
        - **ANN**（Approximate Nearest Neighbor）：用索引近似搜索，速度比精确快几个数量级
        - 检索前**必须**已加载到内存（`loaded=true`）
        - `filter` 在向量检索之前先做标量过滤，可显著提速
      operationId: searchVectors
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/SearchRequest'
      responses:
        '200':
          description: 成功
          content:
            application/json:
              schema:
                allOf:
                  - $ref: '#/components/schemas/ApiResponse'
                  - type: object
                    properties:
                      data:
                        type: array
                        items: {$ref: '#/components/schemas/SearchResult'}
```

- [ ] **Step 3：lint + commit**

```bash
redocly lint contracts/openapi.yaml
git add contracts/openapi.yaml
git commit -m "docs(contracts): vectors + search 端点"
```

### Task 1.5：定义 indexes / partitions / health 端点

> 同样模式；这里给 schema 摘要。

- [ ] **Step 1：indexes 端点（建/查/删索引）**

```yaml
paths:
  /api/v1/collections/{name}/indexes:
    parameters:
      - {name: name, in: path, required: true, schema: {type: string}}
    post:
      tags: [indexes]
      summary: 为向量字段建索引
      operationId: createIndex
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [field_name, index_type]
              properties:
                field_name:
                  type: string
                  description: 要建索引的字段名（一般是向量字段）
                index_type:
                  type: string
                  enum: [FLAT, IVF_FLAT, IVF_SQ8, IVF_PQ, HNSW, ANNOY, AUTOINDEX]
                  description: |
                    索引类型。**AUTOINDEX** 是 Milvus 的"自动选最优"（生产推荐）。
                metric_type: {$ref: '#/components/schemas/DistanceMetric'}
                params:
                  type: object
                  description: 索引参数（如 HNSW 的 M / efConstruction）
                  additionalProperties: true
```

- [ ] **Step 2：partitions 端点**

```yaml
paths:
  /api/v1/collections/{name}/partitions:
    parameters:
      - {name: name, in: path, required: true, schema: {type: string}}
    get:
      tags: [partitions]
      summary: 列出分区
      operationId: listPartitions
    post:
      tags: [partitions]
      summary: 创建分区
      operationId: createPartition
      requestBody:
        required: true
        content:
          application/json:
            schema:
              type: object
              required: [name]
              properties:
                name: {type: string, description: 分区名}
```

- [ ] **Step 3：health 端点（已存在，确认 OpenAPI 同步）**

> `/api/v1/health` 和 `/api/v1/health/ready` 在 OpenAPI 中体现；后端已实现。

- [ ] **Step 4：lint + commit**

```bash
redocly lint contracts/openapi.yaml
git add contracts/openapi.yaml
git commit -m "docs(contracts): indexes + partitions + health 端点"
```

### Task 1.6：用 schemathesis 给后端做契约测试

- [ ] **Step 1：装 schemathesis**

```bash
cd backends/python
uv add --dev schemathesis
```

- [ ] **Step 2：写契约测试**

```python
# backends/python/tests/contract/test_openapi_compliance.py
"""基于 OpenAPI 的契约测试：自动派生所有端点的测试用例。"""
import pytest
import schemathesis
from hypothesis import HealthCheck, settings

from study_vector.main import create_app

app = create_app()
schema = schemathesis.from_asgi("/openapi.json", app)


@pytest.fixture
def fake_repo_override():
    """契约测试不需要真 Milvus，用 FakeRepo 替换。"""
    from study_vector.dependencies import get_vector_repository
    from tests.integration._fake_repo import FakeVectorRepository
    repo = FakeVectorRepository()
    app.dependency_overrides[get_vector_repository] = lambda: repo
    yield repo
    app.dependency_overrides.clear()


@schema.parametrize()
@settings(
    max_examples=20,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)
def test_api_matches_openapi(case, fake_repo_override):
    """对每个 OpenAPI 派生的 case，验证响应符合 schema。"""
    case.call_and_validate()
```

- [ ] **Step 3：跑测试**

```bash
uv run pytest tests/contract -v
```

期望：所有派生用例通过（FakeRepo 满足所有响应 schema）。

- [ ] **Step 4：commit**

```bash
git add backends/python
git commit -m "test(contract): schemathesis 自动派生契约测试"
```

---

# 阶段 2：前端按"向量库 → 功能"重构

**目标**：UI 导航从"功能"改为"向量库"，并加教学维度。

### Task 2.1：生成前端 API 客户端

- [ ] **Step 1：装 openapi-typescript**

```bash
cd frontend
npm install -D openapi-typescript
```

- [ ] **Step 2：在后端导出 OpenAPI JSON**

```bash
cd backends/python
uv run python -c "
import json
from study_vector.main import create_app
app = create_app()
print(json.dumps(app.openapi(), indent=2))
" > ../frontend/src/api/openapi.json
```

或：写个脚本 `contracts/sync_openapi.sh`。

- [ ] **Step 3：生成 TS 类型**

```bash
cd frontend
npx openapi-typescript src/api/openapi.json --output src/api/schema.d.ts
```

- [ ] **Step 4：写 typed API client**

```ts
// frontend/src/api/client.ts
import type { components, paths } from './schema';

type ApiResponse<T> = { code: number; message: string; data: T };

async function call<T>(method: string, url: string, body?: any): Promise<T> {
  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const json: ApiResponse<T> = await r.json();
  if (json.code !== 0) throw new Error(`${json.code}: ${json.message}`);
  return json.data;
}

export const collectionsApi = {
  list: () => call<string[]>('GET', '/api/v1/collections'),
  create: (schema: components['schemas']['CollectionSchema']) =>
    call<{name: string}>('POST', '/api/v1/collections', schema),
  info: (name: string) =>
    call<components['schemas']['CollectionInfo']>('GET', `/api/v1/collections/${name}`),
  remove: (name: string) => call<{name: string}>('DELETE', `/api/v1/collections/${name}`),
};

// 类似地：vectorsApi / searchApi / indexesApi / partitionsApi
```

- [ ] **Step 5：commit**

```bash
git add frontend
git commit -m "feat(frontend): 从 OpenAPI 自动生成 API 客户端"
```

### Task 2.2：导航重构为"向量库 → 功能"

- [ ] **Step 1：写路由配置**

```ts
// frontend/src/router/index.ts
export const routes = [
  { path: '/', component: () => import('@/pages/Home.tsx') },

  // 一级：向量库
  {
    path: '/milvus',
    component: () => import('@/pages/MilvusLayout.tsx'),
    children: [
      { path: '', component: () => import('@/pages/milvus/Dashboard.tsx') },
      { path: 'collections', component: () => import('@/pages/milvus/Collections.tsx') },
      { path: 'collections/:name', component: () => import('@/pages/milvus/CollectionDetail.tsx') },
      { path: 'vectors', component: () => import('@/pages/milvus/Vectors.tsx') },
      { path: 'indexes', component: () => import('@/pages/milvus/Indexes.tsx') },
      { path: 'search', component: () => import('@/pages/milvus/Search.tsx') },
      { path: 'partitions', component: () => import('@/pages/milvus/Partitions.tsx') },
    ],
  },

  // 未来：Qdrant / Weaviate / Chroma...
  // { path: '/qdrant', ... },
];
```

- [ ] **Step 2：写侧边栏组件**

```tsx
// frontend/src/components/Sidebar.tsx
import { NavLink } from 'react-router-dom';

const VECTOR_DBS = [
  { key: 'milvus', name: 'Milvus', icon: '🧊', features: [
    { path: '/milvus/collections', label: '集合 (Collections)' },
    { path: '/milvus/vectors',     label: '向量 (Vectors)' },
    { path: '/milvus/indexes',     label: '索引 (Indexes)' },
    { path: '/milvus/search',      label: '检索 (Search)' },
    { path: '/milvus/partitions',  label: '分区 (Partitions)' },
  ]},
  // 未来：Qdrant / Weaviate / Chroma
];

export function Sidebar() {
  return (
    <nav className="sidebar">
      {VECTOR_DBS.map(db => (
        <div key={db.key} className="db-group">
          <h3>{db.icon} {db.name}</h3>
          {db.features.map(f => (
            <NavLink key={f.path} to={f.path} className="feature-link">
              {f.label}
            </NavLink>
          ))}
        </div>
      ))}
    </nav>
  );
}
```

- [ ] **Step 3：每个功能页面骨架**

```tsx
// frontend/src/pages/milvus/Collections.tsx
import { useEffect, useState } from 'react';
import { collectionsApi } from '@/api/client';
import { ParamHelp } from '@/components/ParamHelp';

export default function Collections() {
  const [list, setList] = useState<string[]>([]);
  const [name, setName] = useState('');
  const [dim, setDim] = useState(1536);
  const [metric, setMetric] = useState<'COSINE' | 'L2' | 'IP'>('COSINE');

  useEffect(() => { collectionsApi.list().then(setList); }, []);

  return (
    <div>
      <h2>集合管理</h2>

      <section>
        <h3>创建集合</h3>
        <form onSubmit={async e => {
          e.preventDefault();
          await collectionsApi.create({ name, dimension: dim, metric });
          setList(await collectionsApi.list());
        }}>
          <label>
            名称
            <ParamHelp field="CollectionSchema.name" />
            <input value={name} onChange={e => setName(e.target.value)} />
          </label>
          <label>
            维度
            <ParamHelp field="CollectionSchema.dimension" />
            <input type="number" value={dim} onChange={e => setDim(+e.target.value)} />
          </label>
          <label>
            距离度量
            <ParamHelp field="CollectionSchema.metric" />
            <select value={metric} onChange={e => setMetric(e.target.value as any)}>
              <option value="COSINE">COSINE (余弦)</option>
              <option value="L2">L2 (欧氏)</option>
              <option value="IP">IP (内积)</option>
            </select>
          </label>
          <button type="submit">创建</button>
        </form>
      </section>

      <section>
        <h3>集合列表</h3>
        <ul>{list.map(n => <li key={n}>{n} <button onClick={() => collectionsApi.remove(n).then(() => collectionsApi.list().then(setList))}>删除</button></li>)}</ul>
      </section>
    </div>
  );
}
```

- [ ] **Step 4：commit**

```bash
git add frontend
git commit -m "feat(frontend): 导航改为向量库 → 功能 + 教学侧边栏"
```

### Task 2.3：ParamHelp 组件（hover 显示字段说明）

- [ ] **Step 1：参数说明元数据**

```ts
// frontend/src/lib/fieldDocs.ts
// 来自 contracts/openapi.yaml 的 description 字段（自动生成 or 手维护）
export const fieldDocs: Record<string, string> = {
  'CollectionSchema.name':        '集合名。以字母开头，后续字符为字母/数字/下划线，长度 1-255。',
  'CollectionSchema.dimension':   '向量维度。与嵌入模型输出一致（如 OpenAI text-embedding-3-small=1536）。一旦创建不可修改。',
  'CollectionSchema.metric':      '相似度度量。COSINE=余弦（推荐）；L2=欧氏；IP=内积。',
  'SearchRequest.top_k':          '返回最相似的 K 条。建议 5-100。',
  'SearchRequest.filter':         '标量过滤（key=字段名，value=值），先于向量检索执行，可显著提速。',
  'VectorRecord.id':              '主键值。留空时后端自动生成 UUID。',
  'VectorRecord.vector':          '向量数组，长度必须等于集合 dimension。',
};
```

- [ ] **Step 2：ParamHelp 组件**

```tsx
// frontend/src/components/ParamHelp.tsx
import { fieldDocs } from '@/lib/fieldDocs';

export function ParamHelp({ field }: { field: string }) {
  const doc = fieldDocs[field];
  if (!doc) return null;
  return (
    <span className="param-help" title={doc}>ⓘ</span>
  );
}
```

- [ ] **Step 3：在 Collections.tsx 等页面引入 ParamHelp（上一 task 已示范）**

- [ ] **Step 4：commit**

```bash
git add frontend
git commit -m "feat(frontend): ParamHelp 组件 + 字段说明元数据"
```

### Task 2.4：ApiResponseViewer 组件（透明展示 API）

- [ ] **Step 1：写组件**

```tsx
// frontend/src/components/ApiResponseViewer.tsx
import { useState } from 'react';

export function ApiResponseViewer({ request, response }: {
  request: { method: string; url: string; body?: any };
  response?: { status: number; data: any; durationMs: number };
}) {
  const [tab, setTab] = useState<'request' | 'response'>('response');
  return (
    <div className="api-viewer">
      <div className="tabs">
        <button onClick={() => setTab('response')} className={tab==='response'?'active':''}>响应</button>
        <button onClick={() => setTab('request')}  className={tab==='request'?'active':''}>请求</button>
      </div>
      {tab === 'response' ? (
        <div>
          <div className="meta">
            状态: <code>{response?.status}</code> · 耗时: <code>{response?.durationMs}ms</code>
          </div>
          <pre>{JSON.stringify(response?.data, null, 2)}</pre>
        </div>
      ) : (
        <pre>{request.method} {request.url}\n{JSON.stringify(request.body, null, 2)}</pre>
      )}
    </div>
  );
}
```

- [ ] **Step 2：在所有功能页用 ApiResponseViewer 包装调用结果**

- [ ] **Step 3：commit**

```bash
git add frontend
git commit -m "feat(frontend): ApiResponseViewer 展示原始请求/响应"
```

---

# 阶段 3：教学示例（每个功能点一个可跑示例）

**目标**：每个功能点（创建集合 / 索引 / 检索 / 分区）有"复制即可跑"的 Markdown 示例 + UI 一键运行。

### Task 3.1：教学 Markdown 模板

- [ ] **Step 1：写 01-first-collection.md**

````markdown
# 第一个集合

## 概念
集合 = 表 + schema + 索引。类比 MySQL：`CREATE TABLE t (id VARCHAR, vector FLOAT_VECTOR(1536))`。

## 1. 创建集合
```bash
curl -X POST http://localhost:8000/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{
    "name": "demo",
    "dimension": 4,
    "metric": "COSINE",
    "description": "my first collection"
  }'
```

## 2. 解释每个参数
- `name`: 集合名（同 MySQL 表名）
- `dimension`: 4 是因为我们演示用，生产一般是 768/1536
- `metric`: 余弦相似度（文本嵌入首选）

## 3. 期望响应
```json
{"code":0,"message":"success","data":{"name":"demo"}}
```

## 4. 接下来
- [插入向量](./02-insert-vectors.md)
````

- [ ] **Step 2：写 02-insert-vectors.md**

类似结构，演示插入两条向量。

- [ ] **Step 3：commit**

```bash
git add frontend/src/tutorials
git commit -m "docs(frontend): 教学示例 01/02 Markdown"
```

### Task 3.2：UI 集成教学示例

- [ ] **Step 1：TutorialPanel 组件**

```tsx
// frontend/src/components/TutorialPanel.tsx
import { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';

export function TutorialPanel({ slug }: { slug: string }) {
  const [content, setContent] = useState('');
  useEffect(() => {
    import(`@/tutorials/milvus/${slug}.md?raw`)
      .then(m => setContent(m.default))
      .catch(() => setContent('# 教程未找到'));
  }, [slug]);
  return <div className="tutorial-panel"><ReactMarkdown>{content}</ReactMarkdown></div>;
}
```

- [ ] **Step 2：每个功能页加 TutorialPanel**

```tsx
// 在 Collections.tsx 末尾
<TutorialPanel slug="01-first-collection" />
```

- [ ] **Step 3：commit**

```bash
git add frontend
git commit -m "feat(frontend): TutorialPanel 集成教学示例"
```

---

# 阶段 4：架构文档与新向量库扩展指南

### Task 4.1：更新 overview.md / repository-pattern.md

- [ ] **Step 1：overview.md 加"多向量库"段落**

把现在的"多语言后端"段落改为"多向量库 + 多语言后端"。

- [ ] **Step 2：repository-pattern.md 加"为新向量库加 driver"步骤**

```markdown
## 添加新向量库（以 Qdrant 为例）

1. 装 SDK：`uv add qdrant-client`
2. 新建 `infra/qdrant/client.py`：单例管理 qdrant_client
3. 新建 `infra/qdrant/repository.py`：
   ```python
   class QdrantRepository:
       """实现 VectorRepository 协议。"""
       async def connect(self) -> None: ...
       async def create_collection(self, schema: CollectionSchema) -> None: ...
       # ... 其他方法
   ```
4. 在 `dependencies.py` 注册：
   ```python
   _BUILDERS = {
       "milvus": lambda: MilvusRepository(),
       "qdrant": lambda: QdrantRepository(),
   }
   ```
5. 在 settings 加 `vector_backend: Literal["milvus","qdrant"]`
6. 跑契约测试（OpenAPI 不变，契约测试自动覆盖新 driver）
7. 前端 `Sidebar.tsx` 加新入口
```

- [ ] **Step 3：commit**

```bash
git add docs
git commit -m "docs: 多向量库 + 新 driver 扩展指南"
```

### Task 4.2：multi-vector-db.md（新文档）

- [ ] **Step 1：写文档**

说明不同向量库对比维度（CRUD 一致性 / 索引类型 / 标量过滤能力 / 混合检索 / 部署难度）。

- [ ] **Step 2：commit**

```bash
git add docs/architecture/multi-vector-db.md
git commit -m "docs: 多向量库对比维度"
```

---

# 阶段 5：验收与一键脚本

### Task 5.1：justfile 新增教学流程 recipe

- [ ] **Step 1：在 justfile 加 tutorial 一组**

```just
# 跑教学示例 01：创建第一个集合
tutorial-01:
    Push-Location backends/python; just run; Pop-Location &
    Sleep 5
    curl -X POST http://127.0.0.1:8000/api/v1/collections \
        -H "Content-Type: application/json" \
        -d '{"name":"demo","dimension":4,"metric":"COSINE"}'
```

> （注意：单行写法保持稳定）

- [ ] **Step 2：commit**

```bash
git add justfile
git commit -m "feat(just): tutorial 教学流程 recipe"
```

### Task 5.2：完整验收清单

- [ ] `docker compose up -d` 一键起 Milvus + API + Frontend
- [ ] `http://localhost:8000/docs` OpenAPI 文档展示所有字段说明
- [ ] `http://localhost:5173` 进入 Milvus → Collections 页，能创建/列出/删除
- [ ] 每个表单字段都有 ⓘ hover 出字段说明
- [ ] 每个操作后下方展示原始 API 响应
- [ ] 侧边栏有"教学示例"按钮，点击加载对应 Markdown
- [ ] `uv run pytest` 全部通过（单元 + 集成 + 契约）
- [ ] `redocly lint contracts/openapi.yaml` 0 errors
- [ ] `ruff check` 0 errors

---

# 阶段 6（v0.3+，可选扩展）

- [ ] 接入 Qdrant / Weaviate / Chroma 任一
- [ ] Go / Node 后端（OpenAPI 契约已就绪，可生成 stub）
- [ ] OpenTelemetry 接入 + Prometheus 指标
- [ ] 教学视频 / 动画

---

# 风险与回滚

| 风险 | 缓解 |
|---|---|
| OpenAPI 与实现漂移 | 阶段 1.6 契约测试 + CI 强制 schemathesis 通过 |
| 前端类型生成遗漏 | openapi-typescript 每次 CI 跑；不一致则 fail |
| Milvus 数据丢失 | 阶段 0 之前用 v0.1 已有的数据；新 schema 兼容 |
| 教学示例过时 | 阶段 3 示例与 OpenAPI 例子同源（从 example 字段渲染） |

---

# 验收清单（v0.2 全部完成时）

- [ ] 阶段 0：Milvus 跑通 + API 200
- [ ] 阶段 1：`contracts/openapi.yaml` 完整 + schemathesis 绿
- [ ] 阶段 2：UI 导航重构完成 + ParamHelp / ApiResponseViewer / TutorialPanel
- [ ] 阶段 3：每个功能点有 Markdown 教学示例
- [ ] 阶段 4：docs 更新
- [ ] 阶段 5：justfile 教学流程 + 验收清单全过
