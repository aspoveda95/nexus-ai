"""Cliente tipado hacia Chroma (HTTP) para recuperación RAG."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Final, List, Sequence

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from chat.tenant import chroma_collection_name

# Rutas citadas en la pregunta (mantener alineado con apps/ai-ingestor/nexus_ingestor/rag/loaders.py).
_PATH_HINT_EXTENSIONS: Final[tuple[str, ...]] = tuple(
    sorted(
        frozenset(
            ext.lstrip(".")
            for ext in (
                ".js",
                ".jsx",
                ".mjs",
                ".cjs",
                ".ts",
                ".tsx",
                ".vue",
                ".svelte",
                ".astro",
                ".py",
                ".pyi",
                ".java",
                ".kt",
                ".kts",
                ".gradle",
                ".scala",
                ".sc",
                ".groovy",
                ".c",
                ".h",
                ".cpp",
                ".cc",
                ".cxx",
                ".hpp",
                ".hxx",
                ".inl",
                ".go",
                ".rs",
                ".swift",
                ".cs",
                ".fs",
                ".vb",
                ".sh",
                ".bash",
                ".zsh",
                ".fish",
                ".ps1",
                ".psm1",
                ".bat",
                ".cmd",
                ".pl",
                ".pm",
                ".dart",
                ".rb",
                ".php",
                ".r",
                ".lua",
                ".ex",
                ".exs",
                ".erl",
                ".hrl",
                ".clj",
                ".cljs",
                ".edn",
                ".hs",
                ".ml",
                ".mli",
                ".nim",
                ".zig",
                ".v",
                ".sv",
                ".md",
                ".mdx",
                ".rst",
                ".adoc",
                ".asciidoc",
                ".tex",
                ".json",
                ".jsonc",
                ".yaml",
                ".yml",
                ".toml",
                ".ini",
                ".cfg",
                ".conf",
                ".properties",
                ".xml",
                ".plist",
                ".html",
                ".htm",
                ".css",
                ".scss",
                ".sass",
                ".less",
                ".sql",
                ".graphql",
                ".gql",
                ".proto",
                ".tf",
                ".tfvars",
                ".prisma",
                ".nix",
                ".cmake",
                ".gotmpl",
                ".tpl",
            )
        ),
        key=len,
        reverse=True,
    )
)
_MENTIONED_PATH_RE = re.compile(
    r"\b((?:[\w.-]+/)*[\w.-]+\.(?:"
    + "|".join(_PATH_HINT_EXTENSIONS)
    + r"))\b",
    re.IGNORECASE,
)


def _mentioned_source_paths(user_query: str) -> List[str]:
    """Extrae posibles `source` de metadatos citados en texto natural."""
    return list(dict.fromkeys(_MENTIONED_PATH_RE.findall(user_query)))


def _batch_to_documents(batch: dict[str, Any]) -> List[Document]:
    texts: List[str] = list(batch.get("documents") or [])
    metas: List[dict[str, Any]] = list(batch.get("metadatas") or [])
    out: List[Document] = []
    for i, text in enumerate(texts):
        meta = metas[i] if i < len(metas) else {}
        out.append(Document(page_content=text or "", metadata=dict(meta)))
    return out


def _documents_for_source_metadata(store: Chroma, source_path: str) -> List[Document]:
    """Recupera fragmentos con `source` exacta: API nativa de Chroma (más fiable que el wrapper)."""
    collection = getattr(store, "_collection", None)
    if collection is not None:
        for where in (
            {"source": source_path},
            {"source": {"$eq": source_path}},
        ):
            try:
                batch = collection.get(where=where, include=["documents", "metadatas"])
                docs = _batch_to_documents(batch)
                if docs:
                    return docs
            except Exception:
                continue

    getter = getattr(store, "get", None)
    if callable(getter):
        for where in (
            {"source": source_path},
            {"source": {"$eq": source_path}},
        ):
            try:
                batch = getter(where=where, include=["documents", "metadatas"])
                docs = _batch_to_documents(batch)
                if docs:
                    return docs
            except Exception:
                continue
    return []


def _chunks_by_semantic_path_match(
    store: Chroma,
    source_path: str,
    user_query: str,
    pool_k: int,
) -> List[Document]:
    """Si `get`/`where` fallan, la query por la propia ruta suele alinear mejor el embedding."""
    out: List[Document] = []
    seen: set[tuple[str, str]] = set()
    for q in (source_path, f"{user_query} {source_path}", user_query):
        try:
            pool = store.similarity_search(q, k=pool_k)
        except Exception:
            continue
        for d in pool:
            if str(d.metadata.get("source", "")) != source_path:
                continue
            sig = (source_path, d.page_content[:200])
            if sig in seen:
                continue
            seen.add(sig)
            out.append(d)
        if out:
            break
    return out


@dataclass(frozen=True, slots=True)
class ChromaGatewaySettings:
    http_host: str
    http_port: int
    ollama_base_url: str
    embed_model: str


def load_chroma_settings_from_env() -> ChromaGatewaySettings:
    host: str = os.environ.get("CHROMA_HTTP_HOST", "127.0.0.1")
    port_raw: str = os.environ.get("CHROMA_HTTP_PORT", "8000")
    ollama_base: str = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    embed_model: str = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    return ChromaGatewaySettings(
        http_host=host,
        http_port=int(port_raw),
        ollama_base_url=ollama_base,
        embed_model=embed_model,
    )


def build_vectorstore(
    *,
    repository_id: str,
    settings: ChromaGatewaySettings,
) -> Chroma:
    """Construye el vector store apuntando a la collection del repositorio."""
    client: chromadb.HttpClient = chromadb.HttpClient(
        host=settings.http_host,
        port=settings.http_port,
    )
    embeddings = OllamaEmbeddings(
        model=settings.embed_model,
        base_url=settings.ollama_base_url,
    )
    collection: str = chroma_collection_name(repository_id)
    return Chroma(
        client=client,
        collection_name=collection,
        embedding_function=embeddings,
    )


def retrieve_context_documents(
    *,
    repository_id: str,
    user_query: str,
    top_k: int,
    settings: ChromaGatewaySettings,
) -> List[Document]:
    """Recupera documentos relevantes para el prompt del LLM.

    Si la pregunta cita rutas de archivo (`lib/main.dart`, etc.), se incluyen primero
    todos los fragmentos con esa metadata `source` para evitar que el embedding ignore
    el archivo y el modelo caiga en conocimiento genérico (p. ej. plantilla Flutter).
    """
    store: Chroma = build_vectorstore(repository_id=repository_id, settings=settings)
    paths = _mentioned_source_paths(user_query)
    merged: List[Document] = []
    seen: set[tuple[str, str]] = set()

    def _sig(doc: Document) -> tuple[str, str]:
        return (str(doc.metadata.get("source", "")), doc.page_content)

    def _add(docs: Sequence[Document]) -> None:
        for d in docs:
            s = _sig(d)
            if s in seen:
                continue
            seen.add(s)
            merged.append(d)

    pool_k = max(24, top_k * 4)

    for path in paths:
        got = _documents_for_source_metadata(store, path)
        if not got:
            try:
                got = store.similarity_search(
                    user_query,
                    k=max(8, top_k),
                    filter={"source": path},
                )
            except Exception:
                got = []
        if not got:
            got = _chunks_by_semantic_path_match(store, path, user_query, pool_k)
        _add(got)

    _add(store.similarity_search(user_query, k=top_k))

    return merged[:top_k]


def format_context_block(documents: Sequence[Document]) -> str:
    """Serializa el contexto recuperado exigiendo trazabilidad por metadata."""
    blocks: List[str] = []
    for index, doc in enumerate(documents, start=1):
        source: str = str(doc.metadata.get("source", "desconocido"))
        repo: str = str(doc.metadata.get("repository_id", ""))
        lang: str = str(doc.metadata.get("language", ""))
        header: str = f"[{index}] archivo={source}"
        if repo:
            header += f" | repositorio={repo}"
        if lang:
            header += f" | lenguaje={lang}"
        blocks.append(f"{header}\n{doc.page_content.strip()}")
    return "\n\n---\n\n".join(blocks)
