<script setup lang="ts">
// Milvus 检索页（教学版）：向量检索 + 混合检索（RRF）
import { onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { collectionsApi, vectorsApi, trackedCall, type ApiCall } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { searchRequestDocs, hybridSearchDocs } from '@/lib/fieldDocs'

const collections = ref<string[]>([])
const collection = ref('')
const info = ref<any>({})
const calls = ref<ApiCall[]>([])

// 向量检索表单
const searchForm = ref({
  vector: '0.1, 0.2, 0.3, 0.4',
  top_k: 5,
  filter_expr: '',
  output_fields: '',
  partition_names: '',
})
const searching = ref(false)
const results = ref<any[]>([])

// 混合检索表单
const hybridForm = ref({
  dense: '0.1, 0.2, 0.3, 0.4',
  dense_weight: 1.0,
  sparse: '{"kw1": 1.0, "kw2": 0.5}',
  sparse_weight: 1.0,
  rrf_k: 60,
  top_k: 5,
})
const hybridSearching = ref(false)
const hybridResults = ref<any[]>([])

async function loadCollections() {
  const resp = await collectionsApi.list()
  if (resp.code === 0) {
    collections.value = resp.data
    if (!collection.value && collections.value.length) {
      collection.value = collections.value[0]
    }
  }
}

async function loadInfo() {
  if (!collection.value) {
    info.value = {}
    return
  }
  const resp = await collectionsApi.info(collection.value)
  if (resp.code === 0) info.value = resp.data
}

function fillVectorExample() {
  searchForm.value = {
    vector: '0.95, 0.05, 0.0, 0.0',
    top_k: 5,
    filter_expr: '{"category": "tech"}',
    output_fields: '',
    partition_names: '',
  }
  ElMessage.success('已填充示例查询')
}

function fillHybridExample() {
  hybridForm.value = {
    dense: '0.95, 0.05, 0.0, 0.0',
    dense_weight: 1.0,
    sparse: '{"kw_intro": 1.0, "kw_welcome": 0.5}',
    sparse_weight: 0.5,
    rrf_k: 60,
    top_k: 5,
  }
  ElMessage.success('已填充混合检索示例')
}

async function doSearch() {
  if (!collection.value) {
    ElMessage.warning('请先选集合')
    return
  }
  let vector: number[]
  try {
    vector = searchForm.value.vector.split(',').map((s) => Number(s.trim()))
    if (vector.some((n) => Number.isNaN(n))) throw new Error('含非数字')
  } catch (e: any) {
    ElMessage.error('query 解析失败：' + e.message)
    return
  }
  if (info.value.dimension && vector.length !== info.value.dimension) {
    ElMessage.warning(
      `query 维度 ${vector.length} ≠ 集合维度 ${info.value.dimension}`,
    )
    return
  }
  const body: any = { vector, top_k: searchForm.value.top_k }
  if (searchForm.value.filter_expr.trim()) {
    try {
      body.filter_expr = JSON.parse(searchForm.value.filter_expr)
    } catch (e: any) {
      ElMessage.error('filter_expr 不是合法 JSON：' + e.message)
      return
    }
  }
  if (searchForm.value.output_fields.trim()) {
    body.output_fields = searchForm.value.output_fields
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  }
  if (searchForm.value.partition_names.trim()) {
    body.partition_names = searchForm.value.partition_names
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
  }
  searching.value = true
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/vectors/${collection.value}/search`,
    body,
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

async function doHybrid() {
  if (!collection.value) {
    ElMessage.warning('请先选集合')
    return
  }
  let dense: number[]
  try {
    dense = hybridForm.value.dense.split(',').map((s) => Number(s.trim()))
    if (dense.some((n) => Number.isNaN(n))) throw new Error('含非数字')
  } catch (e: any) {
    ElMessage.error('dense 解析失败：' + e.message)
    return
  }
  let sparse: Record<string, number> | undefined
  if (hybridForm.value.sparse.trim()) {
    try {
      sparse = JSON.parse(hybridForm.value.sparse)
    } catch (e: any) {
      ElMessage.error('sparse 不是合法 JSON：' + e.message)
      return
    }
  }
  hybridSearching.value = true
  const body: any = {
    dense,
    dense_weight: hybridForm.value.dense_weight,
    sparse,
    sparse_weight: hybridForm.value.sparse_weight,
    rrf_k: hybridForm.value.rrf_k,
    top_k: hybridForm.value.top_k,
  }
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/vectors/${collection.value}/hybrid_search`,
    body,
  )
  calls.value = [call]
  hybridSearching.value = false
  if (data.code === 0) {
    hybridResults.value = data.data
    ElMessage.success(`混合检索命中 ${data.data.length} 条`)
  } else {
    ElMessage.error(data.message)
  }
}

watch(collection, () => {
  loadInfo()
  results.value = []
  hybridResults.value = []
})

