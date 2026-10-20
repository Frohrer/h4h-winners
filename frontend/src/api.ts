import type {
  HairType,
  Location,
  ProductDetail,
  ProductSummary,
  RecommendationRequest,
  RecommendationResponse,
  SimilarProduct,
} from './types'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, body?.detail ?? `Request failed (${res.status})`)
  }
  return res.json()
}

export const api = {
  hairTypes: () => request<HairType[]>('/api/hair-types'),

  searchProducts: (q: string, limit = 8) =>
    request<ProductSummary[]>(`/api/products?${new URLSearchParams({ q, limit: String(limit) })}`),

  productsByIds: (ids: string[]) => {
    if (ids.length === 0) return Promise.resolve([])
    const params = new URLSearchParams()
    ids.forEach((id) => params.append('ids', id))
    return request<ProductSummary[]>(`/api/products?${params}`)
  },

  product: (id: string) => request<ProductDetail>(`/api/products/${encodeURIComponent(id)}`),

  similarProducts: (id: string) =>
    request<SimilarProduct[]>(`/api/products/${encodeURIComponent(id)}/similar`),

  recommend: (body: RecommendationRequest) =>
    request<RecommendationResponse>('/api/recommendations', {
      method: 'POST',
      body: JSON.stringify(body),
    }),

  searchLocations: (q: string) => request<Location[]>(`/api/locations?${new URLSearchParams({ q })}`),
}
