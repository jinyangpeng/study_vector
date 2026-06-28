# syntax=docker/dockerfile:1.7
# ============================================================================
# study_vector — 前端镜像
# 多阶段：node 构建 → nginx 静态服务 + API 反代
#
# 构建上下文：项目根目录（docker-compose.yml 中 context: ..）
#   docker build -f docker/frontend/Dockerfile ..
# ============================================================================

ARG NODE_VERSION=20-alpine
ARG NGINX_VERSION=1.27-alpine

# ───────────────────────── builder ─────────────────────────
FROM node:${NODE_VERSION} AS builder
WORKDIR /app

# 先复制依赖清单（先于源码，最大化缓存）
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci || npm install

# 复制源码并构建
COPY frontend/ ./
RUN npm run build

# ───────────────────────── runtime ─────────────────────────
FROM nginx:${NGINX_VERSION} AS runtime

# nginx 镜像自带 nginx 用户（UID 101），无需新建
COPY --from=builder /app/dist /usr/share/nginx/html
COPY docker/frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
