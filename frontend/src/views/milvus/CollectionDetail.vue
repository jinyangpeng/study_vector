<script setup lang="ts">
// 集合详情：插入 / 检索 / 拉取 / 删除 + 自动 QueryPanel 验证
import { onMounted, ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  collectionsApi,
  vectorsApi,
  trackedCall,
  type ApiCall,
} from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import QueryPanel from '@/components/QueryPanel.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { vectorRecordDocs, searchRequestDocs } from '@/lib/fieldDocs'

const route = useRoute()
const router = useRouter()
const name = String(route.params.name)

const info = ref<any>({})
const loadingInfo = ref(false)
const calls = ref<ApiCall[]>([])

const queryRefresh = ref(0)

// 插入表单
const insertForm = ref({
  id: '',
  vector: '0.1, 0.2, 0.3, 0.4',
  payload: '{"category": "demo", "lang": "zh"}',
})
const inserting = ref(false)

// 批量插入示例
const batchForm = ref({
  count: 5,
  start_id: 'batch_1',
  vector_prefix: '0.1, 0.2, 0.3, 0.4',
})
const batching = ref(false)

async function loadInfo() {
  loadingInfo.value = true
  try {
    const resp = await collectionsApi.info(name)
    if (resp.code === 0) info.value = resp.data
    else ElMessage.error(resp.message)
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loadingInfo.value = false
  }
}

function fillInsertExample() {
  insertForm.value = {
    id: 'doc_' + Date.now(),
    vector: '0.95, 0.05, 0.0, 0.0',
    payload: '{"category": "tech", "lang": "zh", "source": "news"}',
  }
  ElMessage.success('已填充示例数据')
}

async function insertOne() {
  let vector: number[]
  let payload: Record<string, any>
  try {
    vector = insertForm.value.vector.split(',').map((s) => Number(s.trim()))
    if (vector.some((n) => Number.isNaN(n))) throw new Error('vector 含非数字')
    payload = insertForm.value.payload
      ? JSON.parse(insertForm.value.payload)
      : {}
  } catch (e: any) {
    ElMessage.error('参数解析失败：' + (e.message || e))
    return
  }
  // 校验维度
  if (info.value.dimension && vector.length !== info.value.dimension) {
    ElMessage.warning(
      `向量维度 ${vector.length} ≠ 集合维度 ${info.value.dimension}，插入会失败`,
    )
    return
  }
  inserting.value = true
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/vectors/${name}/insert`,
    [{ id: insertForm.value.id || undefined, vector, payload }],
  )
  calls.value = [call]
  inserting.value = false
  if (data.code === 0) {
    ElMessage.success(`已插入 ${data.data.count} 条`)
    insertForm.value.id = ''
    await loadInfo()
    queryRefresh.value++
  } else {
    ElMessage.error(data.message)
  }
}

async function batchInsert() {
  if (batchForm.value.count < 1 || batchForm.value.count > 100) {
    ElMessage.warning('批量数 1-100')
    return
  }
  let prefix: number[]
  try {
    prefix = batchForm.value.vector_prefix
      .split(',')
      .map((s) => Number(s.trim()))
    if (prefix.some((n) => Number.isNaN(n))) throw new Error('含非数字')
  } catch (e: any) {
    ElMessage.error('前缀解析失败：' + e.message)
    return
  }
  if (info.value.dimension && prefix.length !== info.value.dimension) {
    ElMessage.warning(`前缀维度 ${prefix.length} ≠ 集合维度 ${info.value.dimension}`)
    return
  }
  batching.value = true
  const records = Array.from({ length: batchForm.value.count }, (_, i) => ({
    id: `${batchForm.value.start_id}_${i}`,
    vector: prefix.map((v, j) => Number((v + i * 0.01 * (j + 1)).toFixed(4))),
    payload: { category: 'batch', batch_idx: i },
  }))
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/vectors/${name}/insert`,
    records,
  )
  calls.value = [call]
  batching.value = false
  if (data.code === 0) {
    ElMessage.success(`已批量插入 ${data.data.count} 条`)
    await loadInfo()
    queryRefresh.value++
  } else {
    ElMessage.error(data.message)
  }
}

// 检索表单
const searchForm = ref({
  vector: '0.1, 0.2, 0.3, 0.4',
  top_k: 5,
  filter: '',
})
const searching = ref(false)
const results = ref<any[]>([])

