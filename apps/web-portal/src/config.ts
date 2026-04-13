/** Base URL del api-core (sin barra final). En dev usa proxy `/nexus-api`. */
export function getApiBase(): string {
  const raw = import.meta.env.VITE_API_BASE
  if (raw) return raw.replace(/\/$/, '')
  return import.meta.env.DEV ? '/nexus-api' : 'http://127.0.0.1:8000'
}

/** Base URL del ai-ingestor. */
export function getIngestBase(): string {
  const raw = import.meta.env.VITE_INGEST_BASE
  if (raw) return raw.replace(/\/$/, '')
  return import.meta.env.DEV ? '/nexus-ingest' : 'http://127.0.0.1:8100'
}
