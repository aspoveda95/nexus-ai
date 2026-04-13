import { getApiBase } from '@/config'
import type { ChatRequestBody, StreamEvent } from '@/types/api'

function handleEvent(ev: StreamEvent, handlers: Parameters<typeof streamChat>[1]) {
  if (ev.type === 'meta') handlers.onMeta(ev)
  else if (ev.type === 'token') handlers.onToken(ev.text)
  else if (ev.type === 'done') handlers.onDone()
  else if (ev.type === 'error')
    handlers.onError(ev.detail + (ev.error ? `: ${ev.error}` : ''))
}

export async function streamChat(
  body: ChatRequestBody,
  handlers: {
    onMeta: (ev: Extract<StreamEvent, { type: 'meta' }>) => void
    onToken: (text: string) => void
    onDone: () => void
    onError: (message: string) => void
  },
  signal?: AbortSignal,
): Promise<void> {
  const base = getApiBase()
  const res = await fetch(`${base}/chat/stream/`, {
    method: 'POST',
    // `Accept: text/event-stream` hace fallar la negociación de DRF (solo JSONRenderer).
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify(body),
    signal,
  })

  if (!res.ok || !res.body) {
    const t = await res.text().catch(() => '')
    handlers.onError(t || `HTTP ${res.status}`)
    return
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const parts = buffer.split('\n\n')
    buffer = parts.pop() ?? ''

    for (const raw of parts) {
      for (const line of raw.split('\n')) {
        const trimmed = line.trim()
        if (!trimmed.startsWith('data:')) continue
        const json = trimmed.replace(/^data:\s*/, '')
        if (!json) continue
        try {
          const ev = JSON.parse(json) as StreamEvent
          handleEvent(ev, handlers)
        } catch {
          /* ignore */
        }
      }
    }
  }

  const tail = buffer.trim()
  if (tail) {
    for (const line of tail.split('\n')) {
      const trimmed = line.trim()
      if (!trimmed.startsWith('data:')) continue
      const json = trimmed.replace(/^data:\s*/, '')
      if (!json) continue
      try {
        const ev = JSON.parse(json) as StreamEvent
        handleEvent(ev, handlers)
      } catch {
        /* ignore */
      }
    }
  }
}
