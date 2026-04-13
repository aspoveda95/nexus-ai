"""Orquestación híbrida local (Ollama) vs cloud (OpenAI)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Sequence

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
    "Debes citar explícitamente los archivos fuente usando la metadata entre corchetes "
    "del bloque de contexto (por ejemplo: [archivo: services/auth.py]). "
    "Si el contexto no alcanza, dilo con claridad y propón qué archivo o área revisar."
)


@dataclass(frozen=True, slots=True)
class ChatOrchestrationResult:
    answer: str
    citations: List[dict[str, str]]


def _build_messages(
    *,
    user_message: str,
    context_block: str,
) -> List[SystemMessage | HumanMessage]:
    human_payload: str = (
        "Contexto recuperado (RAG):\n"
        f"{context_block}\n\n"
        f"Pregunta del usuario:\n{user_message.strip()}"
    )
    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=human_payload),
    ]


def _extract_citations(documents: Sequence[Document]) -> List[dict[str, str]]:
    citations: List[dict[str, str]] = []
    for doc in documents:
        source: str = str(doc.metadata.get("source", ""))
        repo: str = str(doc.metadata.get("repository_id", ""))
        if not source:
            continue
        citations.append({"source_path": source, "repository_id": repo})
    return citations


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

    if mode == "local":
        ollama_base: str = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        chat_model: str = os.environ.get("OLLAMA_CHAT_MODEL", "llama3")
        llm = ChatOllama(model=chat_model, base_url=ollama_base, temperature=0.1)
    else:
        api_key: str | None = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise PermissionError("OPENAI_API_KEY no configurada para modo cloud.")
        model_name: str = os.environ.get("OPENAI_CHAT_MODEL", "gpt-4o")
        llm = ChatOpenAI(model=model_name, temperature=0.1, api_key=api_key)

    ai_message = llm.invoke(messages)
    answer_text: str = str(ai_message.content)
    citations = _extract_citations(documents)
    return ChatOrchestrationResult(answer=answer_text, citations=citations)
