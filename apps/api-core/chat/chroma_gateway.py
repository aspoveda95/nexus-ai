"""Cliente tipado hacia Chroma (HTTP) para recuperación RAG."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Sequence

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from chat.tenant import chroma_collection_name


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
    """Recupera documentos relevantes para el prompt del LLM."""
    store: Chroma = build_vectorstore(repository_id=repository_id, settings=settings)
    documents: List[Document] = store.similarity_search(user_query, k=top_k)
    return documents


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
