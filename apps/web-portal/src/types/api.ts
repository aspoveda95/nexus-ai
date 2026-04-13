export type ChatMode = 'local' | 'cloud'

export interface ChatCitation {
  source_path: string
  repository_id: string
}

export interface SourceChunk {
  source_path: string
  repository_id: string
  language: string
  content: string
}

export interface ChatRequestBody {
  repository_id: string
  message: string
  mode: ChatMode
  top_k?: number
}

export interface ChatResponseBody {
  answer: string
  mode: ChatMode
  repository_id: string
  citations: ChatCitation[]
  source_chunks: SourceChunk[]
}

export interface IngestRequestBody {
  repository_id: string
  root_path: string
}

export interface IngestResponseBody {
  repository_id: string
  root_path: string
  documents_ingested: number
  collection_name: string
}

export type StreamEvent =
  | {
      type: 'meta'
      citations: ChatCitation[]
      source_chunks: SourceChunk[]
      repository_id: string
      mode: ChatMode
    }
  | { type: 'token'; text: string }
  | { type: 'done' }
  | { type: 'error'; detail: string; error?: string }
