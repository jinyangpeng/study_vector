# study\_vector 实施计划

> **For agentic workers:** 本计划按阶段拆分，每个阶段均可独立交付可运行/可演示的成果。步骤使用 checkbox (`- [ ]`) 语法跟踪进度。

## 目标

构建一个用于**研究多种向量数据库**的学习与对比平台：

* **第一阶段**：Python + FastAPI + Milvus（用户已通过 Docker 部署好 Milvus）。

* **第二阶段**：响应式前端（兼容多语言后端 / 多向量数据库）。

* **第三阶段**：扩展为多语言（Go / Node 等）+ 多向量数据库（Chroma / Qdrant / Weaviate / pgvector 等），通过统一抽象与多服务隔离。

* 全程遵循**企业级最佳实践**：分层架构、配置外部化、依赖注入、可观测性、容器化部署、完善文档。

* 代码与文档统一**中文注释**。

## 总体架构

```
study_vector/                       # 仓库根
├── docs/                           # 顶层文档（架构、ADR、对比报告）
├── deploy/                         # 顶层 Docker Compose / 编排
├── frontend/                       # 唯一前端（与具体后端语言解耦）
├── backends/                       # 多语言后端，按语言隔离
│   └── python/                     # Python 后端（本次首期交付）
│       ├── src/study_vector/       # 业务代码
│       ├── tests/                  # 测试代码
│       ├── config/                 # 多环境配置（dev/test/prod）
│       ├── deploy/                 # 子级 Dockerfile
│       └── pyproject.toml          # uv 管理
│   ├── go/                         # 未来扩展
│   └── node/                       # 未来扩展
└── README.md
```

**关键设计原则**：

1. **后端按语言隔离**：每个语言独立目录、独立 `pyproject.toml / go.mod / package.json`、独立 Dockerfile。
2. **向量数据库通过 Repository 抽象**：`VectorDBRepository` 协议 → `MilvusRepository / ChromaRepository / QdrantRepository ...`；业务层只依赖协议。
3. **后端语言通过统一 OpenAPI/JSON 协议向前端暴露**：前端不关心后端是 Python 还是 Go，只看 OpenAPI 文档。
4. **多环境配置**：`dev / test / prod` 通过 `APP_ENV` 切换；敏感信息走环境变量，绝不入库。
5. **依赖注入**：FastAPI Depends、ContextVar 管理请求级客户端。
6. **可观测性**：结构化日志（loguru）、健康检查、Prometheus 指标（可选）、统一异常处理。

## 技术栈

| 类别        | 选型                                                                    |
| --------- | --------------------------------------------------------------------- |
| 语言        | Python 3.11+                                                          |
| Web 框架    | FastAPI + Uvicorn                                                     |
| 依赖/环境     | uv（lockfile + workspace）                                              |
| 配置        | pydantic-settings + .env.{env}                                        |
| 日志        | loguru + 结构化 JSON                                                     |
| 向量库 SDK   | pymilvus                                                              |
| 数据校验      | Pydantic v2                                                           |
| 迁移/Schema | pymilvus SDK（Milvus 无传统迁移，用工具函数建 Collection）                          |
| 测试        | pytest + pytest-asyncio + httpx + testcontainers（可选）                  |
| 容器化       | Docker + docker compose（顶层编排）                                         |
| 文档        | OpenAPI（FastAPI 自动生成）+ MkDocs（可选）                                     |
| 前端        | Vue 3 + Vite + Element Plus（响应式、桌面/移动端适配），通过 OpenAPI 客户端生成或 axios 调后端 |

***

# 阶段 0：仓库初始化与基础设施

**目标**：建立可扩展的仓库骨架，让任何后端语言、前端、向量数据库都可以无侵入地加入。

### Task 0.1：仓库根初始化

**文件**：

* 创建：`README.md`、`.gitignore`、`.editorconfig`、`.pre-commit-config.yaml`（可选）、`LICENSE`（可选）

* [ ] **Step 1：创建** **`.gitignore`**

```gitignore
# Python
__pycache__/
*.py[cod]
.venv/
*.egg-info/
.pytest_cache/
.ruff_cache/
.mypy_cache/

# 环境
.env
.env.local
*.local

# 编辑器
.vscode/
.idea/
*.swp

# 前端
node_modules/
dist/
.vite/

# 日志 / 数据
logs/
*.log
data/

# 系统
.DS_Store
Thumbs.db
```

* [ ] **Step 2：创建** **`.editorconfig`**

```ini
root = true
[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
indent_style = space
indent_size = 4
trim_trailing_whitespace = true

[*.{yml,yaml,json,md}]
indent_size = 2
```

* [ ] **Step 3：写根** **`README.md`**（中文，写明项目定位、目录结构、扩展方式）

```markdown
# study_vector

一个用于系统学习、对比多种**向量数据库**（Milvus / Chroma / Qdrant / Weaviate / pgvector 等）的开源研究项目。
支持多语言后端（Python / Go / Node 等）、统一抽象、统一前端展示。

## 目录结构

- `backends/python/`：Python 后端（FastAPI + uv + pymilvus，首期交付）
- `backends/go/`：Go 后端（未来扩展）
- `backends/node/`：Node 后端（未来扩展）
- `frontend/`：响应式前端（Vue 3）
- `deploy/`：顶层 Docker Compose 编排
- `docs/`：架构设计、对比报告、ADR

## 快速开始

参见 `docs/quickstart.md`。
```

* [ ] **Step 4：初始化 git 仓库并首次提交**

```bash
cd c:/Workspace/Development/Study/study_vector
git init
git add .
git commit -m "chore: initialize study_vector repository"
```

***

### Task 0.2：建立顶层目录骨架

**文件**：创建空目录占位文件

* [ ] **Step 1：建立目录结构**

```bash
mkdir -p backends/python/src/study_vector
mkdir -p backends/python/tests
mkdir -p backends/python/config
mkdir -p backends/python/deploy
mkdir -p backends/go
mkdir -p backends/node
mkdir -p frontend
mkdir -p deploy
mkdir -p docs/architecture
mkdir -p docs/compare
```

每个空目录加 `.gitkeep`：

```bash
touch backends/go/.gitkeep backends/node/.gitkeep frontend/.gitkeep deploy/.gitkeep docs/architecture/.gitkeep docs/compare/.gitkeep
```

* [ ] **Step 2：顶层** **`docker-compose.yml`** **骨架**（先只放占位）

```yaml
# deploy/docker-compose.yml
# 顶层编排：聚合各后端服务、向量数据库、前端。
# 后续在阶段 4 完善。

services:
  # 占位，各后端服务在对应阶段加入
  milvus:
    image: milvusdb/milvus:v2.4.10
    # ... 由用户提供，或参见 deploy/milvus/
    profiles: ["milvus"]
```

* [ ] **Step 3：提交**

```bash
git add .
git commit -m "chore: scaffold monorepo structure"
```

***

# 阶段 1：Python 后端脚手架

**目标**：可运行的 FastAPI 服务，`/health` 通，配置多环境切换。

### Task 1.1：uv 工程初始化

**文件**：

* 创建：`backends/python/pyproject.toml`、`backends/python/.python-version`、`backends/python/README.md`

* [ ] **Step 1：进入 Python 子工程**

```bash
cd backends/python
```

* [ ] **Step 2：使用 uv 初始化**

```bash
uv init --name study-vector --no-readme --no-pin-python .
```

* [ ] **Step 3：固定 Python 版本**

```bash
uv python pin 3.11
```

* [ ] **Step 4：加入核心依赖**

```bash
uv add fastapi 'uvicorn[standard]' pydantic pydantic-settings loguru httpx pymilvus
uv add --dev pytest pytest-asyncio pytest-cov ruff mypy
```

* [ ] **Step 5：提交**

```bash
git add backends/python/pyproject.toml backends/python/uv.lock backends/python/.python-version
git commit -m "chore(python): init uv project with core deps"
```

***

### Task 1.2：配置管理（多环境）

**文件**：

