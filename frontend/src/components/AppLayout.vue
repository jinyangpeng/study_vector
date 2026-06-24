<script setup lang="ts">
// 响应式布局：顶栏 + 抽屉式侧栏（移动端）+ 后端切换
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useBackendStore } from '@/stores/backend'

const router = useRouter()
const backend = useBackendStore()
const drawer = ref(false)

const onBackendChange = (b: any) => {
  backend.select(b)
  // 切换后端时回到首页并强制刷新
  router.push('/').then(() => location.reload())
}
</script>

<template>
  <el-container style="height: 100%">
    <!-- 顶栏 -->
    <el-header
      style="
        display: flex;
        align-items: center;
        gap: 12px;
        background: #fff;
        border-bottom: 1px solid #ebeef5;
        padding: 0 16px;
      "
    >
      <el-button
        text
        :icon="'Menu'"
        class="mobile-only"
        @click="drawer = true"
        style="font-size: 20px"
      />
      <span
        style="
          font-weight: 600;
          font-size: 18px;
          background: linear-gradient(120deg, #409eff, #67c23a);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
        "
      >
        study_vector
      </span>
      <span
        style="
          color: #909399;
          font-size: 12px;
          margin-left: 8px;
        "
        class="desktop-only"
      >
        向量数据库研究平台
      </span>

      <div style="margin-left: auto; display: flex; align-items: center; gap: 12px">
        <span style="color: #909399; font-size: 12px">后端：</span>
        <el-select
          :model-value="backend.current"
          value-key="baseUrl"
          size="default"
          style="min-width: 220px"
          @change="onBackendChange"
        >
          <el-option
            v-for="b in backend.backends"
            :key="b.baseUrl"
            :label="`${b.name}`"
            :value="b"
          />
        </el-select>
      </div>
    </el-header>

    <!-- 移动端侧栏抽屉 -->
    <el-drawer v-model="drawer" direction="ltr" size="60%" :with-header="false">
      <div style="padding: 16px">
        <h3>导航</h3>
        <el-menu :default-active="$route.path" router @select="drawer = false">
          <el-menu-item index="/">
            <el-icon><DataLine /></el-icon>
            <span>集合管理</span>
          </el-menu-item>
        </el-menu>
      </div>
    </el-drawer>

    <el-container>
      <!-- 桌面端侧栏 -->
      <el-aside
        width="200px"
        class="desktop-only"
        style="background: #fff; border-right: 1px solid #ebeef5"
      >
        <el-menu :default-active="$route.path" router style="border: none">
          <el-menu-item index="/">
            <el-icon><DataLine /></el-icon>
            <span>集合管理</span>
          </el-menu-item>
        </el-menu>
      </el-aside>

      <el-main>
        <slot />
      </el-main>
    </el-container>
  </el-container>
</template>
