"""Troceado recursivo especializado por sintaxis (multi-lenguaje)."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from langchain_core.documents import Document
from langchain_text_splitters import Language, RecursiveCharacterTextSplitter

CHUNK_SIZE: Final[int] = 1200
CHUNK_OVERLAP: Final[int] = 200


def _try_language_splitter(*attr_names: str) -> RecursiveCharacterTextSplitter | None:
    for name in attr_names:
        lang = getattr(Language, name, None)
        if lang is None:
            continue
        try:
            return RecursiveCharacterTextSplitter.from_language(
                language=lang,
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP,
            )
        except Exception:
            continue
    return None


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


def _markdown_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        separators=[
            "\n## ",
            "\n### ",
            "\n#### ",
            "\n---\n",
            "\n\n",
            "\n",
            " ",
            "",
        ],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _structured_data_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        separators=['\n  "', "\n-", "\n{", "\n[", "\n\n", "\n", " ", ""],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _sql_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        separators=[";\n\n", ";\n", "\n\n", "\n", " ", ""],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )


def _plain_line_splitter() -> RecursiveCharacterTextSplitter:
    return RecursiveCharacterTextSplitter(
        separators=["\n\n", "\n# ", "\n#", "\n", " ", ""],
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
    """Selecciona un splitter en función del nombre o extensión del archivo."""
    name_l = file_path.name.lower()
    suf = str(file_path.suffix).lower()

    if suf in {".md", ".mdx"}:
        return _markdown_splitter()
    if name_l in {"contributing", "changelog", "security", "readme"}:
        return _markdown_splitter()
    if name_l in {"license", "codeowners"}:
        return _plain_line_splitter()
    if name_l == "cmakelists.txt":
        return _plain_line_splitter()

    if name_l == "dockerfile" or (name_l.startswith("dockerfile.") and len(name_l) > len("dockerfile")):
        return _plain_line_splitter()
    if name_l in {"makefile", "justfile", "jenkinsfile"}:
        return _plain_line_splitter()
    if name_l in {"gemfile", "rakefile", "vagrantfile", "procfile"}:
        rb = _try_language_splitter("RUBY")
        if rb is not None:
            return rb
        return _plain_line_splitter()

    if file_path.name.startswith(".env") or suf in {".ini", ".cfg", ".conf"}:
        return _plain_line_splitter()
    if file_path.name == ".editorconfig":
        return _plain_line_splitter()

    if suf in {".json", ".jsonc", ".yaml", ".yml", ".toml", ".xml", ".plist", ".properties"}:
        return _structured_data_splitter()
    if suf in {".graphql", ".gql", ".proto", ".tf", ".tfvars", ".prisma", ".nix", ".cmake", ".gotmpl", ".tpl"}:
        return _structured_data_splitter()

    if suf == ".sql":
        return _sql_splitter()

    if suf in {".html", ".htm"}:
        return _html_like_splitter()

    if suf in {".css", ".scss", ".sass", ".less"}:
        css = _try_language_splitter("CSS", "HTML")
        if css is not None:
            return css
        return RecursiveCharacterTextSplitter(
            separators=["\n\n", "\n}", "\n", " ", ""],
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP,
        )

    lang_by_suffix: dict[str, tuple[str, ...]] = {
        ".go": ("GO",),
        ".rs": ("RUST",),
        ".java": ("JAVA",),
        ".kt": ("KOTLIN", "JAVA"),
        ".kts": ("KOTLIN", "JAVA"),
        ".gradle": ("KOTLIN", "JAVA"),
        ".cs": ("CSHARP",),
        ".fs": ("F_SHARP",),
        ".cpp": ("CPP",),
        ".cc": ("CPP",),
        ".cxx": ("CPP",),
        ".hpp": ("CPP",),
        ".hxx": ("CPP",),
        ".inl": ("CPP",),
        ".c": ("C",),
        ".h": ("CPP", "C"),
        ".swift": ("SWIFT",),
        ".rb": ("RUBY",),
        ".php": ("PHP",),
        ".scala": ("SCALA",),
        ".sc": ("SCALA",),
        ".groovy": ("JAVA",),
    }
    if suf in lang_by_suffix:
        spl = _try_language_splitter(*lang_by_suffix[suf])
        if spl is not None:
            return spl

    if suf == ".py" or suf == ".pyi":
        return _python_splitter()
    if suf == ".dart":
        return _dart_splitter()
    if suf in {".vue", ".svelte", ".astro"}:
        return _html_like_splitter()
    if suf in {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx"}:
        return _js_ts_splitter()

    if suf in {".sh", ".bash", ".zsh", ".fish", ".ps1", ".psm1", ".bat", ".cmd"}:
        return _plain_line_splitter()

    if suf in {".rst", ".adoc", ".asciidoc"}:
        return _markdown_splitter()
    if suf == ".tex":
        return _plain_line_splitter()

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
