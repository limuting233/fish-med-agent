<script lang="ts" setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Clock, FileImage, LogOut, MessageCircle, Mic, MoreHorizontal, PanelLeft, Paperclip, Plus, Search, SendHorizontal, Sparkles, X } from 'lucide-vue-next'
import MarkdownIt from 'markdown-it'
import { useRouter } from 'vue-router'
import { toast } from 'vue-sonner'
import { getCurrentUserRequest } from '@/api/auth'
import { fetchConversationList, type Conversation, type ConversationMessage, type MessageImage } from '@/api/conversation'
import { deleteImage, uploadImage, type UploadedImage } from '@/api/upload'
import { useAuthStore } from '@/stores/auth'
import { streamChat, type StreamSession } from '@/utils/stream'

type ConversationGroup = 'today' | 'week' | 'earlier'

type Attachment = {
    id: string
    name: string
    size: string
    file: File
    type: 'image'
    previewUrl?: string
    status?: 'pending' | 'uploading' | 'uploaded' | 'deleting'
    objectKey?: string
    uploadedImage?: UploadedImage
    error?: string
}

type MessageImageView = {
    id: string
    name: string
    previewUrl?: string
    objectKey?: string
    size?: number
}

const MAX_IMAGE_ATTACHMENTS = 6
const sidebarOpen = ref(false)
const sidebarCollapsed = ref(false)
const authStore = useAuthStore()
const router = useRouter()
const selectedConversationId = ref<number>(0)
const draftMessage = ref('')
const messageInputComposing = ref(false)
const fileInput = ref<HTMLInputElement | null>(null)
const messagePane = ref<HTMLElement | null>(null)
const pendingAttachments = ref<Attachment[]>([])
const activeImageUploadCount = ref(0)
const activeImageDeleteCount = ref(0)
const uploadQueue: Attachment[] = []
let uploadQueueRunning = false
const searchOpen = ref(false)
const logoutDialogOpen = ref(false)
const searchQuery = ref('')
const searchDialogInput = ref<HTMLInputElement | null>(null)
const conversationListLoading = ref(false)
const conversationListError = ref('')
const responseGenerating = ref(false)
let activeStream: {
    session: StreamSession
    conversationId: number
    assistantMessageIndex: number
    token: string
} | null = null

const conversations = ref<Conversation[]>([])

const samplePrompts = ['鱼体表白点', '鳃部发红', '鱼群浮头']
const markdown = new MarkdownIt({
    html: false,
    breaks: true,
    linkify: true,
})

const groupedConversations = computed(() =>
    [
        {
            label: '今天',
            items: conversations.value.filter((conversation) => getConversationGroup(getConversationActiveDate(conversation)) === 'today'),
        },
        {
            label: '最近 7 天',
            items: conversations.value.filter((conversation) => getConversationGroup(getConversationActiveDate(conversation)) === 'week'),
        },
        {
            label: '更早',
            items: conversations.value.filter((conversation) => getConversationGroup(getConversationActiveDate(conversation)) === 'earlier'),
        },
    ].filter((group) => group.items.length > 0),
)

const activeConversation = computed<Conversation | null>(() => {
    return conversations.value.find((conversation) => conversation.id === selectedConversationId.value) ?? null
})

const activeConversationTitle = computed(() => {
    return activeConversation.value ? activeConversation.value.title.trim() : '新的鱼病问诊'
})

const activeMessages = computed(() => activeConversation.value?.messages ?? [])
const imagesUploading = computed(() => activeImageUploadCount.value > 0)
const imagesDeleting = computed(() => activeImageDeleteCount.value > 0)
const imagesBusy = computed(() => imagesUploading.value || imagesDeleting.value)
const attachmentsReady = computed(() => pendingAttachments.value.every((attachment) => attachment.status === 'uploaded'))

// 是否可以发送消息，有文本的情况下才允许发送
const canSend = computed(() => {
    return draftMessage.value.trim().length > 0 && !responseGenerating.value && !imagesBusy.value && attachmentsReady.value
})

const searchResults = computed(() => {
    const query = searchQuery.value.trim().toLowerCase()

    if (!query) {
        return conversations.value
    }

    return conversations.value.filter((conversation) => {
        return [getConversationTitle(conversation), getConversationSummary(conversation), getConversationTime(conversation)].some((value) => value.toLowerCase().includes(query))
    })
})

const hasConversations = computed(() => conversations.value.length > 0)
const userNickname = computed(() => authStore.nickname || authStore.username || '鱼病问诊用户')
const userUsername = computed(() => (authStore.username ? `@${authStore.username}` : '@fish-med-user'))
const userInitial = computed(() => Array.from(userNickname.value.trim() || authStore.username.trim() || 'F')[0]?.toUpperCase() ?? 'F')

function toggleSidebar() {
    if (window.matchMedia('(max-width: 900px)').matches) {
        sidebarOpen.value = !sidebarOpen.value
        return
    }

    sidebarCollapsed.value = !sidebarCollapsed.value
}

async function loadCurrentUser() {
    try {
        const user = await getCurrentUserRequest()
        authStore.setUserProfile({
            username: user.username,
            nickname: user.nickname,
            isActive: user.is_active,
        })
    } catch {
        // The sidebar keeps the login username fallback if profile loading is unavailable.
    }
}

async function loadConversationList() {
    conversationListLoading.value = true
    conversationListError.value = ''

    try {
        const list = await fetchConversationList()
        conversations.value = list

        const selectedExists = conversations.value.some((conversation) => conversation.id === selectedConversationId.value)
        selectedConversationId.value = selectedExists ? selectedConversationId.value : (conversations.value[0]?.id ?? 0)
        scrollToBottom()
    } catch (error) {
        conversationListError.value = error instanceof Error ? error.message : '历史对话加载失败'
    } finally {
        conversationListLoading.value = false
    }
}

function getConversationTitle(conversation: Conversation) {
    return conversation.title.trim() || '新的鱼病问诊'
}

function getConversationSummary(conversation: Conversation) {
    const lastContent = getMessageContent(getLastMessage(conversation.messages))
    return conversation.summary?.trim() || lastContent.slice(0, 24) || '暂无消息'
}

function getConversationTime(conversation: Conversation) {
    return formatConversationTime(getConversationActiveDate(conversation))
}

function getConversationActiveDate(conversation: Conversation) {
    return parseDate(getMetadataDate(conversation, 'last_message_at')) ?? new Date()
}

function getLastMessage(messages: Conversation['messages']) {
    return messages?.[messages.length - 1]
}

function getMessageContent(message?: ConversationMessage) {
    return message?.content ?? ''
}

function renderAssistantMarkdown(content: string) {
    return markdown.render(content || '正在分析...')
}

function getMetadataDate(conversation: Conversation, key: string) {
    const value = conversation.metadata_?.[key]
    return typeof value === 'string' ? value : ''
}

function parseDate(value: string | null | undefined) {
    if (!value) {
        return null
    }

    const date = new Date(value)
    return Number.isNaN(date.getTime()) ? null : date
}

function getConversationGroup(date: Date): ConversationGroup {
    const today = startOfDay(new Date())
    const target = startOfDay(date)
    const diffDays = Math.floor((today.getTime() - target.getTime()) / (24 * 60 * 60 * 1000))

    if (diffDays <= 0) {
        return 'today'
    }

    return diffDays < 7 ? 'week' : 'earlier'
}

function formatConversationTime(date: Date) {
    const today = startOfDay(new Date())
    const target = startOfDay(date)
    const diffDays = Math.floor((today.getTime() - target.getTime()) / (24 * 60 * 60 * 1000))

    if (diffDays <= 0) {
        return formatTime(date)
    }

    if (diffDays === 1) {
        return '昨天'
    }

    if (diffDays < 7) {
        return date.toLocaleDateString('zh-CN', { weekday: 'short' })
    }

    if (date.getFullYear() === new Date().getFullYear()) {
        return `${date.getMonth() + 1}月${date.getDate()}日`
    }

    return `${date.getFullYear()}/${date.getMonth() + 1}/${date.getDate()}`
}

function startOfDay(date: Date) {
    return new Date(date.getFullYear(), date.getMonth(), date.getDate())
}

function selectConversation(conversationId: number) {
    selectedConversationId.value = conversationId
    sidebarOpen.value = false
}

function openSearch() {
    searchOpen.value = true
    void nextTick(() => {
        searchDialogInput.value?.focus()
    })
}

function closeSearch() {
    searchOpen.value = false
    searchQuery.value = ''
}

function openLogoutDialog() {
    logoutDialogOpen.value = true
}

