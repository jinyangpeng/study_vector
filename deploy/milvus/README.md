# deploy/milvus

Milvus standalone 容器使用的本地数据卷。

| 子目录 | 用途 |
| --- | --- |
| `volumes/etcd` | etcd 元数据 |
| `volumes/minio` | MinIO 对象存储 |
| `volumes/milvus` | Milvus 索引与日志 |

> **注意**：本目录挂载的卷数据**不进 Git**。`volumes/` 已在仓库根 `.gitignore` 中。
> 部署前请确保 `volumes/` 有写权限。
