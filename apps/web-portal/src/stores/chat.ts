import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

import { getApiBase } from '@/config'
import type {
  ChatMode,
  ChatCitation,
  ConversationListBody,
  ConversationSummary,
  SourceChunk,
} from '@/types/api'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
  citations?: ChatCitation[]
}

function uid(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 9)}`
}

export const useChatStore = defineStore('chat', () => {
  const mode = ref<ChatMode>('local')
  const conversationId = ref<string | null>(null)
  const messages = ref<ChatMessage[]>([])
  const sourceChunks = ref<SourceChunk[]>([])
  const highlightedSourcePath = ref<string | null>(null)
  const isSending = ref(false)
  const lastError = ref<string | null>(null)
  const isHydrating = ref(false)
  const conversationThreads = ref<ConversationSummary[]>([])
  const threadsLoading = ref(false)

  watch(
    () => messages.value.length,
    () => {
      lastError.value = null
    },
  )

  function setMode(next: ChatMode) {
    mode.value = next
  }

  function appendUserMessage(text: string) {
    messages.value.push({
      id: uid(),
      role: 'user',
      content: text.trim(),
    })
  }

  function startAssistantMessage() {
    const id = uid()
    messages.value.push({
      id,
      role: 'assistant',
      content: '',
      streaming: true,
    })
    return id
  }

  function patchAssistantMessage(id: string, patch: Partial<ChatMessage>) {
    const m = messages.value.find((x) => x.id === id)
    if (!m || m.role !== 'assistant') return
    Object.assign(m, patch)
  }

  function setSourceChunks(chunks: SourceChunk[]) {
    sourceChunks.value = chunks
  }

  function setHighlightedPath(path: string | null) {
    highlightedSourcePath.value = path
  }

  function setConversationId(id: string | null) {
    conversationId.value = id
  }

  function clearConversation() {
    conversationId.value = null
    messages.value = []
    sourceChunks.value = []
    highlightedSourcePath.value = null
  }

  async function fetchConversationThreads(repositoryId: string | null) {
    if (!repositoryId) {
      conversationThreads.value = []
      return
    }
    threadsLoading.value = true
    try {
      const base = getApiBase()
      const res = await fetch(
        `${base}/chat/conversations/?repository_id=${encodeURIComponent(repositoryId)}`,
      )
      if (!res.ok) {
        conversationThreads.value = []
        return
      }
      const data = (await res.json()) as ConversationListBody
      conversationThreads.value = data.conversations ?? []
    } finally {
      threadsLoading.value = false
    }
  }

  /** Carga mensajes desde el backend (p. ej. tras recargar si conoces el UUID del hilo). */
  async function hydrateFromBackend(repositoryId: string, threadId: string): Promise<boolean> {
    const base = getApiBase()
    const url = `${base}/chat/conversations/${encodeURIComponent(threadId)}/?repository_id=${encodeURIComponent(repositoryId)}`
    isHydrating.value = true
    lastError.value = null
    try {
      const res = await fetch(url)
      if (!res.ok) {
        lastError.value = await res.text().catch(() => res.statusText)
        return false
      }
      const data = (await res.json()) as {
        id: string
        messages: Array<{ id: string; role: 'user' | 'assistant'; content: string }>
      }
      conversationId.value = data.id
      messages.value = data.messages.map((m) => ({
        id: m.id,
        role: m.role,
        content: m.content,
        streaming: false,
      }))
      sourceChunks.value = []
      highlightedSourcePath.value = null
      void fetchConversationThreads(repositoryId)
      return true
    } finally {
      isHydrating.value = false
    }
  }

  return {
    mode,
    conversationId,
    messages,
    sourceChunks,
    conversationThreads,
    threadsLoading,
    highlightedSourcePath,
    isSending,
    lastError,
    isHydrating,
    setMode,
    appendUserMessage,
    startAssistantMessage,
    patchAssistantMessage,
    setSourceChunks,
    setHighlightedPath,
    setConversationId,
    clearConversation,
    fetchConversationThreads,
    hydrateFromBackend,
    uid,
  }
}, {
  persist: {
    key: 'nexus-ai-chat-v2',
    paths: ['mode'],
  },
})
