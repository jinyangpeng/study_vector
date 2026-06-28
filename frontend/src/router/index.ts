// Vue Router 配置：一级 = 向量库，二级 = 功能
// V1 只做 Milvus；未来扩展 Qdrant/Weaviate 时复用同一套 UI 组件
import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // 默认跳到 Milvus 集合页
  { path: '/', redirect: '/milvus/collections' },

  // ─────────── Milvus（一级：向量库）───────────
  {
    path: '/milvus',
    component: () => import('@/views/milvus/MilvusLayout.vue'),
    children: [
      // 集合（CRUD）
      { path: '', redirect: '/milvus/collections' },
      {
        path: 'collections',
        name: 'milvus-collections',
        component: () => import('@/views/milvus/Collections.vue'),
      },
      {
        path: 'collections/:name',
        name: 'milvus-collection-detail',
        component: () => import('@/views/milvus/CollectionDetail.vue'),
        props: true,
      },
      // 向量（CRUD）
      {
        path: 'vectors',
        name: 'milvus-vectors',
        component: () => import('@/views/milvus/Vectors.vue'),
      },
      // 索引
      {
        path: 'indexes',
        name: 'milvus-indexes',
        component: () => import('@/views/milvus/Indexes.vue'),
      },
      // 检索（含混合检索）
      {
        path: 'search',
        name: 'milvus-search',
        component: () => import('@/views/milvus/Search.vue'),
      },
      // 分区
      {
        path: 'partitions',
        name: 'milvus-partitions',
        component: () => import('@/views/milvus/Partitions.vue'),
      },
      // Alias
      {
        path: 'aliases',
        name: 'milvus-aliases',
        component: () => import('@/views/milvus/Aliases.vue'),
      },
      // 数据库
      {
        path: 'databases',
        name: 'milvus-databases',
        component: () => import('@/views/milvus/Databases.vue'),
      },
      // 用户
      {
        path: 'users',
        name: 'milvus-users',
        component: () => import('@/views/milvus/Users.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