* 创建：

  * `backends/python/src/study_vector/core/settings.py`

  * `backends/python/src/study_vector/core/logging.py`

  * `backends/python/src/study_vector/core/__init__.py`

  * `backends/python/src/study_vector/__init__.py`

  * `backends/python/config/dev.env`、`test.env`、`prod.env`、`.env.example`

* [ ] **Step 1：写** **`core/settings.py`**

```python
"""应用配置：使用 pydantic-settings 加载多环境配置。"""
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """全局配置入口。

    加载优先级：环境变量 > .env.{APP_ENV} > .env > 默认值
    通过 APP_ENV 切换环境：dev / test / prod
    """

    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # 环境标识
    app_env: Literal["dev", "test", "prod"] = Field(default="dev", alias="APP_ENV")
    app_name: str = Field(default="study-vector", alias="APP_NAME")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")

    # 服务
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # Milvus（首期）
    milvus_host: str = Field(default="localhost", alias="MILVUS_HOST")
    milvus_port: int = Field(default=19530, alias="MILVUS_PORT")
    milvus_user: str = Field(default="root", alias="MILVUS_USER")
    milvus_password: str = Field(default="Milvus", alias="MILVUS_PASSWORD")
    milvus_db_name: str = Field(default="default", alias="MILVUS_DB_NAME")
    milvus_secure: bool = Field(default=False, alias="MILVUS_SECURE")

    # 日志
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    log_json: bool = Field(default=False, alias="LOG_JSON")


@lru_cache
def get_settings() -> Settings:
    """缓存的 settings 单例。

    加载文件顺序由 pydantic-settings 决定。
    在 main.py 中根据 APP_ENV 注入具体 env_file。
    """
    return Settings()
```

* [ ] **Step 2：写** **`core/logging.py`**

```python
"""结构化日志配置。"""
import sys

from loguru import logger

from study_vector.core.settings import get_settings


def setup_logging() -> None:
    """根据 settings 初始化 loguru。"""
    settings = get_settings()
    logger.remove()
    if settings.log_json:
        # 生产可对接 ELK / Loki
        logger.add(sys.stdout, serialize=True, level=settings.log_level)
    else:
        logger.add(
            sys.stdout,
            level=settings.log_level,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
            colorize=True,
        )
    logger.info(f"日志初始化完成 env={settings.app_env} level={settings.log_level}")
```

* [ ] **Step 3：写多环境 env 文件**

`config/dev.env`：

```env
APP_ENV=dev
DEBUG=true
LOG_LEVEL=DEBUG
LOG_JSON=false
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

`config/test.env`：

```env
APP_ENV=test
DEBUG=false
LOG_LEVEL=INFO
LOG_JSON=true
```

`config/prod.env`：

```env
APP_ENV=prod
DEBUG=false
LOG_LEVEL=WARNING
LOG_JSON=true
```

`.env.example`：

```env
APP_ENV=dev
APP_NAME=study-vector
HOST=0.0.0.0
PORT=8000

MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=Milvus
MILVUS_DB_NAME=default
MILVUS_SECURE=false

LOG_LEVEL=INFO
LOG_JSON=false
```

* [ ] **Step 4：提交**

```bash
git add backends/python/src/study_vector/core backends/python/config
git commit -m "feat(python): 多环境配置与日志"
```

***

### Task 1.3：FastAPI 入口与健康检查

**文件**：

* 创建：

  * `backends/python/src/study_vector/main.py`

  * `backends/python/src/study_vector/api/__init__.py`

  * `backends/python/src/study_vector/api/v1/__init__.py`

  * `backends/python/src/study_vector/api/v1/health.py`

* [ ] **Step 1：写** **`api/v1/health.py`**

```python
"""健康检查端点。"""
from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", summary="存活探针")
async def liveness() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", summary="就绪探针（后续接 Milvus 真实检查）")
async def readiness() -> dict[str, str]:
    return {"status": "ready"}
```

* [ ] **Step 2：写** **`main.py`**

```python
"""FastAPI 入口。"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from study_vector.api.v1 import health
from study_vector.core.logging import setup_logging
from study_vector.core.settings import Settings, get_settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动/关闭钩子。"""
    setup_logging()
    settings = get_settings()
    app.state.settings = settings
    yield
    # 关闭钩子：后续关闭 Milvus 连接


def create_app() -> FastAPI:
    """工厂函数：便于测试与多环境装配。"""
    settings = get_settings()
    app = FastAPI(
        title="study_vector API",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
    )
    # 路由聚合
    app.include_router(health.router, prefix="/api/v1")
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings: Settings = get_settings()
    uvicorn.run(
        "study_vector.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )
```

* [ ] **Step 3：本地运行验证**

```bash
cd backends/python
uv run uvicorn study_vector.main:app --reload --port 8000
# 浏览器访问 http://localhost:8000/api/v1/health 看到 {"status":"ok"}
# 访问 http://localhost:8000/docs 看到 OpenAPI
```

* [ ] **Step 4：提交**

```bash
git add backends/python/src/study_vector/main.py backends/python/src/study_vector/api
git commit -m "feat(python): FastAPI 入口与健康检查"
```

***

# 阶段 2：向量数据库抽象层（核心架构）

**目标**：定义 `VectorRepository` 协议 + Milvus 实现 + 工厂选择 + 依赖注入。
**架构原则**：业务层只依赖 `VectorRepository` 协议；切换向量库只改配置不改业务。

### Task 2.1：领域模型与 DTO

**文件**：

* 创建：

  * `backends/python/src/study_vector/domain/__init__.py`

  * `backends/python/src/study_vector/domain/models.py`

* [ ] **Step 1：写** **`domain/models.py`**

```python
"""领域模型与跨库 DTO。

业务层与具体向量库解耦，统一的 Pydantic 模型。
"""
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DistanceMetric(str, Enum):
    """相似度度量。"""
    COSINE = "COSINE"
    EUCLIDEAN = "L2"
    INNER_PRODUCT = "IP"
    HAMMING = "HAMMING"
    JACCARD = "JACCARD"


class IndexType(str, Enum):
    """索引类型（覆盖主流选项，具体实现可裁剪）。"""
    FLAT = "FLAT"
    IVF_FLAT = "IVF_FLAT"
    IVF_SQ8 = "IVF_SQ8"
    IVF_PQ = "IVF_PQ"
    HNSW = "HNSW"
    ANNOY = "ANNOY"
    AUTOINDEX = "AUTOINDEX"


class CollectionSchema(BaseModel):
    """集合（表）schema 定义。"""
    name: str = Field(..., min_length=1, max_length=255)
    dimension: int = Field(..., gt=0, le=65536)
    metric: DistanceMetric = DistanceMetric.COSINE
    primary_field: str = "id"
    vector_field: str = "vector"
    description: str | None = None


class VectorRecord(BaseModel):
    """单条向量记录（业务层统一模型）。"""
    id: str | int | UUID = Field(default_factory=lambda: uuid4())
    vector: list[float] = Field(..., min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)
    score: float | None = None  # 检索时由后端填充


class SearchRequest(BaseModel):
    """向量检索请求。"""
    collection: str
    vector: list[float] = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=1000)
    filter_expr: dict[str, Any] | None = None  # 通用过滤（实现层翻译为原生）
    output_fields: list[str] | None = None


class SearchResult(BaseModel):
    """检索结果。"""
    id: str | int | UUID
    score: float
    payload: dict[str, Any] = Field(default_factory=dict)


class CollectionInfo(BaseModel):
    """集合元信息。"""
    name: str
    dimension: int
    metric: DistanceMetric
    row_count: int = 0
    created_at: datetime | None = None
```

* [ ] **Step 2：提交**

```bash
git add backends/python/src/study_vector/domain
git commit -m "feat(python): 领域模型与统一 DTO"
```

***

### Task 2.2：Repository 协议（接口）

**文件**：

* 创建：

  * `backends/python/src/study_vector/repositories/__init__.py`

  * `backends/python/src/study_vector/repositories/base.py`

* [ ] **Step 1：写** **`repositories/base.py`**

```python
"""向量库 Repository 协议定义。

业务层只依赖此协议，不依赖具体实现。
任何向量库只需提供实现即可无缝接入。
"""
from typing import Protocol, runtime_checkable

