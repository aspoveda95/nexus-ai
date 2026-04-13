"""Rutas de la app `chat`."""

from __future__ import annotations

from django.urls import path

from chat.views import ChatCompletionView

urlpatterns = [
    path("chat/", ChatCompletionView.as_view(), name="chat-completion"),
]