function fillSearchExample() {
  searchForm.value = {
    vector: '0.95, 0.05, 0.0, 0.0',
    top_k: 5,
    filter: '{"category": "tech"}',
  }
  ElMessage.success('已填充示例查询')
}

async function doSearch() {
  let vector: number[]
  try {
    vector = searchForm.value.vector.split(',').map((s) => Number(s.trim()))
    if (vector.some((n) => Number.isNaN(n))) throw new Error('含非数字')
  } catch (e: any) {
    ElMessage.error('query 解析失败：' + e.message)
    return
  }
  if (info.value.dimension && vector.length !== info.value.dimension) {
    ElMessage.warning(`query 维度 ${vector.length} ≠ 集合维度 ${info.value.dimension}`)
    return
  }
  let filter_expr: Record<string, any> | undefined
  if (searchForm.value.filter.trim()) {
    try {
      filter_expr = JSON.parse(searchForm.value.filter)
    } catch (e: any) {
      ElMessage.error('filter 必须是合法 JSON：' + e.message)
      return
    }
  }
  searching.value = true
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/vectors/${name}/search`,
    { vector, top_k: searchForm.value.top_k, filter_expr },
  )
  calls.value = [call]
  searching.value = false
  if (data.code === 0) {
    results.value = data.data
    ElMessage.success(`命中 ${data.data.length} 条`)
  } else {
    ElMessage.error(data.message)
  }
}

// 拉取
const getIds = ref('id1,id2')
const fetched = ref<any[]>([])

async function doGet() {
  const ids = getIds.value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  if (ids.length === 0) {
    ElMessage.warning('请填写至少一个 id')
    return
  }
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/vectors/${name}/get`,
    { ids },
  )
  calls.value = [call]
  if (data.code === 0) {
    fetched.value = data.data
    ElMessage.success(`拉取到 ${data.data.length} 条`)
  } else {
    ElMessage.error(data.message)
  }
}

// 按 id 删除
const deleteIds = ref('')
const deleting = ref(false)

async function doDelete() {
  const ids = deleteIds.value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  if (ids.length === 0) {
    ElMessage.warning('请填写至少一个 id')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除 ${ids.length} 条记录吗？`,
      '警告',
      { type: 'warning' },
    )
  } catch {
    return
  }
  deleting.value = true
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/vectors/${name}/delete`,
    { ids },
  )
  calls.value = [call]
  deleting.value = false
  if (data.code === 0) {
    ElMessage.success(`已删除 ${data.data.deleted} 条`)
    await loadInfo()
    queryRefresh.value++
  } else {
    ElMessage.error(data.message)
  }
}

