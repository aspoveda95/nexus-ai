"""Views DRF para `/chat/`."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterator, cast

from django.shortcuts import get_object_or_404
from django.http import StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.conversation_store import (
    append_assistant_message,
    append_user_message,
    history_for_orchestration,
    resolve_conversation,
)
from chat.models import Conversation, Message
from chat.orchestration import iter_hybrid_chat_stream, run_hybrid_chat
from chat.serializers import ChatRequestSerializer, ChatResponseSerializer, ModeLiteral
from chat.tenant import sanitize_repository_id


@method_decorator(csrf_exempt, name="dispatch")
class ChatCompletionView(APIView):
    """POST /chat/ — orquestación híbrida con RAG y citas obligatorias en prompt."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request: Request) -> Response:
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            repository_id: str = sanitize_repository_id(str(data["repository_id"]))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        mode = cast(ModeLiteral, str(data["mode"]))
        top_k: int = int(data.get("top_k", 8))
        user_text: str = str(data["message"])
        conv_id_raw = data.get("conversation_id")

        try:
            conversation = resolve_conversation(
                repository_id=repository_id,
                conversation_id=conv_id_raw,
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        history = history_for_orchestration(conversation)
        append_user_message(conversation=conversation, content=user_text)

        try:
            result = run_hybrid_chat(
                repository_id=repository_id,
                user_message=user_text,
                mode=mode,
                top_k=top_k,
                history=history,
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - diagnóstico operativo
            return Response(
                {"detail": "Error en orquestación", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        append_assistant_message(conversation=conversation, content=result.answer)

        payload: Dict[str, Any] = {
            "answer": result.answer,
            "mode": mode,
            "repository_id": repository_id,
            "conversation_id": conversation.pk,
            "citations": result.citations,
            "source_chunks": result.source_chunks,
        }
        response_serializer = ChatResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class ChatStreamView(APIView):
    """POST /chat/stream/ — misma carga que `/chat/`, respuesta SSE (text/event-stream)."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def post(self, request: Request) -> StreamingHttpResponse | Response:
        serializer = ChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            repository_id = sanitize_repository_id(str(data["repository_id"]))
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        mode = cast(ModeLiteral, str(data["mode"]))
        top_k: int = int(data.get("top_k", 8))
        user_text: str = str(data["message"])
        conv_id_raw = data.get("conversation_id")

        try:
            conversation = resolve_conversation(
                repository_id=repository_id,
                conversation_id=conv_id_raw,
            )
        except ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        history = history_for_orchestration(conversation)
        append_user_message(conversation=conversation, content=user_text)
        conversation_id_str: str = str(conversation.pk)

        def event_stream() -> Iterator[bytes]:
            assistant_text_parts: list[str] = []
            try:
                for item in iter_hybrid_chat_stream(
                    repository_id=repository_id,
                    user_message=user_text,
                    mode=mode,
                    top_k=top_k,
                    history=history,
                ):
                    if item.get("type") == "meta":
                        item = {**item, "conversation_id": conversation_id_str}
                    elif item.get("type") == "token":
                        assistant_text_parts.append(str(item.get("text") or ""))
                    line = f"data: {json.dumps(item, ensure_ascii=False)}\n\n"
                    yield line.encode("utf-8")
                append_assistant_message(
                    conversation=conversation,
                    content="".join(assistant_text_parts),
                )
            except PermissionError as exc:
                err = {
                    "type": "error",
                    "detail": str(exc),
                    "conversation_id": conversation_id_str,
                }
                yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode("utf-8")
            except Exception as exc:  # pragma: no cover
                err = {
                    "type": "error",
                    "detail": "Error en orquestación",
                    "error": str(exc),
                    "conversation_id": conversation_id_str,
                }
                yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode("utf-8")

        response = StreamingHttpResponse(event_stream(), content_type="text/event-stream")
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


@method_decorator(csrf_exempt, name="dispatch")
class ConversationListView(APIView):
    """GET /chat/conversations/?repository_id= — hilos del repositorio (más recientes primero)."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def get(self, request: Request) -> Response:
        rid_raw = str(request.query_params.get("repository_id", "")).strip()
        if not rid_raw:
            return Response(
                {"detail": "Parámetro query repository_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            repository_id = sanitize_repository_id(rid_raw)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        conversations = list(
            Conversation.objects.filter(repository_id=repository_id).order_by("-updated_at")[:80],
        )
        conv_ids = [c.pk for c in conversations]
        preview_by_id: dict[Any, str] = {}
        if conv_ids:
            for msg in (
                Message.objects.filter(
                    conversation_id__in=conv_ids,
                    role=Message.Role.USER,
                )
                .order_by("conversation_id", "created_at")
                .only("conversation_id", "content")
            ):
                if msg.conversation_id not in preview_by_id:
                    preview_by_id[msg.conversation_id] = msg.content

        items: list[dict[str, str]] = []
        for conv in conversations:
            raw_preview = (preview_by_id.get(conv.pk) or "").strip().replace("\n", " ")
            if len(raw_preview) > 140:
                raw_preview = f"{raw_preview[:137]}…"
            items.append(
                {
                    "id": str(conv.pk),
                    "repository_id": conv.repository_id,
                    "updated_at": conv.updated_at.isoformat(),
                    "preview": raw_preview,
                },
            )
        return Response({"conversations": items}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name="dispatch")
class ConversationDetailView(APIView):
    """GET /chat/conversations/<uuid>/ — historial persistido (requiere ?repository_id=)."""

    authentication_classes: list[Any] = []
    permission_classes: list[Any] = []

    def get(self, request: Request, pk: Any) -> Response:
        rid_raw = str(request.query_params.get("repository_id", "")).strip()
        if not rid_raw:
            return Response(
                {"detail": "Parámetro query repository_id requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            repository_id = sanitize_repository_id(rid_raw)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        conv = get_object_or_404(Conversation, pk=pk, repository_id=repository_id)
        messages_out = [
            {
                "id": str(m.pk),
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in conv.messages.order_by("created_at")
        ]
        return Response(
            {
                "id": str(conv.pk),
                "repository_id": conv.repository_id,
                "messages": messages_out,
            },
            status=status.HTTP_200_OK,
        )
