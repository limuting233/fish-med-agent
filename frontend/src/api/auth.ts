import http from '@/utils/request'

// login request payload
export type LoginRequest = {
    username: string
    password: string
}

// login response payload
export type LoginResponse = {
    access_token: string
    token_type: string
    expires_in: number
}


// login request function
export function loginRequest(payload: LoginRequest): Promise<LoginResponse> {
    return http.post<LoginResponse>('/auth/login', payload)
}
