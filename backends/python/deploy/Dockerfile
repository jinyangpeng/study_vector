# ---- 构建阶段 ----
# 使用 python:3.11-slim 作为基础镜像，体量小、Debian 系
FROM python:3.11-slim AS builder

# uv 通过官方镜像复制（避免 pip install uv 反复下载）
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app

# 系统依赖：build-essential 仅在 builder 阶段需要，runtime 阶段不打包
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 先复制 lockfile 利用 Docker 缓存
COPY pyproject.toml uv.lock README.md ./

# 安装依赖到独立目录（不创建项目 venv）
RUN uv sync --frozen --no-dev --no-install-project

# 复制源码
COPY src ./src

# 安装项目本身
RUN uv sync --frozen --no-dev

# ---- 运行阶段 ----
FROM python:3.11-slim AS runtime

# 容器内环境变量
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=prod \
    PATH="/app/.venv/bin:$PATH" \
    # 容器内推荐用 TZ=Asia/Shanghai，但保留 UTC 也可
    TZ=UTC

WORKDIR /app

# 仅复制必要的运行时产物：虚拟环境 + 源码 + 多环境配置
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/src ./src
COPY config ./config

EXPOSE 8000

# 健康检查：使用 uvicorn 自带的 /api/v1/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health', timeout=3).read()" \
    || exit 1

# 启动命令：2 worker 应对一般小规模流量
CMD ["uvicorn", "study_vector.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
