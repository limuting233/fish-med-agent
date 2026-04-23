<script lang="ts" setup>
import { computed, nextTick, ref } from 'vue'
import {
  Clock,
  FileImage,
  Menu,
  MessageCircle,
  Mic,
  MoreHorizontal,
  Paperclip,
  Plus,
  Search,
  SendHorizontal,
  Sparkles,
  X,
} from 'lucide-vue-next'

type ConversationGroup = 'today' | 'week' | 'earlier'

type Conversation = {
  id: string
  title: string
  summary: string
  time: string
  group: ConversationGroup
}

type Attachment = {
  id: string
  name: string
  size: string
  type: 'image' | 'file'
  previewUrl?: string
}

type DiagnosisSection = {
  title: string
  body: string
}

type ChatMessage = {
  id: string
  role: 'user' | 'assistant'
  content: string
  time: string
  attachments?: Attachment[]
  sections?: DiagnosisSection[]
  pending?: boolean
}

const sidebarOpen = ref(false)
const selectedConversationId = ref('conv-1')
const draftMessage = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const pendingAttachments = ref<Attachment[]>([])
const searchOpen = ref(false)
const searchQuery = ref('')
const searchDialogInput = ref<HTMLInputElement | null>(null)

const conversations = ref<Conversation[]>([
  {
    id: 'conv-1',
    title: '草鱼体表白点',
    summary: '建议补充水温、死亡数量与近期用药',
    time: '14:32',
    group: 'today',
  },
  {
    id: 'conv-2',
    title: '鲈鱼鳃部发红',
    summary: '关注溶氧、氨氮与摄食变化',
    time: '10:18',
    group: 'today',
  },
  {
    id: 'conv-3',
    title: '池塘鱼群浮头',
    summary: '优先排查缺氧和水质突变',
    time: '昨天',
    group: 'week',
  },
  {
    id: 'conv-4',
    title: '罗非鱼体表溃烂',
    summary: '记录病灶扩散速度与死亡数量',
    time: '周一',
    group: 'week',
  },
  {
    id: 'conv-5',
    title: '虾塘水色异常',
    summary: '结合水色、透明度和换水记录判断',
    time: '4月12日',
    group: 'earlier',
  },
])

const messages = ref<Record<string, ChatMessage[]>>({
  'conv-1': [
    {
      id: 'msg-1',
      role: 'user',
      content: '草鱼体表出现白点，近两天摄食下降，水温约 24℃。',
      time: '14:28',
      attachments: [
        {
          id: 'att-1',
          name: 'fish-lesion.jpg',
          size: '2.4 MB',
          type: 'image',
        },
      ],
    },
    {
      id: 'msg-2',
      role: 'assistant',
      content: '初步判断需要把体表白点、鳃部状态和水质变化放在一起看。',
      time: '14:32',
      sections: [
        {
          title: '可能病因',
          body: '寄生虫性白点、细菌继发感染或水质波动均可能造成相似表现。',
        },
        {
          title: '需要补充确认',
          body: '补充死亡数量、鳃丝颜色、是否蹭池、近期换水和用药记录。',
        },
        {
          title: '处置建议',
          body: '先检测溶氧、氨氮、亚硝酸盐，隔离明显病鱼，避免盲目混用药物。',
        },
        {
          title: '风险提示',
          body: '若死亡数量上升或鱼群大面积浮头，应尽快联系水产技术人员现场确认。',
        },
      ],
    },
  ],
  'conv-2': [
    {
      id: 'msg-3',
      role: 'assistant',
      content: '当前会话还缺少图片和水质参数。可以先描述鱼种、症状持续时间和摄食变化。',
      time: '10:18',
      pending: true,
    },
  ],
  'conv-3': [],
  'conv-4': [],
  'conv-5': [],
})

const samplePrompts = ['鱼体表白点', '鳃部发红', '鱼群浮头']
const fallbackConversation: Conversation = {
  id: 'fallback',
  title: '新的鱼病问诊',
  summary: '等待症状描述与图片',
  time: '刚刚',
  group: 'today',
}

const groupedConversations = computed(() => [
  {
    label: '今天',
    items: conversations.value.filter((conversation) => conversation.group === 'today'),
  },
  {
    label: '最近 7 天',
    items: conversations.value.filter((conversation) => conversation.group === 'week'),
  },
  {
    label: '更早',
    items: conversations.value.filter((conversation) => conversation.group === 'earlier'),
  },
])

