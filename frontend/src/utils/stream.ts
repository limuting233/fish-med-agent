import { useAuthStore } from '@/stores/auth'
import { RequestError } from '@/utils/request'

export type ChatStreamImageInput = {
    object_key: string
    content_type: string
    extension: string
    size: number
    original_filename?: string | null
    url?: string
    url_expires_at?: number
}

export type ChatStreamRequest = {
    conversation_id: number
    message: {
        content: string
        images?: ChatStreamImageInput[] | null
    }
}

export type StreamEventName = 'message.delta' | 'done' | 'error' | string

export type StreamEvent<T = unknown> = {
    event: StreamEventName
    data: T | null
    raw: string
}

export type MessageDeltaData = {
    content?: string
}

export type StreamHandlers = {
    onOpen?: (response: Response) => void
    onEvent?: (event: StreamEvent) => void
    onMessageDelta?: (content: string, event: StreamEvent<MessageDeltaData>) => void
    onDone?: (event: StreamEvent) => void
    onError?: (error: Error | RequestError, event?: StreamEvent) => void
    onClose?: () => void
}

export type StreamOptions = {
    endpoint?: string
    headers?: HeadersInit
    skipAuth?: boolean
    signal?: AbortSignal
}

export type StreamSession = {
    abort: () => void
    completed: Promise<void>
}

const DEFAULT_BASE_URL = '/api/v1'
const DEFAULT_STREAM_ENDPOINT = '/chat/stream'

function getBaseUrl() {
    return import.meta.env.VITE_API_BASE_URL || DEFAULT_BASE_URL
}

function getAccessToken() {
    const authStore = useAuthStore()
    return authStore.getAccessToken()
}

function buildStreamUrl(endpoint: string) {
    const baseUrl = getBaseUrl().replace(/\/$/, '')
    const path = endpoint.startsWith('/') ? endpoint : `/${endpoint}`

    return new URL(`${baseUrl}${path}`, window.location.origin).toString()
}

function mergeAbortSignals(controller: AbortController, signal?: AbortSignal) {
    if (!signal) {
        return
    }

    if (signal.aborted) {
        controller.abort(signal.reason)
        return
    }

    signal.addEventListener(
        'abort',
        () => {
            controller.abort(signal.reason)
        },
        { once: true },
    )
}

function parseEventBlock(block: string): StreamEvent {
    const normalizedBlock = block.replace(/\r\n/g, '\n').trim()
    const lines = normalizedBlock.split('\n')
    let event: StreamEventName = 'message'
    const dataLines: string[] = []

    lines.forEach((line) => {
        if (!line || line.startsWith(':')) {
            return
        }

        if (line.startsWith('event:')) {
            event = line.slice(6).trim() || 'message'
            return
        }

        if (line.startsWith('data:')) {
            dataLines.push(line.slice(5).trim())
        }
    })

    const rawData = dataLines.join('\n')
    let data: unknown = null

    if (rawData) {
        try {
            data = JSON.parse(rawData)
        } catch {
            data = rawData
        }
    }

    return {
        event,
        data,
        raw: normalizedBlock,
    }
}

async function parseErrorResponse(response: Response) {
    const contentType = response.headers.get('content-type') ?? ''

    if (contentType.includes('application/json')) {
        return response.json()
    }

    return response.text()
}

export function streamChat(
    payload: ChatStreamRequest,
    handlers: StreamHandlers = {},
    options: StreamOptions = {},
): StreamSession {
    const controller = new AbortController()
    const { endpoint = DEFAULT_STREAM_ENDPOINT, headers, skipAuth = false, signal } = options

    mergeAbortSignals(controller, signal)

    const completed = (async () => {
        const requestHeaders = new Headers(headers)
        const accessToken = getAccessToken()
        const authorization = requestHeaders.get('Authorization')

        requestHeaders.set('Accept', 'text/event-stream')
        requestHeaders.set('Content-Type', 'application/json')

        if (accessToken && !skipAuth && !authorization?.trim()) {
            requestHeaders.set('Authorization', `Bearer ${accessToken}`)
        }

        let streamErrorDispatched = false

        try {
            const response = await fetch(buildStreamUrl(endpoint), {
                method: 'POST',
                headers: requestHeaders,
                body: JSON.stringify(payload),
                signal: controller.signal,
            })

            if (!response.ok) {
                const errorPayload = await parseErrorResponse(response)
                throw new RequestError(
                    typeof errorPayload === 'object' && errorPayload && 'message' in errorPayload
                        ? String(errorPayload.message)
                        : response.statusText || 'Stream request failed',
                    {
                        status: response.status,
                        data: errorPayload,
                    },
                )
            }

            if (!response.body) {
                throw new RequestError('Stream response body is empty', { status: response.status })
            }

            handlers.onOpen?.(response)

            const reader = response.body.getReader()
            const decoder = new TextDecoder('utf-8')
            let buffer = ''

            while (true) {
                const { value, done } = await reader.read()

                if (done) {
                    buffer += decoder.decode()
                    break
                }

                buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

                let boundaryIndex = buffer.indexOf('\n\n')
                while (boundaryIndex !== -1) {
                    const block = buffer.slice(0, boundaryIndex)
                    buffer = buffer.slice(boundaryIndex + 2)

                    if (block.trim()) {
                        const event = parseEventBlock(block)
                        handlers.onEvent?.(event)

                        if (event.event === 'message.delta') {
                            const data = event.data as MessageDeltaData | null
                            if (typeof data?.content === 'string') {
                                handlers.onMessageDelta?.(data.content, event as StreamEvent<MessageDeltaData>)
                            }
                        }

                        if (event.event === 'done') {
                            handlers.onDone?.(event)
                        }

                        if (event.event === 'error') {
                            const data = event.data as { message?: string } | null
                            const streamError = new RequestError(data?.message || 'Stream error event received', {
                                status: 0,
                                data: event.data,
                            })
                            streamErrorDispatched = true
                            handlers.onError?.(streamError, event)
                            throw streamError
                        }
                    }

                    boundaryIndex = buffer.indexOf('\n\n')
                }
            }

            if (buffer.trim()) {
                const event = parseEventBlock(buffer)
                handlers.onEvent?.(event)

                if (event.event === 'message.delta') {
                    const data = event.data as MessageDeltaData | null
                    if (typeof data?.content === 'string') {
                        handlers.onMessageDelta?.(data.content, event as StreamEvent<MessageDeltaData>)
                    }
                }

                if (event.event === 'done') {
                    handlers.onDone?.(event)
                }

                if (event.event === 'error') {
                    const data = event.data as { message?: string } | null
                    const streamError = new RequestError(data?.message || 'Stream error event received', {
                        status: 0,
                        data: event.data,
                    })
                    streamErrorDispatched = true
                    handlers.onError?.(streamError, event)
                    throw streamError
                }
            }

            handlers.onClose?.()
        } catch (error) {
            if (controller.signal.aborted) {
                handlers.onClose?.()
                return
            }

            const streamError =
                error instanceof RequestError
                    ? error
                    : new RequestError(error instanceof Error ? error.message : 'Stream request failed', { status: 0 })

            if (!streamErrorDispatched) {
                handlers.onError?.(streamError)
            }
            throw streamError
        }
    })()

    return {
        abort: () => controller.abort(),
        completed,
    }
}

export default streamChat