onMounted(loadInfo)
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <el-page-header @back="router.push('/milvus/collections')" style="margin-bottom: 8px">
        <template #content>
          <span style="font-size: 20px; font-weight: 600">集合：{{ name }}</span>
        </template>
      </el-page-header>
      <el-descriptions v-if="info.name" :column="4" border size="small">
        <el-descriptions-item label="维度">{{ info.dimension }}</el-descriptions-item>
        <el-descriptions-item label="向量类型">{{ info.vector_type || 'FloatVector' }}</el-descriptions-item>
        <el-descriptions-item label="度量">{{ info.metric }}</el-descriptions-item>
        <el-descriptions-item label="行数">{{ info.row_count }}</el-descriptions-item>
        <el-descriptions-item label="加载">{{ info.loaded ? '✅' : '❌' }}</el-descriptions-item>
        <el-descriptions-item label="一致性">{{ info.consistency_level || 'Session' }}</el-descriptions-item>
        <el-descriptions-item label="索引">{{ (info.indexes || []).map((i: any) => i.index_type).join(', ') || '无' }}</el-descriptions-item>
        <el-descriptions-item label="描述">{{ info.description || '-' }}</el-descriptions-item>
      </el-descriptions>
    </header>

    <el-row :gutter="16">
      <!-- 插入 -->
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>➕ 插入向量</span>
              <el-button text type="primary" @click="fillInsertExample">
                📋 填充示例
              </el-button>
            </div>
          </template>
          <el-form :model="insertForm" label-width="80px">
            <el-form-item label="id">
              <el-input v-model="insertForm.id" placeholder="留空自动生成" />
              <ParamHelp :doc="vectorRecordDocs.id" />
            </el-form-item>
            <el-form-item label="vector">
              <el-input v-model="insertForm.vector" placeholder="逗号分隔" />
              <ParamHelp :doc="vectorRecordDocs.vector" />
            </el-form-item>
            <el-form-item label="payload">
              <el-input
                v-model="insertForm.payload"
                type="textarea"
                :rows="2"
                placeholder="JSON 对象"
              />
              <ParamHelp :doc="vectorRecordDocs.payload" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="inserting" @click="insertOne">
                插入单条
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 批量插入 -->
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <span>📦 批量插入（自动构造）</span>
          </template>
          <el-form :model="batchForm" label-width="100px">
            <el-form-item label="条数">
              <el-input-number v-model="batchForm.count" :min="1" :max="100" style="width: 100%" />
            </el-form-item>
            <el-form-item label="id 前缀">
              <el-input v-model="batchForm.start_id" placeholder="如 batch_1" />
            </el-form-item>
            <el-form-item label="向量前缀">
              <el-input
                v-model="batchForm.vector_prefix"
                placeholder="逗号分隔，每条按维度微调"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="success" :loading="batching" @click="batchInsert">
                批量插入 {{ batchForm.count }} 条
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 检索 -->
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>🔍 向量检索</span>
              <el-button text type="primary" @click="fillSearchExample">
                📋 填充示例
              </el-button>
            </div>
          </template>
          <el-form :model="searchForm" label-width="80px">
            <el-form-item label="query">
              <el-input v-model="searchForm.vector" placeholder="逗号分隔" />
              <ParamHelp :doc="searchRequestDocs.vector" />
            </el-form-item>
            <el-form-item label="top_k">
              <el-input-number
                v-model="searchForm.top_k"
                :min="1"
                :max="1000"
                style="width: 100%"
              />
              <ParamHelp :doc="searchRequestDocs.top_k" />
            </el-form-item>
            <el-form-item label="filter">
              <el-input
                v-model="searchForm.filter"
                placeholder='JSON，例如 {"category":"tech"}'
              />
              <ParamHelp :doc="searchRequestDocs.filter_expr" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="searching" @click="doSearch">
                检索
              </el-button>
            </el-form-item>
          </el-form>
          <el-table
            v-if="results.length"
            :data="results"
            size="small"
            max-height="280"
            empty-text="无命中"
          >
            <el-table-column prop="id" label="id" width="160" />
            <el-table-column label="score" width="100">
              <template #default="{ row }">
                {{ Number(row.score).toFixed(4) }}
              </template>
            </el-table-column>
            <el-table-column label="payload" min-width="200">
              <template #default="{ row }">
                <code style="font-size: 12px">{{ JSON.stringify(row.payload) }}</code>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- 拉取 + 删除 -->
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <span>📥 按 id 拉取 / 删除</span>
          </template>
          <el-form label-width="80px">
            <el-form-item label="ids">
              <el-input v-model="getIds" placeholder="逗号分隔" />
            </el-form-item>
            <el-form-item>
              <el-button @click="doGet">拉取</el-button>
            </el-form-item>
            <el-divider style="margin: 8px 0" />
            <el-form-item label="ids (删)">
              <el-input v-model="deleteIds" placeholder="逗号分隔" />
            </el-form-item>
            <el-form-item>
              <el-button type="danger" :loading="deleting" @click="doDelete">
                删除
              </el-button>
            </el-form-item>
          </el-form>
          <el-table
            v-if="fetched.length"
            :data="fetched"
            size="small"
            max-height="240"
            empty-text="无"
          >
            <el-table-column prop="id" label="id" width="160" />
            <el-table-column label="vector (前 4)" min-width="200">
              <template #default="{ row }">
                <code style="font-size: 12px">
                  [<span v-if="row.vector">{{ row.vector.slice(0, 4).map((v: number) => v.toFixed(3)).join(', ') }}</span>]
                </code>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- API 调用跟踪 -->
    <ApiResponseViewer :calls="calls" />

    <!-- 自动验证面板 -->
    <QueryPanel
      :collection="name"
      :refresh-key="queryRefresh"
      :auto-ms="5000"
      title="📊 数据已落库（自动验证）"
    />

    <!-- 教学 Markdown -->
    <TutorialPanel slug="02-insert-and-search" />
  </div>
</template>

<style scoped>
.page-inner { padding: 0; }
.page-header { margin-bottom: 16px; }
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
</style>
