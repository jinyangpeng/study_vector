# syntax=docker/dockerfile:1.7
# ============================================================================
# study_vector — Python API 镜像
# 多阶段构建：builder（编译依赖）→ runtime（最小运行时，非 root）
#
# 构建上下文：项目根目录（docker-compose.yml 中 context: ..）
#   docker build -f docker/api/Dockerfile ..
# ============================================================================

# 全局 ARG：必须在首个 FROM 之前声明，才能在 FROM 中插值
ARG PYTHON_VERSION=3.11-slim
ARG UV_VERSION=0.5.4

# ───────────────────────── uv 工具 stage ─────────────────────────
# 注意：Docker 不支持在 `COPY --from=<image>:${VAR}` 里用 ARG 插值，
# 但支持在 `FROM <image>:${VAR}` 里插值。故先把 uv 抽成命名 stage，
# 再在 builder 中用 `COPY --from=uv`（引用 stage 名，不带变量）。
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# ───────────────────────── builder ─────────────────────────
FROM python:${PYTHON_VERSION} AS builder

# 从 uv stage 复制 uv / uvx 二进制
COPY --from=uv /uv /uvx /usr/local/bin/

WORKDIR /app

# 系统依赖：build-essential 仅 builder 阶段需要，runtime 不打包
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖清单，最大化层缓存命中
COPY backends/python/pyproject.toml backends/python/uv.lock backends/python/README.md ./

# 安装依赖到独立 venv（不安装项目本身）
RUN uv sync --frozen --no-dev --no-install-project

# 复制源码并安装项目
COPY backends/python/src ./src
RUN uv sync --frozen --no-dev

# ───────────────────────── runtime ─────────────────────────
FROM python:${PYTHON_VERSION} AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_ENV=prod \
    PATH="/app/.venv/bin:$PATH" \
    TZ=UTC

# 最小运行时依赖 + 非 root 用户（安全最佳实践）
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates tini \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system --gid 1001 app \
    && useradd  --system --uid 1001 --gid app --home-dir /app --shell /usr/sbin/nologin app

WORKDIR /app

# 仅复制运行时产物：venv + 源码 + 多环境配置
COPY --from=builder --chown=app:app /app/.venv ./.venv
COPY --from=builder --chown=app:app /app/src ./src
COPY --chown=app:app backends/python/config ./config

USER app

EXPOSE 8000

# 健康检查：FastAPI /api/v1/health
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/v1/health || exit 1

# tini 作为 PID 1 正确处理信号
ENTRYPOINT ["/usr/bin/tini", "--"]
CMD ["uvicorn", "study_vector.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
