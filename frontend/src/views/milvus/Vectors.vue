<script setup lang="ts">
// Milvus 向量操作总览（教学版）：先选集合，再跳转到该集合详情
// 这里提供一个"集合选择器 + 跳转到详情页"的教学入口
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { collectionsApi } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { vectorRecordDocs } from '@/lib/fieldDocs'

const router = useRouter()
const collections = ref<string[]>([])
const collection = ref('')
const loading = ref(false)

const demoVector = ref({
  id: 'demo_001',
  vector: '0.1, 0.2, 0.3, 0.4',
  payload: '{"category": "demo"}',
})

async function load() {
  loading.value = true
  try {
    const resp = await collectionsApi.list()
    if (resp.code === 0) collections.value = resp.data
  } catch (e: any) {
    ElMessage.error(e.message)
  } finally {
    loading.value = false
  }
}

function goto() {
  if (!collection.value) {
    ElMessage.warning('请先选集合')
    return
  }
  router.push(`/milvus/collections/${collection.value}`)
}

function parseVec() {
  try {
    return demoVector.value.vector.split(',').map((s) => Number(s.trim()))
  } catch {
    return []
  }
}

const parsedVec = () => {
  const arr = parseVec()
  return arr.length ? `[${arr.map((n) => Number(n).toFixed(3)).join(', ')}]` : '—'
}

onMounted(load)
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>向量（Vectors）</h2>
      <p class="desc">
        向量 = 实际存储的数据行（一条记录 = 1 个 id + 1 个 vector + N 个 payload 字段）。
        选一个集合进入后，可以插入 / 检索 / 拉取 / 删除 / 自动验证（教学闭环）。
      </p>
    </header>

    <el-row :gutter="16">
      <el-col :xs="24" :md="12">
        <el-card>
          <template #header><span>📋 选择集合进入</span></template>
          <el-form label-width="80px">
            <el-form-item label="集合">
              <el-select
                v-model="collection"
                placeholder="选集合"
                filterable
                style="width: 100%"
              >
                <el-option
                  v-for="c in collections"
                  :key="c"
                  :value="c"
                  :label="c"
                />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="goto">
                进入集合详情
              </el-button>
              <el-button @click="load">刷新列表</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="12">
        <el-card>
          <template #header><span>📐 单条向量结构</span></template>
          <el-form :model="demoVector" label-width="80px">
            <el-form-item label="id">
              <el-input v-model="demoVector.id" />
              <ParamHelp :doc="vectorRecordDocs.id" />
            </el-form-item>
            <el-form-item label="vector">
              <el-input v-model="demoVector.vector" />
              <ParamHelp :doc="vectorRecordDocs.vector" />
            </el-form-item>
            <el-form-item label="payload">
              <el-input
                v-model="demoVector.payload"
                type="textarea"
                :rows="2"
              />
              <ParamHelp :doc="vectorRecordDocs.payload" />
            </el-form-item>
            <el-form-item label="预览">
              <code class="preview">{{ parsedVec() }}</code>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <TutorialPanel slug="05-vectors" />
  </div>
</template>

<style scoped>
.page-inner { padding: 0; }
.page-header { margin-bottom: 16px; }
.page-header h2 { margin: 0 0 4px; font-size: 22px; }
.page-header .desc { margin: 0; color: #606266; font-size: 13px; }
.preview {
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 12px;
  background: #f0f9ff;
  padding: 4px 8px;
  border-radius: 3px;
}
</style>
