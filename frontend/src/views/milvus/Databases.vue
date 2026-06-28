<script setup lang="ts">
// Milvus 数据库管理（教学版）
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { databasesApi, trackedCall, type ApiCall } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { databaseDocs } from '@/lib/fieldDocs'

const dbs = ref<string[]>([])
const newName = ref('tenant_a')
const calls = ref<ApiCall[]>([])
const creating = ref(false)
const loadingList = ref(false)

async function load() {
  loadingList.value = true
  try {
    const { data, call } = await trackedCall('GET', '/api/v1/databases')
    calls.value = [call]
    if (data.code === 0) dbs.value = data.data
    else ElMessage.error(data.message)
  } finally {
    loadingList.value = false
  }
}

async function create() {
  if (!newName.value) {
    ElMessage.warning('请输入数据库名')
    return
  }
  creating.value = true
  const { data, call } = await trackedCall('POST', '/api/v1/databases', {
    name: newName.value,
  })
  calls.value = [call]
  creating.value = false
  if (data.code === 0) {
    ElMessage.success(`已创建数据库 ${newName.value}`)
    newName.value = ''
    await load()
  } else {
    ElMessage.error(data.message)
  }
}

async function drop(name: string) {
  try {
    await ElMessageBox.confirm(
      `确认删除数据库 "${name}" 吗？该 DB 下所有集合会被一起删。`,
      '警告',
      { type: 'warning' },
    )
  } catch {
    return
  }
  const { data, call } = await trackedCall('DELETE', `/api/v1/databases/${name}`)
  calls.value = [call]
  if (data.code === 0) {
    ElMessage.success(`已删除 ${name}`)
    await load()
  } else {
    ElMessage.error(data.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>数据库（Databases）</h2>
      <p class="desc">
        Milvus 默认有 <code>default</code> 数据库。多租户场景下，每个租户可建独立 DB，<b>物理隔离</b>集合。
      </p>
    </header>

    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <el-card>
          <template #header><span>➕ 创建数据库</span></template>
          <el-form label-width="80px">
            <el-form-item label="name">
              <el-input v-model="newName" placeholder="如 tenant_a" />
              <ParamHelp :doc="databaseDocs.name" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="creating" @click="create">
                创建
              </el-button>
            </el-form-item>
          </el-form>
          <ApiResponseViewer :calls="calls" />
        </el-card>
      </el-col>

      <el-col :xs="24" :md="14">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📋 数据库列表</span>
              <el-button text @click="load">刷新</el-button>
            </div>
          </template>
          <div v-loading="loadingList" class="db-list">
            <div
              v-for="db in dbs"
              :key="db"
              class="db-item"
              :class="{ 'is-default': db === 'default' }"
            >
              <el-tag :type="db === 'default' ? 'warning' : 'info'" size="large">
                {{ db }}
              </el-tag>
              <el-button
                size="small"
                type="danger"
                :disabled="db === 'default'"
                @click="drop(db)"
              >
                删除
              </el-button>
            </div>
            <div v-if="!dbs.length" class="empty-tip">无数据库</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <TutorialPanel slug="08-databases" />
  </div>
</template>

<style scoped>
.page-inner { padding: 0; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 22px; }
.page-header .desc { margin: 0; color: #606266; font-size: 13px; }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
.db-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 0;
  min-height: 60px;
}
.db-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
}
.empty-tip {
  color: #909399;
  font-size: 13px;
  padding: 8px;
}
</style>
