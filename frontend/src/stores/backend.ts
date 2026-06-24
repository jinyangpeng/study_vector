// 后端切换 store：管理多个语言后端实例
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Backend {
  name: string
  baseUrl: string
  language: 'python' | 'go' | 'node' | string
}

export const useBackendStore = defineStore('backend', () => {
  // 默认指向本地 Python 后端；用户可切换至其他语言后端
  // 注意：开发态下若 Vite proxy 在某些平台（Windows 双栈）不稳定，
  // 可切换为 "Python FastAPI (Docker)" 走 nginx 反代，或保持当前绝对 URL
  const backends = ref<Backend[]>([
    { name: 'Python FastAPI (本机直接)', baseUrl: 'http://127.0.0.1:8000', language: 'python' },
    { name: 'Python FastAPI (同源 nginx)', baseUrl: '', language: 'python' },
    // 未来扩展示例：
    // { name: 'Go Gin (本机)', baseUrl: 'http://127.0.0.1:8001', language: 'go' },
    // { name: 'Node Express (本机)', baseUrl: 'http://127.0.0.1:8002', language: 'node' },
  ])

  // 当前后端：默认第一个
  const current = ref<Backend>(backends.value[0])
  const select = (b: Backend) => {
    current.value = b
  }

  return { backends, current, select }
})
