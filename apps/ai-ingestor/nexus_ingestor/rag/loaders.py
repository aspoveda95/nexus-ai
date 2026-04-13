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
    ".gradle",
    ".next",
    ".nuxt",
    "coverage",
    "Pods",
    ".turbo",
}

# Lockfiles y artefactos enormes: poco valor semántico para onboarding.
IGNORED_FILE_NAMES: Final[Set[str]] = {
    "package-lock.json",
    "npm-shrinkwrap.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "pnpm-lock.yml",
    "Gemfile.lock",
    "composer.lock",
    "Podfile.lock",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "go.sum",
    "uv.lock",
}

# Archivos sin extensión o con nombre fijo muy usados al incorporarse a un repo.
SPECIAL_SOURCE_NAMES_LOWER: Final[Set[str]] = {
    "dockerfile",
    "makefile",
    "gemfile",
    "rakefile",
    "procfile",
    "jenkinsfile",
    "vagrantfile",
    "justfile",
    "cmakelists.txt",
    "codeowners",
    "license",
    "contributing",
    "security",
    "changelog",
    "readme",
}

# Punto de entrada / convenciones (tamaño acotado en la práctica).
DOTFILE_SOURCE_NAMES: Final[Set[str]] = {
    ".gitignore",
    ".gitattributes",
    ".gitmodules",
    ".dockerignore",
    ".editorconfig",
    ".npmrc",
    ".nvmrc",
    ".node-version",
    ".ruby-version",
    ".python-version",
    ".tool-versions",
    ".prettierignore",
    ".eslintignore",
    ".env",
}

SOURCE_SUFFIXES: Final[Set[str]] = {
    # Web / JS
    ".js",
    ".jsx",
    ".mjs",
    ".cjs",
    ".ts",
    ".tsx",
    ".vue",
    ".svelte",
    ".astro",
    # Python / JVM / Android
    ".py",
    ".pyi",
    ".java",
    ".kt",
    ".kts",
    ".gradle",
    ".scala",
    ".sc",
    ".groovy",
    # Systems / native
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
    # .NET
    ".cs",
    ".fs",
    ".vb",
    # Scripting / shell
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
    # Otros lenguajes
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
    # Docs
    ".md",
    ".mdx",
    ".rst",
    ".adoc",
    ".asciidoc",
    ".tex",
    # Config / datos estructurados
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
    # Web estático
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    # Infra / API
    ".sql",
    ".graphql",
    ".gql",
    ".proto",
    ".tf",
    ".tfvars",
    ".prisma",
    ".nix",
    ".cmake",
    # Plantillas Helm / otros
    ".gotmpl",
    ".tpl",
}


@dataclass(frozen=True, slots=True)
class RepositoryScanConfig:
    repository_root: Path
    repository_id: str


def _should_skip_dir(path: Path) -> bool:
    return path.name in IGNORED_DIR_NAMES


def _is_env_dotfile(path: Path) -> bool:
    n = path.name
    if not n.startswith(".env"):
        return False
    if n.endswith(".swp") or n.endswith("~"):
        return False
    return n == ".env" or n.startswith(".env.")


def _should_index_file(path: Path) -> bool:
    if path.name in IGNORED_FILE_NAMES:
        return False
    nl = path.name.lower()
    if nl.endswith(".min.js") or nl.endswith(".min.cjs") or nl.endswith(".min.mjs"):
        return False
    if path.name in DOTFILE_SOURCE_NAMES or _is_env_dotfile(path):
        return True
    if nl in SPECIAL_SOURCE_NAMES_LOWER:
        return True
    if nl.startswith("dockerfile.") and len(nl) > len("dockerfile"):
        return True
    return path.suffix.lower() in SOURCE_SUFFIXES


def _language_for_file(path: Path) -> str:
    name_l = path.name.lower()
    suf = path.suffix.lower()

    special: dict[str, str] = {
        "dockerfile": "dockerfile",
        "makefile": "makefile",
        "gemfile": "ruby",
        "rakefile": "ruby",
        "procfile": "procfile",
        "jenkinsfile": "groovy",
        "vagrantfile": "ruby",
        "justfile": "just",
        "cmakelists.txt": "cmake",
        "codeowners": "plaintext",
        "license": "plaintext",
        "contributing": "markdown",
        "security": "markdown",
        "changelog": "markdown",
        "readme": "markdown",
    }
    if name_l in special:
        return special[name_l]
    if name_l.startswith("dockerfile."):
        return "dockerfile"
    if path.name in DOTFILE_SOURCE_NAMES or _is_env_dotfile(path):
        if path.name.startswith(".env"):
            return "env"
        if path.name == ".editorconfig":
            return "ini"
        return "plaintext"

    mapping: dict[str, str] = {
        ".py": "python",
        ".pyi": "python",
        ".dart": "dart",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".vue": "vue",
        ".svelte": "svelte",
        ".astro": "astro",
        ".md": "markdown",
        ".mdx": "markdown",
        ".rst": "rst",
        ".adoc": "asciidoc",
        ".asciidoc": "asciidoc",
        ".tex": "latex",
        ".json": "json",
        ".jsonc": "jsonc",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        ".properties": "properties",
        ".xml": "xml",
        ".plist": "xml",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".sql": "sql",
        ".graphql": "graphql",
        ".gql": "graphql",
        ".proto": "protobuf",
        ".tf": "terraform",
        ".tfvars": "terraform",
        ".prisma": "prisma",
        ".nix": "nix",
        ".cmake": "cmake",
        ".gotmpl": "gotemplate",
        ".tpl": "template",
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".gradle": "gradle",
        ".scala": "scala",
        ".sc": "scala",
        ".groovy": "groovy",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".hxx": "cpp",
        ".inl": "cpp",
        ".go": "go",
        ".rs": "rust",
        ".swift": "swift",
        ".cs": "csharp",
        ".fs": "fsharp",
        ".vb": "vb",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".fish": "shell",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".bat": "batch",
        ".cmd": "batch",
        ".rb": "ruby",
        ".php": "php",
        ".r": "r",
        ".lua": "lua",
        ".ex": "elixir",
        ".exs": "elixir",
        ".erl": "erlang",
        ".hrl": "erlang",
        ".clj": "clojure",
        ".cljs": "clojure",
        ".edn": "edn",
        ".hs": "haskell",
        ".ml": "ocaml",
        ".mli": "ocaml",
        ".nim": "nim",
        ".zig": "zig",
        ".v": "verilog",
        ".sv": "systemverilog",
        ".pl": "perl",
        ".pm": "perl",
    }
    return mapping.get(suf, "unknown")


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
        if not _should_index_file(file_path):
            continue
        if any(part in IGNORED_DIR_NAMES for part in file_path.parts):
            continue
        language: str = _language_for_file(file_path)
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


def load_repository_documents(cfg: RepositoryScanConfig) -> list[Document]:
    """Materializa todos los documentos (útil para pruebas y lotes pequeños)."""
    return list(iter_source_documents(cfg))