function closeLogoutDialog() {
    logoutDialogOpen.value = false
}

function confirmLogout() {
    abortActiveStream('已停止生成。')
    authStore.clearAccessToken()
    sidebarOpen.value = false
    logoutDialogOpen.value = false
    void router.replace('/login')
}

function selectSearchResult(conversationId: number) {
    selectConversation(conversationId)
    closeSearch()
}

function createConversation() {
    abortActiveStream('已停止生成。')
    selectedConversationId.value = 0
    draftMessage.value = ''
    clearPendingAttachments()
    sidebarOpen.value = false
}



function createPendingConversation() {
    const id =
        conversations.value.reduce((maxId, conversation) => {
            return Math.max(maxId, conversation.id)
        }, 0) + 1

    const nowIso = new Date().toISOString()
    const conversation: Conversation = {
        id,
        title: '新的鱼病问诊',
        user_id: 0,
        summary: '等待症状描述与图片',
        messages: [],
        metadata_: {
            last_message_at: nowIso,
        },
        created_at: nowIso,
        updated_at: nowIso,
        deleted_at: null,
    }

    selectedConversationId.value = id
    return conversation
}

function choosePrompt(prompt: string) {
    draftMessage.value = prompt
}

function handleMessageInputCompositionStart() {
    messageInputComposing.value = true
}

function handleMessageInputCompositionEnd() {
    messageInputComposing.value = false
}

function handleMessageInputKeydown(event: KeyboardEvent) {
    if (event.key !== 'Enter' || event.shiftKey || event.metaKey || event.ctrlKey || event.altKey) {
        return
    }

    if (event.isComposing || messageInputComposing.value || event.keyCode === 229) {
        return
    }

    event.preventDefault()
    sendMessage()
}

function openFilePicker() {
    fileInput.value?.click()
}

function handleFileChange(event: Event) {
    const input = event.target as HTMLInputElement
    const selectedFiles = Array.from(input.files ?? [])
    const imageFiles = selectedFiles.filter((file) => file.type.startsWith('image/'))
    const availableSlots = Math.max(0, MAX_IMAGE_ATTACHMENTS - pendingAttachments.value.length)

    if (imageFiles.length < selectedFiles.length) {
        toast.warning('只能上传图片文件')
    }

    if (imageFiles.length > availableSlots) {
        toast.warning(`最多上传 ${MAX_IMAGE_ATTACHMENTS} 张图片`)
    }

    imageFiles.slice(0, availableSlots).forEach((file) => {
        const attachment: Attachment = {
            id: createId('attachment'),
            name: file.name,
            size: formatFileSize(file.size),
            file,
            type: 'image',
            previewUrl: URL.createObjectURL(file),
            status: 'pending',
        }

        pendingAttachments.value.push(attachment)
        uploadQueue.push(attachment)
    })

    void processUploadQueue()
    input.value = ''
}

async function removePendingAttachment(attachmentId: string) {
    const attachment = pendingAttachments.value.find((item) => item.id === attachmentId)
    if (!attachment || attachment.status === 'deleting') {
        return
    }

    if (attachment.status !== 'uploaded' || !attachment.objectKey) {
        removeFromUploadQueue(attachment.id)
        removePendingAttachmentLocally(attachment)
        return
    }

    activeImageDeleteCount.value += 1
    updatePendingAttachment(attachment.id, { status: 'deleting', error: undefined })

    try {
        await deleteImage(attachment.objectKey)
        removePendingAttachmentLocally(attachment)
    } catch (error) {
        const message = error instanceof Error ? error.message : '图片删除失败'
        toast.error(message || '图片删除失败')
        updatePendingAttachment(attachment.id, {
            status: 'uploaded',
            error: undefined,
        })
    } finally {
        activeImageDeleteCount.value = Math.max(0, activeImageDeleteCount.value - 1)
    }
}

function removePendingAttachmentLocally(attachment: Attachment) {
    if (attachment.previewUrl) {
        URL.revokeObjectURL(attachment.previewUrl)
    }

    pendingAttachments.value = pendingAttachments.value.filter((item) => item.id !== attachment.id)
    removeFromUploadQueue(attachment.id)
}

function removeFromUploadQueue(attachmentId: string) {
    const index = uploadQueue.findIndex((attachment) => attachment.id === attachmentId)

    if (index !== -1) {
        uploadQueue.splice(index, 1)
    }
}

function clearPendingAttachments(options: { revokePreviews?: boolean } = { revokePreviews: true }) {
    if (options.revokePreviews !== false) {
        pendingAttachments.value.forEach((attachment) => {
            if (attachment.previewUrl) {
                URL.revokeObjectURL(attachment.previewUrl)
            }
        })
    }

    pendingAttachments.value = []
    uploadQueue.splice(0, uploadQueue.length)
}

function updatePendingAttachment(attachmentId: string, patch: Partial<Attachment>) {
    pendingAttachments.value = pendingAttachments.value.map((attachment) => {
        if (attachment.id !== attachmentId) {
            return attachment
        }

        return {
            ...attachment,
            ...patch,
        }
    })
}

function getAttachmentStatusText(attachment: Attachment) {
    if (attachment.status === 'uploading') {
        return '上传中'
    }

    if (attachment.status === 'uploaded') {
        return '已上传'
    }

    if (attachment.status === 'deleting') {
        return '删除中'
    }

    return attachment.size
}

async function uploadAttachment(attachment: Attachment) {
    activeImageUploadCount.value += 1
    updatePendingAttachment(attachment.id, { status: 'uploading' })

    try {
        const uploadedImage = await uploadImage(attachment.file)
        if (!pendingAttachments.value.some((item) => item.id === attachment.id)) {
            return
        }

        updatePendingAttachment(attachment.id, {
            status: 'uploaded',
            objectKey: uploadedImage.object_key,
            uploadedImage,
            error: undefined,
        })
    } catch (error) {
        if (!pendingAttachments.value.some((item) => item.id === attachment.id)) {
            return
        }

        const message = error instanceof Error ? error.message : '图片上传失败'
        removePendingAttachmentLocally(attachment)
        toast.error(message || '图片上传失败')
    } finally {
        activeImageUploadCount.value = Math.max(0, activeImageUploadCount.value - 1)
    }
}

async function processUploadQueue() {
    if (uploadQueueRunning) {
        return
    }

    uploadQueueRunning = true

    try {
        while (uploadQueue.length > 0) {
            const attachment = uploadQueue.shift()
            if (!attachment || !pendingAttachments.value.some((item) => item.id === attachment.id)) {
                continue
            }

            await uploadAttachment(attachment)
        }
    } finally {
        uploadQueueRunning = false
    }
}

function createMessageImages(attachments: Attachment[], uploadedImages: UploadedImage[]): MessageImage[] {
    return attachments.map((attachment, index) => {
        const uploadedImage = uploadedImages[index]

        return {
            object_key: uploadedImage?.object_key,
            content_type: uploadedImage?.content_type,
            extension: uploadedImage?.extension,
            size: uploadedImage?.size ?? attachment.file.size,
            original_filename: uploadedImage?.original_filename ?? attachment.name,
            previewUrl: attachment.previewUrl,
            name: attachment.name,
        }
    })
}

function getMessageImages(message: ConversationMessage): MessageImageView[] {
    return (message.images ?? []).map((image, index) => {
        if (typeof image === 'string') {
            return {
                id: `${message.created}-image-${index}`,
                name: image.split('/').pop() || '图片',
                objectKey: image,
            }
        }

        const objectKey = image.object_key
        return {
            id: `${message.created}-image-${index}`,
            name: image.name || image.original_filename || objectKey?.split('/').pop() || '图片',
            previewUrl: image.previewUrl,
            objectKey,
            size: image.size,
        }
    })
}

function revokeConversationPreviewUrls() {
    conversations.value.forEach((conversation) => {
        const messages = conversation.messages ?? []

        messages.forEach((message) => {
            const images = message.images ?? []

            images.forEach((image) => {
                if (typeof image !== 'string' && image.previewUrl) {
                    URL.revokeObjectURL(image.previewUrl)
                }
            })
        })
    })
}

function updateConversationState(conversationId: number, updater: (conversation: Conversation) => Conversation) {
    let updatedConversation: Conversation | null = null
    const nextConversations = conversations.value.map((conversation) => {
        if (conversation.id !== conversationId) {
            return conversation
        }

        updatedConversation = updater(conversation)
        return updatedConversation
    })

    if (updatedConversation) {
        conversations.value = [updatedConversation, ...nextConversations.filter((conversation) => conversation.id !== conversationId)]
        return
    }

    const currentConversation = activeConversation.value
    if (!currentConversation || currentConversation.id !== conversationId) {
        conversations.value = nextConversations
        return
    }

    updatedConversation = updater(currentConversation)
    conversations.value = [updatedConversation, ...nextConversations]
}

