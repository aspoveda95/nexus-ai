"""CLI opcional para ejecutar ingesta sin levantar HTTP (desarrollo local)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Sequence

from nexus_ingestor.config import get_settings
from nexus_ingestor.rag.pipeline import ingest_local_repository
from nexus_ingestor.tenant import sanitize_repository_id


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Nexus-AI — ingesta RAG local")
    parser.add_argument(
        "--repository-id",
        required=True,
        help="Identificador multi-tenant (debe coincidir con el usado en /chat/).",
    )
    parser.add_argument(
        "--root",
        type=Path,
        required=True,
        help="Carpeta raíz del repositorio a indexar.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    settings = get_settings()
    repository_id = sanitize_repository_id(str(args.repository_id))
    summary = ingest_local_repository(
        repository_id=repository_id,
        root_path=args.root,
        settings=settings,
    )
    payload = {
        "repository_id": summary.repository_id,
        "root_path": summary.root_path,
        "documents_ingested": summary.documents_ingested,
        "collection_name": summary.collection_name,
    }
    sys.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
