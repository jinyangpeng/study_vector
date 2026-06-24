// API 域聚合：与后端 OpenAPI 路径一一对应
import { getClient } from './client'

// 业务响应统一格式
export interface ApiResponse<T = unknown> {
  code: number | string
  message: string
  data: T
}

// 集合
export const collectionsApi = {
  list: () =>
    getClient().get<any, ApiResponse<string[]>>('/api/v1/collections'),
  create: (body: {
    name: string
    dimension: number
    metric?: string
    description?: string
  }) => getClient().post<any, ApiResponse<{ name: string }>>(
    '/api/v1/collections',
    body,
  ),
  info: (name: string) =>
    getClient().get<any, ApiResponse<any>>(`/api/v1/collections/${name}`),
  remove: (name: string) =>
    getClient().delete<any, ApiResponse<{ name: string }>>(
      `/api/v1/collections/${name}`,
    ),
}

// 向量
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
  delete: (collection: string, ids: string[]) =>
    getClient().post<any, ApiResponse<{ deleted: number }>>(
      `/api/v1/vectors/${collection}/delete`,
      { ids },
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
    },
  ) =>
    getClient().post<any, ApiResponse<any[]>>(
      `/api/v1/vectors/${collection}/search`,
      { ...body, collection },
    ),
}