function updateMessageAt(conversationId: number, messageIndex: number, updater: (message: ConversationMessage) => ConversationMessage) {
    updateConversationState(conversationId, (conversation) => ({
        ...conversation,
        messages: (conversation.messages ?? []).map((message, index) => {
            if (index !== messageIndex) {
                return message
            }

            return updater(message)
        }),
    }))
}

function getConversationMessage(conversationId: number, messageIndex: number) {
    return conversations.value.find((conversation) => conversation.id === conversationId)?.messages?.[messageIndex]
}

function formatTime(date: Date) {
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false,
    })
}

function formatMessageTime(created: string) {
    const date = parseDate(created)
    return date ? formatTime(date) : ''
}

function scrollToBottom() {
    void nextTick(() => {
        if (!messagePane.value) {
            return
        }

        messagePane.value.scrollTop = messagePane.value.scrollHeight
    })
}

function finalizeAssistantMessage(conversationId: number, assistantMessageIndex: number, fallbackText?: string) {
    updateMessageAt(conversationId, assistantMessageIndex, (message) => {
        const nextContent = message.content.trim() || fallbackText || ''

        return {
            ...message,
            content: nextContent,
        }
    })
}

function abortActiveStream(fallbackText?: string) {
    if (!activeStream) {
        return
    }

    const { session, conversationId, assistantMessageIndex } = activeStream
    finalizeAssistantMessage(conversationId, assistantMessageIndex, fallbackText)
    session.abort()
    activeStream = null
    responseGenerating.value = false
}

async function sendMessage() {
    if (!canSend.value) {
        return
    }

    const content = draftMessage.value.trim()
    const attachmentsToSend = pendingAttachments.value.filter((attachment) => attachment.status === 'uploaded' && attachment.uploadedImage)
    const uploadedImages = attachmentsToSend.map((attachment) => attachment.uploadedImage as UploadedImage)

    const existingConversation = conversations.value.find((conversation) => conversation.id === selectedConversationId.value)
    const activeConversationItem = existingConversation ?? createPendingConversation()
    const activeId = activeConversationItem.id

    if (!existingConversation) {
        conversations.value = [activeConversationItem, ...conversations.value]
    }

    const currentMessages = activeConversationItem.messages ?? []
    const now = new Date()
    const nowIso = now.toISOString()
    const assistantMessageIndex = currentMessages.length + 1
    const streamToken = createId('stream')
    const messageImages = createMessageImages(attachmentsToSend, uploadedImages)
    const imageObjectKeys = uploadedImages.map((image) => image.object_key)

    updateConversationState(activeId, (conversation) => ({
        ...conversation,
        summary: '正在生成诊断结果',
        messages: [
            ...currentMessages,
            {
                role: 'user',
                content: content,
                created: nowIso,
                images: messageImages.length ? messageImages : null,
            },
            {
                role: 'assistant',
                content: '',
                created: nowIso,
            },
        ],
        metadata_: {
            ...conversation.metadata_,
            last_message_at: nowIso,
        },
        updated_at: nowIso,
    }))

    draftMessage.value = ''
    clearPendingAttachments({ revokePreviews: false })
    scrollToBottom()

    const session = streamChat(
        {
            conversation_id: activeConversationItem.id,
            message: {
                content,
                images: imageObjectKeys.length ? imageObjectKeys : null,
            },
        },
        {
            onMessageDelta(delta) {
                if (activeStream?.token !== streamToken) {
                    return
                }

                updateMessageAt(activeId, assistantMessageIndex, (message) => ({
                    ...message,
                    content: `${message.content}${delta}`,
                }))
                updateConversationState(activeId, (conversation) => ({
                    ...conversation,
                    summary: `${getConversationMessage(activeId, assistantMessageIndex)?.content ?? ''}`.trim().slice(0, 24) || '正在生成诊断结果',
                    metadata_: {
                        ...conversation.metadata_,
                        last_message_at: nowIso,
                    },
                    updated_at: nowIso,
                }))
                scrollToBottom()
            },
            onClose() {
                if (activeStream?.token !== streamToken) {
                    return
                }

                finalizeAssistantMessage(activeId, assistantMessageIndex, '本次问诊未返回诊断结果。')
                updateConversationState(activeId, (conversation) => ({
                    ...conversation,
                    summary: getConversationMessage(activeId, assistantMessageIndex)?.content.trim().slice(0, 24) || '本次问诊未返回诊断结果',
                    metadata_: {
                        ...conversation.metadata_,
                        last_message_at: nowIso,
                    },
                    updated_at: nowIso,
                }))

                if (activeStream?.token === streamToken) {
                    activeStream = null
                }
                responseGenerating.value = false
                scrollToBottom()
            },
            onError(error) {
                if (activeStream?.token !== streamToken) {
                    return
                }

                finalizeAssistantMessage(activeId, assistantMessageIndex, '问诊请求失败，请稍后重试。')
                updateConversationState(activeId, (conversation) => ({
                    ...conversation,
                    summary: error.message || '问诊请求失败，请稍后重试',
                    metadata_: {
                        ...conversation.metadata_,
                        last_message_at: nowIso,
                    },
                    updated_at: nowIso,
                }))

                if (activeStream?.token === streamToken) {
                    activeStream = null
                }
                responseGenerating.value = false
            },
        },
        {
            endpoint: '/chat/stream',
        },
    )

    activeStream = {
        session,
        conversationId: activeId,
        assistantMessageIndex,
        token: streamToken,
    }
    responseGenerating.value = true

    void session.completed
        .catch(() => undefined)
        .finally(() => {
            if (activeStream?.token === streamToken) {
                activeStream = null
            }
            responseGenerating.value = false
        })
}

function formatFileSize(size: number) {
    if (size < 1024 * 1024) {
        return `${Math.max(1, Math.round(size / 1024))} KB`
    }

    return `${(size / 1024 / 1024).toFixed(1)} MB`
}

function createId(prefix: string) {
    return `${prefix}-${Date.now()}-${Math.round(Math.random() * 100000)}`
}

watch(
    selectedConversationId,
    (currentId, previousId) => {
        if (previousId && currentId !== previousId) {
            abortActiveStream('已停止生成。')
        }

        scrollToBottom()
    },
    { flush: 'post' },
)

onMounted(() => {
    void loadCurrentUser()
    void loadConversationList()
})

onBeforeUnmount(() => {
    abortActiveStream()
    clearPendingAttachments()
    revokeConversationPreviewUrls()
})
</script>

