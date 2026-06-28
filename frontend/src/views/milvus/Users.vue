<script setup lang="ts">
// Milvus 用户管理（教学版）
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usersApi, trackedCall, type ApiCall } from '@/api'
import ParamHelp from '@/components/ParamHelp.vue'
import ApiResponseViewer from '@/components/ApiResponseViewer.vue'
import TutorialPanel from '@/components/TutorialPanel.vue'
import { userDocs } from '@/lib/fieldDocs'

const users = ref<any[]>([])
const form = ref({ user_name: 'reader_01', password: 'P@ssw0rd!' })
const calls = ref<ApiCall[]>([])
const creating = ref(false)
const loadingList = ref(false)

async function load() {
  loadingList.value = true
  try {
    const { data, call } = await trackedCall('GET', '/api/v1/users')
    calls.value = [call]
    if (data.code === 0) users.value = data.data
    else ElMessage.error(data.message)
  } finally {
    loadingList.value = false
  }
}

async function create() {
  if (!form.value.user_name || !form.value.password) {
    ElMessage.warning('请填写用户名和密码')
    return
  }
  creating.value = true
  const { data, call } = await trackedCall('POST', '/api/v1/users', form.value)
  calls.value = [call]
  creating.value = false
  if (data.code === 0) {
    ElMessage.success(`已创建用户 ${form.value.user_name}`)
    form.value = { user_name: '', password: '' }
    await load()
  } else {
    ElMessage.error(data.message)
  }
}

async function drop(name: string) {
  try {
    await ElMessageBox.confirm(`确认删除用户 "${name}" 吗？`, '警告', {
      type: 'warning',
    })
  } catch {
    return
  }
  const { data, call } = await trackedCall('DELETE', `/api/v1/users/${name}`)
  calls.value = [call]
  if (data.code === 0) {
    ElMessage.success(`已删除 ${name}`)
    await load()
  } else {
    ElMessage.error(data.message)
  }
}

onMounted(load)
</script>

<template>
  <div class="page-inner">
    <header class="page-header">
      <h2>用户（Users）</h2>
      <p class="desc">
        Milvus 支持基于 RBAC 的用户管理。生产环境强烈建议开启用户 / 角色 / 权限，
        避免用 <code>root</code> 跑业务。
      </p>
    </header>

    <el-row :gutter="16">
      <el-col :xs="24" :md="10">
        <el-card>
          <template #header><span>➕ 创建用户</span></template>
          <el-form :model="form" label-width="80px">
            <el-form-item label="user_name">
              <el-input v-model="form.user_name" placeholder="字母开头" />
              <ParamHelp :doc="userDocs.user_name" />
            </el-form-item>
            <el-form-item label="password">
              <el-input v-model="form.password" type="password" show-password />
              <ParamHelp :doc="userDocs.password" />
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
              <span>📋 用户列表</span>
              <el-button text @click="load">刷新</el-button>
            </div>
          </template>
          <el-table v-loading="loadingList" :data="users" stripe empty-text="无用户">
            <el-table-column prop="user_name" label="用户名" />
            <el-table-column prop="roles" label="角色">
              <template #default="{ row }">
                <el-tag
                  v-for="r in (row.roles || [])"
                  :key="r"
                  size="small"
                  style="margin-right: 4px"
                >
                  {{ r }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" type="danger" @click="drop(row.user_name)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <TutorialPanel slug="09-users" />
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
