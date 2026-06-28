// 统一 API 客户端：基于 axios + 当前后端 store
import axios, { type AxiosInstance } from 'axios'
import { useBackendStore } from '@/stores/backend'

let _instance: AxiosInstance | null = null

export function getClient(): AxiosInstance {
  if (_instance) return _instance
  const backend = useBackendStore()
  _instance = axios.create({
    baseURL: backend.current.baseUrl,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
  })

  // 响应拦截：直接返回 data 字段（业务层统一格式 { code, message, data }）
  // 错误时把后端 message 冒泡出来
  _instance.interceptors.response.use(
    (resp) => resp.data,
    (err) => {
      const body = err.response?.data
      const message = body?.message || err.message
      const code = body?.code || 'NETWORK_ERROR'
      return Promise.reject({ message, code, status: err.response?.status })
    },
  )

  // 后端切换时重建实例
  backend.$subscribe(() => {
    _instance = null
  })

  return _instance
}

/** 不走响应拦截的"裸"客户端（用于 ApiResponseViewer 教学展示完整状态码/headers） */
export function getRawClient(): AxiosInstance {
  const backend = useBackendStore()
  return axios.create({
    baseURL: backend.current.baseUrl,
    timeout: 30000,
    headers: { 'Content-Type': 'application/json' },
  })
}
