// API 域聚合：与后端 OpenAPI 路径一一对应
import { getClient, getRawClient } from './client'

// 业务响应统一格式
export interface ApiResponse<T = unknown> {
  code: number | string
  message: string
  data: T
}

// 跟踪 API 调用的辅助工具（用于 ApiResponseViewer 教学展示）
export interface ApiCall {
  method: string
  url: string
  body?: any
  status?: number
  response?: any
  durationMs?: number
  error?: string
}

/** 带跟踪的请求封装：返回完整响应（status / data / headers） */
export async function trackedCall<T = any>(
  method: string,
  url: string,
  body?: any,
): Promise<{ data: ApiResponse<T>; call: ApiCall }> {
  const t0 = Date.now()
  const call: ApiCall = { method, url, body }
  try {
    const resp = await getRawClient().request({
      method: method as any,
      url,
      data: body,
    })
    call.status = resp.status
    call.response = resp.data
    call.durationMs = Date.now() - t0
    return { data: resp.data as ApiResponse<T>, call }
  } catch (err: any) {
    call.status = err.response?.status
    call.response = err.response?.data
    call.error = err.response?.data?.message || err.message
    call.durationMs = Date.now() - t0
    return { data: err.response?.data as any, call }
  }
}

// ============ Collections ============
export const collectionsApi = {
  list: () =>
    getClient().get<any, ApiResponse<string[]>>('/api/v1/collections'),
  create: (body: {
    name: string
    dimension: number
    metric?: string
    vector_type?: string
    description?: string
    primary_field?: string
    vector_field?: string
    index_type?: string
    consistency_level?: string
  }) =>
    getClient().post<any, ApiResponse<{ name: string }>>(
      '/api/v1/collections',
      body,
    ),
  info: (name: string) =>
    getClient().get<any, ApiResponse<any>>(`/api/v1/collections/${name}`),
  remove: (name: string) =>
    getClient().delete<any, ApiResponse<{ name: string }>>(
      `/api/v1/collections/${name}`,
    ),
  load: (name: string, body?: any) =>
    getClient().post<any, ApiResponse<{ name: string; loaded: boolean }>>(
      `/api/v1/collections/${name}/load`,
      body,
    ),
  release: (name: string) =>
    getClient().post<any, ApiResponse<{ name: string; loaded: boolean }>>(
      `/api/v1/collections/${name}/release`,
    ),
}

// ============ Vectors ============
export const vectorsApi = {
  insert: (collection: string, records: any[]) =>
    getClient().post<any, ApiResponse<{ ids: any[]; count: number }>>(
      `/api/v1/vectors/${collection}/insert`,
      records,
    ),
  upsert: (collection: string, records: any[]) =>
    getClient().post<any, ApiResponse<{ ids: any[]; count: number }>>(
      `/api/v1/vectors/${collection}/upsert`,
      records,
    ),
  delete: (collection: string, body: { ids?: string[]; filter?: any }) =>
    getClient().post<any, ApiResponse<{ deleted: number }>>(
      `/api/v1/vectors/${collection}/delete`,
      body,
    ),
  get: (collection: string, ids: string[]) =>
    getClient().post<any, ApiResponse<any[]>>(
      `/api/v1/vectors/${collection}/get`,
      { ids },
    ),
  search: (
    collection: string,
    body: {
      vector: number[]
      top_k: number
      filter_expr?: Record<string, any>
      output_fields?: string[]
      partition_names?: string[]
    },
  ) =>
    getClient().post<any, ApiResponse<any[]>>(
      `/api/v1/vectors/${collection}/search`,
      { ...body, collection },
    ),
  query: (collection: string, body: any) =>
    getClient().post<any, ApiResponse<any>>(
      `/api/v1/vectors/${collection}/query`,
      { ...body, collection },
    ),
  hybrid_search: (collection: string, body: any) =>
    getClient().post<any, ApiResponse<any[]>>(
      `/api/v1/vectors/${collection}/hybrid_search`,
      { ...body, collection },
    ),
}

// ============ Indexes ============
export const indexesApi = {
  create: (collection: string, body: any) =>
    getClient().post<any, ApiResponse<any>>(
      `/api/v1/collections/${collection}/indexes`,
      body,
    ),
  list: (collection: string) =>
    getClient().get<any, ApiResponse<any[]>>(
      `/api/v1/collections/${collection}/indexes`,
    ),
  drop: (collection: string, fieldName: string) =>
    getClient().delete<any, ApiResponse<any>>(
      `/api/v1/collections/${collection}/indexes/${fieldName}`,
    ),
}

// ============ Partitions ============
export const partitionsApi = {
  list: (collection: string) =>
    getClient().get<any, ApiResponse<any[]>>(
      `/api/v1/collections/${collection}/partitions`,
    ),
  create: (collection: string, name: string) =>
    getClient().post<any, ApiResponse<any>>(
      `/api/v1/collections/${collection}/partitions`,
      { name },
    ),
  drop: (collection: string, name: string) =>
    getClient().delete<any, ApiResponse<any>>(
      `/api/v1/collections/${collection}/partitions/${name}`,
    ),
}

// ============ Alias ============
export const aliasApi = {
  list: (collection: string) =>
    getClient().get<any, ApiResponse<string[]>>(
      `/api/v1/collections/${collection}/alias`,
    ),
  create: (collection: string, alias: string) =>
    getClient().post<any, ApiResponse<any>>(
      `/api/v1/collections/${collection}/alias`,
      { alias },
    ),
  drop: (collection: string, alias: string) =>
    getClient().delete<any, ApiResponse<any>>(
      `/api/v1/collections/${collection}/alias/${alias}`,
    ),
}

// ============ Databases ============
export const databasesApi = {
  list: () =>
    getClient().get<any, ApiResponse<string[]>>('/api/v1/databases'),
  create: (name: string) =>
    getClient().post<any, ApiResponse<any>>('/api/v1/databases', { name }),
  drop: (name: string) =>
    getClient().delete<any, ApiResponse<any>>(`/api/v1/databases/${name}`),
}

// ============ Users ============
export const usersApi = {
  list: () => getClient().get<any, ApiResponse<any[]>>('/api/v1/users'),
  create: (user_name: string, password: string) =>
    getClient().post<any, ApiResponse<any>>('/api/v1/users', {
      user_name,
      password,
    }),
  drop: (user_name: string) =>
    getClient().delete<any, ApiResponse<any>>(`/api/v1/users/${user_name}`),
}

// ============ Health ============
export const healthApi = {
  liveness: () =>
    getClient().get<any, ApiResponse<any>>('/api/v1/health'),
  readiness: () =>
    getClient().get<any, ApiResponse<any>>('/api/v1/health/ready'),
}
