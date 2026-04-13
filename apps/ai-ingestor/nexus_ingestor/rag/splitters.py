"""Troceado recursivo especializado por sintaxis (multi-lenguaje)."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

CHUNK_SIZE: Final[int] = 1200
CHUNK_OVERLAP: Final[int] = 200


def _python_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _js_ts_splitter() -> RecursiveCharacterTextSplitter:
    js_lang = getattr(Language, "JS", None) or getattr(Language, "JAVASCRIPT", None)
    if js_lang is not None:
        return RecursiveCharacterTextSplitter.from_language(
            language=js_lang,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
    return RecursiveCharacterTextSplitter(
        separators=["\nfunction ", "\nconst ", "\nexport ", "\n\n", "\n", " ", ""],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _html_like_splitter() -> RecursiveCharacterTextSplitter:
    html_lang = getattr(Language, "HTML", None)
    if html_lang is not None:
        return RecursiveCharacterTextSplitter.from_language(
            language=html_lang,
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )
    return RecursiveCharacterTextSplitter(
        separators=["<template", "<script", "\n\n", "\n", " ", ""],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _dart_splitter() -> RecursiveCharacterTextSplitter:
    separators: list[str] = [
        "\nclass ",
        "\nenum ",
        "\nvoid ",
        "\nFuture<",
        "\nimport ",
        "\n///",
        "\n//",
        "\n\n",
        "\n",
        " ",
        "",
    ]
    return RecursiveCharacterTextSplitter(
        separators=separators,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def select_splitter_for_path(file_path: Path) -> RecursiveCharacterTextSplitter:
    """Selecciona un splitter en función de la extensión del archivo."""
    suffix: str = file_path.suffix.lower()
    if suffix == ".py":
        return _python_splitter()
    if suffix in {".dart"}:
        return _dart_splitter()
    if suffix in {".vue"}:
        return _html_like_splitter()
    if suffix in {".js", ".jsx", ".ts", ".tsx"}:
        return _js_ts_splitter()
    return RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)


def split_documents(documents: list[Document]) -> list[Document]:
    """Aplica el troceado especializado preservando metadata por fragmento."""
    chunked: list[Document] = []
    for doc in documents:
        source_meta: str = str(doc.metadata.get("source", "unknown"))
        path = Path(source_meta)
        splitter = select_splitter_for_path(path)
        chunked.extend(splitter.split_documents([doc]))
    return chunked
