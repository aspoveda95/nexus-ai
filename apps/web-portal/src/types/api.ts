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
  /** UUID del hilo en el backend; omitir para iniciar conversación nueva. */
  conversation_id?: string
}

export interface ChatResponseBody {
  answer: string
  mode: ChatMode
  repository_id: string
  conversation_id: string
  citations: ChatCitation[]
  source_chunks: SourceChunk[]
}

export interface ConversationHydrateMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

export interface ConversationDetailBody {
  id: string
  repository_id: string
  messages: ConversationHydrateMessage[]
}

export interface ConversationSummary {
  id: string
  repository_id: string
  updated_at: string
  preview: string
}

export interface ConversationListBody {
  conversations: ConversationSummary[]
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
      conversation_id: string
    }
  | { type: 'token'; text: string }
  | { type: 'done' }
  | { type: 'error'; detail: string; error?: string; conversation_id?: string }
