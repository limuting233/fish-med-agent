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

type TokenData = {
    access_token: string
    token_type: string
    expires_at: number
}

export class RequestError<T = unknown> extends Error {
    status: number
    code?: number
    requestId?: string
    data?: T

    constructor(
        message: string,
        options: {
            status: number
            code?: number
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
const DEFAULT_TIMEOUT = 30 * 1000  // 30秒超时
const REFRESH_TOKEN_PATH = '/auth/token/refresh'
const INVALID_ACCESS_TOKEN_CODE = 401002
const INVALID_REFRESH_TOKEN_CODE = 401003
let refreshTokenPromise: Promise<TokenData> | null = null


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

function isRefreshTokenRequest(url: string) {
    return url.includes(REFRESH_TOKEN_PATH)
}

function getApiCode(payload: unknown) {
    if (!payload || typeof payload !== 'object' || !('code' in payload)) {
        return undefined
    }

    const code = (payload as Partial<ApiResponse<unknown>>).code
    return typeof code === 'number' ? code : undefined
}

function redirectToLogin() {
    const authStore = useAuthStore()
    authStore.clearAccessToken()

    const currentPath = `${window.location.pathname}${window.location.search}${window.location.hash}`
    if (window.location.pathname === '/login') {
        return
    }

    window.location.replace(`/login?redirect=${encodeURIComponent(currentPath)}`)
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

async function refreshAccessTokenRequest() {
    const response = await fetch(buildUrl(REFRESH_TOKEN_PATH), {
        method: 'POST',
        credentials: 'include',
    })
    const payload = await parseResponse(response)
    const payloadCode = getApiCode(payload)

    if (payloadCode === INVALID_REFRESH_TOKEN_CODE) {
        redirectToLogin()
    }

    if (!response.ok) {
        const errorPayload = payload as Partial<ApiResponse<unknown>> | null

        throw new RequestError(errorPayload?.message || response.statusText || 'Refresh token failed', {
            status: response.status,
            code: errorPayload?.code,
            requestId: errorPayload?.request_id,
            data: payload,
        })
    }

    const apiPayload = payload as Partial<ApiResponse<TokenData>> | null

    const tokenData = apiPayload?.data

    if (!tokenData || apiPayload.code !== 200) {
        if (apiPayload?.code === INVALID_REFRESH_TOKEN_CODE) {
            redirectToLogin()
        }

        throw new RequestError(apiPayload?.message || 'Refresh token failed', {
            status: response.status,
            code: apiPayload?.code,
            requestId: apiPayload?.request_id,
            data: payload,
        })
    }

    const authStore = useAuthStore()
    authStore.setToken(tokenData.access_token, tokenData.expires_at)
    return tokenData
}

export async function refreshAccessToken() {
    if (!refreshTokenPromise) {
        refreshTokenPromise = refreshAccessTokenRequest().finally(() => {
            refreshTokenPromise = null
        })
    }

    return refreshTokenPromise
}

export async function request<T = unknown>(url: string, options: RequestOptions = {}): Promise<T> {
    const { params, timeout = DEFAULT_TIMEOUT, skipAuth = false, rawResponse = false, headers, body, ...requestInit } = options
    const controller = new AbortController()
    const timer = window.setTimeout(() => controller.abort(), timeout)
    const shouldUseAuth = !skipAuth && !isRefreshTokenRequest(url)

    try {
        if (shouldUseAuth && !getAccessToken()) {
            try {
                await refreshAccessToken()
            } catch (error) {
                const authStore = useAuthStore()
                authStore.clearAccessToken()
                if (error instanceof RequestError && error.code === INVALID_REFRESH_TOKEN_CODE) {
                    redirectToLogin()
                }
                throw error
            }
        }

        const send = async () => {
            const requestHeaders = new Headers(headers)
            const accessToken = getAccessToken()
            const authorization = requestHeaders.get('Authorization')

            if (accessToken && !skipAuth && !authorization?.trim()) {
                requestHeaders.set('Authorization', `Bearer ${accessToken}`)
            }

            return fetch(buildUrl(url, params), {
                ...requestInit,
                headers: requestHeaders,
                body: normalizeBody(body, requestHeaders),
                signal: controller.signal,
            })
        }

        let response = await send()
        let payload = await parseResponse(response)

        if (shouldUseAuth && getApiCode(payload) === INVALID_ACCESS_TOKEN_CODE) {
            try {
                await refreshAccessToken()
                response = await send()
                payload = await parseResponse(response)
            } catch (error) {
                const authStore = useAuthStore()
                authStore.clearAccessToken()
                if (error instanceof RequestError && error.code === INVALID_REFRESH_TOKEN_CODE) {
                    redirectToLogin()
                }
                throw error
            }
        }

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