from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    SearchRequest,
    SearchResult,
    VectorRecord,
)


@runtime_checkable
class VectorRepository(Protocol):
    """向量库统一接口（Protocol，结构化子类型）。"""

    # ----- 连接生命周期 -----
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def healthcheck(self) -> bool: ...

    # ----- 集合管理 -----
    async def create_collection(self, schema: CollectionSchema) -> None: ...
    async def drop_collection(self, name: str) -> None: ...
    async def has_collection(self, name: str) -> bool: ...
    async def list_collections(self) -> list[str]: ...
    async def get_collection_info(self, name: str) -> CollectionInfo: ...

    # ----- 向量写入 -----
    async def insert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]: ...
    async def upsert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]: ...
    async def delete(
        self, collection: str, ids: list[str | int]
    ) -> int: ...

    # ----- 向量检索 -----
    async def search(self, request: SearchRequest) -> list[SearchResult]: ...
    async def get(
        self, collection: str, ids: list[str | int]
    ) -> list[VectorRecord]: ...
```

* [ ] **Step 2：写** **`repositories/__init__.py`**

```python
"""Repository 抽象层入口。"""
from study_vector.repositories.base import VectorRepository

__all__ = ["VectorRepository"]
```

* [ ] **Step 3：提交**

```bash
git add backends/python/src/study_vector/repositories
git commit -m "feat(python): VectorRepository 协议"
```

***

### Task 2.3：Milvus 客户端封装 + Repository 实现

**文件**：

* 创建：

  * `backends/python/src/study_vector/infra/__init__.py`

  * `backends/python/src/study_vector/infra/milvus/__init__.py`

  * `backends/python/src/study_vector/infra/milvus/client.py`

  * `backends/python/src/study_vector/infra/milvus/repository.py`

* [ ] **Step 1：写** **`infra/milvus/client.py`**

```python
"""Milvus 客户端单例管理。

封装 pymilvus 连接，避免在请求级反复创建连接。
"""
from threading import Lock

from loguru import logger
from pymilvus import MilvusException, connections

from study_vector.core.settings import get_settings


class MilvusClientFactory:
    """线程安全的 Milvus 客户端工厂。"""

    _instance: "MilvusClientFactory | None" = None
    _lock = Lock()
    _connected = False

    def __new__(cls) -> "MilvusClientFactory":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def connect(self) -> None:
        """建立到 Milvus 的连接（幂等）。"""
        if self._connected:
            return
        settings = get_settings()
        try:
            connections.connect(
                alias="default",
                host=settings.milvus_host,
                port=str(settings.milvus_port),
                user=settings.milvus_user,
                password=settings.milvus_password,
                db_name=settings.milvus_db_name,
                secure=settings.milvus_secure,
            )
            self._connected = True
            logger.info(
                f"已连接 Milvus host={settings.milvus_host} port={settings.milvus_port} "
                f"db={settings.milvus_db_name}"
            )
        except MilvusException as e:
            logger.exception("连接 Milvus 失败")
            raise RuntimeError(f"无法连接 Milvus: {e}") from e

    def close(self) -> None:
        if not self._connected:
            return
        try:
            connections.disconnect(alias="default")
            self._connected = False
            logger.info("已断开 Milvus 连接")
        except MilvusException:
            logger.exception("断开 Milvus 失败")

    @property
    def is_connected(self) -> bool:
        return self._connected


def get_milvus_factory() -> MilvusClientFactory:
    return MilvusClientFactory()
```

* [ ] **Step 2：写** **`infra/milvus/repository.py`**

```python
"""Milvus Repository 实现。

将领域模型 <-> pymilvus 模型互相转换。
"""
from datetime import datetime
from typing import Any

from loguru import logger
from pymilvus import (
    Collection,
    CollectionSchema as MilvusCollectionSchema,
    DataType,
    FieldSchema,
    MilvusException,
    utility,
)
from pymilvus.orm.search import SearchResult as MilvusSearchResult

from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    DistanceMetric,
    IndexType,
    SearchRequest,
    SearchResult,
    VectorRecord,
)
from study_vector.infra.milvus.client import get_milvus_factory

# 字符串到 pymilvus DataType 映射
_PAYLOAD_FIELD_TYPE = DataType.VARCHAR  # 业务 payload 统一用 JSON 字符串存放


class MilvusRepository:
    """基于 pymilvus 的 VectorRepository 实现。"""

    def __init__(self) -> None:
        self._factory = get_milvus_factory()

    # ---------- 生命周期 ----------
    async def connect(self) -> None:
        self._factory.connect()

    async def close(self) -> None:
        self._factory.close()

    async def healthcheck(self) -> bool:
        try:
            return utility.get_server_version() is not None
        except MilvusException:
            logger.exception("Milvus 健康检查失败")
            return False

    # ---------- 集合管理 ----------
    def _build_milvus_schema(self, schema: CollectionSchema) -> MilvusCollectionSchema:
        """将业务 schema 翻译为 pymilvus schema。

        业务约定：
        - 主键字段：VARCHAR
        - 向量字段：FLOAT_VECTOR
        - 业务负载：JSON 字符串字段 `payload`
        """
        fields = [
            FieldSchema(
                name=schema.primary_field,
                dtype=DataType.VARCHAR,
                is_primary=True,
                max_length=128,
            ),
            FieldSchema(
                name=schema.vector_field,
                dtype=DataType.FLOAT_VECTOR,
                dim=schema.dimension,
            ),
            FieldSchema(name="payload", dtype=DataType.JSON),
        ]
        return MilvusCollectionSchema(
            fields=fields,
            description=schema.description or "",
            enable_dynamic_field=False,
        )

    async def create_collection(self, schema: CollectionSchema) -> None:
        if await self.has_collection(schema.name):
            logger.info(f"集合已存在，跳过创建 name={schema.name}")
            return
        milvus_schema = self._build_milvus_schema(schema)
        coll = Collection(name=schema.name, schema=milvus_schema)
        # 默认使用 AUTOINDEX；具体调参可暴露配置
        index_params = {
            "metric_type": schema.metric.value,
            "index_type": IndexType.AUTOINDEX.value,
            "params": {},
        }
        coll.create_index(field_name=schema.vector_field, index_params=index_params)
        coll.load()
        logger.info(f"已创建集合 name={schema.name} dim={schema.dimension}")

    async def drop_collection(self, name: str) -> None:
        if not await self.has_collection(name):
            return
        utility.drop_collection(name)
        logger.info(f"已删除集合 name={name}")

    async def has_collection(self, name: str) -> bool:
        return utility.has_collection(name)

    async def list_collections(self) -> list[str]:
        return utility.list_collections()

    async def get_collection_info(self, name: str) -> CollectionInfo:
        coll = Collection(name=name)
        # 取第一个 FLOAT_VECTOR 字段的 dim
        vector_field = next(
            f for f in coll.schema.fields if f.dtype == DataType.FLOAT_VECTOR
        )
        # 统计行数（仅做演示，生产可走 num_entities 缓存）
        coll.flush()
        return CollectionInfo(
            name=name,
            dimension=vector_field.dim or 0,
            metric=DistanceMetric.COSINE,  # 简化：实际可读索引参数
            row_count=coll.num_entities,
            created_at=datetime.utcnow(),
        )

    # ---------- 写入 ----------
    def _to_milvus_rows(
        self, schema: CollectionSchema, records: list[VectorRecord]
    ) -> list[list[Any]]:
        """将业务记录转成 pymilvus 列式数据。"""
        return [
            [str(r.id) for r in records],
            [r.vector for r in records],
            [r.payload for r in records],
        ]

    def _from_milvus_row(
        self, schema: CollectionSchema, raw: dict[str, Any]
    ) -> VectorRecord:
        return VectorRecord(
            id=raw[schema.primary_field],
            vector=raw[schema.vector_field],
            payload=raw.get("payload") or {},
        )

    async def insert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        if not records:
            return []
        coll = Collection(collection)
        info = await self.get_collection_info(collection)
        rows = self._to_milvus_rows(info, records)
        mut_result = coll.insert(rows)
        coll.flush()
        return [str(r.id) for r in records]

    async def upsert(
        self, collection: str, records: list[VectorRecord]
    ) -> list[str | int]:
        if not records:
            return []
        coll = Collection(collection)
        info = await self.get_collection_info(collection)
        rows = self._to_milvus_rows(info, records)
        coll.upsert(rows)
        coll.flush()
        return [str(r.id) for r in records]

    async def delete(self, collection: str, ids: list[str | int]) -> int:
        if not ids:
            return 0
        coll = Collection(collection)
        expr = f"id in {[str(i) for i in ids]}"
        mut = coll.delete(expr)
        coll.flush()
        return mut.delete_count

    # ---------- 检索 ----------
    async def search(self, request: SearchRequest) -> list[SearchResult]:
        coll = Collection(request.collection)
        coll.load()
        # 过滤条件：业务 dict -> Milvus expr（简化版，仅支持 ==）
        expr = self._build_filter_expr(request.filter_expr)
        output_fields = request.output_fields or ["payload"]
        if "payload" not in output_fields:
            output_fields.append("payload")
        results: MilvusSearchResult = coll.search(
            data=[request.vector],
            anns_field="vector",
            param={"metric_type": "COSINE"},
            limit=request.top_k,
            expr=expr,
            output_fields=output_fields,
        )
        out: list[SearchResult] = []
        for hit in results[0]:
            out.append(
                SearchResult(
                    id=hit.id if isinstance(hit.id, (str, int)) else str(hit.id),
                    score=float(hit.score),
                    payload=dict(hit.entity.get("payload") or {}),
                )
            )
        return out

    @staticmethod
    def _build_filter_expr(filter_expr: dict[str, Any] | None) -> str | None:
        """通用过滤 -> Milvus 表达式（极简版）。

        仅支持 `payload["key"] == value`，用 AND 连接。
        """
        if not filter_expr:
            return None
        parts: list[str] = []
        for k, v in filter_expr.items():
            if isinstance(v, str):
                parts.append(f'payload["{k}"] == "{v}"')
            elif isinstance(v, bool):
                parts.append(f'payload["{k}"] == {str(v).lower()}')
            else:
                parts.append(f'payload["{k}"] == {v}')
        return " and ".join(parts) if parts else None

    async def get(
        self, collection: str, ids: list[str | int]
    ) -> list[VectorRecord]:
        if not ids:
            return []
        coll = Collection(collection)
        expr = f"id in {[str(i) for i in ids]}"
        rows = coll.query(expr=expr, output_fields=["id", "vector", "payload"])
        info = await self.get_collection_info(collection)
        return [self._from_milvus_row(info, r) for r in rows]
