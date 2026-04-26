import http from '@/utils/request'

export type LoginRequest = {
    username: string
    password: string
}

export type LoginResponse = {
    access_token: string
    token_type: string
    expires_in: number
}

export function loginRequest(payload: LoginRequest): Promise<LoginResponse> {
    return http.post<LoginResponse>('/auth/login', payload)
}