onMounted(async () => {
  await loadCollections()
  await loadInfo()
})
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>检索（Search）</h2>
      <p class="desc">向量检索是向量数据库的核心能力。Milvus 提供 <b>单向量检索</b>（ANN）和 <b>混合检索</b>（dense + sparse，RRF 重排）。</p>
    </header>

    <el-card style="margin-bottom: 16px">
      <el-form label-width="100px" inline>
        <el-form-item label="集合">
          <el-select v-model="collection" placeholder="选集合" filterable style="width: 280px">
            <el-option v-for="c in collections" :key="c" :value="c" :label="c" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="info.dimension" label="维度">
          <el-tag>{{ info.dimension }}</el-tag>
        </el-form-item>
        <el-form-item v-if="info.metric" label="度量">
          <el-tag type="success">{{ info.metric }}</el-tag>
        </el-form-item>
        <el-form-item v-if="info.vector_type" label="向量类型">
          <el-tag type="warning">{{ info.vector_type }}</el-tag>
        </el-form-item>
      </el-form>
    </el-card>

    <el-tabs type="border-card">
      <!-- Tab 1：向量检索 -->
      <el-tab-pane label="单向量检索">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>🔍 向量相似度检索（ANN）</span>
              <el-button text type="primary" @click="fillVectorExample">
                📋 填充示例
              </el-button>
            </div>
          </template>
          <el-form :model="searchForm" label-width="120px">
            <el-form-item label="query 向量">
              <el-input v-model="searchForm.vector" placeholder="逗号分隔" />
              <ParamHelp :doc="searchRequestDocs.vector" />
            </el-form-item>
            <el-form-item label="top_k">
              <el-input-number v-model="searchForm.top_k" :min="1" :max="1000" style="width: 100%" />
              <ParamHelp :doc="searchRequestDocs.top_k" />
            </el-form-item>
            <el-form-item label="filter_expr">
              <el-input
                v-model="searchForm.filter_expr"
                type="textarea"
                :rows="2"
                placeholder='JSON，可空。例如 {"category":"tech"}'
              />
              <ParamHelp :doc="searchRequestDocs.filter_expr" />
            </el-form-item>
            <el-form-item label="output_fields">
              <el-input v-model="searchForm.output_fields" placeholder="逗号分隔，可空" />
              <ParamHelp :doc="searchRequestDocs.output_fields" />
            </el-form-item>
            <el-form-item label="partition_names">
              <el-input v-model="searchForm.partition_names" placeholder="逗号分隔，可空" />
              <ParamHelp :doc="searchRequestDocs.partition_names" />
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
            max-height="320"
            empty-text="无命中"
            style="margin-top: 12px"
          >
            <el-table-column prop="id" label="id" width="180" />
            <el-table-column label="score" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ Number(row.score).toFixed(4) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="payload" min-width="200">
              <template #default="{ row }">
                <code style="font-size: 12px">{{ JSON.stringify(row.payload || {}) }}</code>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>

      <!-- Tab 2：混合检索 -->
      <el-tab-pane label="混合检索 (Hybrid / RRF)">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span>🔀 混合检索 = dense + sparse + RRF</span>
              <el-button text type="primary" @click="fillHybridExample">
                📋 填充示例
              </el-button>
            </div>
          </template>
          <el-alert type="info" :closable="false" style="margin-bottom: 12px">
            <p>
              <b>RRF (Reciprocal Rank Fusion)</b>：把 dense 和 sparse 的排名用
              <code>1 / (k + rank)</code> 加权合并，<b>k 越大各路贡献越平均</b>。
            </p>
            <p style="margin: 4px 0 0">
              典型用法：dense（语义）拿语义匹配，sparse（关键词）拿字面匹配，两路互补。
            </p>
          </el-alert>
          <el-form :model="hybridForm" label-width="120px">
            <el-form-item label="dense">
              <el-input v-model="hybridForm.dense" placeholder="逗号分隔" />
              <ParamHelp :doc="hybridSearchDocs.dense" />
            </el-form-item>
            <el-form-item label="dense_weight">
              <el-input-number v-model="hybridForm.dense_weight" :min="0" :max="10" :step="0.1" style="width: 100%" />
              <ParamHelp :doc="hybridSearchDocs.dense_weight" />
            </el-form-item>
            <el-form-item label="sparse">
              <el-input
                v-model="hybridForm.sparse"
                type="textarea"
                :rows="2"
                placeholder='JSON，例如 {"kw1": 1.0}'
              />
              <ParamHelp :doc="hybridSearchDocs.sparse" />
            </el-form-item>
            <el-form-item label="sparse_weight">
              <el-input-number v-model="hybridForm.sparse_weight" :min="0" :max="10" :step="0.1" style="width: 100%" />
              <ParamHelp :doc="hybridSearchDocs.sparse_weight" />
            </el-form-item>
            <el-form-item label="rrf_k">
              <el-input-number v-model="hybridForm.rrf_k" :min="1" :max="1000" style="width: 100%" />
              <ParamHelp :doc="hybridSearchDocs.rrf_k" />
            </el-form-item>
            <el-form-item label="top_k">
              <el-input-number v-model="hybridForm.top_k" :min="1" :max="100" style="width: 100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="hybridSearching" @click="doHybrid">
                混合检索
              </el-button>
            </el-form-item>
          </el-form>

          <el-table
            v-if="hybridResults.length"
            :data="hybridResults"
            size="small"
            max-height="320"
            empty-text="无命中"
            style="margin-top: 12px"
          >
            <el-table-column prop="id" label="id" width="180" />
            <el-table-column label="score" width="100">
              <template #default="{ row }">
                <el-tag size="small" type="success">{{ Number(row.score).toFixed(6) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="payload" min-width="200">
              <template #default="{ row }">
                <code style="font-size: 12px">{{ JSON.stringify(row.payload || {}) }}</code>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <ApiResponseViewer :calls="calls" />

    <TutorialPanel slug="04-search-and-hybrid" />
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
</style>
