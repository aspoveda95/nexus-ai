"""Configuración tipada (Pydantic Settings) para ai-ingestor."""

from __future__ import annotations

from functools import lru_cache
from typing import Final

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestorSettings(BaseSettings):
    """Variables de entorno del servicio de ingesta."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    chroma_http_host: str = Field(default="127.0.0.1")
    chroma_http_port: int = Field(default=8000)
    ollama_base_url: str = Field(default="http://127.0.0.1:11434")
    ollama_embed_model: str = Field(default="nomic-embed-text")
    ingestor_host: str = Field(default="0.0.0.0")
    ingestor_port: int = Field(default=8100)
    allowed_repo_root: str = Field(default="/data/repos")


@lru_cache(maxsize=1)
def get_settings() -> IngestorSettings:
    """Singleton de configuración (cacheada por proceso)."""
    return IngestorSettings()


DEFAULT_TEXT_ENCODING: Final[str] = "utf-8"