const activeConversation = computed<Conversation>(() => {
  return conversations.value.find((conversation) => conversation.id === selectedConversationId.value) ?? fallbackConversation
})

const activeMessages = computed(() => messages.value[selectedConversationId.value] ?? [])

const canSend = computed(() => {
  return draftMessage.value.trim().length > 0 || pendingAttachments.value.length > 0
})

const searchResults = computed(() => {
  const query = searchQuery.value.trim().toLowerCase()

  if (!query) {
    return conversations.value
  }

  return conversations.value.filter((conversation) => {
    return [conversation.title, conversation.summary, conversation.time].some((value) => value.toLowerCase().includes(query))
  })
})

function selectConversation(conversationId: string) {
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

function selectSearchResult(conversationId: string) {
  selectConversation(conversationId)
  closeSearch()
}

function createConversation() {
  const id = createId('conv')
  const conversation: Conversation = {
    id,
    title: '新的鱼病问诊',
    summary: '等待症状描述与图片',
    time: '刚刚',
    group: 'today',
  }

  conversations.value.unshift(conversation)
  messages.value[id] = []
  selectedConversationId.value = id
  draftMessage.value = ''
  pendingAttachments.value = []
  sidebarOpen.value = false
}

function choosePrompt(prompt: string) {
  draftMessage.value = prompt
}

function openFilePicker() {
  fileInput.value?.click()
}

function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const selectedFiles = Array.from(input.files ?? [])
  const availableSlots = Math.max(0, 5 - pendingAttachments.value.length)

  selectedFiles.slice(0, availableSlots).forEach((file) => {
    const isImage = file.type.startsWith('image/')
    pendingAttachments.value.push({
      id: createId('attachment'),
      name: file.name,
      size: formatFileSize(file.size),
      type: isImage ? 'image' : 'file',
      previewUrl: isImage ? URL.createObjectURL(file) : undefined,
    })
  })

  input.value = ''
}

function removePendingAttachment(attachmentId: string) {
  const attachment = pendingAttachments.value.find((item) => item.id === attachmentId)

  if (attachment?.previewUrl) {
    URL.revokeObjectURL(attachment.previewUrl)
  }

  pendingAttachments.value = pendingAttachments.value.filter((item) => item.id !== attachmentId)
}

