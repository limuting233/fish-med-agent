import http from '@/utils/request'

export type ConversationMessage = {
    role: 'user' | 'assistant' | 'tool' | (string & {})
    content: string
    created: string
    images?: (string | MessageImage)[] | null
    tool_calls?: unknown
    tool_call_id?: string
}

export type MessageImage = {
    object_key?: string
    content_type?: string
    extension?: string
    size?: number
    original_filename?: string | null
    previewUrl?: string
    name?: string
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
