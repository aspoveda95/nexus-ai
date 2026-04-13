import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import { getIngestBase } from '@/config'
import { useChatStore } from '@/stores/chat'
import type { IngestRequestBody, IngestResponseBody } from '@/types/api'

export type RepoStatus = 'idle' | 'ready' | 'ingesting' | 'error'

export interface RepositoryItem {
  id: string
  label: string
  rootPath: string
  status: RepoStatus
  errorMessage?: string
  lastIngestedAt?: number
  documentsIngested?: number
}

export const useRepositoriesStore = defineStore('repositories', () => {
  const items = ref<RepositoryItem[]>([])
  const searchQuery = ref('')
  const activeId = ref<string | null>(null)

  const filtered = computed(() => {
    const q = searchQuery.value.trim().toLowerCase()
    if (!q) return items.value
    return items.value.filter(
      (r) =>
        r.id.toLowerCase().includes(q) ||
        r.label.toLowerCase().includes(q) ||
        r.rootPath.toLowerCase().includes(q),
    )
  })

  function setActive(id: string | null) {
    if (activeId.value === id) return
    activeId.value = id
    useChatStore().clearConversation()
  }

  function addRepository(payload: { id: string; label: string; rootPath: string }) {
    const exists = items.value.some((r) => r.id === payload.id)
    if (exists) return false
    items.value.push({
      id: payload.id,
      label: payload.label,
      rootPath: payload.rootPath,
      status: 'idle',
    })
    setActive(payload.id)
    return true
  }

  async function runIngest(repositoryId: string): Promise<IngestResponseBody> {
    const repo = items.value.find((r) => r.id === repositoryId)
    if (!repo) throw new Error('Repositorio no encontrado')
    repo.status = 'ingesting'
    repo.errorMessage = undefined
    const body: IngestRequestBody = {
      repository_id: repositoryId,
      root_path: repo.rootPath,
    }
    const base = getIngestBase()
    const res = await fetch(`${base}/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
    if (!res.ok) {
      const text = await res.text()
      repo.status = 'error'
      let msg = text || res.statusText
      try {
        const parsed = JSON.parse(text) as { detail?: unknown }
        if (typeof parsed.detail === 'string') msg = parsed.detail
      } catch {
        /* cuerpo no JSON */
      }
      repo.errorMessage = msg
      throw new Error(msg)
    }
    const data = (await res.json()) as IngestResponseBody
    repo.status = 'ready'
    repo.lastIngestedAt = Date.now()
    repo.documentsIngested = data.documents_ingested
    return data
  }

  return {
    items,
    searchQuery,
    activeId,
    filtered,
    setActive,
    addRepository,
    runIngest,
  }
}, {
  persist: {
    key: 'nexus-ai-repositories',
    paths: ['items', 'searchQuery', 'activeId'],
  },
})
