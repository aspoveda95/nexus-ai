"""Serializers DRF para el endpoint de chat."""

from __future__ import annotations

from typing import Literal

from rest_framework import serializers


class ChatRequestSerializer(serializers.Serializer):
    """Validación estricta de la petición `/chat/`."""

    repository_id = serializers.CharField(max_length=128)
    message = serializers.CharField()
    mode = serializers.ChoiceField(choices=["local", "cloud"])
    top_k = serializers.IntegerField(required=False, min_value=1, max_value=32, default=8)
    conversation_id = serializers.UUIDField(required=False, allow_null=True)


class ChatCitationSerializer(serializers.Serializer):
    """Metadatos de cita devueltos al cliente."""

    source_path = serializers.CharField()
    repository_id = serializers.CharField()


class SourceChunkSerializer(serializers.Serializer):
    """Fragmento RAG para el inspector de conocimiento."""

    source_path = serializers.CharField()
    repository_id = serializers.CharField()
    language = serializers.CharField(allow_blank=True, required=False)
    content = serializers.CharField()


class ChatResponseSerializer(serializers.Serializer):
    """Respuesta JSON del orquestador."""

    answer = serializers.CharField()
    mode = serializers.ChoiceField(choices=["local", "cloud"])
    repository_id = serializers.CharField()
    conversation_id = serializers.UUIDField()
    citations = ChatCitationSerializer(many=True)
    source_chunks = SourceChunkSerializer(many=True)


ModeLiteral = Literal["local", "cloud"]
