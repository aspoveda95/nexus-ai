import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

import type { ChatMode, ChatCitation, SourceChunk } from '@/types/api'

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
  const messages = ref<ChatMessage[]>([])
  const sourceChunks = ref<SourceChunk[]>([])
  const highlightedSourcePath = ref<string | null>(null)
  const isSending = ref(false)
  const lastError = ref<string | null>(null)

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

  function clearConversation() {
    messages.value = []
    sourceChunks.value = []
    highlightedSourcePath.value = null
  }

  return {
    mode,
    messages,
    sourceChunks,
    highlightedSourcePath,
    isSending,
    lastError,
    setMode,
    appendUserMessage,
    startAssistantMessage,
    patchAssistantMessage,
    setSourceChunks,
    setHighlightedPath,
    clearConversation,
    uid,
  }
}, {
  persist: {
    key: 'nexus-ai-chat',
    paths: ['mode', 'messages', 'sourceChunks', 'highlightedSourcePath'],
    afterRestore: ({ store }) => {
      const s = store as unknown as {
        messages: ChatMessage[]
        isSending: boolean
        lastError: string | null
      }
      if (Array.isArray(s.messages) && s.messages.length) {
        s.messages = s.messages.map((m) => ({ ...m, streaming: false }))
      }
      s.isSending = false
      s.lastError = null
    },
  },
})