```

* [ ] **Step 3：暴露** **`infra`** **入口**

```python
# backends/python/src/study_vector/infra/__init__.py
```

```python
# backends/python/src/study_vector/infra/milvus/__init__.py
from study_vector.infra.milvus.repository import MilvusRepository

__all__ = ["MilvusRepository"]
```

* [ ] **Step 4：提交**

```bash
git add backends/python/src/study_vector/infra
git commit -m "feat(python): Milvus Repository 实现"
```

***

### Task 2.4：Repository 工厂 + 依赖注入

**文件**：

* 创建：

  * `backends/python/src/study_vector/dependencies.py`

* [ ] **Step 1：写** **`dependencies.py`**

```python
"""FastAPI 依赖注入：按配置返回具体 Repository。"""
from functools import lru_cache

from fastapi import Depends

from study_vector.core.settings import Settings, get_settings
from study_vector.infra.milvus import MilvusRepository
from study_vector.repositories.base import VectorRepository


@lru_cache
def _build_repository(backend: str) -> VectorRepository:
    """根据 backend 类型构造 Repository 实例（单例缓存）。"""
    if backend == "milvus":
        return MilvusRepository()
    # 未来扩展：
    # elif backend == "chroma": return ChromaRepository()
    # elif backend == "qdrant": return QdrantRepository()
    raise ValueError(f"不支持的向量库 backend={backend}")


def get_vector_repository(
    settings: Settings = Depends(get_settings),
) -> VectorRepository:
    """FastAPI 依赖：返回当前配置的 Repository。"""
    # 第一阶段：硬编码 milvus；后续通过 settings.vector_backend 选择
    return _build_repository("milvus")
```

* [ ] **Step 2：提交**

```bash
git add backends/python/src/study_vector/dependencies.py
git commit -m "feat(python): Repository 工厂与依赖注入"
```

***

# 阶段 3：业务 API 与异常处理

**目标**：暴露 RESTful API（集合管理 + 向量 CRUD + 检索），统一异常处理，统一响应格式。

### Task 3.1：统一异常与响应

**文件**：

* 创建：

  * `backends/python/src/study_vector/api/exception_handlers.py`

  * `backends/python/src/study_vector/api/responses.py`

  * `backends/python/src/study_vector/exceptions.py`

* [ ] **Step 1：写** **`exceptions.py`**

```python
"""自定义业务异常。"""
class StudyVectorError(Exception):
    """业务基类。"""
    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(self, message: str = "", *, code: str | None = None) -> None:
        super().__init__(message or self.__class__.__doc__ or self.code)
        if code:
            self.code = code


class CollectionNotFoundError(StudyVectorError):
    code = "COLLECTION_NOT_FOUND"
    http_status = 404


class CollectionAlreadyExistsError(StudyVectorError):
    code = "COLLECTION_ALREADY_EXISTS"
    http_status = 409


class VectorDimensionError(StudyVectorError):
    code = "VECTOR_DIMENSION_MISMATCH"
    http_status = 422


class VectorBackendError(StudyVectorError):
    code = "VECTOR_BACKEND_ERROR"
    http_status = 502
```

* [ ] **Step 2：写** **`api/responses.py`**

```python
"""统一响应封装。"""
from typing import Any


def ok(data: Any = None, message: str = "success") -> dict[str, Any]:
    return {"code": 0, "message": message, "data": data}


def fail(code: str, message: str, http_status: int = 400) -> dict[str, Any]:
    return {"code": code, "message": message, "data": None}
```

* [ ] **Step 3：写** **`api/exception_handlers.py`**

```python
"""全局异常处理：转统一响应格式。"""
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from loguru import logger
from pymilvus import MilvusException

from study_vector.exceptions import StudyVectorError


def _error_response(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status,
        content={"code": code, "message": message, "data": None},
    )


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StudyVectorError)
    async def handle_business(request: Request, exc: StudyVectorError):
        logger.warning(f"业务异常 code={exc.code} msg={exc}")
        return _error_response(exc.code, str(exc), exc.http_status)

    @app.exception_handler(MilvusException)
    async def handle_milvus(request: Request, exc: MilvusException):
        logger.exception("Milvus 错误")
        return _error_response("VECTOR_BACKEND_ERROR", str(exc), 502)

    @app.exception_handler(RequestValidationError)
    async def handle_validation(request: Request, exc: RequestValidationError):
        return _error_response(
            "VALIDATION_ERROR", "参数校验失败: " + str(jsonable_encoder(exc.errors())), 422
        )

    @app.exception_handler(Exception)
    async def handle_unkown(request: Request, exc: Exception):
        logger.exception("未捕获异常")
        return _error_response("INTERNAL_ERROR", "服务器内部错误", 500)
```

* [ ] **Step 4：在** **`main.py`** **注册**

修改 `create_app`：

```python
from study_vector.api.exception_handlers import register_exception_handlers

# ...

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(...)
    register_exception_handlers(app)
    app.include_router(health.router, prefix="/api/v1")
    return app