<template>
    <div class="home-shell" :class="{ 'home-shell--sidebar-open': sidebarOpen, 'home-shell--sidebar-collapsed': sidebarCollapsed }">
        <button v-if="sidebarOpen" class="sidebar-scrim" type="button" aria-label="关闭会话列表" @click="sidebarOpen = false"></button>

        <div v-if="searchOpen" class="search-dialog-layer" role="presentation" @keydown.esc.stop.prevent="closeSearch">
            <button class="search-dialog-scrim" type="button" aria-label="关闭搜索" @click="closeSearch"></button>

            <section class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="search-dialog-title">
                <div class="search-dialog__header">
                    <Search :size="20" stroke-width="2" aria-hidden="true" />
                    <input ref="searchDialogInput" v-model="searchQuery" type="search" placeholder="搜索历史对话" aria-label="搜索历史对话" />
                    <button class="search-dialog__close" type="button" aria-label="关闭搜索" @click="closeSearch">
                        <X :size="18" stroke-width="2" />
                    </button>
                </div>

                <div class="search-dialog__body">
                    <p id="search-dialog-title" class="search-dialog__title">历史对话</p>

                    <div v-if="conversationListLoading" class="search-dialog__empty">正在加载历史对话</div>
                    <div v-else-if="conversationListError" class="search-dialog__empty">
                        <span>{{ conversationListError }}</span>
                        <button type="button" @click="loadConversationList">重试</button>
                    </div>
                    <div v-else-if="searchResults.length" class="search-dialog__list">
                        <button v-for="conversation in searchResults" :key="conversation.id" class="search-dialog__item" type="button" @click="selectSearchResult(conversation.id)">
                            <span class="search-dialog__item-main">
                                <span>{{ getConversationTitle(conversation) }}</span>
                                <small>{{ getConversationSummary(conversation) }}</small>
                            </span>
                            <span class="search-dialog__time">{{ getConversationTime(conversation) }}</span>
                        </button>
                    </div>

                    <div v-else class="search-dialog__empty">{{ hasConversations ? '没有匹配的历史对话' : '暂无历史对话' }}</div>
                </div>
            </section>
        </div>

        <div v-if="logoutDialogOpen" class="logout-dialog-layer" role="presentation" @keydown.esc.stop.prevent="closeLogoutDialog">
            <button class="logout-dialog-scrim" type="button" aria-label="取消退出登录" @click="closeLogoutDialog"></button>

            <section class="logout-dialog" role="dialog" aria-modal="true" aria-labelledby="logout-dialog-title" aria-describedby="logout-dialog-description">
                <div class="logout-dialog__content">
                    <h2 id="logout-dialog-title">退出登录？</h2>
                    <p id="logout-dialog-description">退出后需要重新登录才能继续使用鱼病问诊助手。</p>
                </div>

                <div class="logout-dialog__actions">
                    <button class="logout-dialog__button logout-dialog__button--secondary" type="button" @click="closeLogoutDialog">取消</button>
                    <button class="logout-dialog__button logout-dialog__button--primary" type="button" @click="confirmLogout">退出登录</button>
                </div>
            </section>
        </div>

        <aside class="conversation-sidebar" aria-label="会话列表">
            <div class="sidebar-brand">
                <img class="sidebar-brand__logo" src="/images/fish-med-agent-logo.svg" alt="Fish Med Agent 图标" />
                <div class="sidebar-brand__text">
                    <strong>Fish Med Agent</strong>
                    <span>鱼病问诊助手</span>
                </div>
            </div>

            <button class="new-chat-button" type="button" @click="createConversation">
                <Plus :size="18" stroke-width="2" />
                <span>新建对话</span>
            </button>

            <button class="search-field search-field--trigger" type="button" @click="openSearch">
                <Search :size="16" stroke-width="2" aria-hidden="true" />
                <span>搜索历史对话</span>
            </button>

            <nav class="conversation-groups" aria-label="历史对话">
                <div v-if="conversationListLoading" class="conversation-state">正在加载历史对话</div>
                <div v-else-if="conversationListError" class="conversation-state conversation-state--error">
                    <span>{{ conversationListError }}</span>
                    <button type="button" @click="loadConversationList">重试</button>
                </div>
                <div v-else-if="!hasConversations" class="conversation-state">暂无历史对话</div>

                <template v-else>
                    <section v-for="group in groupedConversations" :key="group.label" class="conversation-group">
                        <h2 class="conversation-group__title">{{ group.label }}</h2>

                        <button
                            v-for="conversation in group.items"
                            :key="conversation.id"
                            class="conversation-item"
                            :class="{ 'conversation-item--active': conversation.id === selectedConversationId }"
                            type="button"
                            @click="selectConversation(conversation.id)">
                            <span class="conversation-item__topline">
                                <span class="conversation-item__title">{{ getConversationTitle(conversation) }}</span>
                                <span class="conversation-item__time">{{ getConversationTime(conversation) }}</span>
                            </span>
                        </button>
                    </section>
                </template>
            </nav>

            <section class="sidebar-user-panel" aria-label="当前用户">
                <div class="sidebar-user-panel__avatar" aria-hidden="true">
                    <img v-if="authStore.avatarUrl" :src="authStore.avatarUrl" alt="" />
                    <span v-else>{{ userInitial }}</span>
                </div>

                <div class="sidebar-user-panel__identity">
                    <strong>{{ userNickname }}</strong>
                    <span>{{ userUsername }}</span>
                </div>

                <button class="sidebar-user-panel__logout" type="button" aria-label="退出登录" title="退出登录" @click="openLogoutDialog">
                    <LogOut :size="17" stroke-width="2" />
                </button>
            </section>
        </aside>

        <main class="chat-workspace">
            <header class="chat-header">
                <button class="mobile-menu-button" type="button" aria-label="切换会话列表" @click="toggleSidebar">
                    <PanelLeft :size="20" stroke-width="2" />
                </button>

                <div class="chat-header__title-block">
                    <p class="chat-header__eyebrow">鱼病问诊</p>
                    <h1>{{ activeConversationTitle }}</h1>
                </div>

                <div class="chat-header__actions">
                    <button class="header-icon-button" type="button" aria-label="查看历史">
                        <Clock :size="19" stroke-width="2" />
                    </button>
                    <button class="header-icon-button" type="button" aria-label="更多操作">
                        <MoreHorizontal :size="20" stroke-width="2" />
                    </button>
                </div>
            </header>

            <section ref="messagePane" class="message-pane" aria-label="当前会话消息">
                <div v-if="activeMessages.length > 0" class="message-list">
                    <article
                        v-for="(message, messageIndex) in activeMessages"
                        :key="`${message.created}-${messageIndex}`"
                        class="chat-message"
                        :class="`chat-message--${message.role}`">
                        <div v-if="message.role === 'assistant'" class="assistant-mark" aria-hidden="true">
                            <Sparkles :size="16" stroke-width="2" />
                        </div>

                        <div class="chat-message__content">
                            <div class="chat-message__meta">
                                <span>{{ message.role === 'assistant' ? 'Fish Med Agent' : '你' }}</span>
                                <time>{{ formatMessageTime(message.created) }}</time>
                            </div>

                            <div class="message-bubble" :class="{ 'message-bubble--pending': message.role === 'assistant' && !message.content }">
                                <div v-if="message.role === 'assistant'" class="message-markdown" v-html="renderAssistantMarkdown(message.content)"></div>
                                <template v-else>
                                    <p>{{ message.content }}</p>
                                    <div v-if="message.images?.length" class="message-attachments" aria-label="已发送图片">
                                        <div v-for="image in getMessageImages(message)" :key="image.id" class="message-attachment">
                                            <div class="message-attachment__thumb">
                                                <img v-if="image.previewUrl" :src="image.previewUrl" :alt="image.name" />
                                                <FileImage v-else :size="18" stroke-width="2" />
                                            </div>
                                            <div class="message-attachment__text">
                                                <span>{{ image.name }}</span>
                                                <small>{{ image.objectKey || (image.size ? formatFileSize(image.size) : '已上传图片') }}</small>
                                            </div>
                                        </div>
                                    </div>
                                </template>
                            </div>
                        </div>
                    </article>
                </div>

                <div v-else class="empty-state">
                    <div class="empty-state__mark" aria-hidden="true">
                        <MessageCircle :size="24" stroke-width="1.8" />
                    </div>
                    <h2>新的鱼病问诊</h2>
                    <div class="prompt-row" aria-label="症状示例">
                        <button v-for="prompt in samplePrompts" :key="prompt" type="button" @click="choosePrompt(prompt)">
                            {{ prompt }}
                        </button>
                    </div>
                </div>
            </section>

            <footer class="composer-area">
                <div v-if="pendingAttachments.length" class="pending-files" aria-label="待发送附件">
                    <div
                        v-for="attachment in pendingAttachments"
                        :key="attachment.id"
                        class="pending-file"
                        :class="{
                            'pending-file--uploading': attachment.status === 'pending' || attachment.status === 'uploading',
                            'pending-file--deleting': attachment.status === 'deleting',
                        }">
                        <div class="pending-file__preview">
                            <img v-if="attachment.previewUrl" :src="attachment.previewUrl" :alt="attachment.name" />
                            <FileImage v-else :size="18" stroke-width="2" />
                            <span v-if="attachment.status === 'pending' || attachment.status === 'uploading' || attachment.status === 'deleting'" class="pending-file__spinner" aria-label="图片处理中"></span>
                            <button v-if="attachment.status === 'uploaded'" type="button" :aria-label="`移除 ${attachment.name}`" @click="removePendingAttachment(attachment.id)">
                                <X :size="14" stroke-width="2.4" />
                            </button>
                        </div>
                    </div>
                </div>

                <form class="composer" @submit.prevent="sendMessage">
                    <button class="composer-icon-button" type="button" aria-label="语音输入">
                        <Mic :size="19" stroke-width="2" />
                    </button>

                    <button class="composer-icon-button" type="button" :disabled="imagesBusy || responseGenerating" aria-label="上传图片" @click="openFilePicker">
                        <Paperclip :size="19" stroke-width="2" />
                    </button>

                    <textarea
                        v-model="draftMessage"
                        rows="1"
                        placeholder="输入鱼种、症状、水温、发病时长..."
                        @compositionstart="handleMessageInputCompositionStart"
                        @compositionend="handleMessageInputCompositionEnd"
                        @keydown="handleMessageInputKeydown"></textarea>

                    <button class="send-button" type="submit" :disabled="!canSend" aria-label="发送">
                        <SendHorizontal :size="19" stroke-width="2.2" />
                    </button>

                    <input ref="fileInput" class="file-input" type="file" accept="image/*" multiple :disabled="imagesBusy || responseGenerating" @change="handleFileChange" />
                </form>
            </footer>
        </main>
    </div>
