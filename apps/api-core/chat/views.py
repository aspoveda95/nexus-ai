"""Views DRF para `/chat/`."""

from __future__ import annotations

from typing import Any, Dict, cast

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from chat.orchestration import run_hybrid_chat
from chat.serializers import ChatRequestSerializer, ChatResponseSerializer, ModeLiteral
from chat.tenant import sanitize_repository_id


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

        try:
            result = run_hybrid_chat(
                repository_id=repository_id,
                user_message=str(data["message"]),
                mode=mode,
                top_k=top_k,
            )
        except PermissionError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:  # pragma: no cover - diagnóstico operativo
            return Response(
                {"detail": "Error en orquestación", "error": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        payload: Dict[str, Any] = {
            "answer": result.answer,
            "mode": mode,
            "repository_id": repository_id,
            "citations": result.citations,
        }
        response_serializer = ChatResponseSerializer(data=payload)
        response_serializer.is_valid(raise_exception=True)
        return Response(response_serializer.data, status=status.HTTP_200_OK)
