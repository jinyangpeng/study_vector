<script setup lang="ts">
// ApiResponseViewer：tabbed 视图展示 API 原始请求/响应
// 教学目的：让用户看清"我们到底发了什么，收到了什么"
import { ref, computed } from 'vue'

interface ApiCall {
  method: string
  url: string
  body?: any
  status?: number
  response?: any
  durationMs?: number
  error?: string
}

const props = defineProps<{
  calls: ApiCall[] // 一个操作可能产生多个调用（如 insert + 自动 query 验证）
}>()

const activeTab = ref('request')
const activeIndex = ref(0)

const currentCall = computed(() => props.calls[activeIndex.value] || ({} as ApiCall))

const formatJson = (data: any) => {
  if (data === undefined || data === null) return ''
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

const requestPreview = computed(() => {
  const c = currentCall.value
  if (!c) return ''
  const lines = [`${c.method} ${c.url}`]
  if (c.body !== undefined) lines.push('', formatJson(c.body))
  return lines.join('\n')
})

const responsePreview = computed(() => {
  const c = currentCall.value
  if (!c) return ''
  if (c.error) return c.error
  return formatJson(c.response)
})

const statusColor = computed(() => {
  const s = currentCall.value?.status
  if (s === undefined) return ''
  if (s >= 200 && s < 300) return '#67c23a'
  if (s >= 400 && s < 500) return '#e6a23c'
  return '#f56c6c'
})
</script>

<template>
  <div v-if="calls.length" class="api-viewer">
    <div class="header">
      <span class="title">📡 API 调用记录</span>
      <el-radio-group v-model="activeIndex" size="small">
        <el-radio-button
          v-for="(c, i) in calls"
          :key="i"
          :label="i"
        >
          #{{ i + 1 }} {{ c.method }}
          <span
            v-if="c.status"
            class="status-dot"
            :style="{ background: c.status >= 200 && c.status < 300 ? '#67c23a' : c.status >= 400 && c.status < 500 ? '#e6a23c' : '#f56c6c' }"
          />
        </el-radio-button>
      </el-radio-group>
    </div>

    <el-tabs v-model="activeTab" class="api-tabs">
      <el-tab-pane label="请求" name="request">
        <pre class="code">{{ requestPreview }}</pre>
      </el-tab-pane>
      <el-tab-pane label="响应" name="response">
        <div class="meta">
          <span v-if="currentCall.status !== undefined">
            状态：<code :style="{ color: statusColor, fontWeight: 600 }">{{ currentCall.status }}</code>
          </span>
          <span v-if="currentCall.durationMs !== undefined">
            耗时：<code>{{ currentCall.durationMs }}ms</code>
          </span>
        </div>
        <pre class="code">{{ responsePreview }}</pre>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.api-viewer {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fafbfc;
  margin-top: 12px;
  overflow: hidden;
}
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  border-bottom: 1px solid #e4e7ed;
  background: #fff;
}
.title {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
}
.api-tabs {
  padding: 0 12px;
}
.api-tabs :deep(.el-tabs__header) {
  margin: 0;
}
.api-tabs :deep(.el-tabs__content) {
  padding: 8px 0;
}
.code {
  margin: 0;
  padding: 12px;
  background: #1e1e1e;
  color: #d4d4d4;
  border-radius: 4px;
  font-family: 'JetBrains Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 12px;
  line-height: 1.5;
  max-height: 320px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.meta {
  display: flex;
  gap: 16px;
  margin-bottom: 8px;
  font-size: 13px;
  color: #606266;
}
.meta code {
  background: #f0f9ff;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: 'JetBrains Mono', Consolas, monospace;
}
.status-dot {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-left: 4px;
}
</style>
