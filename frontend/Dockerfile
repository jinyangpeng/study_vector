# 构建阶段
FROM node:20-alpine AS builder
WORKDIR /app

# 复制依赖清单（先于源码，最大化缓存）
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# 复制源码并构建
COPY . .
RUN npm run build

# 运行阶段：用 nginx 提供静态文件 + 反向代理 /api/*
FROM nginx:1.27-alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
  CMD wget -q --spider http://localhost/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
