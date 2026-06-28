<script setup lang="ts">
// Milvus 分区管理（教学版）
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { collectionsApi, partitionsApi, trackedCall, type ApiCall } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { partitionDocs } from '@/lib/fieldDocs'

const collections = ref<string[]>([])
const collection = ref('')
const partitions = ref<string[]>([])
const newName = ref('y2024')
const calls = ref<ApiCall[]>([])
const creating = ref(false)
const loadingList = ref(false)

async function loadCollections() {
  const resp = await collectionsApi.list()
  if (resp.code === 0) {
    collections.value = resp.data
    if (!collection.value && collections.value.length) {
      collection.value = collections.value[0]
    }
  }
}

async function loadPartitions() {
  if (!collection.value) {
    partitions.value = []
    return
  }
  loadingList.value = true
  try {
    const resp = await partitionsApi.list(collection.value)
    if (resp.code === 0) partitions.value = resp.data
    else ElMessage.error(resp.message)
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loadingList.value = false
  }
}

async function create() {
  if (!collection.value) {
    ElMessage.warning('请选集合')
    return
  }
  if (!newName.value) {
    ElMessage.warning('请输入分区名')
    return
  }
  creating.value = true
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/collections/${collection.value}/partitions`,
    { name: newName.value },
  )
  calls.value = [call]
  creating.value = false
  if (data.code === 0) {
    ElMessage.success(`已创建分区 ${newName.value}`)
    newName.value = ''
    await loadPartitions()
  } else {
    ElMessage.error(data.message)
  }
}

async function drop(name: string) {
  try {
    await ElMessageBox.confirm(
      `确认删除分区 "${name}" 吗？该分区数据会丢失。`,
      '警告',
      { type: 'warning' },
    )
  } catch {
    return
  }
  const { data, call } = await trackedCall(
    'DELETE',
    `/api/v1/collections/${collection.value}/partitions/${name}`,
  )
  calls.value = [call]
  if (data.code === 0) {
    ElMessage.success(`已删除分区 ${name}`)
    await loadPartitions()
  } else {
    ElMessage.error(data.message)
  }
}

watch(collection, () => loadPartitions())
onMounted(async () => {
  await loadCollections()
  await loadPartitions()
})
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>分区（Partitions）</h2>
      <p class="desc">
        分区 = 集合内按业务维度切分的子集（如按时间 <code>y2024</code> / <code>y2025</code>，按租户 <code>tenant_a</code>）。
        检索时指定 <code>partition_names</code> 可缩小扫描范围，<b>提速显著</b>。
      </p>
    </header>

    <el-card style="margin-bottom: 16px">
      <el-form inline>
        <el-form-item label="集合">
          <el-select v-model="collection" placeholder="选集合" filterable style="width: 280px">
            <el-option v-for="c in collections" :key="c" :value="c" :label="c" />
          </el-select>
        </el-form-item>
      </el-form>
    </el-card>

    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <el-card>
          <template #header><span>➕ 创建分区</span></template>
          <el-form label-width="80px">
            <el-form-item label="分区名">
              <el-input v-model="newName" placeholder="如 y2024" />
              <ParamHelp :doc="partitionDocs.name" />
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
              <span>📋 分区列表</span>
              <el-tag size="small">{{ partitions.length }} 个</el-tag>
            </div>
          </template>
          <div v-loading="loadingList" class="partition-list">
            <div v-for="p in partitions" :key="p" class="partition-item">
              <code class="part-name">{{ p }}</code>
              <el-button size="small" type="danger" @click="drop(p)">删除</el-button>
            </div>
            <div v-if="!partitions.length" class="empty-tip">无分区</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <TutorialPanel slug="06-partitions" />
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
.partition-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 0;
  min-height: 60px;
}
.partition-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fafbfc;
}
.part-name {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 14px;
  color: #409eff;
  background: #ecf5ff;
  padding: 2px 8px;
  border-radius: 3px;
}
.empty-tip {
  color: #909399;
  font-size: 13px;
  padding: 8px;
}
</style>
