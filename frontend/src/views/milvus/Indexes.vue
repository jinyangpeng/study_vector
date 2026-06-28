<script setup lang="ts">
// Milvus 索引管理页（教学版）
import { onMounted, ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { collectionsApi, indexesApi, trackedCall, type ApiCall } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { createIndexDocs, collectionSchemaDocs } from '@/lib/fieldDocs'

const collections = ref<string[]>([])
const collection = ref('')
const indexes = ref<any[]>([])
const calls = ref<ApiCall[]>([])
const creating = ref(false)
const loadingList = ref(false)

const form = ref({
  field_name: 'vector',
  index_type: 'HNSW',
  metric_type: 'COSINE',
  params: '{"M": 16, "efConstruction": 64}',
})

const presets: Record<string, string> = {
  AUTOINDEX: '',
  HNSW: '{"M": 16, "efConstruction": 64}',
  IVF_FLAT: '{"nlist": 1024}',
  IVF_SQ8: '{"nlist": 1024}',
  IVF_PQ: '{"nlist": 1024, "m": 8, "nbits": 8}',
  FLAT: '',
  ANNOY: '{"n_trees": 8}',
  DISKANN: '',
}

async function loadCollections() {
  try {
    const resp = await collectionsApi.list()
    if (resp.code === 0) {
      collections.value = resp.data
      if (!collection.value && collections.value.length > 0) {
        collection.value = collections.value[0]
      }
    }
  } catch (e: any) {
    ElMessage.error(e.message)
  }
}

async function loadIndexes() {
  if (!collection.value) {
    indexes.value = []
    return
  }
  loadingList.value = true
  try {
    const resp = await indexesApi.list(collection.value)
    if (resp.code === 0) {
      indexes.value = resp.data
    } else {
      ElMessage.error(resp.message)
    }
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loadingList.value = false
  }
}

function fillPreset() {
  form.value.params = presets[form.value.index_type] || ''
  if (form.value.params) {
    ElMessage.success(`已填充 ${form.value.index_type} 典型参数`)
  }
}

async function create() {
  if (!collection.value) {
    ElMessage.warning('请先选集合')
    return
  }
  let params: Record<string, any> | undefined
  if (form.value.params.trim()) {
    try {
      params = JSON.parse(form.value.params)
    } catch (e: any) {
      ElMessage.error('params 不是合法 JSON：' + e.message)
      return
    }
  }
  creating.value = true
  const body: any = {
    field_name: form.value.field_name,
    index_type: form.value.index_type,
    metric_type: form.value.metric_type,
  }
  if (params) body.params = params
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/collections/${collection.value}/indexes`,
    body,
  )
  calls.value = [call]
  creating.value = false
  if (data.code === 0) {
    ElMessage.success(`已在 ${form.value.field_name} 上建好 ${form.value.index_type} 索引`)
    await loadIndexes()
  } else {
    ElMessage.error(data.message)
  }
}

async function drop(fieldName: string) {
  try {
    await ElMessageBox.confirm(
      `确认删除 ${fieldName} 上的索引吗？删除后需要重建才能检索。`,
      '警告',
      { type: 'warning' },
    )
  } catch {
    return
  }
  const { data, call } = await trackedCall(
    'DELETE',
    `/api/v1/collections/${collection.value}/indexes/${fieldName}`,
  )
  calls.value = [call]
  if (data.code === 0) {
    ElMessage.success('索引已删除')
    await loadIndexes()
  } else {
    ElMessage.error(data.message)
  }
}

watch(collection, () => loadIndexes())
onMounted(async () => {
  await loadCollections()
  await loadIndexes()
})
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>索引（Indexes）</h2>
      <p class="desc">向量索引 = 加速最近邻搜索的数据结构。Milvus 提供 8 种索引，<b>AUTOINDEX</b> 让 Milvus 自动选最优（生产推荐）。</p>
    </header>

    <el-row :gutter="16">
      <el-col :xs="24" :md="11">
        <el-card>
          <template #header><span>➕ 建索引</span></template>
          <el-form :model="form" label-width="100px">
            <el-form-item label="集合">
              <el-select v-model="collection" placeholder="选集合" style="width: 100%" filterable>
                <el-option v-for="c in collections" :key="c" :value="c" :label="c" />
              </el-select>
            </el-form-item>
            <el-form-item label="字段名">
              <el-input v-model="form.field_name" />
              <ParamHelp :doc="createIndexDocs.field_name" />
            </el-form-item>
            <el-form-item label="索引类型">
              <el-select v-model="form.index_type" style="width: 100%">
                <el-option
                  v-for="opt in createIndexDocs.index_type.options"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </el-select>
              <ParamHelp :doc="createIndexDocs.index_type" />
            </el-form-item>
            <el-form-item label="距离度量">
              <el-select v-model="form.metric_type" style="width: 100%">
                <el-option
                  v-for="opt in createIndexDocs.metric_type.options"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.value"
                />
              </el-select>
              <ParamHelp :doc="createIndexDocs.metric_type" />
            </el-form-item>
            <el-form-item label="params">
              <el-input v-model="form.params" type="textarea" :rows="2" placeholder="JSON，可空" />
              <ParamHelp :doc="createIndexDocs.params" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="creating" @click="create">建索引</el-button>
              <el-button text @click="fillPreset">📋 填入 {{ form.index_type }} 典型参数</el-button>
            </el-form-item>
          </el-form>
          <ApiResponseViewer :calls="calls" />
        </el-card>
      </el-col>

      <el-col :xs="24" :md="13">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📋 索引列表</span>
              <span style="font-size: 12px; color: #909399">集合：{{ collection || '（未选）' }}</span>
            </div>
          </template>
          <el-table
            v-loading="loadingList"
            :data="indexes"
            stripe
            empty-text="无索引"
          >
            <el-table-column prop="field_name" label="字段" width="120" />
            <el-table-column prop="index_type" label="类型" width="120" />
            <el-table-column prop="metric_type" label="度量" width="100" />
            <el-table-column label="参数" min-width="180">
              <template #default="{ row }">
                <code style="font-size: 12px">{{ JSON.stringify(row.params || {}) }}</code>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" type="danger" @click="drop(row.field_name)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <TutorialPanel slug="03-indexes" />
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
