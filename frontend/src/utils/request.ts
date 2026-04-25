import { useAuthStore } from '@/stores/auth'

type QueryValue = string | number | boolean | null | undefined
type QueryParams = Record<string, QueryValue | QueryValue[]>
type JsonBody = Record<string, unknown> | unknown[]
type RequestBody = BodyInit | JsonBody | null | undefined

export type ApiResponse<T> = {
    code?: number
    message?: string
    request_id?: string
    data: T
}

export type RequestOptions = Omit<RequestInit, 'body'> & {
    params?: QueryParams
    body?: RequestBody
    timeout?: number
    skipAuth?: boolean
    rawResponse?: boolean
}

export type UploadOptions = Omit<RequestOptions, 'method' | 'body'> & {
    fileField?: string
    fields?: Record<string, QueryValue>
}

export class RequestError<T = unknown> extends Error {
    status: number
    code?: number | string
    requestId?: string
    data?: T

    constructor(
        message: string,
        options: {
            status: number
            code?: number | string
            requestId?: string
            data?: T
        },
    ) {
        super(message)
        this.name = 'RequestError'
        this.status = options.status
        this.code = options.code
        this.requestId = options.requestId
        this.data = options.data
    }
}

const DEFAULT_BASE_URL = '/api/v1'  // 默认基础URL
const DEFAULT_TIMEOUT = 10 * 60 * 1000  // 10分钟超时


// 获取基础URL
function getBaseUrl() {
    return import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
}


// 获取accessToken
function getAccessToken() {
    const authStore = useAuthStore()
    return authStore.getAccessToken()
}

// 构建URL
function buildUrl(url: string, params?: QueryParams) {
    const isAbsoluteUrl = /^https?:\/\//i.test(url)
    const baseUrl = getBaseUrl().replace(/\/$/, '')
    const path = url.startsWith('/') ? url : `/${url}`
    const requestUrl = new URL(isAbsoluteUrl ? url : `${baseUrl}${path}`, window.location.origin)

    if (params) {
        Object.entries(params).forEach(([key, value]) => {
            const values = Array.isArray(value) ? value : [value]

            values.forEach((item) => {
                if (item !== undefined && item !== null) {
                    requestUrl.searchParams.append(key, String(item))
                }
            })
        })
    }

    return requestUrl.toString()
}

function isJsonBody(body: RequestBody): body is JsonBody {
    if (!body || typeof body !== 'object') {
        return false
    }

    return !(body instanceof FormData) && !(body instanceof Blob) && !(body instanceof ArrayBuffer) && !(body instanceof URLSearchParams)
}

function normalizeBody(body: RequestBody, headers: Headers) {
    if (body === undefined || body === null) {
        return undefined
    }

    if (isJsonBody(body)) {
        if (!headers.has('Content-Type')) {
            headers.set('Content-Type', 'application/json')
        }

        return JSON.stringify(body)
    }

    return body as BodyInit
}



async function parseResponse(response: Response) {
    if (response.status === 204) {
        return null
    }

    const contentType = response.headers.get('content-type') ?? ''

    if (contentType.includes('application/json')) {
        return response.json()
    }

    return response.text()
}

export async function request<T = unknown>(url: string, options: RequestOptions = {}): Promise<T> {
    const { params, timeout = DEFAULT_TIMEOUT, skipAuth = false, rawResponse = false, headers, body, ...requestInit } = options
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), timeout)
    const requestHeaders = new Headers(headers)
    const accessToken = getAccessToken()
    const authorization = requestHeaders.get('Authorization')

    if (accessToken && !skipAuth && !authorization?.trim()) {
        requestHeaders.set('Authorization', `Bearer ${accessToken}`)
    }

    try {
        const response = await fetch(buildUrl(url, params), {
            ...requestInit,
            headers: requestHeaders,
            body: normalizeBody(body, requestHeaders),
            signal: controller.signal,
        })

        const payload = await parseResponse(response)

        if (!response.ok) {
            const errorPayload = payload as Partial<ApiResponse<unknown>> | null

            throw new RequestError(errorPayload?.message || response.statusText || 'Request failed', {
                status: response.status,
                code: errorPayload?.code,
                requestId: errorPayload?.request_id,
                data: payload,
            })
        }

        if (rawResponse) {
            return payload as T
        }

        const apiPayload = payload as Partial<ApiResponse<T>> | null

        if (apiPayload && typeof apiPayload === 'object' && 'data' in apiPayload) {
            if (apiPayload.code !== 200) {
                throw new RequestError(apiPayload.message || 'Request failed', {
                    status: response.status,
                    code: apiPayload.code,
                    requestId: apiPayload.request_id,
                    data: payload,
                })
            }

            return apiPayload.data as T
        }

        return payload as T
    } catch (error) {
        if (error instanceof RequestError) {
            throw error
        }

        if (error instanceof DOMException && error.name === 'AbortError') {
            throw new RequestError('Request timeout', { status: 0 })
        }

        throw new RequestError(error instanceof Error ? error.message : 'Network error', { status: 0 })
    } finally {
        window.clearTimeout(timer)
    }
}

function upload<T = unknown>(url: string, file: File | Blob, options: UploadOptions = {}) {
    const { fileField = 'file', fields, ...requestOptions } = options
    const formData = new FormData()

    formData.append(fileField, file)

    if (fields) {
        Object.entries(fields).forEach(([key, value]) => {
            if (value !== undefined && value !== null) {
                formData.append(key, String(value))
            }
        })
    }

    return request<T>(url, {
        ...requestOptions,
        method: 'POST',
        body: formData,
    })
}

function uploadForm<T = unknown>(url: string, formData: FormData, options: Omit<RequestOptions, 'body'> = {}) {
    return request<T>(url, {
        ...options,
        method: options.method ?? 'POST',
        body: formData,
    })
}

export const http = {
    request,
    get: <T = unknown>(url: string, options?: RequestOptions) => request<T>(url, { ...options, method: 'GET' }),
    post: <T = unknown>(url: string, body?: RequestBody, options?: RequestOptions) => request<T>(url, { ...options, method: 'POST', body }),
    put: <T = unknown>(url: string, body?: RequestBody, options?: RequestOptions) => request<T>(url, { ...options, method: 'PUT', body }),
    patch: <T = unknown>(url: string, body?: RequestBody, options?: RequestOptions) => request<T>(url, { ...options, method: 'PATCH', body }),
    delete: <T = unknown>(url: string, options?: RequestOptions) => request<T>(url, { ...options, method: 'DELETE' }),
    upload,
    uploadForm,
}

export default http
