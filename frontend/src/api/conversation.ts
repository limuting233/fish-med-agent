import http from '@/utils/request'

export type ConversationMessage = {
    role: 'user' | 'assistant'
    content: string
    created: string
    images?: Record<string, unknown>[] | null
}

export type Conversation = {
    id: number
    title: string
    user_id: number
    summary: string | null
    messages: ConversationMessage[] | null
    metadata_: Record<string, unknown> | null
    created_at: string
    updated_at: string
    deleted_at: string | null
}

// 获取对话列表
export function fetchConversationList() {
    return http.get<Conversation[]>('/conversation/list')
}
