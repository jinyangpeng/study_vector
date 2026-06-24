# Milvus 对比笔记

> 第一阶段默认向量库。后续会在 `docs/compare/` 增加 chroma.md / qdrant.md / weaviate.md / pgvector.md。

## 1. 基础信息

| 项                    | 值                                                       |
| --------------------- | -------------------------------------------------------- |
| 官方地址              | <https://milvus.io>                                      |
| 当前使用版本          | `milvusdb/milvus:v2.4.10`                                |
| 协议                  | gRPC :19530 / HTTP :9091                                 |
| 存储                  | 依赖 etcd（元数据）+ MinIO/S3（向量与索引）              |
| 部署模式              | Standalone / Cluster                                     |
| License               | Apache-2.0                                               |

## 2. 关键特性

- **亿级向量检索**：HNSW / IVF / DiskANN 多索引；GPU 索引（CAGRA）。
- **混合检索**：向量 + 标量过滤（`expr` 语法）。
- **多租户**：Database / Collection / Partition / Resource Group。
- **动态字段**：JSON 字段可放任意 payload，业务友好。
- **生态**：Attu（Web UI）、Birdwatcher（运维）、milvus-backup。

## 3. 与本项目的适配

| 维度           | 适配情况                                                                         |
| -------------- | -------------------------------------------------------------------------------- |
| 主键           | VARCHAR(128)，业务 `id` 统一 `str(uuid4())`                                      |
| 向量           | FLOAT_VECTOR，dim 由 `CollectionSchema.dimension` 决定                            |
| 负载           | JSON 字段 `payload`，业务 dict 直接写入                                          |
| 索引           | 默认 `AUTOINDEX`（Milvus 自适应选 HNSW/IVF）                                    |
| 距离度量       | COSINE / L2 / IP 完整支持                                                        |
| 过滤表达式     | 业务 `dict` → Milvus `expr`（当前实现支持 `==`，可扩展 `>` / `<` / `in`）        |
| 异步接口       | pymilvus 是同步；用 `asyncio.to_thread` 包装到 FastAPI 异步生态                  |

## 4. 踩过的坑

1. **开发态 API 跑容器时用容器名**：容器内 `localhost` = 自己，`127.0.0.1` = 宿主不可达。
   **解决**：API 容器与 Milvus 同 `study_vector_study_vector_net` 网络，用容器名 `milvus-standalone`。
   **而宿主上跑 API（开发态推荐）时**，直接 `MILVUS_HOST=localhost:19530` 即可，Windows Docker Desktop 上 `127.0.0.1` 端口映射也通。

2. **`Test-NetConnection` 假阴性**：PowerShell 的这个 cmdlet 在部分环境会返回 `False` 即便 TCP 实际可达。
   **验证应该用**：`Invoke-WebRequest http://127.0.0.1:9091/`（应 404）或 `python -c "import socket; s=socket.socket(); s.connect(('127.0.0.1',19530))"`。

3. **行数缓存**：`coll.num_entities` 在删除后不立即更新。
   **影响**：详情页 `row_count` 短暂失真。生产可定期 `flush()` 或读真实 segment 统计。

4. **gRPC 重试风暴**：`[list_collections] Retry run out of 75 retry times` 暴露出 SDK 默认 75 次重试。
   **缓解**：连接失败时 `MilvusClientFactory` 标记 `_connected=False`，不缓存错误连接。

5. **索引未加载就搜索**：刚 insert 后立刻 search 可能命中空集合。
   **缓解**：`create_collection` 末尾 `coll.load()`；前端插入后等待 1-2s 再搜。

6. **端口冲突**：Milvus standalone 自带 etcd:2379 / minio:9000 / milvus:9091。
   **缓解**：compose 编排时统一映射为 2379/9001/9091/19530；如与现有服务冲突，改 `ports`。

## 5. 性能粗略观察（仅参考）

> 测试环境：Milvus 2.4.10 standalone，4C8G 容器，dim=384，10w 条向量。

| 操作                | 延迟         |
| ------------------- | ------------ |
| create_collection   | 1-2 s        |
| insert (100 条)     | 50-150 ms    |
| insert (1w 条)      | 3-6 s        |
| search top_k=10     | 10-30 ms     |
| get by id (10)      | 5-15 ms      |
| delete by id (10)   | 20-50 ms     |

> 实际数据因硬件 / 数据分布 / 索引参数差异较大；后续会做正式 benchmark。

## 6. 切换 / 替换计划

未来如果切到 Chroma / Qdrant：
- `repositories/base.py` 不变
- 新增 `infra/chroma/repository.py`
- `dependencies.py` 改一行
- 业务层、前端、API 路由全部不动