</template>

<style scoped>
:global(html),
:global(body),
:global(#app) {
    height: 100%;
    min-height: 100%;
}

:global(body) {
    margin: 0;
}

.home-shell,
.home-shell * {
    box-sizing: border-box;
}

.home-shell {
    --background: #ffffff;
    --foreground: #09090b;
    --card: #ffffff;
    --card-foreground: #09090b;
    --primary: #18181b;
    --primary-foreground: #fafafa;
    --secondary: #f4f4f5;
    --secondary-foreground: #18181b;
    --muted: #f4f4f5;
    --muted-foreground: #71717a;
    --accent: #f4f4f5;
    --accent-foreground: #18181b;
    --border: #e4e4e7;
    --input: #e4e4e7;
    --ring: #18181b;
    --ocean-blue: #0e7fb0;
    --ocean-blue-hover: #0a6a9c;
    --ocean-blue-soft: rgba(14, 127, 176, 0.14);
    --ocean-blue-glow: rgba(14, 127, 176, 0.16);
    --radius: 12px;
    --shadow-sm: 0 1px 2px rgba(0, 0, 0, 0.05);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -2px rgba(0, 0, 0, 0.08);
    --shadow-lg: 0 18px 40px -16px rgba(0, 0, 0, 0.22);
    height: 100vh;
    height: 100dvh;
    max-height: 100vh;
    max-height: 100dvh;
    display: grid;
    grid-template-columns: 320px minmax(0, 1fr);
    overflow: hidden;
    background: var(--muted);
    color: var(--foreground);
    font-family: Inter, 'SF Pro Text', 'Helvetica Neue', Helvetica, Arial, sans-serif;
    transition: grid-template-columns 220ms ease;
}

.home-shell--sidebar-collapsed {
    grid-template-columns: 80px minmax(0, 1fr);
}

button,
input,
textarea {
    font: inherit;
}

button {
    cursor: pointer;
}

button:focus-visible,
input:focus-visible,
textarea:focus-visible {
    outline: 2px solid var(--ring);
    outline-offset: 2px;
}

.sidebar-scrim {
    display: none;
}

.search-dialog-layer {
    position: fixed;
    inset: 0;
    z-index: 30;
    display: grid;
    place-items: start center;
    padding: min(16vh, 132px) 16px 24px;
}

.search-dialog-scrim {
    position: absolute;
    inset: 0;
    border: 0;
    background: rgba(9, 9, 11, 0.38);
    backdrop-filter: blur(4px);
}

.search-dialog {
    position: relative;
    z-index: 1;
    display: grid;
    width: min(720px, 100%);
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: 18px;
    background: var(--card);
    box-shadow: 0 24px 80px rgba(0, 0, 0, 0.24);
}

.search-dialog__header {
    display: grid;
    min-height: 68px;
    grid-template-columns: 24px minmax(0, 1fr) 38px;
    align-items: center;
    gap: 12px;
    border-bottom: 1px solid var(--border);
    padding: 0 14px 0 18px;
    color: var(--muted-foreground);
}

.search-dialog__header input {
    min-width: 0;
    border: 0;
    background: transparent;
    color: var(--foreground);
    font-size: 18px;
    line-height: 1.4;
    outline: none;
}

.search-dialog__header input::placeholder {
    color: var(--muted-foreground);
}

.search-dialog__close {
    display: inline-flex;
    width: 38px;
    height: 38px;
    align-items: center;
    justify-content: center;
    border: 0;
    border-radius: calc(var(--radius) - 4px);
    background: transparent;
    color: var(--muted-foreground);
}

.search-dialog__close:hover {
    background: var(--accent);
    color: var(--accent-foreground);
}

.search-dialog__body {
    display: grid;
    gap: 8px;
    padding: 10px;
}

.search-dialog__title {
    margin: 0;
    padding: 4px 8px;
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
}

.search-dialog__list {
    display: grid;
    max-height: min(48vh, 420px);
    gap: 4px;
    overflow: hidden auto;
    overscroll-behavior: contain;
}

.search-dialog__item {
    display: flex;
    width: 100%;
    min-height: 58px;
    align-items: center;
    gap: 16px;
    border: 1px solid transparent;
    border-radius: calc(var(--radius) - 2px);
    background: transparent;
    padding: 9px 10px;
    color: var(--foreground);
    text-align: left;
}

.search-dialog__item:hover {
    border-color: var(--border);
    background: var(--accent);
}

.search-dialog__item-main {
    display: grid;
    min-width: 0;
    flex: 1;
    gap: 4px;
}

.search-dialog__item-main span,
.search-dialog__item-main small {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.search-dialog__item-main span {
    font-size: 14px;
    line-height: 1.25;
}

.search-dialog__item-main small,
.search-dialog__time,
.search-dialog__empty {
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
}

.search-dialog__time {
    flex: 0 0 auto;
}

.search-dialog__empty {
    display: grid;
    min-height: 96px;
    gap: 10px;
    place-items: center;
}

.logout-dialog-layer {
    position: fixed;
    inset: 0;
    z-index: 35;
    display: grid;
    place-items: center;
    padding: 16px;
}

.logout-dialog-scrim {
    position: absolute;
    inset: 0;
    border: 0;
    background: rgba(9, 9, 11, 0.32);
    backdrop-filter: blur(4px);
}

.logout-dialog {
    position: relative;
    z-index: 1;
    display: grid;
    width: min(360px, 100%);
    gap: 20px;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--card);
    box-shadow: 0 20px 64px rgba(0, 0, 0, 0.2);
    padding: 20px;
}

.logout-dialog__content {
    display: grid;
    gap: 8px;
}

.logout-dialog__content h2,
.logout-dialog__content p {
    margin: 0;
}

.logout-dialog__content h2 {
    color: var(--foreground);
    font-size: 18px;
    font-weight: 600;
    line-height: 1.2;
}

.logout-dialog__content p {
    color: var(--muted-foreground);
    font-size: 14px;
    line-height: 1.5;
}

.logout-dialog__actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
}

.logout-dialog__button {
    min-height: 36px;
    border: 0;
    border-radius: calc(var(--radius) - 4px);
    padding: 0 14px;
    font-size: 14px;
    line-height: 1;
    transition:
        background-color 160ms ease,
        color 160ms ease,
        transform 160ms ease;
}

.logout-dialog__button:active {
    transform: scale(0.98);
}

.logout-dialog__button--secondary {
    background: var(--accent);
    color: var(--foreground);
}

.logout-dialog__button--secondary:hover {
    background: var(--border);
}

.logout-dialog__button--primary {
    background: var(--ocean-blue);
    color: var(--primary-foreground);
}

.logout-dialog__button--primary:hover {
    background: var(--ocean-blue-hover);
}

.search-dialog__empty button,
.conversation-state button {
    min-height: 32px;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 4px);
    background: var(--background);
    color: var(--foreground);
    padding: 0 12px;
    font-size: 13px;
}

.search-dialog__empty button:hover,
.conversation-state button:hover {
    background: var(--accent);
}

.conversation-sidebar {
    position: relative;
    z-index: 4;
    display: flex;
    height: 100%;
    min-height: 0;
    flex-direction: column;
    gap: 12px;
    border-right: 1px solid var(--border);
    background: var(--background);
    padding: 12px;
    overflow: hidden;
}

.sidebar-brand {
    display: flex;
    height: 50px;
    flex: 0 0 50px;
    align-items: center;
    gap: 10px;
    overflow: hidden;
    border: 1px solid transparent;
    border-radius: var(--radius);
    padding: 6px 6px 10px 11px;
}

.sidebar-brand__logo {
    width: 34px;
    height: 34px;
    flex: 0 0 auto;
    object-fit: contain;
}

.sidebar-brand__text {
    display: grid;
    min-width: 0;
    gap: 2px;
    transition:
        opacity 100ms ease,
        transform 140ms ease;
}