function sendMessage() {
  if (!canSend.value) {
    return
  }

  const activeId = selectedConversationId.value
  const content = draftMessage.value.trim()
  const outgoingAttachments = pendingAttachments.value.map((attachment) => ({ ...attachment }))
  const currentMessages = messages.value[activeId] ?? []
  const now = '刚刚'

  messages.value[activeId] = [
    ...currentMessages,
    {
      id: createId('msg'),
      role: 'user',
      content: content || '已上传图片',
      time: now,
      attachments: outgoingAttachments,
    },
    {
      id: createId('msg'),
      role: 'assistant',
      content: '已收到本次问诊信息。',
      time: now,
      pending: true,
    },
  ]

  const active = conversations.value.find((conversation) => conversation.id === activeId)
  if (active) {
    active.title = content ? content.slice(0, 18) : '图片问诊'
    active.summary = '等待诊断结果'
    active.time = now
  }

  draftMessage.value = ''
  pendingAttachments.value = []
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
</script>

<template>
  <div class="home-shell" :class="{ 'home-shell--sidebar-open': sidebarOpen }">
    <button
      v-if="sidebarOpen"
      class="sidebar-scrim"
      type="button"
      aria-label="关闭会话列表"
      @click="sidebarOpen = false"
    ></button>

    <div v-if="searchOpen" class="search-dialog-layer" role="presentation" @keydown.esc.stop.prevent="closeSearch">
      <button class="search-dialog-scrim" type="button" aria-label="关闭搜索" @click="closeSearch"></button>

      <section class="search-dialog" role="dialog" aria-modal="true" aria-labelledby="search-dialog-title">
        <div class="search-dialog__header">
          <Search :size="20" stroke-width="2" aria-hidden="true" />
          <input
            ref="searchDialogInput"
            v-model="searchQuery"
            type="search"
            placeholder="搜索历史对话"
            aria-label="搜索历史对话"
          />
          <button class="search-dialog__close" type="button" aria-label="关闭搜索" @click="closeSearch">
            <X :size="18" stroke-width="2" />
          </button>
        </div>

        <div class="search-dialog__body">
          <p id="search-dialog-title" class="search-dialog__title">历史对话</p>

          <div v-if="searchResults.length" class="search-dialog__list">
            <button
              v-for="conversation in searchResults"
              :key="conversation.id"
              class="search-dialog__item"
              type="button"
              @click="selectSearchResult(conversation.id)"
            >
              <span class="search-dialog__item-main">
                <span>{{ conversation.title }}</span>
                <small>{{ conversation.summary }}</small>
              </span>
              <span class="search-dialog__time">{{ conversation.time }}</span>
            </button>
          </div>

          <div v-else class="search-dialog__empty">没有匹配的历史对话</div>
        </div>
      </section>
    </div>

    <aside class="conversation-sidebar" aria-label="会话列表">
      <div class="sidebar-brand">
        <img class="sidebar-brand__logo" src="/images/SHOU_logo.svg" alt="上海海洋大学校徽" />
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
        <section v-for="group in groupedConversations" :key="group.label" class="conversation-group">
          <h2 class="conversation-group__title">{{ group.label }}</h2>

          <button
            v-for="conversation in group.items"
            :key="conversation.id"
            class="conversation-item"
            :class="{ 'conversation-item--active': conversation.id === selectedConversationId }"
            type="button"
            @click="selectConversation(conversation.id)"
          >
            <span class="conversation-item__topline">
              <span class="conversation-item__title">{{ conversation.title }}</span>
              <span class="conversation-item__time">{{ conversation.time }}</span>
            </span>
            <span class="conversation-item__summary">{{ conversation.summary }}</span>
          </button>
        </section>
      </nav>
    </aside>

    <main class="chat-workspace">
      <header class="chat-header">
        <button class="mobile-menu-button" type="button" aria-label="打开会话列表" @click="sidebarOpen = true">
          <Menu :size="20" stroke-width="2" />
        </button>

        <div class="chat-header__title-block">
          <p class="chat-header__eyebrow">鱼病问诊</p>
          <h1>{{ activeConversation.title }}</h1>
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

      <section class="message-pane" aria-label="当前会话消息">
        <div v-if="activeMessages.length > 0" class="message-list">
          <article
            v-for="message in activeMessages"
            :key="message.id"
            class="chat-message"
            :class="`chat-message--${message.role}`"
          >
            <div v-if="message.role === 'assistant'" class="assistant-mark" aria-hidden="true">
              <Sparkles :size="16" stroke-width="2" />
            </div>

            <div class="chat-message__content">
              <div class="chat-message__meta">
                <span>{{ message.role === 'assistant' ? 'Fish Med Agent' : '你' }}</span>
                <time>{{ message.time }}</time>
              </div>

              <div class="message-bubble" :class="{ 'message-bubble--pending': message.pending }">
                <p>{{ message.content }}</p>

                <div v-if="message.attachments?.length" class="message-attachments">
                  <div v-for="attachment in message.attachments" :key="attachment.id" class="message-attachment">
                    <div class="message-attachment__thumb">
                      <img v-if="attachment.previewUrl" :src="attachment.previewUrl" :alt="attachment.name" />
                      <FileImage v-else :size="18" stroke-width="2" />
                    </div>
                    <div>
                      <span>{{ attachment.name }}</span>
                      <small>{{ attachment.size }}</small>
                    </div>
                  </div>
                </div>

                <div v-if="message.sections?.length" class="diagnosis-grid">
                  <section v-for="section in message.sections" :key="section.title" class="diagnosis-section">
                    <h2>{{ section.title }}</h2>
                    <p>{{ section.body }}</p>
                  </section>
                </div>
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
          <div v-for="attachment in pendingAttachments" :key="attachment.id" class="pending-file">
            <div class="pending-file__preview">
              <img v-if="attachment.previewUrl" :src="attachment.previewUrl" :alt="attachment.name" />
              <FileImage v-else :size="18" stroke-width="2" />
            </div>
            <div class="pending-file__text">
              <span>{{ attachment.name }}</span>
              <small>{{ attachment.size }}</small>
            </div>
            <button type="button" :aria-label="`移除 ${attachment.name}`" @click="removePendingAttachment(attachment.id)">
              <X :size="15" stroke-width="2" />
            </button>
          </div>
        </div>

        <form class="composer" @submit.prevent="sendMessage">
          <button class="composer-icon-button" type="button" aria-label="语音输入">
            <Mic :size="19" stroke-width="2" />
          </button>

          <button class="composer-icon-button" type="button" aria-label="上传图片" @click="openFilePicker">
            <Paperclip :size="19" stroke-width="2" />
          </button>

          <textarea
            v-model="draftMessage"
            rows="1"
            placeholder="输入鱼种、症状、水温、发病时长..."
            @keydown.enter.exact.prevent="sendMessage"
          ></textarea>

          <button class="send-button" type="submit" :disabled="!canSend" aria-label="发送">
            <SendHorizontal :size="19" stroke-width="2.2" />
          </button>

          <input ref="fileInput" class="file-input" type="file" accept="image/*" multiple @change="handleFileChange" />
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
  font-family: Inter, "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif;
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
  place-items: center;
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
  align-items: center;
  gap: 10px;
  border: 1px solid transparent;
  border-radius: var(--radius);
  padding: 6px 6px 10px;
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
  color: var(--muted-foreground);
  font-size: 12px;
  line-height: 1.2;
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
  display: grid;
  width: 100%;
  gap: 5px;
  border: 1px solid transparent;
  border-radius: calc(var(--radius) - 2px);
  background: transparent;
  padding: 10px 11px;
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
  min-width: 0;
  align-items: center;
  gap: 10px;
}