```

* [ ] **Step 5：提交**

```bash
git add backends/python/src/study_vector/exceptions.py backends/python/src/study_vector/api
git commit -m "feat(python): 统一异常处理与响应格式"
```

***

### Task 3.2：集合管理 API

**文件**：

* 创建：

  * `backends/python/src/study_vector/api/v1/collections.py`

* [ ] **Step 1：写路由**

```python
"""集合（Collection）管理 API。"""
from fastapi import APIRouter, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import CollectionInfo, CollectionSchema
from study_vector.exceptions import CollectionNotFoundError
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", summary="创建集合")
async def create_collection(
    schema: CollectionSchema, repo: VectorRepository = Depends(get_vector_repository)
) -> dict:
    await repo.create_collection(schema)
    return ok({"name": schema.name})


@router.get("", summary="列出所有集合")
async def list_collections(
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    names = await repo.list_collections()
    return ok(names)


@router.get("/{name}", summary="查看集合详情", response_model=None)
async def get_collection(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    if not await repo.has_collection(name):
        raise CollectionNotFoundError(f"集合不存在 name={name}")
    info: CollectionInfo = await repo.get_collection_info(name)
    return ok(info.model_dump())


@router.delete("/{name}", summary="删除集合")
async def delete_collection(
    name: str = Path(..., min_length=1),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    await repo.drop_collection(name)
    return ok({"name": name})
```

* [ ] **Step 2：在** **`main.py`** **注册路由**

```python
from study_vector.api.v1 import collections

# 在 create_app 内
app.include_router(collections.router, prefix="/api/v1")
```

* [ ] **Step 3：提交**

```bash
git add backends/python/src/study_vector/api/v1/collections.py
git commit -m "feat(python): 集合管理 API"
```

***

### Task 3.3：向量 CRUD 与检索 API

**文件**：

* 创建：

  * `backends/python/src/study_vector/api/v1/vectors.py`

* [ ] **Step 1：写路由**

```python
"""向量 CRUD 与检索 API。"""
from fastapi import APIRouter, Body, Depends, Path

from study_vector.api.responses import ok
from study_vector.dependencies import get_vector_repository
from study_vector.domain.models import (
    SearchRequest,
    VectorRecord,
)
from study_vector.repositories.base import VectorRepository

router = APIRouter(prefix="/vectors", tags=["vectors"])


@router.post("/{collection}/insert", summary="批量插入")
async def insert_vectors(
    collection: str = Path(..., min_length=1),
    records: list[VectorRecord] = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    ids = await repo.insert(collection, records)
    return ok({"ids": ids, "count": len(ids)})


@router.post("/{collection}/upsert", summary="存在则更新否则插入")
async def upsert_vectors(
    collection: str = Path(..., min_length=1),
    records: list[VectorRecord] = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    ids = await repo.upsert(collection, records)
    return ok({"ids": ids, "count": len(ids)})


@router.post("/{collection}/delete", summary="按 id 删除")
async def delete_vectors(
    collection: str = Path(..., min_length=1),
    ids: list[str] = Body(..., embed=True),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    deleted = await repo.delete(collection, ids)
    return ok({"deleted": deleted})


@router.get("/{collection}/get", summary="按 id 拉取")
async def get_vectors(
    collection: str = Path(..., min_length=1),
    ids: list[str] = Body(..., embed=True),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    records = await repo.get(collection, ids)
    return ok([r.model_dump() for r in records])


@router.post("/{collection}/search", summary="向量检索")
async def search_vectors(
    collection: str = Path(..., min_length=1),
    request: SearchRequest = Body(...),
    repo: VectorRepository = Depends(get_vector_repository),
) -> dict:
    request.collection = collection
    results = await repo.search(request)
    return ok([r.model_dump() for r in results])
```

* [ ] **Step 2：在** **`main.py`** **注册**

```python
from study_vector.api.v1 import vectors

app.include_router(vectors.router, prefix="/api/v1")
```

* [ ] **Step 3：提交**

```bash
git add backends/python/src/study_vector/api/v1/vectors.py
git commit -m "feat(python): 向量 CRUD + 检索 API"
```

***

### Task 3.4：启动时连接 Milvus

**文件**：修改 `backends/python/src/study_vector/main.py`

* [ ] **Step 1：扩展 lifespan**

```python
from study_vector.infra.milvus import MilvusRepository
from study_vector.infra.milvus.client import get_milvus_factory

# 修改 lifespan：
@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    settings = get_settings()
    app.state.settings = settings
    # 启动时建立 Milvus 连接
    factory = get_milvus_factory()
    try:
        factory.connect()
    except Exception:
        logger.exception("启动时连接 Milvus 失败，进入 degraded 模式")
    yield
    factory.close()
```

* [ ] **Step 2：提交**

```bashgit
git commit -m "feat(python): 启动时连接 Milvus"
```

***

### Task 3.5：端到端冒烟测试

**文件**：在 README 中给出手动 curl 示例

* [ ] **Step 1：启动服务**

```bash
cd backends/python
cp config/dev.env .env
uv run uvicorn study_vector.main:app --reload --port 8000
```

* [ ] **Step 2：手动验证**

```bash
# 1. 健康检查
curl http://localhost:8000/api/v1/health
# 期望：{"code":0,"message":"success","data":{"status":"ok"}}

# 2. 创建集合
curl -X POST http://localhost:8000/api/v1/collections \
  -H "Content-Type: application/json" \
  -d '{"name":"demo","dimension":4,"metric":"COSINE","description":"demo collection"}'

# 3. 插入向量
curl -X POST http://localhost:8000/api/v1/vectors/demo/insert \
  -H "Content-Type: application/json" \
  -d '[{"id":"a","vector":[0.1,0.2,0.3,0.4],"payload":{"tag":"x"}},
       {"id":"b","vector":[0.2,0.1,0.4,0.3],"payload":{"tag":"y"}}]'

# 4. 向量检索
curl -X POST http://localhost:8000/api/v1/vectors/demo/search \
  -H "Content-Type: application/json" \
  -d '{"collection":"demo","vector":[0.1,0.2,0.3,0.4],"top_k":5}'

# 5. 删除
curl -X DELETE http://localhost:8000/api/v1/collections/demo
```

***

# 阶段 4：测试

**目标**：核心 Repository 与 API 有可重复执行的单元 / 集成测试。

### Task 4.1：单元测试 - Milvus Repository（mock 客户端）

**文件**：

* 创建：`backends/python/tests/unit/test_milvus_repository.py`、`backends/python/tests/__init__.py`、`backends/python/tests/unit/__init__.py`、`backends/python/pytest.ini`

* [ ] **Step 1：写** **`pytest.ini`**

```ini
[pytest]
asyncio_mode = auto
testpaths = tests
pythonpath = src
```

* [ ] **Step 2：写过滤表达式单元测试**

```python
# tests/unit/test_milvus_repository.py
from study_vector.infra.milvus.repository import MilvusRepository


def test_build_filter_expr_none():
    assert MilvusRepository._build_filter_expr(None) is None
    assert MilvusRepository._build_filter_expr({}) is None


def test_build_filter_expr_string():
    out = MilvusRepository._build_filter_expr({"tag": "x"})
    assert out == 'payload["tag"] == "x"'


def test_build_filter_expr_bool():
    out = MilvusRepository._build_filter_expr({"active": True, "tag": "a"})
    assert 'payload["active"] == true' in out
    assert 'payload["tag"] == "a"' in out
    assert " and " in out
```

* [ ] **Step 3：跑测试**

```bash
cd backends/python
uv run pytest -v
```

期望：3 个用例全部通过。

* [ ] **Step 4：提交**

```bash
git add backends/python/tests
git commit -m "test(python): Milvus Repository 单元测试"
```

***

### Task 4.2：API 集成测试（用 httpx + 内存 backend mock）

**文件**：

* 创建：`backends/python/tests/integration/test_api.py`、`backends/python/tests/integration/__init__.py`

* [ ] **Step 1：写一个内存版 Repository 替身（仅测试用）**

```python
# tests/integration/_fake_repo.py
from study_vector.domain.models import (
    CollectionInfo,
    CollectionSchema,
    SearchRequest,
    SearchResult,
    VectorRecord,
)
from study_vector.repositories.base import VectorRepository


class FakeVectorRepository(VectorRepository):
    def __init__(self) -> None:
        self._cols: dict[str, dict] = {}
        self._recs: dict[str, list[VectorRecord]] = {}

    async def connect(self): pass
    async def close(self): pass
    async def healthcheck(self) -> bool: return True

    async def create_collection(self, schema: CollectionSchema) -> None:
        self._cols[schema.name] = schema.model_dump()
        self._recs.setdefault(schema.name, [])

    async def drop_collection(self, name: str) -> None:
        self._cols.pop(name, None)
        self._recs.pop(name, None)

    async def has_collection(self, name: str) -> bool:
        return name in self._cols

    async def list_collections(self) -> list[str]:
        return list(self._cols.keys())

    async def get_collection_info(self, name: str) -> CollectionInfo:
        s = self._cols[name]
        return CollectionInfo(name=name, dimension=s["dimension"], metric=s["metric"], row_count=len(self._recs[name]))

    async def insert(self, collection, records):
        self._recs[collection].extend(records)
        return [str(r.id) for r in records]

    async def upsert(self, collection, records):
        return await self.insert(collection, records)

    async def delete(self, collection, ids):
        before = len(self._recs[collection])
        self._recs[collection] = [r for r in self._recs[collection] if str(r.id) not in {str(i) for i in ids}]
        return before - len(self._recs[collection])

    async def search(self, request: SearchRequest):
        # 朴素 cosine
        import math
        def cos(a, b):
            dot = sum(x*y for x, y in zip(a, b))
            na = math.sqrt(sum(x*x for x in a))
            nb = math.sqrt(sum(x*x for x in b))
            return dot / (na*nb + 1e-12)
        scored = [(cos(request.vector, r.vector), r) for r in self._recs[request.collection]]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            SearchResult(id=r.id, score=round(s, 6), payload=r.payload)
            for s, r in scored[: request.top_k]
        ]

    async def get(self, collection, ids):
        idset = {str(i) for i in ids}
        return [r for r in self._recs[collection] if str(r.id) in idset]
```

* [ ] **Step 2：写 API 测试（用 FastAPI 依赖覆盖）**

```python
# tests/integration/test_api.py
import pytest
from httpx import ASGITransport, AsyncClient

from study_vector.dependencies import get_vector_repository
from study_vector.main import create_app
from tests.integration._fake_repo import FakeVectorRepository


@pytest.fixture
def fake_repo():
    return FakeVectorRepository()


@pytest.fixture
async def client(fake_repo):
    app = create_app()
    app.dependency_overrides[get_vector_repository] = lambda: fake_repo
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_create_and_search_flow(client):
    r = await client.post("/api/v1/collections", json={"name": "demo", "dimension": 4, "metric": "COSINE"})
    assert r.json()["code"] == 0

    r = await client.post(
        "/api/v1/vectors/demo/insert",
        json=[
            {"id": "a", "vector": [0.1, 0.2, 0.3, 0.4], "payload": {"tag": "x"}},
            {"id": "b", "vector": [0.2, 0.1, 0.4, 0.3], "payload": {"tag": "y"}},
        ],
    )
    assert r.json()["data"]["count"] == 2

    r = await client.post(
        "/api/v1/vectors/demo/search",
        json={"collection": "demo", "vector": [0.1, 0.2, 0.3, 0.4], "top_k": 2},
    )
    body = r.json()
    assert body["code"] == 0
    assert len(body["data"]) == 2
    assert body["data"][0]["id"] == "a"


@pytest.mark.asyncio
async def test_collection_not_found(client):
    r = await client.get("/api/v1/collections/missing")
    assert r.status_code == 404
    assert r.json()["code"] == "COLLECTION_NOT_FOUND"
```

* [ ] **Step 3：跑测试**

```bash
cd backends/python
uv run pytest -v
```

期望：单元 + 集成全部通过。

* [ ] **Step 4：提交**

```bash
git add backends/python/tests
git commit -m "test(python): API 集成测试（Fake Repository）"
```

***

# 阶段 5：Docker Compose 部署

**目标**：一条命令拉起整套服务（API + Milvus standalone + 前端占位）。

### Task 5.1：Python 后端 Dockerfile

**文件**：

* 创建：`backends/python/deploy/Dockerfile`、`backends/python/deploy/.dockerignore`

* [ ] **Step 1：写 Dockerfile（多阶段构建）**

```dockerfile
# ---- 构建阶段 ----
FROM python:3.11-slim AS builder

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# 复制依赖文件先行，提高缓存命中率
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 复制源码并打包
COPY src ./src
RUN uv sync --frozen --no-dev

# ---- 运行阶段 ----
FROM python:3.11-slim AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=prod \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# 复制构建产物
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/src ./src
COPY config ./config

EXPOSE 8000

CMD ["uvicorn", "study_vector.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

* [ ] **Step 2：写** **`.dockerignore`**

```
.venv
__pycache__
.pytest_cache
tests
.env
.env.*
*.log
```

* [ ] **Step 3：提交**

```bash
git add backends/python/deploy
git commit -m "build(python): Dockerfile 多阶段构建"
```

***

### Task 5.2：顶层 docker-compose

**文件**：

* 创建：`deploy/docker-compose.yml`、`deploy/.env.example`、`deploy/milvus/standalone.yml`（官方标准文件，按官方文档复制）

* [ ] **Step 1：复制 Milvus 官方 standalone compose**

```bash
mkdir -p deploy/milvus/volumes
curl -L https://github.com/milvus-io/milvus/releases/download/v2.4.10/milvus-standalone-docker-compose.yml -o deploy/milvus/standalone.yml
# 同时按官方文档把 milvus 的 volumes、etcd、minio 配置进来（保持官方默认）
```

> **注意**：用户已自行部署 Milvus，可以注释掉 compose 里的 milvus 服务，改为外部 `MILVUS_HOST` 指向已存在实例；或者保留 compose 内置便于本地起一套。

* [ ] **Step 2：写** **`deploy/docker-compose.yml`**

```yaml
name: study_vector

services:
  milvus:
    # 选 1：内置 Milvus（推荐用于本地研究）
    image: milvusdb/milvus:v2.4.10
    command: ["milvus", "run", "standalone"]
    environment:
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    depends_on: [etcd, minio]
    ports:
      - "19530:19530"
      - "9091:9091"
    volumes:
      - ./milvus/volumes/milvus:/var/lib/milvus

  etcd:
    image: quay.io/coreos/etcd:v3.5.16
    environment:
      ETCD_AUTO_COMPACTION_MODE: revision
      ETCD_AUTO_COMPACTION_RETENTION: "1000"
      ETCD_QUOTA_BACKEND_BYTES: "4294967296"
      ETCD_SNAPSHOT_COUNT: "50000"
    volumes:
      - ./milvus/volumes/etcd:/etcd
    command: etcd -advertise-client-urls=http://etcd:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  minio:
    image: minio/minio:RELEASE.2024-09-13T20-26-02Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    command: minio server /minio_data --console-address ":9001"
    volumes:
      - ./milvus/volumes/minio:/minio_data
    ports:
      - "9001:9001"

  api:
    build:
      context: ../backends/python
      dockerfile: deploy/Dockerfile
    environment:
      APP_ENV: ${APP_ENV:-prod}
      MILVUS_HOST: ${MILVUS_HOST:-milvus}
      MILVUS_PORT: ${MILVUS_PORT:-19530}
      MILVUS_USER: ${MILVUS_USER:-root}
      MILVUS_PASSWORD: ${MILVUS_PASSWORD:-Milvus}
      MILVUS_DB_NAME: ${MILVUS_DB_NAME:-default}
    depends_on:
      - milvus
    ports:
      - "8000:8000"
    env_file:
      - .env

  # 后续阶段：frontend
  # frontend:
  #   build: ../frontend
  #   ports: ["5173:80"]
  #   depends_on: [api]
```

* [ ] **Step 3：写** **`deploy/.env.example`**

```env
APP_ENV=prod
MILVUS_HOST=milvus
MILVUS_PORT=19530
MILVUS_USER=root
MILVUS_PASSWORD=Milvus
MILVUS_DB_NAME=default
```

* [ ] **Step 4：启动验证**

```bash
cd deploy
cp .env.example .env
docker compose up -d
# 验证
curl http://localhost:8000/api/v1/health
docker compose logs -f api
```

* [ ] **Step 5：提交**

```bash
git add deploy
git commit -m "build: 顶层 docker compose 编排（API + Milvus）"
```

***

# 阶段 6：响应式前端

**目标**：在浏览器可视化操作集合 / 向量 / 检索，**与后端语言无关**（只调 OpenAPI）。

### Task 6.1：前端工程脚手架

**文件**：在 `frontend/` 下

* [ ] **Step 1：用 Vite 初始化 Vue 3 + TS**

```bash
cd frontend
npm create vite@latest . -- --template vue-ts
npm install
npm install element-plus @element-plus/icons-vue pinia axios
npm install -D unplugin-auto-import unplugin-vue-components
```

* [ ] **Step 2：配置 Element Plus 按需引入**（修改 `vite.config.ts`）

```ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({ resolvers: [ElementPlusResolver()] }),
    Components({ resolvers: [ElementPlusResolver()] }),
  ],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
```

* [ ] **Step 3：提交**

```bash
git add frontend
git commit -m "feat(frontend): Vite + Vue 3 + Element Plus 脚手架"
```

***

### Task 6.2：API 客户端与后端切换机制

**文件**：

* 创建：`frontend/src/api/client.ts`、`frontend/src/api/index.ts`、`frontend/src/stores/backend.ts`

* [ ] **Step 1：写** **`stores/backend.ts`（Pinia）**

```ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export type Backend = { name: string; baseUrl: string; language: 'python' | 'go' | 'node' | string }

export const useBackendStore = defineStore('backend', () => {
  // 默认指向本地 Python 后端；用户可切换至其他语言后端
  const backends: Backend[] = [
    { name: 'Python FastAPI (本机)', baseUrl: 'http://localhost:8000', language: 'python' },
    // 未来扩展示例：
    // { name: 'Go Gin (本机)', baseUrl: 'http://localhost:8001', language: 'go' },
  ]
  const current = ref<Backend>(backends[0])
  const select = (b: Backend) => (current.value = b)
  return { backends, current, select }
})
```

* [ ] **Step 2：写** **`api/client.ts`**

```ts
import axios, { type AxiosInstance } from 'axios'
import { useBackendStore } from '@/stores/backend'

export function createClient(): AxiosInstance {
  const inst = axios.create({ baseURL: useBackendStore().current.baseUrl, timeout: 30000 })
  inst.interceptors.response.use(
    (r) => r.data,
    (err) => {
      const body = err.response?.data
      return Promise.reject({ message: body?.message || err.message, code: body?.code || 'ERR' })
    }
  )
  return inst
}
```

* [ ] **Step 3：写** **`api/index.ts`（按域聚合）**

```ts
import { createClient } from './client'

const c = createClient()

export const collectionsApi = {
  list: () => c.get<any, { code: number; data: string[] }>('/api/v1/collections'),
  create: (body: any) => c.post('/api/v1/collections', body),
  info: (name: string) => c.get(`/api/v1/collections/${name}`),
  remove: (name: string) => c.delete(`/api/v1/collections/${name}`),
}

export const vectorsApi = {
  insert: (collection: string, records: any[]) =>
    c.post(`/api/v1/vectors/${collection}/insert`, records),
  upsert: (collection: string, records: any[]) =>
    c.post(`/api/v1/vectors/${collection}/upsert`, records),
  delete: (collection: string, ids: string[]) =>
    c.post(`/api/v1/vectors/${collection}/delete`, { ids }),
  get: (collection: string, ids: string[]) =>
    c.post(`/api/v1/vectors/${collection}/get`, { ids }),
  search: (collection: string, body: any) =>
    c.post(`/api/v1/vectors/${collection}/search`, body),
}
```

* [ ] **Step 4：提交**

```bash
git add frontend/src
git commit -m "feat(frontend): API 客户端 + 多后端切换"
```

***

### Task 6.3：核心页面

**文件**：

* 创建：

  * `frontend/src/views/Dashboard.vue`（集合列表 + 概览）

  * `frontend/src/views/CollectionDetail.vue`（向量 CRUD + 检索）

  * `frontend/src/components/Layout.vue`（顶栏 + 后端切换）

* [ ] **Step 1：写** **`Layout.vue`（响应式 + 移动端汉堡菜单）**

```vue
<script setup lang="ts">
import { useBackendStore } from '@/stores/backend'
import { ref } from 'vue'
const drawer = ref(false)
const backend = useBackendStore()
</script>

<template>
  <el-container>
    <el-header style="display:flex; align-items:center; gap:12px">
      <el-button text @click="drawer = true" :icon="'Menu'" class="mobile-only" />
      <span style="font-weight:600">study_vector</span>
      <el-select v-model="backend.current" value-key="baseUrl" size="small" style="margin-left:auto; min-width:220px">
        <el-option v-for="b in backend.backends" :key="b.baseUrl" :label="`${b.name}`" :value="b" />
      </el-select>
    </el-header>
    <el-drawer v-model="drawer" direction="ltr" size="60%">
      <slot name="nav" />
    </el-drawer>
    <el-container>
      <el-aside width="200px" class="desktop-only">
        <slot name="nav" />
      </el-aside>
      <el-main>
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.mobile-only { display: none; }
@media (max-width: 768px) {
  .desktop-only { display: none; }
  .mobile-only { display: inline-flex; }
}
</style>
```

* [ ] **Step 2：写** **`Dashboard.vue`**

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { collectionsApi } from '@/api'
import { useRouter } from 'vue-router'
const names = ref<string[]>([])
const form = ref({ name: '', dimension: 384, metric: 'COSINE' })
const router = useRouter()
const load = async () => { names.value = (await collectionsApi.list()).data }
const create = async () => {
  await collectionsApi.create(form.value)
  await load()
}
onMounted(load)
</script>

<template>
  <el-card>
    <template #header>创建集合</template>
    <el-form inline :model="form" @submit.prevent>
      <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
      <el-form-item label="维度"><el-input-number v-model="form.dimension" :min="1" :max="65536" /></el-form-item>
      <el-form-item label="度量">
        <el-select v-model="form.metric">
          <el-option label="COSINE" value="COSINE" />
          <el-option label="L2" value="L2" />
          <el-option label="IP" value="IP" />
        </el-select>
      </el-form-item>
      <el-button type="primary" @click="create">创建</el-button>
    </el-form>
  </el-card>
  <el-card style="margin-top:16px">
    <template #header>集合列表</template>
    <el-table :data="names" stripe>
      <el-table-column prop="" label="名称" />
      <el-table-column label="操作">
        <template #default="{ row }">
          <el-button size="small" @click="router.push(`/collections/${row}`)">进入</el-button>
          <el-popconfirm title="确认删除？" @confirm="async () => { await collectionsApi.remove(row); await load() }">
            <template #reference><el-button size="small" type="danger">删除</el-button></template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
```

* [ ] **Step 3：写** **`CollectionDetail.vue`（含检索）**

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { collectionsApi, vectorsApi } from '@/api'
const route = useRoute()
const name = String(route.params.name)
const info = ref<any>({})
const rec = ref({ id: '', vector: '0.1,0.2,0.3,0.4', payload: '{"tag":"x"}' })
const query = ref({ vector: '0.1,0.2,0.3,0.4', top_k: 5 })
const results = ref<any[]>([])
const load = async () => { info.value = (await collectionsApi.info(name)).data }
const insertOne = async () => {
  const records = [{
    id: rec.value.id || crypto.randomUUID(),
    vector: rec.value.vector.split(',').map(Number),
    payload: JSON.parse(rec.value.payload || '{}'),
  }]
  await vectorsApi.insert(name, records)
  await load()
}
const doSearch = async () => {
  const r = await vectorsApi.search(name, {
    collection: name,
    vector: query.value.vector.split(',').map(Number),
    top_k: query.value.top_k,
  })
  results.value = r.data
}
onMounted(load)
</script>

<template>
  <el-card>
    <template #header>集合：{{ name }} （dim={{ info.dimension }}, rows={{ info.row_count }}）</template>
  </el-card>

  <el-card style="margin-top:16px">
    <template #header>插入 / 检索</template>
    <el-form label-width="80px">
      <el-form-item label="id"><el-input v-model="rec.id" placeholder="留空自动生成" /></el-form-item>
      <el-form-item label="vector"><el-input v-model="rec.vector" /></el-form-item>
      <el-form-item label="payload"><el-input v-model="rec.payload" /></el-form-item>
      <el-button type="primary" @click="insertOne">插入</el-button>
    </el-form>
    <el-divider />
    <el-form label-width="80px">
      <el-form-item label="query"><el-input v-model="query.vector" /></el-form-item>
      <el-form-item label="top_k"><el-input-number v-model="query.top_k" :min="1" :max="100" /></el-form-item>
      <el-button type="success" @click="doSearch">检索</el-button>
    </el-form>
    <el-table :data="results" style="margin-top:12px">
      <el-table-column prop="id" label="id" />
      <el-table-column prop="score" label="score" />
      <el-table-column label="payload">
        <template #default="{ row }">
          <code>{{ JSON.stringify(row.payload) }}</code>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
</template>
```

* [ ] **Step 4：路由**

`frontend/src/router/index.ts`：

```ts
import { createRouter, createWebHistory } from 'vue-router'
const routes = [
  { path: '/', component: () => import('@/views/Dashboard.vue') },
  { path: '/collections/:name', component: () => import('@/views/CollectionDetail.vue') },
]
export default createRouter({ history: createWebHistory(), routes })
```

`frontend/src/main.ts` 注入 router、pinia、Element Plus。

* [ ] **Step 5：提交**

```bash
git add frontend
git commit -m "feat(frontend): 集合 / 向量 / 检索页面"
```

***

### Task 6.4：前端 Docker 化

**文件**：

* 创建：`frontend/Dockerfile`、`frontend/nginx.conf`

* [ ] **Step 1：写 Dockerfile（多阶段：node build → nginx）**

```dockerfile
# ---- 构建 ----
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- 运行 ----
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

* [ ] **Step 2：写 nginx.conf（API 反代 + SPA）**

```nginx
server {
  listen 80;
  server_name _;
  root /usr/share/nginx/html;
  index index.html;

  # 后端 API 反代
  location /api/ {
    proxy_pass http://api:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
  }

  # SPA 路由回退
  location / {
    try_files $uri $uri/ /index.html;
  }
}
```

* [ ] **Step 3：把 frontend 加入** **`deploy/docker-compose.yml`**

```yaml
  frontend:
    build:
      context: ../frontend
    depends_on: [api]
    ports:
      - "5173:80"
```

* [ ] **Step 4：提交**

```bash
git add frontend/Dockerfile frontend/nginx.conf deploy/docker-compose.yml
git commit -m "build(frontend): nginx 容器 + 反代 API"
```

***

# 阶段 7：文档

**目标**：让任何贡献者 5 分钟内能跑起来、明白架构、扩展新向量库 / 新语言。

### Task 7.1：文档结构

**文件**：

* 创建：

  * `README.md`（更新）

  * `docs/quickstart.md`

  * `docs/architecture/overview.md`

  * `docs/architecture/repository-pattern.md`

  * `docs/architecture/multi-backend.md`

  * `docs/compare/milvus.md`（后续：chroma.md、qdrant.md…）

* [ ] **Step 1：写** **`docs/quickstart.md`**

```markdown
# 快速开始

## 1. 准备
- 安装 Docker / Docker Compose
- 确认 8000 / 19530 / 9001 端口空闲

## 2. 启动
cd deploy
cp .env.example .env
docker compose up -d

## 3. 验证
- API 文档： http://localhost:8000/docs
- 前端： http://localhost:5173
- Milvus 控制台： http://localhost:9001 （minioadmin / minioadmin）

## 4. 仅 Python 后端（开发态）
cd backends/python
cp config/dev.env .env
uv sync
uv run uvicorn study_vector.main:app --reload
```

* [ ] **Step 2：写** **`docs/architecture/overview.md`**（中文图 + 说明）

内容大纲：

* 系统组成图

* 进程间关系

* 数据流（前端 → API → Repository → Milvus）

* 扩展点（新增语言 / 新增向量库）

* [ ] **Step 3：写** **`docs/architecture/repository-pattern.md`**

内容大纲：

* 业务为什么只依赖 `VectorRepository` 协议

* 如何新增一个向量库实现（以 Chroma 为例的伪代码 + 步骤清单）

* 切换 backend 的方式（settings / 环境变量）

* [ ] **Step 4：写** **`docs/architecture/multi-backend.md`**

内容大纲：

* 前端为何与后端语言解耦（OpenAPI / 统一 JSON 协议）

* 顶层 `deploy/docker-compose.yml` 同时编排 python / go / node

* 如何让前端选择不同后端

* [ ] **Step 5：提交**

```bash
git add docs
git commit -m "docs: 项目文档（快速开始 + 架构）"
```

***

# 阶段 8（可选/未来）：多语言 & 多向量库扩展

> 本阶段**不阻塞**首期交付；给出蓝图即可。

### Task 8.1：扩展新向量库（以 Chroma 为例）

* [ ] 新建 `backends/python/src/study_vector/infra/chroma/repository.py` 实现 `VectorRepository`。

* [ ] 在 `dependencies.py` 注册：`elif backend == "chroma": return ChromaRepository()`。

* [ ] 在 settings 增加 `vector_backend: Literal["milvus","chroma",...]`。

* [ ] 增加 `tests/unit/test_chroma_repository.py`。

* [ ] 在 `docs/compare/milvus.md` 之外新增 `chroma.md` 对比报告。

### Task 8.2：扩展新语言（以 Go 为例）

* [ ] 在 `backends/go/` 初始化 go module，复用相同 OpenAPI 契约。

* [ ] 端口不同（如 8001），在 `frontend/stores/backend.ts` 中加入。

* [ ] `deploy/docker-compose.yml` 增加 `go-api` 服务。

* [ ] `docs/architecture/multi-backend.md` 增加 Go 章节。

***

# 风险与回滚

| 风险                             | 缓解                                                |
| ------------------------------ | ------------------------------------------------- |
| Milvus 版本差异导致 API 不兼容          | 锁定 `v2.4.10`，CI 中用 testcontainers 拉同一版本           |
| pymilvus 同步 API 与 FastAPI 异步冲突 | 阶段 2 中用 `run_in_executor` 包装（已在 2.3 提示）           |
| 前端大对象渲染性能                      | 检索结果分页 / 虚拟滚动（Element Plus el-table-v2）           |
| 多语言后端 schema 不一致               | 以 OpenAPI 为单一事实源，前端通过 `openapi-typescript` 自动生成类型 |

***

# 验收清单（首期）

* [ ] `docker compose up -d` 一键起 API + Milvus + 前端

* [ ] `http://localhost:8000/docs` 可用，列出全部接口

* [ ] `http://localhost:5173` 可创建集合、插入向量、检索

* [ ] `uv run pytest` 全部通过

* [ ] `ruff check` / `mypy` 无 error

* [ ] 切换后端（手动改 `MILVUS_HOST`）后仍能工作

* [ ] 文档：`quickstart.md` + `architecture/overview.md` + `repository-pattern.md` 可读

