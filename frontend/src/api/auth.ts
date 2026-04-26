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

// complete login response json
export type LoginResponse = ApiResponse<LoginData>

// 登录请求函数
export function loginRequest(payload: LoginRequest): Promise<LoginResponse> {
    return http.post<LoginResponse>('/auth/login', payload, {
        skipAuth: true,
        rawResponse: true,
    })
}