.sidebar-brand__text strong {
    overflow: hidden;
    color: var(--foreground);
    font-size: 15px;
    font-weight: 400;
    line-height: 1.1;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.sidebar-brand__text span {
    overflow: hidden;
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.new-chat-button {
    display: inline-flex;
    min-height: 40px;
    align-items: center;
    justify-content: center;
    gap: 8px;
    border: 1px solid transparent;
    border-radius: calc(var(--radius) - 2px);
    background: var(--ocean-blue);
    box-shadow: var(--shadow-sm);
    color: var(--primary-foreground);
    font-size: 14px;
    font-weight: 400;
    line-height: 1;
    transition:
        background-color 160ms ease,
        opacity 100ms ease,
        transform 160ms ease;
}

.new-chat-button:hover {
    background: var(--ocean-blue-hover);
}

.new-chat-button:active {
    transform: scale(0.99);
}

.search-field {
    display: flex;
    width: 100%;
    min-height: 40px;
    align-items: center;
    gap: 8px;
    border: 1px solid var(--input);
    border-radius: calc(var(--radius) - 2px);
    background: var(--background);
    padding: 0 12px;
    color: var(--muted-foreground);
    box-shadow: var(--shadow-sm);
    text-align: left;
    transition:
        opacity 100ms ease,
        transform 140ms ease;
}

.search-field:focus-within {
    border-color: var(--ring);
    box-shadow: 0 0 0 3px rgba(24, 24, 27, 0.12);
}

.search-field--trigger:focus,
.search-field--trigger:focus-visible,
.search-field--trigger:focus-within {
    border-color: var(--input);
    box-shadow: var(--shadow-sm);
    outline: none;
}

.search-field input {
    min-width: 0;
    flex: 1;
    border: 0;
    background: transparent;
    color: var(--foreground);
    font-size: 14px;
    line-height: 1.25;
    outline: none;
}

.search-field input::placeholder {
    color: var(--muted-foreground);
}

.search-field--trigger span {
    min-width: 0;
    flex: 1;
    overflow: hidden;
    color: var(--muted-foreground);
    font-size: 14px;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.conversation-groups {
    display: flex;
    min-height: 0;
    flex: 1;
    flex-direction: column;
    gap: 14px;
    overflow: hidden auto;
    padding: 2px 0 10px;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    transition:
        opacity 100ms ease,
        transform 140ms ease;
}

.home-shell--sidebar-collapsed .conversation-sidebar {
    width: 100%;
    min-width: 0;
    align-items: stretch;
    padding: 12px;
    opacity: 1;
}

.home-shell--sidebar-collapsed .sidebar-brand {
    width: 56px;
    height: 50px;
    flex-basis: 50px;
    justify-content: flex-start;
    overflow: hidden;
    padding: 6px 6px 10px 11px;
}

.home-shell--sidebar-collapsed .sidebar-brand__logo {
    width: 34px;
    height: 34px;
}

.home-shell--sidebar-collapsed .sidebar-brand__text,
.home-shell--sidebar-collapsed .new-chat-button,
.home-shell--sidebar-collapsed .search-field,
.home-shell--sidebar-collapsed .new-chat-button span,
.home-shell--sidebar-collapsed .search-field span,
.home-shell--sidebar-collapsed .sidebar-user-panel__identity,
.home-shell--sidebar-collapsed .sidebar-user-panel__logout {
    opacity: 0;
    pointer-events: none;
    transform: translateX(-10px);
    transition:
        opacity 100ms ease,
        transform 140ms ease;
}

.home-shell--sidebar-collapsed .sidebar-brand__text,
.home-shell--sidebar-collapsed .sidebar-user-panel__identity,
.home-shell--sidebar-collapsed .sidebar-user-panel__logout {
    display: none;
}

.home-shell--sidebar-collapsed .conversation-groups {
    display: none;
}

.home-shell--sidebar-collapsed .new-chat-button,
.home-shell--sidebar-collapsed .search-field {
    display: none;
}

.home-shell--sidebar-collapsed .sidebar-user-panel {
    width: 56px;
    height: 50px;
    margin-top: auto;
    justify-content: flex-start;
    align-items: center;
    border-top: 0;
    padding: 12px 8px 2px 10px;
    transform: none;
}

.conversation-state {
    display: grid;
    min-height: 96px;
    place-items: center;
    gap: 10px;
    padding: 14px 8px;
    color: var(--muted-foreground);
    font-size: 13px;
    line-height: 1.4;
    text-align: center;
}

.conversation-state--error {
    color: var(--foreground);
}

.conversation-group {
    display: grid;
    gap: 4px;
}

.conversation-group__title {
    margin: 0;
    padding: 0 8px;
    color: var(--muted-foreground);
    font-size: 12px;
    font-weight: 400;
    line-height: 1.2;
}

.conversation-item {
    display: flex;
    width: 100%;
    min-height: 42px;
    align-items: center;
    border: 1px solid transparent;
    border-radius: calc(var(--radius) - 2px);
    background: transparent;
    padding: 0 11px;
    color: var(--foreground);
    text-align: left;
    transition:
        background-color 160ms ease,
        border-color 160ms ease,
        color 160ms ease;
}

.conversation-item:hover {
    background: var(--accent);
    color: var(--accent-foreground);
}

.conversation-item--active {
    border-color: var(--border);
    background: var(--accent);
    box-shadow: var(--shadow-sm);
}

.conversation-item__topline {
    display: flex;
    width: 100%;
    min-width: 0;
    align-items: center;
    gap: 10px;
}

.conversation-item__title {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.conversation-item__title {
    flex: 1;
    font-size: 14px;
    font-weight: 400;
    line-height: 1.25;
}

.conversation-item__time {
    flex: 0 0 auto;
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
}

.sidebar-user-panel {
    display: flex;
    flex: 0 0 auto;
    min-width: 0;
    align-items: center;
    gap: 10px;
    border-top: 1px solid var(--border);
    background: transparent;
    padding: 12px 8px 2px 10px;
    transition:
        opacity 100ms ease,
        transform 140ms ease;
}

.sidebar-user-panel__avatar {
    display: inline-flex;
    width: 36px;
    height: 36px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border: 1px solid rgba(14, 127, 176, 0.18);
    border-radius: 50%;
    background: var(--ocean-blue-soft);
    color: var(--ocean-blue);
    font-size: 14px;
    font-weight: 600;
    line-height: 1;
}

.sidebar-user-panel__avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.sidebar-user-panel__identity {
    display: grid;
    min-width: 0;
    flex: 1;
    gap: 2px;
}

.sidebar-user-panel__identity strong,
.sidebar-user-panel__identity span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.sidebar-user-panel__identity strong {
    color: var(--foreground);
    font-size: 14px;
    font-weight: 600;
    line-height: 1.2;
}

.sidebar-user-panel__identity span {
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
}

.sidebar-user-panel__logout {
    display: inline-flex;
    width: 34px;
    height: 34px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border: 0;
    border-radius: calc(var(--radius) - 4px);
    background: transparent;
    color: var(--muted-foreground);
    transition:
        background-color 160ms ease,
        color 160ms ease,
        transform 160ms ease;
}

.sidebar-user-panel__logout:hover,
.sidebar-user-panel__logout:focus-visible {
    background: rgba(14, 127, 176, 0.1);
    color: var(--ocean-blue);
}

.sidebar-user-panel__logout:active {
    transform: scale(0.96);
    background: rgba(14, 127, 176, 0.16);
    color: var(--ocean-blue-hover);
}

.chat-workspace {
    --message-bottom-cover-height: 126px;
    --message-scrollbar-gutter: 18px;
    position: relative;
    display: grid;
    min-width: 0;
    min-height: 0;
    height: 100%;
    grid-template-rows: 65px minmax(0, 1fr);
    overflow: hidden;
    background: var(--background);
}

.chat-workspace::after {
    position: absolute;
    right: var(--message-scrollbar-gutter);
    bottom: 0;
    left: 0;
    z-index: 1;
    height: var(--message-bottom-cover-height);
    background: var(--background);
    content: '';
    pointer-events: none;
}

.chat-header {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 14px;
    border-bottom: 1px solid var(--border);
    background: rgba(255, 255, 255, 0.92);
    padding: 0 clamp(16px, 2.4vw, 28px);
    backdrop-filter: blur(12px);
}

.mobile-menu-button {
    display: inline-flex;
    flex: 0 0 auto;
}

.chat-header__title-block {
    display: grid;
    min-width: 0;
    flex: 1;
    gap: 2px;
}

.chat-header__eyebrow {
    margin: 0;
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
}

.chat-header h1 {
    overflow: hidden;
    margin: 0;
    color: var(--foreground);
    font-size: 18px;
    font-weight: 400;
    line-height: 1.2;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.chat-header__actions {
    display: flex;
    align-items: center;
    gap: 6px;
}

.header-icon-button,
.mobile-menu-button,
.composer-icon-button,
.send-button,
.pending-file button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border: 0;
}

.header-icon-button,
.mobile-menu-button,
.composer-icon-button {
    width: 38px;
    height: 38px;
    border-radius: calc(var(--radius) - 4px);
    background: transparent;
    color: var(--muted-foreground);
    transition:
        background-color 160ms ease,
        color 160ms ease,
        transform 160ms ease;
}

.header-icon-button:hover {
    background: var(--accent);
    color: var(--accent-foreground);
}

.mobile-menu-button:hover,
.mobile-menu-button:focus-visible,
.composer-icon-button:hover,
.composer-icon-button:focus-visible {
    background: rgba(14, 127, 176, 0.1);
    color: var(--ocean-blue);
}

.header-icon-button:active,
.mobile-menu-button:active,
.composer-icon-button:active,
.send-button:active {
    transform: scale(0.96);
}

.composer-icon-button:active {
    background: rgba(14, 127, 176, 0.16);
    color: var(--ocean-blue-hover);
}

.message-pane {
    min-height: 0;
    overflow: hidden auto;
    overscroll-behavior: contain;
    scrollbar-gutter: stable;
    background: var(--background);
}

.message-list {
    display: grid;
    gap: 30px;
    width: min(100%, 920px);
    margin: 0 auto;
    padding: 28px clamp(16px, 3vw, 28px) 190px;
}

.chat-message {
    display: flex;
    min-width: 0;
    gap: 10px;
}

.chat-message--user {
    justify-content: flex-end;
}

.chat-message--assistant {
    justify-content: flex-start;
}

.chat-message--assistant .assistant-mark {
    display: none;
}

.assistant-mark {
    display: inline-flex;
    width: 32px;
    height: 32px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 4px);
    background: var(--card);
    box-shadow: var(--shadow-sm);
    color: var(--foreground);
}

.chat-message__content {
    display: grid;
    max-width: min(680px, 100%);
    gap: 6px;
}

.chat-message--assistant .chat-message__content {
    width: 100%;
    max-width: min(780px, 100%);
}

.chat-message--user .chat-message__content {
    justify-items: end;
}

.chat-message__meta {
    display: flex;
    align-items: center;
    gap: 8px;
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
}

.chat-message--user .chat-message__meta {
    justify-content: flex-end;
}

.chat-message--assistant .chat-message__meta {
    display: none;
}

.message-bubble {
    display: grid;
    gap: 12px;
    border-radius: var(--radius);
    color: var(--foreground);
    font-size: 14px;
    line-height: 1.55;
}

.chat-message--user .message-bubble {
    border: 0;
    background: var(--secondary);
    color: var(--secondary-foreground);
    border-radius: 18px;
    padding: 11px 15px;
    font-size: 15px;
    line-height: 1.55;
}

.chat-message--assistant .message-bubble {
    border: 0;
    background: transparent;
    box-shadow: none;
    padding: 0;
    font-size: 16px;
    line-height: 1.78;
}

.message-bubble p {
    margin: 0;
}

.message-markdown {
    display: grid;
    gap: 10px;
    overflow-wrap: anywhere;
}

.message-markdown :deep(h1),
.message-markdown :deep(h2),
.message-markdown :deep(h3),
.message-markdown :deep(h4) {
    margin: 0;
    color: var(--foreground);
    font-weight: 600;
    line-height: 1.25;
}

.message-markdown :deep(h1) {
    font-size: 18px;
}

.message-markdown :deep(h2),
.message-markdown :deep(h3),
.message-markdown :deep(h4) {
    font-size: 16px;
}

.message-markdown :deep(p),
.message-markdown :deep(ul),
.message-markdown :deep(ol),
.message-markdown :deep(blockquote),
.message-markdown :deep(pre),
.message-markdown :deep(table) {
    margin: 0;
}

.message-markdown :deep(ul),
.message-markdown :deep(ol) {
    display: grid;
    gap: 5px;
    padding-left: 20px;
}

.message-markdown :deep(li) {
    padding-left: 2px;
}

.message-markdown :deep(strong) {
    font-weight: 600;
}

.message-markdown :deep(a) {
    color: var(--ocean-blue);
    text-decoration: underline;
    text-underline-offset: 3px;
}

.message-markdown :deep(code) {
    border-radius: 5px;
    background: var(--muted);
    padding: 2px 5px;
    font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', monospace;
    font-size: 0.92em;
}

.message-markdown :deep(pre) {
    overflow-x: auto;
    border-radius: calc(var(--radius) - 4px);
    background: var(--muted);
    padding: 10px 12px;
}

.message-markdown :deep(pre code) {
    display: block;
    background: transparent;
    padding: 0;
    white-space: pre;
}

.message-markdown :deep(blockquote) {
    border-left: 3px solid var(--border);
    color: var(--muted-foreground);
    padding-left: 10px;
}

.message-markdown :deep(table) {
    display: block;
    max-width: 100%;
    overflow-x: auto;
    border-collapse: collapse;
}

.message-markdown :deep(th),
.message-markdown :deep(td) {
    border: 1px solid var(--border);
    padding: 6px 8px;
    text-align: left;
}

.message-bubble--pending {
    color: var(--muted-foreground);
}

.message-attachments {
    display: grid;
    gap: 8px;
}

.message-attachment {
    display: flex;
    min-width: 0;
    align-items: center;
    gap: 9px;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--background);
    padding: 7px;
}

.message-attachment__thumb {
    display: inline-flex;
    width: 42px;
    height: 42px;
    flex: 0 0 auto;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 4px);
    background: var(--muted);
    color: var(--muted-foreground);
}

.message-attachment__thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.message-attachment__text {
    min-width: 0;
    flex: 1;
}

.message-attachment span,
.pending-file__text span {
    display: block;
    overflow: hidden;
    color: var(--foreground);
    font-size: 13px;
    font-weight: 400;
    line-height: 1.25;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.message-attachment small,
.pending-file__text small {
    display: block;
    color: var(--muted-foreground);
    font-size: 12px;
    line-height: 1.2;
}

.diagnosis-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-top: 4px;
}

.diagnosis-section {
    display: grid;
    gap: 6px;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--muted);
    padding: 12px;
}

