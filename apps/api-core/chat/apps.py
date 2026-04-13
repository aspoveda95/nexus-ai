"""Configuración de la app `chat`."""

from django.apps import AppConfig


class ChatConfig(AppConfig):
    default_auto_field: str = "django.db.models.BigAutoField"
    name: str = "chat"
    verbose_name: str = "Chat Nexus-AI"
