# study-vector / 前端

Vue 3 + Vite + TypeScript + Element Plus 响应式前端。

## 技术栈

- Vue 3.5 + Composition API
- Vite 5
- TypeScript 5
- Element Plus 2.8（按需引入）
- Pinia 2（后端切换）
- Vue Router 4

## 本地开发

```bash
cd frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173
# 需先启动后端：http://localhost:8000
```

## 生产构建

```bash
npm run build
# 产物在 dist/
```

## 响应式断点

- 桌面端：> 768px
- 移动端：≤ 768px
  - 顶栏出现汉堡菜单
  - 侧栏变成抽屉

## 后端切换

通过顶栏下拉框切换后端实例，便于对比 Python / Go / Node 等不同实现的响应差异。
切换后会自动回到首页并刷新数据。

## Docker 部署

参见 [`docker/docker-compose.yml`](../docker/docker-compose.yml) 与 [`docker/README.md`](../docker/README.md)。
