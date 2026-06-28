<script setup lang="ts">
// Milvus Alias 管理（教学版）
// 业务代码访问 alias；底层集合升级/迁移时切换 alias 即可，业务无感
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { collectionsApi, aliasApi, trackedCall, type ApiCall } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { aliasDocs } from '@/lib/fieldDocs'

const collections = ref<string[]>([])
const collection = ref('')
const aliases = ref<string[]>([])
const newAlias = ref('docs_latest')
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

async function loadAliases() {
  if (!collection.value) {
    aliases.value = []
    return
  }
  loadingList.value = true
  try {
    const resp = await aliasApi.list(collection.value)
    if (resp.code === 0) aliases.value = resp.data
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
  if (!newAlias.value) {
    ElMessage.warning('请输入别名')
    return
  }
  creating.value = true
  const { data, call } = await trackedCall(
    'POST',
    `/api/v1/collections/${collection.value}/alias`,
    { alias: newAlias.value },
  )
  calls.value = [call]
  creating.value = false
  if (data.code === 0) {
    ElMessage.success(`已为 ${collection.value} 创建 alias ${newAlias.value}`)
    newAlias.value = ''
    await loadAliases()
  } else {
    ElMessage.error(data.message)
  }
}

async function drop(name: string) {
  try {
    await ElMessageBox.confirm(
      `确认删除 alias "${name}" 吗？`,
      '警告',
      { type: 'warning' },
    )
  } catch {
    return
  }
  const { data, call } = await trackedCall(
    'DELETE',
    `/api/v1/collections/${collection.value}/alias/${name}`,
  )
  calls.value = [call]
  if (data.code === 0) {
    ElMessage.success(`已删除 alias ${name}`)
    await loadAliases()
  } else {
    ElMessage.error(data.message)
  }
}

watch(collection, () => loadAliases())
onMounted(async () => {
  await loadCollections()
  await loadAliases()
})
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>别名（Aliases）</h2>
      <p class="desc">
        别名 = 集合的"逻辑名"。业务代码访问 alias，底层可以切换 alias 指向不同集合，<b>业务无感知</b>。
        经典用法：蓝绿部署、灰度切换、版本回滚。
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
          <template #header><span>➕ 创建 alias</span></template>
          <el-form label-width="80px">
            <el-form-item label="alias">
              <el-input v-model="newAlias" placeholder="如 docs_latest" />
              <ParamHelp :doc="aliasDocs.alias" />
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
              <span>📋 集合的 aliases</span>
              <el-tag size="small">{{ aliases.length }} 个</el-tag>
            </div>
          </template>
          <div v-loading="loadingList" class="alias-list">
            <el-tag
              v-for="a in aliases"
              :key="a"
              type="info"
              size="large"
              closable
              class="alias-tag"
              @close="drop(a)"
            >
              {{ a }}
            </el-tag>
            <div v-if="!aliases.length" class="empty-tip">无 alias</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <TutorialPanel slug="07-aliases" />
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
.alias-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 0;
  min-height: 60px;
}
.alias-tag {
  font-family: 'JetBrains Mono', Consolas, monospace;
}
.empty-tip {
  color: #909399;
  font-size: 13px;
  padding: 8px;
}
</style>
