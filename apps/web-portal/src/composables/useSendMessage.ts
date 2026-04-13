import { ref } from 'vue'

import { streamChat } from '@/composables/useChatStream'
import { useChatStore } from '@/stores/chat'
import { useRepositoriesStore } from '@/stores/repositories'

export function useSendMessage() {
  const chat = useChatStore()
  const repos = useRepositoriesStore()
  const abort = ref<AbortController | null>(null)

  async function send(text: string) {
    const trimmed = text.trim()
    const repoId = repos.activeId
    if (!trimmed || !repoId || chat.isSending) return

    abort.value?.abort()
    abort.value = new AbortController()

    chat.appendUserMessage(trimmed)
    const assistantId = chat.startAssistantMessage()
    chat.isSending = true
    chat.lastError = null

    let buffer = ''
    let finished = false

    try {
      await streamChat(
        {
          repository_id: repoId,
          message: trimmed,
          mode: chat.mode,
          top_k: 8,
        },
        {
          onMeta: (ev) => {
            chat.setSourceChunks(ev.source_chunks)
            chat.patchAssistantMessage(assistantId, {
              citations: ev.citations,
            })
          },
          onToken: (t) => {
            buffer += t
            chat.patchAssistantMessage(assistantId, {
              content: buffer,
            })
          },
          onDone: () => {
            finished = true
            chat.patchAssistantMessage(assistantId, {
              streaming: false,
              content: buffer,
            })
          },
          onError: (message) => {
            finished = true
            chat.lastError = message
            chat.patchAssistantMessage(assistantId, {
              streaming: false,
              content:
                buffer ||
                `No se pudo completar la respuesta. ${message}`.trim(),
            })
          },
        },
        abort.value.signal,
      )
    } finally {
      if (!finished) {
        chat.patchAssistantMessage(assistantId, { streaming: false, content: buffer })
      }
      chat.isSending = false
    }
  }

  function stop() {
    abort.value?.abort()
  }

  return { send, stop }
}
