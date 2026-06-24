# Repository 模式与多向量库扩展

> 业务层只依赖 `VectorRepository` 协议；切换 / 扩展向量库不改业务代码。

## 1. 为什么需要 Repository 模式

向量库的 SDK 各不相同：
- **Milvus**：必须先建 `Collection` + 索引；用 `expr` 过滤；`JSON` 字段存 payload。
- **Chroma**：自动建 collection；用 `where={"k":"v"}` 过滤；payload 用 metadata。
- **Qdrant**：必须先建 collection + payload index；用 `Filter`（must/should）；payload 是一级字段。
- **Weaviate**：类 + 属性 + 引用；GraphQL / REST；payload 是属性集合。
- **pgvector**：标准 SQL 表 + `vector` 列 + ivfflat / hnsw 索引；payload 是普通列。

如果业务层直接调 pymilvus，就锁死了 Milvus，以后想对比 Chroma 就要重写业务代码。

## 2. 协议（`VectorRepository`）

`backends/python/src/study_vector/repositories/base.py`：

```python
@runtime_checkable
class VectorRepository(Protocol):
    # ----- 生命周期 -----
    async def connect(self) -> None: ...
    async def close(self) -> None: ...
    async def healthcheck(self) -> bool: ...

    # ----- 集合 -----
    async def create_collection(self, schema: CollectionSchema) -> None: ...
    async def drop_collection(self, name: str) -> None: ...
    async def has_collection(self, name: str) -> bool: ...
    async def list_collections(self) -> list[str]: ...
    async def get_collection_info(self, name: str) -> CollectionInfo: ...

    # ----- 写入 -----
    async def insert(self, collection, records) -> list[id]: ...
    async def upsert(self, collection, records) -> list[id]: ...
    async def delete(self, collection, ids) -> int: ...

    # ----- 检索 -----
    async def search(self, request: SearchRequest) -> list[SearchResult]: ...
    async def get(self, collection, ids) -> list[VectorRecord]: ...
```

要点：
- **全部 async**：与 FastAPI 异步生态一致；同步 SDK 在实现层用 `asyncio.to_thread` 包装。
- **统一业务 DTO**：`CollectionSchema / VectorRecord / SearchRequest / SearchResult` 是与 SDK 无关的。
- **`runtime_checkable`**：允许 `isinstance(obj, VectorRepository)` 运行时检查。

## 3. 领域模型（`domain/models.py`）

| 模型                | 作用                                            |
| ------------------- | ----------------------------------------------- |
| `CollectionSchema`  | 集合元信息（name / dim / metric / index_type） |
| `VectorRecord`      | 单条向量（id / vector / payload）               |
| `SearchRequest`     | 检索请求（vector / top_k / filter_expr）        |
| `SearchResult`      | 检索命中（id / score / payload）                |
| `CollectionInfo`    | 集合运行时信息（row_count 等）                  |
| `DistanceMetric`    | 度量枚举（COSINE / L2 / IP / HAMMING / JACCARD）|
| `IndexType`         | 索引枚举（FLAT / IVF_* / HNSW / AUTOINDEX）     |

`SearchRequest.filter_expr` 是个 `dict`，例如：

```json
{ "tag": "x", "active": true, "count": 3 }
```

实现层负责把 `dict` 翻译成原生表达式（Milvus `expr` / Chroma `where` / Qdrant `Filter` / pgvector SQL）。

## 4. 工厂 + 依赖注入

`dependencies.py`：

```python
_BUILDERS: dict[str, callable] = {
    "milvus": lambda: MilvusRepository(),
    # "chroma": lambda: ChromaRepository(),
    # "qdrant": lambda: QdrantRepository(),
    # "weaviate": lambda: WeaviateRepository(),
    # "pgvector": lambda: PgVectorRepository(),
}

def get_vector_repository(settings: Settings = Depends(get_settings)) -> VectorRepository:
    return _build_repository("milvus")
```

`main.py` 通过 `Depends(get_vector_repository)` 注入到路由；
测试时用 `app.dependency_overrides[get_vector_repository] = lambda: fake_repo` 替换。

## 5. 完整步骤：新增一个向量库（Chroma）

### Step 1：建目录

```bash
mkdir -p backends/python/src/study_vector/infra/chroma
```

### Step 2：写客户端封装

```python
# infra/chroma/client.py
import chromadb

class ChromaClientFactory:
    _instance = None
    def __new__(cls, settings):
        if cls._instance is None:
            cls._instance = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
        return cls._instance
```

### Step 3：实现 Repository

```python
# infra/chroma/repository.py
from study_vector.repositories.base import VectorRepository

class ChromaRepository:
    def __init__(self):
        self._client = get_chroma_factory()

    async def create_collection(self, schema):
        return await asyncio.to_thread(
            self._client.get_or_create_collection,
            name=schema.name, metadata={"dim": schema.dimension}
        )
    # ... 实现其余接口
```

### Step 4：注册

```python
# dependencies.py
from study_vector.infra.chroma import ChromaRepository

_BUILDERS = {
    "milvus": lambda: MilvusRepository(),
    "chroma": lambda: ChromaRepository(),
}
```

### Step 5：补配置 + 测试 + 文档

- `core/settings.py` 加 `chroma_host / chroma_port`
- `tests/unit/test_chroma_repository.py`
- `docs/compare/chroma.md`

**业务代码、API 路由、领域模型、前端全部不需要改。**

## 6. 测试策略

| 测试类型        | 工具                                | 替身                                |
| --------------- | ----------------------------------- | ----------------------------------- |
| 单元测试        | pytest                              | mock `pymilvus.utility / Collection`|
| 集成测试        | pytest + httpx + `app.dependency_overrides` | `FakeVectorRepository`（in-memory） |
| E2E             | Playwright                          | 真实 API + 真实 Milvus（Docker）    |

`tests/integration/_fake_repo.py` 提供 `FakeVectorRepository`：纯 Python 实现 cosine 相似度，足以覆盖 API 业务路径。
