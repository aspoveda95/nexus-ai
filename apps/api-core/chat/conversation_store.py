"""Persistencia de conversaciones para el chat (historial en base de datos)."""

from __future__ import annotations

import uuid
from typing import Any, List

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from chat.models import Conversation, Message


def bump_conversation_timestamp(conversation: Conversation) -> None:
    """Ordena listados recientes (p. ej. estilo Gemini) al añadir mensajes."""
    Conversation.objects.filter(pk=conversation.pk).update(updated_at=timezone.now())


def resolve_conversation(
    *,
    repository_id: str,
    conversation_id: uuid.UUID | None,
) -> Conversation:
    """Crea un hilo nuevo o recupera uno existente; valida que coincida el repositorio."""
    if conversation_id is None:
        return Conversation.objects.create(repository_id=repository_id)
    try:
        conv = Conversation.objects.get(pk=conversation_id)
    except Conversation.DoesNotExist as exc:
        raise ValidationError(
            {"conversation_id": "Conversación no encontrada."},
        ) from exc
    if conv.repository_id != repository_id:
        raise ValidationError(
            {"conversation_id": "Esta conversación no pertenece al repositorio indicado."},
        )
    return conv


def history_for_orchestration(conversation: Conversation, *, max_messages: int = 48) -> List[dict[str, Any]]:
    """Turnos previos al mensaje que aún no se ha guardado (solo lectura)."""
    qs = conversation.messages.order_by("created_at").values("role", "content")
    rows = list(qs)
    if len(rows) > max_messages:
        rows = rows[-max_messages:]
    return [{"role": r["role"], "content": r["content"]} for r in rows]


def append_user_message(*, conversation: Conversation, content: str) -> None:
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.USER,
        content=content,
    )
    bump_conversation_timestamp(conversation)


def append_assistant_message(*, conversation: Conversation, content: str) -> None:
    Message.objects.create(
        conversation=conversation,
        role=Message.Role.ASSISTANT,
        content=content,
    )
    bump_conversation_timestamp(conversation)
