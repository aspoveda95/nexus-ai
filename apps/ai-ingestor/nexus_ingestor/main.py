"""API HTTP del microservicio de ingesta (FastAPI)."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from nexus_ingestor.config import get_settings
from nexus_ingestor.rag.pipeline import IngestionSummary, ingest_local_repository
from nexus_ingestor.tenant import sanitize_repository_id

app = FastAPI(title="Nexus-AI ai-ingestor", version="0.1.0")


class IngestRequest(BaseModel):
    """Cuerpo para disparar una ingesta completa."""

    repository_id: str = Field(..., min_length=1, max_length=128)
    root_path: str = Field(
        ...,
        description="Ruta absoluta del repositorio dentro del volumen montado (/data/repos/...)",
    )


class IngestResponse(BaseModel):
    """Resumen deterministico post-ingesta."""

    repository_id: str
    root_path: str
    documents_ingested: int
    collection_name: str


@app.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness/readiness minimal para orquestadores."""
    return {"status": "ok", "service": "ai-ingestor"}


@app.post("/ingest", response_model=IngestResponse)
def trigger_ingestion(request: IngestRequest) -> IngestResponse:
    """Ingesta un repositorio local hacia la collection aislada del `repository_id`."""
    settings = get_settings()
    try:
        repository_id = sanitize_repository_id(request.repository_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    root = Path(request.root_path)
    try:
        summary: IngestionSummary = ingest_local_repository(
            repository_id=repository_id,
            root_path=root,
            settings=settings,
        )
    except (NotADirectoryError, PermissionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - errores de red/embeddings
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return IngestResponse(
        repository_id=summary.repository_id,
        root_path=summary.root_path,
        documents_ingested=summary.documents_ingested,
        collection_name=summary.collection_name,
    )
