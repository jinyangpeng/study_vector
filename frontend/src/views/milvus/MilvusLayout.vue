<script setup lang="ts">
// Milvus 二级布局：左侧功能菜单 + 右侧主区（教学子路由出口）
import { useRoute } from 'vue-router'
import { computed } from 'vue'

const route = useRoute()

const menus = [
  {
    key: 'lifecycle',
    title: '生命周期',
    items: [
      { path: '/milvus/collections', label: '集合（Collections）', icon: 'DataLine' },
      { path: '/milvus/partitions', label: '分区（Partitions）', icon: 'Grid' },
      { path: '/milvus/aliases', label: '别名（Aliases）', icon: 'Connection' },
    ],
  },
  {
    key: 'data',
    title: '数据',
    items: [
      { path: '/milvus/vectors', label: '向量（Vectors）', icon: 'Coin' },
      { path: '/milvus/indexes', label: '索引（Indexes）', icon: 'Files' },
    ],
  },
  {
    key: 'query',
    title: '检索',
    items: [
      { path: '/milvus/search', label: '检索（Search）', icon: 'Search' },
    ],
  },
  {
    key: 'admin',
    title: '管理',
    items: [
      { path: '/milvus/databases', label: '数据库（Databases）', icon: 'Folder' },
      { path: '/milvus/users', label: '用户（Users）', icon: 'User' },
    ],
  },
]

const isActive = (path: string) => {
  return route.path === path || route.path.startsWith(path + '/')
}
const collectionName = computed(() => {
  if (route.name === 'milvus-collection-detail') {
    return String(route.params.name || '')
  }
  return ''
})
</script>

<template>
  <div class="milvus-layout">
    <!-- 左侧功能菜单 -->
    <aside class="sidebar">
      <div class="brand">
        <span class="logo">🧊</span>
        <span class="name">Milvus</span>
      </div>
      <div v-for="group in menus" :key="group.key" class="menu-group">
        <div class="group-title">{{ group.title }}</div>
        <router-link
          v-for="item in group.items"
          :key="item.path"
          :to="item.path"
          class="menu-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </div>
    </aside>

    <!-- 右侧主区（子路由出口） -->
    <main class="main">
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.milvus-layout {
  display: flex;
  gap: 16px;
}
.sidebar {
  width: 220px;
  flex-shrink: 0;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 16px 0;
  height: fit-content;
  position: sticky;
  top: 16px;
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px 16px;
  border-bottom: 1px solid #ebeef5;
  margin-bottom: 12px;
}
.brand .logo {
  font-size: 22px;
}
.brand .name {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.menu-group {
  margin-bottom: 12px;
}
.group-title {
  padding: 4px 16px;
  color: #909399;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  color: #606266;
  text-decoration: none;
  font-size: 14px;
  border-left: 3px solid transparent;
  transition: all 0.15s;
}
.menu-item:hover {
  background: #f5f7fa;
  color: #409eff;
}
.menu-item.active {
  background: linear-gradient(90deg, #ecf5ff, #fff);
  border-left-color: #409eff;
  color: #409eff;
  font-weight: 600;
}
.menu-item .el-icon {
  font-size: 16px;
}
.main {
  flex: 1;
  min-width: 0;
}
</style>
