<script setup lang="ts">
// 集合管理主页：列表 + 创建
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { collectionsApi } from '@/api'

const router = useRouter()
interface CollectionRow { name: string }
const rows = ref<CollectionRow[]>([])
const loading = ref(false)
const creating = ref(false)
const form = ref({
  name: '',
  dimension: 4,
  metric: 'COSINE' as 'COSINE' | 'L2' | 'IP',
  description: '',
})

const load = async () => {
  loading.value = true
  try {
    const resp = await collectionsApi.list()
    if (resp.code === 0) rows.value = resp.data.map((name) => ({ name }))
    else ElMessage.error(resp.message)
  } catch (e: any) {
    ElMessage.error(e.message || '加载失败')
  } finally {
    loading.value = false
  }
}

const create = async () => {
  if (!form.value.name) {
    ElMessage.warning('请填写集合名称')
    return
  }
  creating.value = true
  try {
    const resp = await collectionsApi.create(form.value)
    if (resp.code === 0) {
      ElMessage.success(`已创建集合 ${resp.data.name}`)
      form.value.name = ''
      form.value.description = ''
      await load()
    } else {
      ElMessage.error(resp.message)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '创建失败')
  } finally {
    creating.value = false
  }
}

const remove = async (name: string) => {
  try {
    await ElMessageBox.confirm(`确认删除集合 "${name}" 吗？此操作不可恢复。`, '警告', {
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    const resp = await collectionsApi.remove(name)
    if (resp.code === 0) {
      ElMessage.success(`已删除 ${name}`)
      await load()
    } else {
      ElMessage.error(resp.message)
    }
  } catch (e: any) {
    ElMessage.error(e.message || '删除失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="page">
    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <el-card>
          <template #header>
            <span style="font-weight: 600">创建集合</span>
          </template>
          <el-form :model="form" label-width="80px" @submit.prevent>
            <el-form-item label="名称">
              <el-input v-model="form.name" placeholder="例如 demo" maxlength="255" />
            </el-form-item>
            <el-form-item label="维度">
              <el-input-number
                v-model="form.dimension"
                :min="1"
                :max="65536"
                style="width: 100%"
              />
            </el-form-item>
            <el-form-item label="度量">
              <el-select v-model="form.metric" style="width: 100%">
                <el-option label="COSINE（余弦相似度）" value="COSINE" />
                <el-option label="L2（欧氏距离）" value="L2" />
                <el-option label="IP（内积）" value="IP" />
              </el-select>
            </el-form-item>
            <el-form-item label="描述">
              <el-input
                v-model="form.description"
                type="textarea"
                :rows="2"
                placeholder="可选：集合用途说明"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="creating" @click="create">
                创建
              </el-button>
              <el-button @click="load">刷新列表</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="14">
        <el-card>
          <template #header>
            <div style="display: flex; align-items: center; gap: 8px">
              <span style="font-weight: 600">集合列表</span>
              <el-tag size="small">{{ rows.length }}</el-tag>
            </div>
          </template>
          <el-table
            v-loading="loading"
            :data="rows"
            stripe
            empty-text="暂无集合"
          >
            <el-table-column label="名称" min-width="180">
              <template #default="{ row }">
                <el-link type="primary" @click="router.push(`/collections/${row.name}`)">
                  {{ row.name }}
                </el-link>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button
                  size="small"
                  @click="router.push(`/collections/${row.name}`)"
                >
                  进入
                </el-button>
                <el-button size="small" type="danger" @click="remove(row.name)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
