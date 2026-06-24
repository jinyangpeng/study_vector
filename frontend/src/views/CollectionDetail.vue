<script setup lang="ts">
// 集合详情：插入 / 检索 / 拉取 / 删除
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { collectionsApi, vectorsApi } from '@/api'

const route = useRoute()
const router = useRouter()
const name = String(route.params.name)

const info = ref<any>({})
const loadingInfo = ref(false)

// 插入表单
const recordForm = ref({
  id: '',
  vector: '0.1, 0.2, 0.3, 0.4',
  payload: '{"tag": "x"}',
})
const inserting = ref(false)

// 检索表单
const searchForm = ref({
  vector: '0.1, 0.2, 0.3, 0.4',
  top_k: 5,
  filter: '',
})
const searching = ref(false)
const results = ref<any[]>([])

// 拉取
const getIds = ref('id1,id2')
const fetched = ref<any[]>([])

const loadInfo = async () => {
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

const insertOne = async () => {
  let vector: number[]
  let payload: Record<string, any>
  try {
    vector = recordForm.value.vector.split(',').map((s) => Number(s.trim()))
    if (vector.some((n) => Number.isNaN(n))) throw new Error('vector 含非数字')
    payload = recordForm.value.payload
      ? JSON.parse(recordForm.value.payload)
      : {}
  } catch (e: any) {
    ElMessage.error('参数解析失败：' + (e.message || e))
    return
  }
  inserting.value = true
  try {
    const records = [
      {
        id: recordForm.value.id || undefined,
        vector,
        payload,
      },
    ]
    const resp = await vectorsApi.insert(name, records)
    if (resp.code === 0) {
      ElMessage.success(`已插入 ${resp.data.count} 条`)
      recordForm.value.id = ''
      await loadInfo()
    } else {
      ElMessage.error(resp.message)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '插入失败')
  } finally {
    inserting.value = false
  }
}

const doSearch = async () => {
  let vector: number[]
  try {
    vector = searchForm.value.vector.split(',').map((s) => Number(s.trim()))
    if (vector.some((n) => Number.isNaN(n))) throw new Error('vector 含非数字')
  } catch (e: any) {
    ElMessage.error('query 解析失败：' + (e.message || e))
    return
  }
  let filter_expr: Record<string, any> | undefined
  if (searchForm.value.filter.trim()) {
    try {
      filter_expr = JSON.parse(searchForm.value.filter)
    } catch (e: any) {
      ElMessage.error('filter 必须是合法 JSON：' + (e.message || e))
      return
    }
  }
  searching.value = true
  try {
    const resp = await vectorsApi.search(name, {
      vector,
      top_k: searchForm.value.top_k,
      filter_expr,
    })
    if (resp.code === 0) {
      results.value = resp.data
      ElMessage.success(`命中 ${resp.data.length} 条`)
    } else {
      ElMessage.error(resp.message)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '检索失败')
  } finally {
    searching.value = false
  }
}

const doGet = async () => {
  const ids = getIds.value
    .split(',')
    .map((s) => s.trim())
    .filter(Boolean)
  if (ids.length === 0) {
    ElMessage.warning('请填写至少一个 id')
    return
  }
  try {
    const resp = await vectorsApi.get(name, ids)
    if (resp.code === 0) {
      fetched.value = resp.data
      ElMessage.success(`拉取到 ${resp.data.length} 条`)
    } else {
      ElMessage.error(resp.message)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '拉取失败')
  }
}

onMounted(loadInfo)
</script>

<template>
  <div class="page">
    <el-page-header @back="router.push('/')" style="margin-bottom: 16px">
      <template #content>
        <span style="font-size: 20px; font-weight: 600">集合：{{ name }}</span>
      </template>
    </el-page-header>

    <el-card v-loading="loadingInfo">
      <template #header>
        <span>集合元信息</span>
      </template>
      <el-descriptions :column="3" border>
        <el-descriptions-item label="名称">{{ info.name }}</el-descriptions-item>
        <el-descriptions-item label="维度">{{ info.dimension }}</el-descriptions-item>
        <el-descriptions-item label="度量">{{ info.metric }}</el-descriptions-item>
        <el-descriptions-item label="行数">{{ info.row_count }}</el-descriptions-item>
        <el-descriptions-item label="创建时间" :span="2">
          {{ info.created_at || '-' }}
        </el-descriptions-item>
      </el-descriptions>
    </el-card>

    <el-row :gutter="16" style="margin-top: 16px">
      <!-- 插入 -->
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <span style="font-weight: 600">插入向量</span>
          </template>
          <el-form :model="recordForm" label-width="80px">
            <el-form-item label="id">
              <el-input v-model="recordForm.id" placeholder="留空自动生成" />
            </el-form-item>
            <el-form-item label="vector">
              <el-input v-model="recordForm.vector" placeholder="逗号分隔" />
            </el-form-item>
            <el-form-item label="payload">
              <el-input
                v-model="recordForm.payload"
                type="textarea"
                :rows="2"
                placeholder="JSON 对象"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="inserting" @click="insertOne">
                插入
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 检索 -->
      <el-col :xs="24" :lg="12">
        <el-card>
          <template #header>
            <span style="font-weight: 600">向量检索</span>
          </template>
          <el-form :model="searchForm" label-width="80px">
            <el-form-item label="query">
              <el-input v-model="searchForm.vector" placeholder="逗号分隔" />
            </el-form-item>
            <el-form-item label="top_k">
              <el-input-number
                v-model="searchForm.top_k"
                :min="1"
                :max="1000"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="filter">
              <el-input
                v-model="searchForm.filter"
                placeholder='JSON，例如 {"tag":"x"}'
              />
            </el-form-item>
            <el-form-item>
              <el-button type="success" :loading="searching" @click="doSearch">
                检索
              </el-button>
            </el-form-item>
          </el-form>

          <el-table v-if="results.length" :data="results" size="small" max-height="300">
            <el-table-column prop="id" label="id" width="180" />
            <el-table-column prop="score" label="score" width="100">
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
    </el-row>

    <!-- 拉取 -->
    <el-card style="margin-top: 16px">
      <template #header>
        <span style="font-weight: 600">按 id 拉取</span>
      </template>
      <el-form :model="{ ids: getIds }" label-width="80px" inline>
        <el-form-item label="ids">
          <el-input
            v-model="getIds"
            placeholder="逗号分隔"
            style="min-width: 320px"
          />
        </el-form-item>
        <el-form-item>
          <el-button @click="doGet">拉取</el-button>
        </el-form-item>
      </el-form>
      <el-table v-if="fetched.length" :data="fetched" size="small" max-height="300">
        <el-table-column prop="id" label="id" width="180" />
        <el-table-column label="vector" min-width="200">
          <template #default="{ row }">
            <code style="font-size: 12px">
              [{{ (row.vector as number[]).map((v) => v.toFixed(3)).join(', ') }}]
            </code>
          </template>
        </el-table-column>
        <el-table-column label="payload" min-width="200">
          <template #default="{ row }">
            <code style="font-size: 12px">{{ JSON.stringify(row.payload) }}</code>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>
