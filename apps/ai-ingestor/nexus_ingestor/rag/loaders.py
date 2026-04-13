"""Carga recursiva de archivos fuente con metadatos de trazabilidad."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterator, Set

from langchain_core.documents import Document

from nexus_ingestor.config import DEFAULT_TEXT_ENCODING

IGNORED_DIR_NAMES: Final[Set[str]] = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".idea",
    ".vscode",
    "target",
}

SOURCE_SUFFIXES: Final[Set[str]] = {
    ".py",
    ".dart",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".vue",
}


@dataclass(frozen=True, slots=True)
class RepositoryScanConfig:
    repository_root: Path
    repository_id: str


def _should_skip_dir(path: Path) -> bool:
    return path.name in IGNORED_DIR_NAMES


def iter_source_documents(cfg: RepositoryScanConfig) -> Iterator[Document]:
    """Recorre el repositorio y emite `Document` con metadata de archivo."""
    root: Path = cfg.repository_root.resolve()
    if not root.is_dir():
        raise NotADirectoryError(str(root))

    for file_path in root.rglob("*"):
        if file_path.is_dir():
            if _should_skip_dir(file_path):
                continue
            continue
        if file_path.suffix.lower() not in SOURCE_SUFFIXES:
            continue
        if any(part in IGNORED_DIR_NAMES for part in file_path.parts):
            continue
        language: str = _language_tag(file_path.suffix.lower())
        try:
            text: str = file_path.read_text(encoding=DEFAULT_TEXT_ENCODING)
        except UnicodeDecodeError:
            text = file_path.read_text(encoding=DEFAULT_TEXT_ENCODING, errors="replace")

        relative: str = str(file_path.relative_to(root))
        yield Document(
            page_content=text,
            metadata={
                "source": relative,
                "absolute_path": str(file_path),
                "repository_id": cfg.repository_id,
                "language": language,
            },
        )


def _language_tag(suffix: str) -> str:
    mapping: dict[str, str] = {
        ".py": "python",
        ".dart": "dart",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".vue": "vue",
    }
    return mapping.get(suffix, "unknown")


def load_repository_documents(cfg: RepositoryScanConfig) -> list[Document]:
    """Materializa todos los documentos (útil para pruebas y lotes pequeños)."""
    return list(iter_source_documents(cfg))
