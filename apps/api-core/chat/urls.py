"""Rutas de la app `chat`."""

from __future__ import annotations

from django.urls import path

from chat.views import ChatCompletionView, ChatStreamView

urlpatterns = [
    path("chat/", ChatCompletionView.as_view(), name="chat-completion"),
    path("chat/stream/", ChatStreamView.as_view(), name="chat-stream"),
]
