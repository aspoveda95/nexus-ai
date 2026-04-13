# Nexus-AI

Monorepo ([Nx](https://nx.dev)) para una plataforma agnóstica de onboarding técnico y orquestación de ingeniería: **api-core** (Django REST Framework), **ai-ingestor** (RAG con LangChain + Ollama), **PostgreSQL**, **Redis**, **ChromaDB**.

## Requisitos

- Docker / Docker Compose
- Ollama en el host con modelos `llama3` y `nomic-embed-text` (para embeddings y modo `local`)

## Arranque

```bash
docker compose up --build
```

- API: `http://localhost:8000/chat/` (POST JSON: `repository_id`, `message`, `mode`: `local` | `cloud`)
- Ingestor: `http://localhost:8100/ingest` (POST: `repository_id`, `root_path`)
- Chroma (HTTP): `http://localhost:8001`

Los contenedores acceden a Ollama vía `host.docker.internal:11434`.

## Ingesta de ejemplo

1. Añade un bind mount para que el contenedor vea el repo de prueba, por ejemplo en un `docker-compose.override.yml` local:

```yaml
services:
  ai-ingestor:
    volumes:
      - ./samples/demo-repo:/data/repos/demo:ro
```

2. Con el stack arriba, ejecuta la ingesta:

```bash
curl -s -X POST http://localhost:8100/ingest \
  -H 'Content-Type: application/json' \
  -d '{"repository_id":"demo","root_path":"/data/repos/demo"}'
```

## Nx

Tras clonar, instala dependencias de Node: `npm install`.

```bash
npx nx graph
npx nx run api-core:serve
```

## Variables

- `OPENAI_API_KEY`: obligatoria para `mode=cloud` en `/chat/`.
