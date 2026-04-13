"""Pipeline de ingesta: recorrido → troceado → embeddings → Chroma."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final

import chromadb
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings

from nexus_ingestor.config import IngestorSettings
from nexus_ingestor.rag.loaders import RepositoryScanConfig, load_repository_documents
from nexus_ingestor.rag.splitters import split_documents
from nexus_ingestor.tenant import chroma_collection_name

BATCH_SIZE: Final[int] = 128


@dataclass(frozen=True, slots=True)
class IngestionSummary:
    repository_id: str
    root_path: str
    documents_ingested: int
    collection_name: str


def _assert_allowed_root(*, candidate: Path, settings: IngestorSettings) -> Path:
    resolved: Path = candidate.resolve()
    base: Path = Path(settings.allowed_repo_root).resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise PermissionError(
            "La ruta del repositorio debe estar bajo el directorio permitido: "
            f"{settings.allowed_repo_root}"
        ) from exc
    return resolved


def _reset_collection(client: chromadb.HttpClient, collection_name: str) -> None:
    try:
        client.delete_collection(name=collection_name)
    except Exception:
        # Collection inexistente en primer arranque — se ignora.
        pass


def ingest_local_repository(
    *,
    repository_id: str,
    root_path: Path,
    settings: IngestorSettings,
) -> IngestionSummary:
    """Ingesta un repositorio local en una collection aislada de Chroma."""
    safe_root: Path = _assert_allowed_root(candidate=root_path, settings=settings)
    cfg = RepositoryScanConfig(repository_root=safe_root, repository_id=repository_id)
    raw_docs: list[Document] = load_repository_documents(cfg)
    chunks: list[Document] = split_documents(raw_docs)

    client = chromadb.HttpClient(
        host=settings.chroma_http_host,
        port=settings.chroma_http_port,
    )
    collection_name: str = chroma_collection_name(repository_id)
    _reset_collection(client, collection_name)

    embeddings = OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=str(settings.ollama_base_url),
    )

    if not chunks:
        Chroma.from_documents(
            documents=[
                Document(
                    page_content="(sin archivos fuente indexables en esta ruta)",
                    metadata={
                        "source": "nexus-empty",
                        "repository_id": repository_id,
                        "language": "meta",
                    },
                )
            ],
            embedding=embeddings,
            client=client,
            collection_name=collection_name,
        )
        return IngestionSummary(
            repository_id=repository_id,
            root_path=str(safe_root),
            documents_ingested=0,
            collection_name=collection_name,
        )

    for index in range(0, len(chunks), BATCH_SIZE):
        batch: list[Document] = chunks[index : index + BATCH_SIZE]
        if index == 0:
            Chroma.from_documents(
                documents=batch,
                embedding=embeddings,
                client=client,
                collection_name=collection_name,
            )
        else:
            store = Chroma(
                client=client,
                collection_name=collection_name,
                embedding_function=embeddings,
            )
            store.add_documents(batch)

    return IngestionSummary(
        repository_id=repository_id,
        root_path=str(safe_root),
        documents_ingested=len(chunks),
        collection_name=collection_name,
    )
