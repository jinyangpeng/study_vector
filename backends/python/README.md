# study-vector / Python 后端

FastAPI + pymilvus，向量数据库研究平台的首个后端实现。

## 目录结构

```
src/study_vector/
├── api/v1/             # FastAPI 路由（按版本分目录）
├── core/               # 配置、日志、启动/关闭钩子
├── domain/             # 领域模型（与具体向量库解耦）
├── infra/              # 基础设施层（向量库 SDK 封装）
│   └── milvus/         # Milvus 特定实现
└── repositories/       # Repository 协议（业务层接口）
```

## 开发

```bash
# 安装依赖（需先安装 uv： https://docs.astral.sh/uv/）
cd backends/python
uv sync
cp config/dev.env .env

# 启动
uv run uvicorn study_vector.main:app --reload --port 8000

# 测试
uv run pytest

# 代码检查
uv run ruff check
uv run mypy src
```

## 配置

通过 `APP_ENV` 切换环境：

| 环境 | 配置文件 | 用途 |
| --- | --- | --- |
| dev | `config/dev.env` | 本地开发，默认 `DEBUG=true` |
| test | `config/test.env` | 测试环境，JSON 日志 |
| prod | `config/prod.env` | 生产环境 |

## 端口

- API：`8000`（可在 `HOST` / `PORT` 环境变量中修改）
- 依赖 Milvus：默认 `localhost:19530`（可通过 `MILVUS_HOST` / `MILVUS_PORT` 覆盖）
