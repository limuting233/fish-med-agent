import http, { type ApiResponse } from '@/utils/request'


// login request payload
export type LoginRequest = {
    username: string
    password: string
}

// login response data
export type LoginData = {
    access_token: string
    token_type: string
    expires_at: number  // 过期时间的毫秒级时间戳
}

export type UserInfo = {
    id: number
    username: string
    nickname: string | null
    email: string | null
    phone: string | null
    is_active: boolean
    last_login_at: string | null
    created_at: string
    updated_at: string
    deleted_at: string | null
}

// complete login response json
export type LoginResponse = ApiResponse<LoginData>

// 登录请求函数
export function loginRequest(payload: LoginRequest): Promise<LoginResponse> {
    return http.post<LoginResponse>('/auth/login', payload, {
        credentials: 'include',
        skipAuth: true,
        rawResponse: true,
    })
}

export function getCurrentUserRequest(): Promise<UserInfo> {
    return http.get<UserInfo>('/auth/me')
}
