"""Rutas de la app `chat`."""

from __future__ import annotations

from django.urls import path

from chat.views import (
    ChatCompletionView,
    ChatStreamView,
    ConversationDetailView,
    ConversationListView,
)

urlpatterns = [
    path("chat/", ChatCompletionView.as_view(), name="chat-completion"),
    path("chat/stream/", ChatStreamView.as_view(), name="chat-stream"),
    path(
        "chat/conversations/",
        ConversationListView.as_view(),
        name="chat-conversation-list",
    ),
    path(
        "chat/conversations/<uuid:pk>/",
        ConversationDetailView.as_view(),
        name="chat-conversation-detail",
    ),
]