.diagnosis-section h2 {
    margin: 0;
    color: var(--foreground);
    font-size: 14px;
    font-weight: 400;
    line-height: 1.25;
}

.diagnosis-section p {
    color: var(--muted-foreground);
    font-size: 14px;
    line-height: 1.45;
}

.empty-state {
    display: grid;
    width: min(520px, calc(100% - 32px));
    min-height: 100%;
    place-items: center;
    align-content: center;
    gap: 16px;
    margin: 0 auto;
    padding: 24px 24px 180px;
    text-align: center;
}

.empty-state__mark {
    display: inline-flex;
    width: 54px;
    height: 54px;
    align-items: center;
    justify-content: center;
    border: 1px solid var(--border);
    border-radius: var(--radius);
    background: var(--card);
    box-shadow: var(--shadow-sm);
    color: var(--foreground);
}

.empty-state h2 {
    margin: 0;
    color: var(--foreground);
    font-size: 26px;
    font-weight: 400;
    line-height: 1.15;
}

.prompt-row {
    display: flex;
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
}

.prompt-row button {
    min-height: 34px;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) - 2px);
    background: var(--background);
    color: var(--foreground);
    padding: 0 12px;
    box-shadow: var(--shadow-sm);
    font-size: 14px;
    font-weight: 400;
    line-height: 1.25;
}

.prompt-row button:hover {
    background: var(--accent);
}

.composer-area {
    position: absolute;
    right: 50%;
    bottom: max(24px, env(safe-area-inset-bottom));
    display: grid;
    width: min(920px, calc(100% - 32px));
    transform: translateX(50%);
    z-index: 2;
    gap: 10px;
    border: 1px solid rgba(14, 127, 176, 0.46);
    border-radius: 20px;
    background: rgba(255, 255, 255, 0.96);
    box-shadow:
        var(--shadow-lg),
        0 0 0 2px rgba(14, 127, 176, 0.05),
        0 0 14px rgba(14, 127, 176, 0.08);
    padding: 10px;
    animation: composer-ocean-breath 2.8s ease-in-out infinite;
    backdrop-filter: blur(12px);
}

.composer-area:focus-within {
    border-color: var(--ocean-blue);
    box-shadow:
        var(--shadow-lg),
        0 0 0 3px var(--ocean-blue-soft),
        0 0 20px var(--ocean-blue-glow);
    animation-play-state: paused;
}

