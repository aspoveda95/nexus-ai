"""Multi-tenancy — misma semántica que api-core."""

from __future__ import annotations

import re
from typing import Final

_REPOSITORY_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$")

COLLECTION_PREFIX: Final[str] = "nexus_repo_"


def sanitize_repository_id(raw_repository_id: str) -> str:
    candidate: str = raw_repository_id.strip()
    if not _REPOSITORY_ID_PATTERN.fullmatch(candidate):
        raise ValueError(
            "repository_id inválido: use 1–128 caracteres [a-zA-Z0-9_-], "
            "debe comenzar con alfanumérico."
        )
    return candidate


def chroma_collection_name(repository_id: str) -> str:
    safe_id: str = sanitize_repository_id(repository_id)
    return f"{COLLECTION_PREFIX}{safe_id}"
