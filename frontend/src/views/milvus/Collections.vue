<script setup lang="ts">
// Milvus 集合管理页（教学版）
// 含：创建表单（带 ⓘ 字段说明 + 一键填充示例 + ApiResponseViewer 展示）+ 集合列表 + 教学 Markdown
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { collectionsApi, trackedCall, type ApiCall } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { collectionSchemaDocs } from '@/lib/fieldDocs'

const router = useRouter()
const rows = ref<string[]>([])
const collectionRows = computed(() => rows.value.map((name) => ({ name })))
const loading = ref(false)
const creating = ref(false)
const calls = ref<ApiCall[]>([])

const form = ref({
  name: 'demo_chunks',
  dimension: 768,
  vector_type: 'FloatVector',
  metric: 'COSINE',
  primary_field: 'id',
  vector_field: 'vector',
  description: 'BGE-base 嵌入的教学集合',
  index_type: 'AUTOINDEX',
  consistency_level: 'Session',
})

async function load() {
  loading.value = true
  try {
    const resp = await collectionsApi.list()
    if (resp.code === 0) {
      rows.value = resp.data
    } else {
      ElMessage.error(resp.message)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

function fillExample() {
  form.value = {
    name: 'demo_chunks',
    dimension: 768,
    vector_type: 'FloatVector',
    metric: 'COSINE',
    primary_field: 'id',
    vector_field: 'vector',
    description: 'BGE-base 嵌入的教学集合（768 维）',
    index_type: 'AUTOINDEX',
    consistency_level: 'Session',
  }
  ElMessage.success('已填充示例：BGE-base 768 维 + COSINE + AUTOINDEX')
}

async function create() {
  if (!form.value.name) {
    ElMessage.warning('请填写集合名称')
    return
  }
  if (form.value.dimension < 1 || form.value.dimension > 65536) {
    ElMessage.warning('维度需在 1-65536 之间')
    return
  }
  creating.value = true
  calls.value = []
  const { data, call } = await trackedCall(
    'POST',
    '/api/v1/collections',
    form.value,
  )
  calls.value = [call]
  creating.value = false
  if (data.code === 0) {
    ElMessage.success(`已创建集合 ${data.data.name}`)
    await load()
  } else {
    ElMessage.error(`${data.message}`)
  }
}

async function remove(name: string) {
  try {
    await ElMessageBox.confirm(`确认删除集合 "${name}" 吗？此操作不可恢复。`, '警告', {
      type: 'warning',
    })
  } catch {
    return
  }
  loading.value = true
  const { data, call } = await trackedCall(
    'DELETE',
    `/api/v1/collections/${name}`,
  )
  calls.value = [call]
  loading.value = false
  if (data.code === 0) {
    ElMessage.success(`已删除 ${name}`)
    await load()
  } else {
    ElMessage.error(data.message)
  }
}

async function loadInfo(name: string) {
  const { data, call } = await trackedCall(
    'GET',
    `/api/v1/collections/${name}`,
  )
  calls.value = [call]
  if (data.code === 0) {
    ElMessage.success(`集合 ${name} 当前行数 = ${data.data.row_count}`)
  } else {
    ElMessage.error(data.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>集合（Collections）</h2>
      <p class="desc">Milvus 中的"集合"类比 MySQL 的"表"，是组织向量数据的容器。创建一个集合 = 选定 schema + 度量 + 索引 + 加载到内存。</p>
    </header>

    <el-row :gutter="16">
      <!-- 左侧：创建表单 -->
      <el-col :xs="24" :md="11">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>➕ 创建集合</span>
              <el-button text type="primary" @click="fillExample">
                📋 一键填充示例
              </el-button>
            </div>
          </template>

          <el-form :model="form" label-width="100px" label-position="right">
            <el-form-item label="集合名">
              <el-input v-model="form.name" placeholder="字母开头 + 字母数字下划线" />
              <ParamHelp :doc="collectionSchemaDocs.name" />
            </el-form-item>

            <el-form-item label="向量维度">
              <el-input-number
                v-model="form.dimension"
                :min="1"
                :max="65536"
                style="width: 100%"
              />
              <ParamHelp :doc="collectionSchemaDocs.dimension" />
            </el-form-item>

            <el-form-item label="向量类型">
              <el-select v-model="form.vector_type" style="width: 100%">
                <el-option
                  v-for="opt in collectionSchemaDocs.vector_type.options"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </el-select>
              <ParamHelp :doc="collectionSchemaDocs.vector_type" />
            </el-form-item>

            <el-form-item label="距离度量">
              <el-select v-model="form.metric" style="width: 100%">
                <el-option
                  v-for="opt in collectionSchemaDocs.metric.options"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </el-select>
              <ParamHelp :doc="collectionSchemaDocs.metric" />
            </el-form-item>

            <el-form-item label="默认索引">
              <el-select v-model="form.index_type" style="width: 100%">
                <el-option
                  v-for="opt in collectionSchemaDocs.index_type.options"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </el-select>
              <ParamHelp :doc="collectionSchemaDocs.index_type" />
            </el-form-item>

            <el-form-item label="一致性">
              <el-select v-model="form.consistency_level" style="width: 100%">
                <el-option
                  v-for="opt in collectionSchemaDocs.consistency_level.options"
                  :key="opt.value"
                  :value="opt.value"
                  :label="opt.label"
                />
              </el-select>
              <ParamHelp :doc="collectionSchemaDocs.consistency_level" />
            </el-form-item>

            <el-form-item label="主键字段">
              <el-input v-model="form.primary_field" />
              <ParamHelp :doc="collectionSchemaDocs.primary_field" />
            </el-form-item>

            <el-form-item label="向量字段">
              <el-input v-model="form.vector_field" />
              <ParamHelp :doc="collectionSchemaDocs.vector_field" />
            </el-form-item>

            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="2"
                placeholder="可选"
              />
              <ParamHelp :doc="collectionSchemaDocs.description" />
            </el-form-item>

            <el-form-item>
              <el-button type="primary" :loading="creating" @click="create">
                创建集合
              </el-button>
              <el-button @click="load">刷新列表</el-button>
            </el-form-item>
          </el-form>

          <ApiResponseViewer :calls="calls" />
        </el-card>
      </el-col>

      <!-- 右侧：集合列表 -->
      <el-col :xs="24" :md="13">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>📋 集合列表</span>
              <el-tag size="small" type="info">{{ rows.length }} 个</el-tag>
            </div>
          </template>
          <el-table v-loading="loading" :data="collectionRows" stripe empty-text="暂无集合">
            <el-table-column label="名称" min-width="200">
              <template #default="{ row }">
                <el-link type="primary" @click="router.push(`/milvus/collections/${row.name}`)">
                  {{ row.name }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="240">
              <template #default="{ row }">
                <el-button size="small" @click="router.push(`/milvus/collections/${row.name}`)">
                  进入
                </el-button>
                <el-button size="small" @click="loadInfo(row.name)">详情</el-button>
                <el-button size="small" type="danger" @click="remove(row.name)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 教学 Markdown -->
    <TutorialPanel slug="01-first-collection" />
  </div>
</template>

<style scoped>
.page-inner {
  padding: 0;
}
.page-header {
  margin-bottom: 16px;
}
.page-header h2 {
  margin: 0 0 4px;
  font-size: 22px;
  color: #303133;
}
.page-header .desc {
  margin: 0;
  color: #606266;
  font-size: 13px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-weight: 600;
}
</style>
