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

## Repositorios en tu máquina (desarrollo)

Docker monta una carpeta del host en `/data/repos` dentro de **api-core** y **ai-ingestor**:

- Por defecto: `./repos` en la raíz del monorepo (creada vacía; puedes clonar ahí).
- Otra ruta: variable `NEXUS_HOST_REPOS` en `.env` (ruta absoluta o relativa al `docker compose`).

Ejemplo: clonar un proyecto para indexarlo como `acme`:

```bash
mkdir -p repos
git clone https://github.com/org/acme.git repos/acme
```

Ingesta (`repository_id` libre, `root_path` = ruta **dentro del contenedor**):

```bash
curl -s -X POST http://localhost:8100/ingest \
  -H 'Content-Type: application/json' \
  -d '{"repository_id":"acme","root_path":"/data/repos/acme"}'
```

Prueba rápida sin clone: `cp -R samples/demo-repo repos/demo` y usa `repository_id` `demo` con `root_path` `/data/repos/demo`.

## Nx

Tras clonar, instala dependencias de Node: `npm install`.

```bash
npx nx graph
npx nx run api-core:serve
```

## Variables

- `OPENAI_API_KEY`: obligatoria para `mode=cloud` en `/chat/`.
