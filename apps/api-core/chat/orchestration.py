"""Orquestación híbrida local (Ollama) vs cloud (OpenAI)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Sequence

from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI

from chat.chroma_gateway import (
    ChromaGatewaySettings,
    format_context_block,
    load_chroma_settings_from_env,
    retrieve_context_documents,
)
from chat.serializers import ModeLiteral

SYSTEM_PROMPT: str = (
    "Eres Nexus-AI, un asistente de onboarding técnico para equipos de software. "
    "Responde con precisión y en español salvo que se pida otro idioma. "
    "Solo puedes describir rutas, carpetas o archivos que aparezcan de forma explícita "
    "en el bloque de contexto recuperado (RAG) que recibes. "
    "No inventes estructura de repositorio, no supongas README, tests, src ni dependencias "
    "si no salen en ese contexto. "
    "Cita cada afirmación sobre código usando la metadata del contexto entre corchetes "
    "(por ejemplo: [archivo: services/auth.py]). "
    "Si el contexto está vacío, es insuficiente o no responde a la pregunta, dilo sin rodeos: "
    "explica que no hay datos recuperados o que hace falta indexar o reformular la pregunta; "
    "no rellenes con plantillas genéricas de proyectos. "
    "Si preguntan qué exporta, define o expone un archivo, responde con los nombres concretos "
    "(funciones, clases, variables, directivas export) que aparezcan en el fragmento recuperado; "
    "si el lenguaje distingue «exportar» de «declarar en el archivo», acláralo solo con base en lo visible. "
    "No asumas frameworks (p. ej. Flutter), plataformas ni dependencias que no aparezcan en el contexto. "
    "Si el fragmento está truncado o no muestra el archivo completo, dilo y lista únicamente lo que sí se ve. "
    "Si el contexto recuperado contiene código o rutas relevantes para la pregunta, úsalo; "
    "no digas que el RAG no tiene datos si el texto del contexto sí muestra ese archivo o símbolos."
)


@dataclass(frozen=True, slots=True)
class ChatOrchestrationResult:
    answer: str
    citations: List[dict[str, str]]
    source_chunks: List[Dict[str, str]]


def _build_messages(
    *,
    user_message: str,
    context_block: str,
) -> List[SystemMessage | HumanMessage]:
    human_payload: str = (
        "Contexto recuperado (RAG):\n"
        f"{context_block}\n\n"
        "Prioridad: el texto anterior es código real de este repositorio. Si entra en conflicto "
        "con patrones típicos de un lenguaje o framework (por ejemplo asumir que todo "
        "`main.dart` define `void main()` de Flutter), prevalece el fragmento: no lo sustituyas "
        "por plantillas genéricas.\n\n"
        f"Pregunta del usuario:\n{user_message.strip()}"
    )
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_payload),
    ]


def _extract_citations(documents: Sequence[Document]) -> List[dict[str, str]]:
    """Una cita por archivo (evita repetir la misma ruta por cada chunk)."""
    seen: set[tuple[str, str]] = set()
    citations: List[dict[str, str]] = []
    for doc in documents:
        source: str = str(doc.metadata.get("source", ""))
        repo: str = str(doc.metadata.get("repository_id", ""))
        if not source:
            continue
        key = (repo, source)
        if key in seen:
            continue
        seen.add(key)
        citations.append({"source_path": source, "repository_id": repo})
    return citations


def _documents_to_source_chunks(
    documents: Sequence[Document],
    *,
    max_chars: int = 6000,
) -> List[Dict[str, str]]:
    """Fragmentos recuperados para clientes (inspector / UI); un bloque por archivo."""
    best: dict[tuple[str, str], Dict[str, str]] = {}
    for doc in documents:
        sp = str(doc.metadata.get("source", ""))
        rid = str(doc.metadata.get("repository_id", ""))
        if not sp:
            continue
        raw: str = doc.page_content.strip()
        if len(raw) > max_chars:
            raw = f"{raw[:max_chars]}\n…"
        key = (rid, sp)
        prev = best.get(key)
        if prev is None or len(raw) > len(prev["content"]):
            best[key] = {
                "source_path": sp,
                "repository_id": rid,
                "language": str(doc.metadata.get("language", "")),
                "content": raw,
            }
    return list(best.values())


def _build_llm(mode: ModeLiteral):
    if mode == "local":
        ollama_base: str = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        chat_model: str = os.environ.get("OLLAMA_CHAT_MODEL", "llama3")
        return ChatOllama(model=chat_model, base_url=ollama_base, temperature=0.1)
    api_key: str | None = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise PermissionError("OPENAI_API_KEY no configurada para modo cloud.")
    model_name: str = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o")
    return ChatOpenAI(model=model_name, temperature=0.1, api_key=api_key)


def run_hybrid_chat(
    *,
    repository_id: str,
    user_message: str,
    mode: ModeLiteral,
    top_k: int,
    chroma_settings: ChromaGatewaySettings | None = None,
) -> ChatOrchestrationResult:
    """Ejecuta recuperación + generación con el proveedor solicitado."""
    settings: ChromaGatewaySettings = chroma_settings or load_chroma_settings_from_env()
    documents: List[Document] = retrieve_context_documents(
        repository_id=repository_id,
        user_query=user_message,
        top_k=top_k,
        settings=settings,
    )
    context_block: str = format_context_block(documents)
    messages = _build_messages(user_message=user_message, context_block=context_block)

    llm = _build_llm(mode)

    ai_message = llm.invoke(messages)
    answer_text: str = str(ai_message.content)
    citations = _extract_citations(documents)
    source_chunks = _documents_to_source_chunks(documents)
    return ChatOrchestrationResult(
        answer=answer_text,
        citations=citations,
        source_chunks=source_chunks,
    )


def iter_hybrid_chat_stream(
    *,
    repository_id: str,
    user_message: str,
    mode: ModeLiteral,
    top_k: int,
    chroma_settings: ChromaGatewaySettings | None = None,
) -> Iterator[Dict[str, Any]]:
    """Eventos para SSE: meta (citas + chunks), tokens parciales, done."""
    settings: ChromaGatewaySettings = chroma_settings or load_chroma_settings_from_env()
    documents: List[Document] = retrieve_context_documents(
        repository_id=repository_id,
        user_query=user_message,
        top_k=top_k,
        settings=settings,
    )
    context_block: str = format_context_block(documents)
    citations = _extract_citations(documents)
    source_chunks = _documents_to_source_chunks(documents)
    yield {
        "type": "meta",
        "citations": citations,
        "source_chunks": source_chunks,
        "repository_id": repository_id,
        "mode": mode,
    }

    messages = _build_messages(user_message=user_message, context_block=context_block)
    llm = _build_llm(mode)
    for chunk in llm.stream(messages):
        piece: str = str(getattr(chunk, "content", "") or "")
        if piece:
            yield {"type": "token", "text": piece}
    yield {"type": "done"}
