"""Admin mínimo para inspeccionar conversaciones."""

from __future__ import annotations

from django.contrib import admin

from chat.models import Conversation, Message


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    readonly_fields = ("id", "role", "created_at")
    fields = ("id", "role", "created_at", "content")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("id", "repository_id", "created_at", "updated_at")
    list_filter = ("repository_id",)
    inlines = [MessageInline]
    readonly_fields = ("id", "created_at", "updated_at")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("id", "conversation", "role", "created_at")
    list_filter = ("role",)
    readonly_fields = ("id", "created_at")
