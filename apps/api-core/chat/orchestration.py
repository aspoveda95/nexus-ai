"""Orquestación híbrida local (Ollama) vs cloud (OpenAI)."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any, Dict, Iterator, List, Literal, Sequence, TypedDict

from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
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
    "Redacta siempre en prosa natural para el usuario. No copies los encabezados del contexto "
    "(líneas «Documento N», «Ruta relativa:», «Metadato repository_id:», «Lenguaje detectado:») "
    "ni inventes listas numeradas al estilo «[1] archivo=… | repositorio=…». "
    "Si la pregunta es si existe un archivo (p. ej. README.md), empieza con Sí o No y "
    "añade una frase breve con la ruta relativa; no repitas el mismo archivo tres veces. "
    "El usuario ya eligió el repositorio en la aplicación: no hace falta insistir en el "
    "repository_id salvo que lo pidan explícitamente. "
    "Cuando cites código o archivos, usa solo el formato [archivo: ruta/relativa]. "
    "Si el contexto está vacío, es insuficiente o no responde a la pregunta, dilo sin rodeos: "
    "explica que no hay datos recuperados o que hace falta indexar o reformular la pregunta; "
    "no rellenes con plantillas genéricas de proyectos. "
    "Si preguntan qué exporta, define o expone un archivo, responde con los nombres concretos "
    "(funciones, clases, variables, directivas export) que aparezcan en el fragmento recuperado; "
    "si el lenguaje distingue «exportar» de «declarar en el archivo», acláralo solo con base en lo visible. "
    "No asumas frameworks (p. ej. Flutter), plataformas ni dependencias que no aparezcan en el contexto. "
    "Si el fragmento está truncado o no muestra el archivo completo, dilo y lista únicamente lo que sí se ve. "
    "Si el contexto recuperado contiene código o rutas relevantes para la pregunta, úsalo; "
    "no digas que el RAG no tiene datos si el texto del contexto sí muestra ese archivo o símbolos. "
    "Si recibes mensajes previos de la misma conversación, úsalos para interpretar preguntas "
    "breves o ambiguas («qué dice», «ese archivo», «y eso») como continuación del tema anterior; "
    "responde sobre ese tema usando el RAG de este turno, sin pedir que reformulen sin necesidad. "
    "Si el usuario solo agradece, cierra cordialmente o confirma sin pedir datos técnicos nuevos "
    "(p. ej. «gracias», «entendido», «ok»), responde en una frase breve; no vuelvas a resumir "
    "archivos, el README ni el historial salvo que pida explícitamente más detalle."
)


class ChatHistoryTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


def _normalize_history(
    history: Sequence[dict[str, Any]] | None,
    *,
    max_messages: int = 24,
    max_chars_per_message: int = 8000,
) -> list[ChatHistoryTurn]:
    if not history:
        return []
    out: list[ChatHistoryTurn] = []
    for item in list(history)[-max_messages:]:
        role_raw = item.get("role")
        content_raw = item.get("content")
        if role_raw not in ("user", "assistant") or not isinstance(content_raw, str):
            continue
        content = content_raw.strip()
        if not content:
            continue
        if len(content) > max_chars_per_message:
            content = f"{content[:max_chars_per_message]}\n…"
        typed_turn: ChatHistoryTurn = {
            "role": role_raw,
            "content": content,
        }
        out.append(typed_turn)
    return out


def _retrieval_query(*, user_message: str, history: Sequence[ChatHistoryTurn]) -> str:
    """Amplía la consulta semántica con turnos recientes (p. ej. «qué dice?» → README)."""
    if not history:
        return user_message.strip()
    parts: list[str] = []
    for turn in history[-8:]:
        label = "Usuario" if turn["role"] == "user" else "Asistente"
        parts.append(f"{label}: {turn['content']}")
    parts.append(f"Pregunta actual: {user_message.strip()}")
    text = "\n".join(parts)
    if len(text) > 14000:
        text = text[-14000:]
    return text


_CLOSURE_FULLMATCH: re.Pattern[str] = re.compile(
    r"^("
    r"(entiendo|entendido)(\s+gracias)?"
    r"|gracias(\s+entiendo)?"
    r"|(muchas\s+|mil\s+)?gracias(\s+por\s+todo)?"
    r"|(ok|vale|perfecto|listo|genial|excelente|correcto|claro)(\s+gracias)?"
    r"|de\s+nada"
    r"|thank\s+you|thanks|thx"
    r")$",
    re.IGNORECASE,
)


def _is_conversational_closure(user_message: str) -> bool:
    """Agradecimientos / cierre sin pregunta técnica: evita RAG que reinyecta el mismo README."""
    raw = user_message.strip()
    if not raw or len(raw) > 120:
        return False
    if "?" in raw or "`" in raw:
        return False
    if re.search(
        r"\b[\w./-]+\.(?:md|mdx|py|pyi|ts|tsx|vue|js|mjs|cjs|json|yaml|yml|go|rs|java)\b",
        raw,
        re.IGNORECASE,
    ):
        return False
    t = raw.lower()
    t = re.sub(r"^[¡¿]+", "", t)
    t = re.sub(r"[\.,!;:]+", " ", t)
    t = " ".join(t.split())
    if not t:
        return False
    return bool(_CLOSURE_FULLMATCH.match(t))


def _context_block_for_turn(
    *,
    user_message: str,
    documents: List[Document],
) -> str:
    if not documents and _is_conversational_closure(user_message):
        return (
            "(Este turno no usa búsqueda en el código: el mensaje es solo conversación breve o cierre. "
            "Responde de forma cordial en una o dos frases; no resumas el repositorio ni el README.)"
        )
    return format_context_block(documents)


@dataclass(frozen=True, slots=True)
class ChatOrchestrationResult:
    answer: str
    citations: List[dict[str, str]]
    source_chunks: List[Dict[str, str]]


def _build_messages(
    *,
    repository_id: str,
    user_message: str,
    context_block: str,
    history: Sequence[ChatHistoryTurn],
) -> List[BaseMessage]:
    human_payload: str = (
        f"Repositorio activo en esta conversación (id): {repository_id}\n"
        "Las rutas del contexto son relativas a la raíz de ese repositorio indexado.\n\n"
        "Contexto recuperado (RAG):\n"
        f"{context_block}\n\n"
        "Prioridad: el texto anterior es código real de este repositorio. Si entra en conflicto "
        "con patrones típicos de un lenguaje o framework (por ejemplo asumir que todo "
        "`main.dart` define `void main()` de Flutter), prevalece el fragmento: no lo sustituyas "
        "por plantillas genéricas.\n\n"
        f"Pregunta del usuario:\n{user_message.strip()}"
    )
    out: List[BaseMessage] = [SystemMessage(content=SYSTEM_PROMPT)]
    for turn in history:
        if turn["role"] == "user":
            out.append(HumanMessage(content=turn["content"]))
        else:
            out.append(AIMessage(content=turn["content"]))
    out.append(HumanMessage(content=human_payload))
    return out


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
    history: Sequence[dict[str, Any]] | None = None,
    chroma_settings: ChromaGatewaySettings | None = None,
) -> ChatOrchestrationResult:
    """Ejecuta recuperación + generación con el proveedor solicitado."""
    settings: ChromaGatewaySettings = chroma_settings or load_chroma_settings_from_env()
    hist = _normalize_history(history)
    if _is_conversational_closure(user_message):
        documents = []
    else:
        rag_query: str = _retrieval_query(user_message=user_message, history=hist)
        documents = retrieve_context_documents(
            repository_id=repository_id,
            user_query=rag_query,
            top_k=top_k,
            settings=settings,
        )
    context_block: str = _context_block_for_turn(user_message=user_message, documents=documents)
    messages = _build_messages(
        repository_id=repository_id,
        user_message=user_message,
        context_block=context_block,
        history=hist,
    )

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
    history: Sequence[dict[str, Any]] | None = None,
    chroma_settings: ChromaGatewaySettings | None = None,
) -> Iterator[Dict[str, Any]]:
    """Eventos para SSE: meta (citas + chunks), tokens parciales, done."""
    settings: ChromaGatewaySettings = chroma_settings or load_chroma_settings_from_env()
    hist = _normalize_history(history)
    if _is_conversational_closure(user_message):
        documents = []
    else:
        rag_query = _retrieval_query(user_message=user_message, history=hist)
        documents = retrieve_context_documents(
            repository_id=repository_id,
            user_query=rag_query,
            top_k=top_k,
            settings=settings,
        )
    context_block: str = _context_block_for_turn(user_message=user_message, documents=documents)
    citations = _extract_citations(documents)
    source_chunks = _documents_to_source_chunks(documents)
    yield {
        "type": "meta",
        "citations": citations,
        "source_chunks": source_chunks,
        "repository_id": repository_id,
        "mode": mode,
    }

    messages = _build_messages(
        repository_id=repository_id,
        user_message=user_message,
        context_block=context_block,
        history=hist,
    )
    llm = _build_llm(mode)
    for chunk in llm.stream(messages):
        piece: str = str(getattr(chunk, "content", "") or "")
        if piece:
            yield {"type": "token", "text": piece}
    yield {"type": "done"}
