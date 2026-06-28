<script setup lang="ts">
// QueryPanel：操作后自动 query 验证（教学闭环）
// 写操作后调用 `POST /api/v1/vectors/{name}/query` 拉回数据，让用户"看得见落库"
import { ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { vectorsApi } from '@/api'

const props = defineProps<{
  /** 集合名（必填） */
  collection: string
  /** 触发刷新的计数器（每次 +1 触发一次 query） */
  refreshKey?: number
  /** 自动刷新间隔（毫秒）；0 = 不自动刷新 */
  autoMs?: number
  /** 标题 */
  title?: string
}>()

interface QueryResult {
  id: string | number
  vector?: number[]
  payload?: Record<string, any>
  score?: number
}

const records = ref<QueryResult[]>([])
const total = ref(0)
const loading = ref(false)
const errorMsg = ref('')
const auto = ref(false)
let timer: number | null = null

async function loadQuery() {
  if (!props.collection) {
    errorMsg.value = '请先选择集合'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const resp = await vectorsApi.query(props.collection, {
      limit: 10,
      output_fields: ['*'],
    } as any)
    if (resp.code === 0) {
      const data = resp.data
      if (typeof data === 'number') {
        total.value = data
        records.value = []
      } else if (Array.isArray(data)) {
        records.value = data
        total.value = data.length
      } else {
        records.value = []
        total.value = 0
      }
    } else {
      errorMsg.value = resp.message
    }
  } catch (e: any) {
    errorMsg.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

async function loadCount() {
  if (!props.collection) return
  loading.value = true
  try {
    const resp = await vectorsApi.query(props.collection, {
      count_only: true,
    } as any)
    if (resp.code === 0 && typeof resp.data === 'number') {
      total.value = resp.data
      ElMessage.success(`集合共 ${total.value} 条记录`)
    }
  } catch (e: any) {
    errorMsg.value = e.message || String(e)
  } finally {
    loading.value = false
  }
}

function toggleAuto(val: string | number | boolean) {
  const enabled = Boolean(val)
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  if (enabled) {
    loadQuery()
    timer = window.setInterval(loadQuery, props.autoMs || 3000)
  }
}

watch(
  () => props.refreshKey,
  () => {
    if (props.refreshKey) loadQuery()
  },
)

watch(
  () => props.collection,
  (c) => {
    if (c) loadQuery()
  },
  { immediate: true },
)
</script>

<template>
  <div class="query-panel">
    <div class="header">
      <span class="icon">🔍</span>
      <span class="title">{{ title || '操作后验证（QueryPanel）' }}</span>
      <span class="count">集合：<code>{{ collection || '（未选）' }}</code> · 总数 <code>{{ total }}</code></span>
      <div class="actions">
        <el-switch
          v-model="auto"
          size="small"
          inline-prompt
          active-text="轮询"
          inactive-text="关"
          @change="toggleAuto"
        />
        <el-button size="small" :loading="loading" @click="loadQuery">刷新</el-button>
        <el-button size="small" plain :loading="loading" @click="loadCount">count</el-button>
      </div>
    </div>

    <div v-if="errorMsg" class="error">{{ errorMsg }}</div>

    <el-table
      v-if="records.length"
      :data="records"
      size="small"
      stripe
      max-height="320"
      empty-text="集合为空（0 条）"
    >
      <el-table-column prop="id" label="id" width="180" />
      <el-table-column label="vector (前 4 维)" min-width="220">
        <template #default="{ row }">
          <code class="vec">
            [<span v-if="row.vector">{{ row.vector.slice(0, 4).map((v: number) => v.toFixed(3)).join(', ') }}</span><span v-else>—</span>]
          </code>
        </template>
      </el-table-column>
      <el-table-column label="payload" min-width="240">
        <template #default="{ row }">
          <code class="payload">{{ JSON.stringify(row.payload || {}) }}</code>
        </template>
      </el-table-column>
    </el-table>
    <div v-else-if="!errorMsg" class="empty">
      <el-icon><DocumentRemove /></el-icon>
      <span>集合为空 / 暂无数据</span>
    </div>
  </div>
</template>

<style scoped>
.query-panel {
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  background: #fff;
  margin-top: 12px;
  overflow: hidden;
}
.header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  background: linear-gradient(90deg, #fdf6ec, #fff);
  border-bottom: 1px solid #ebeef5;
}
.header .icon {
  font-size: 18px;
}
.header .title {
  font-weight: 600;
  color: #303133;
}
.header .count {
  color: #606266;
  font-size: 12px;
}
.header .count code {
  background: #fff7e6;
  padding: 1px 6px;
  border-radius: 3px;
  color: #d4691b;
  font-family: 'JetBrains Mono', Consolas, monospace;
}
.header .actions {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}
.error {
  padding: 12px 16px;
  color: #f56c6c;
  background: #fef0f0;
}
.empty {
  padding: 32px;
  text-align: center;
  color: #909399;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.empty .el-icon {
  font-size: 32px;
  color: #c0c4cc;
}
.vec,
.payload {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  color: #5c4400;
}
.payload {
  color: #5a6f8a;
  word-break: break-all;
}
</style>