@keyframes composer-ocean-breath {
    0%,
    100% {
        border-color: rgba(14, 127, 176, 0.32);
        box-shadow:
            var(--shadow-lg),
            0 0 0 1px rgba(14, 127, 176, 0.04),
            0 0 10px rgba(14, 127, 176, 0.06);
    }

    50% {
        border-color: rgba(14, 127, 176, 0.58);
        box-shadow:
            var(--shadow-lg),
            0 0 0 3px rgba(14, 127, 176, 0.08),
            0 0 18px rgba(14, 127, 176, 0.12);
    }
}

@media (prefers-reduced-motion: reduce) {
    .composer-area {
        animation: none;
    }

    .pending-file__spinner::after {
        animation: none;
    }
}

.pending-files {
    display: flex;
    width: 100%;
    gap: 10px;
    overflow-x: auto;
    overscroll-behavior-x: contain;
    padding: 2px 0 4px;
}

.pending-file {
    position: relative;
    display: inline-flex;
    width: 124px;
    height: 124px;
    flex: 0 0 auto;
    align-items: stretch;
    justify-content: stretch;
}

.pending-file--uploading {
    opacity: 0.92;
}

.pending-file--deleting {
    opacity: 0.74;
}

.pending-file__preview {
    position: relative;
    display: inline-flex;
    width: 100%;
    height: 100%;
    flex: 1;
    align-items: center;
    justify-content: center;
    overflow: hidden;
    border: 1px solid var(--border);
    border-radius: calc(var(--radius) + 6px);
    background: var(--background);
    color: var(--muted-foreground);
    box-shadow: var(--shadow-sm);
}

.pending-file__preview img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.pending-file__spinner {
    position: absolute;
    inset: 0;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    background: rgba(255, 255, 255, 0.68);
}

.pending-file__spinner::after {
    width: 18px;
    height: 18px;
    border: 2px solid rgba(14, 127, 176, 0.22);
    border-top-color: var(--ocean-blue);
    border-radius: 50%;
    content: '';
    animation: image-upload-spin 760ms linear infinite;
}

@keyframes image-upload-spin {
    to {
        transform: rotate(360deg);
    }
}

.pending-file button {
    position: absolute;
    top: 7px;
    right: 7px;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: rgba(9, 9, 11, 0.92);
    color: var(--primary-foreground);
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.2);
}

.pending-file button:hover {
    background: rgba(39, 39, 42, 0.96);
    color: var(--primary-foreground);
}

.pending-file button:disabled,
.composer-icon-button:disabled {
    cursor: not-allowed;
    opacity: 0.42;
}

.composer {
    display: grid;
    width: 100%;
    min-height: 104px;
    grid-template-columns: 40px 40px minmax(0, 1fr) 42px;
    grid-template-rows: minmax(52px, auto) 42px;
    align-items: end;
    gap: 6px;
    border: 0;
    background: transparent;
    padding: 0;
}

.composer textarea {
    grid-column: 1 / -1;
    grid-row: 1;
    min-height: 52px;
    max-height: 140px;
    resize: none;
    border: 0;
    background: transparent;
    color: var(--foreground);
    font-size: 15px;
    line-height: 1.5;
    outline: none;
    padding: 8px 6px;
}

.composer textarea::placeholder {
    color: var(--muted-foreground);
}

.composer-icon-button {
    grid-row: 2;
    width: 38px;
    height: 38px;
    color: var(--muted-foreground);
}

.composer-icon-button:first-of-type {
    grid-column: 1;
}

.composer-icon-button:nth-of-type(2) {
    grid-column: 2;
}

.send-button {
    grid-column: 4;
    grid-row: 2;
    width: 38px;
    height: 38px;
    border-radius: calc(var(--radius) - 4px);
    background: var(--ocean-blue);
    color: var(--primary-foreground);
    transition:
        background-color 160ms ease,
        opacity 160ms ease,
        transform 160ms ease;
}

.send-button:hover {
    background: var(--ocean-blue-hover);
}

.send-button:disabled {
    cursor: not-allowed;
    opacity: 0.38;
}

.file-input {
    display: none;
}

@media (max-width: 900px) {
    .home-shell {
        grid-template-columns: minmax(0, 1fr);
    }

    .home-shell--sidebar-collapsed {
        grid-template-columns: minmax(0, 1fr);
    }

    .sidebar-scrim {
        position: fixed;
        inset: 0;
        z-index: 3;
        display: block;
        border: 0;
        background: rgba(0, 0, 0, 0.18);
    }

    .conversation-sidebar {
        position: fixed;
        inset: 0 auto 0 0;
        width: min(320px, calc(100vw - 44px));
        height: 100vh;
        height: 100dvh;
        transform: translateX(-102%);
        transition: transform 180ms ease;
    }

    .home-shell--sidebar-collapsed .conversation-sidebar {
        width: min(320px, calc(100vw - 44px));
        align-items: stretch;
        gap: 12px;
        border-right: 1px solid var(--border);
        padding: 12px;
        opacity: 1;
        pointer-events: auto;
    }

    .home-shell--sidebar-collapsed .sidebar-brand {
        width: auto;
        height: 50px;
        flex-basis: 50px;
        justify-content: flex-start;
        overflow: hidden;
        padding: 6px 6px 10px;
    }

    .home-shell--sidebar-collapsed .sidebar-brand__logo {
        width: 34px;
        height: 34px;
    }

    .home-shell--sidebar-collapsed .sidebar-brand__text,
    .home-shell--sidebar-collapsed .new-chat-button,
    .home-shell--sidebar-collapsed .search-field,
    .home-shell--sidebar-collapsed .conversation-groups,
    .home-shell--sidebar-collapsed .sidebar-user-panel {
        opacity: 1;
        pointer-events: auto;
        transform: none;
    }

    .home-shell--sidebar-collapsed .new-chat-button,
    .home-shell--sidebar-collapsed .search-field,
    .home-shell--sidebar-collapsed .sidebar-user-panel {
        position: static;
        width: 100%;
        height: auto;
        left: auto;
        bottom: auto;
        margin-top: 0;
        justify-content: center;
    }

    .home-shell--sidebar-collapsed .conversation-groups {
        display: flex;
    }

    .home-shell--sidebar-collapsed .search-field {
        border-color: var(--input);
        background: var(--background);
        box-shadow: var(--shadow-sm);
    }

    .home-shell--sidebar-collapsed .sidebar-user-panel {
        justify-content: flex-start;
        border-top: 1px solid var(--border);
        padding: 12px 8px 2px;
    }

    .home-shell--sidebar-collapsed .new-chat-button span,
    .home-shell--sidebar-collapsed .search-field span,
    .home-shell--sidebar-collapsed .sidebar-user-panel__identity,
    .home-shell--sidebar-collapsed .sidebar-user-panel__logout {
        opacity: 1;
        pointer-events: auto;
        transform: none;
    }

    .home-shell--sidebar-collapsed .sidebar-brand__text,
    .home-shell--sidebar-collapsed .sidebar-user-panel__identity,
    .home-shell--sidebar-collapsed .sidebar-user-panel__logout {
        display: grid;
    }

    .home-shell--sidebar-collapsed .sidebar-user-panel__logout {
        display: inline-flex;
    }

    .home-shell--sidebar-open .conversation-sidebar {
        transform: translateX(0);
    }

    .chat-header {
        padding: 0 12px;
    }

    .chat-header__actions {
        gap: 2px;
    }
}

@media (max-width: 640px) {
    .chat-workspace {
        --message-bottom-cover-height: 104px;
        --message-scrollbar-gutter: 14px;
        grid-template-rows: 58px minmax(0, 1fr);
    }

    .chat-header h1 {
        font-size: 18px;
    }

    .chat-header__eyebrow {
        display: none;
    }

    .message-list {
        gap: 18px;
        padding: 20px 12px 178px;
    }

    .assistant-mark {
        width: 28px;
        height: 28px;
    }

    .chat-message__content {
        max-width: calc(100vw - 62px);
    }

    .diagnosis-grid {
        grid-template-columns: 1fr;
    }

    .empty-state h2 {
        font-size: 28px;
    }

    .empty-state {
        padding: 20px 20px 170px;
    }

    .composer-area {
        bottom: max(12px, env(safe-area-inset-bottom));
        width: calc(100% - 20px);
        border-radius: 22px;
        padding: 9px;
    }

    .composer {
        grid-template-columns: 36px 36px minmax(0, 1fr) 38px;
        grid-template-rows: minmax(48px, auto) 38px;
        min-height: 94px;
    }

    .composer-icon-button,
    .send-button {
        width: 34px;
        height: 34px;
    }

    .composer textarea {
        min-height: 48px;
        font-size: 14px;
        padding: 7px 4px;
    }

    .pending-file {
        min-width: 190px;
    }
}
</style>