.conversation-item__title,
.conversation-item__summary {
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

.conversation-item__summary {
  color: var(--muted-foreground);
  font-size: 12px;
  line-height: 1.2;
}

.chat-workspace {
  position: relative;
  display: grid;
  min-width: 0;
  min-height: 0;
  height: 100%;
  grid-template-rows: 65px minmax(0, 1fr);
  overflow: hidden;
  background: var(--background);
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
  display: none;
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

.header-icon-button:hover,
.mobile-menu-button:hover,
.composer-icon-button:hover {
  background: var(--accent);
  color: var(--accent-foreground);
}

.header-icon-button:active,
.mobile-menu-button:active,
.composer-icon-button:active,
.send-button:active {
  transform: scale(0.96);
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
  gap: 22px;
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

.message-bubble {
  display: grid;
  gap: 12px;
  border-radius: var(--radius);
  color: var(--foreground);
  font-size: 14px;
  line-height: 1.55;
}

.chat-message--user .message-bubble {
  border: 1px solid var(--border);
  background: var(--secondary);
  color: var(--secondary-foreground);
  padding: 12px 14px;
}

.chat-message--assistant .message-bubble {
  border: 1px solid var(--border);
  background: var(--card);
  box-shadow: var(--shadow-sm);
  padding: 14px;
}

.message-bubble p {
  margin: 0;
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
}

.pending-files {
  display: flex;
  width: 100%;
  gap: 8px;
  overflow-x: auto;
  overscroll-behavior-x: contain;
}

.pending-file {
  display: flex;
  min-width: 220px;
  max-width: 280px;
  align-items: center;
  gap: 8px;
  border: 1px solid var(--border);
  border-radius: calc(var(--radius) - 2px);
  background: var(--muted);
  padding: 7px;
}

.pending-file__preview {
  display: inline-flex;
  width: 42px;
  height: 42px;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: calc(var(--radius) - 4px);
  background: var(--background);
  color: var(--muted-foreground);
}

.pending-file__preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.pending-file__text {
  min-width: 0;
  flex: 1;
}

.pending-file button {
  width: 28px;
  height: 28px;
  flex: 0 0 auto;
  border-radius: 50%;
  background: transparent;
  color: var(--muted-foreground);
}

.pending-file button:hover {
  background: var(--accent);
  color: var(--accent-foreground);
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

  .home-shell--sidebar-open .conversation-sidebar {
    transform: translateX(0);
  }

  .mobile-menu-button {
    display: inline-flex;
    flex: 0 0 auto;
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
