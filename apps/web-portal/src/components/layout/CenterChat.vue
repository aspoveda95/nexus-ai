<script setup lang="ts">
import { MessageSquarePlus, RefreshCw, Send, Settings } from 'lucide-vue-next'
import { computed, nextTick, ref, watch } from 'vue'

import ChatMessage from '@/components/chat/ChatMessage.vue'
import Button from '@/components/ui/Button.vue'
import ModeSwitch from '@/components/ui/ModeSwitch.vue'
import ScrollArea from '@/components/ui/ScrollArea.vue'
import Separator from '@/components/ui/Separator.vue'
import { useSendMessage } from '@/composables/useSendMessage'
import { useChatStore } from '@/stores/chat'
import { useRepositoriesStore } from '@/stores/repositories'
import type { ChatMode } from '@/types/api'

const chat = useChatStore()
const repos = useRepositoriesStore()
const { send } = useSendMessage()

const input = ref('')
const bottomAnchor = ref<HTMLElement | null>(null)

const title = computed(() => {
  const r = repos.items.find((x) => x.id === repos.activeId)
  return r?.label ?? 'Sin repositorio'
})

async function scrollToBottom() {
  await nextTick()
  bottomAnchor.value?.scrollIntoView({ behavior: 'smooth', block: 'end' })
}

watch(
  () => chat.messages.length,
  () => {
    void scrollToBottom()
  },
)

watch(
  () => chat.messages.at(-1)?.content,
  () => {
    void scrollToBottom()
  },
)

async function onSubmit() {
  const t = input.value
  if (!t.trim()) return
  input.value = ''
  await send(t)
}

function onSelectCitation(path: string) {
  chat.setHighlightedPath(path)
  const el = document.querySelector(`[data-citation-anchor="${CSS.escape(path)}"]`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}
</script>

<template>
  <section class="flex min-h-0 min-w-0 flex-1 flex-col bg-zinc-950">
    <header
      class="flex items-center justify-between gap-3 border-b border-zinc-800/80 px-4 py-3 backdrop-blur-sm"
    >
      <div class="min-w-0 flex items-center gap-2">
        <div class="min-w-0">
          <p class="truncate text-sm font-semibold text-zinc-100">{{ title }}</p>
          <p class="truncate text-[11px] text-zinc-500">
            {{ repos.activeId ? `ID: ${repos.activeId}` : 'Selecciona un repositorio' }}
          </p>
        </div>
        <Button
          variant="ghost"
          size="icon"
          class="h-8 w-8 shrink-0"
          title="Nueva conversación"
          :disabled="!repos.activeId || chat.isSending"
          @click="chat.clearConversation()"
        >
          <MessageSquarePlus class="h-4 w-4 text-zinc-400" />
        </Button>
        <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0" title="Ajustes (próximamente)">
          <Settings class="h-4 w-4 text-zinc-400" />
        </Button>
      </div>
      <ModeSwitch :model-value="chat.mode" @update:model-value="(m: ChatMode) => chat.setMode(m)" />
    </header>

    <ScrollArea class="flex-1 px-4 py-4">
      <div v-if="!chat.messages.length" class="mx-auto max-w-xl py-16 text-center">
        <p class="text-sm font-medium text-zinc-300">Nexus-AI</p>
        <p class="mt-2 text-[13px] leading-relaxed text-zinc-500">
          Haz una pregunta sobre el código indexado. El modo <span class="text-zinc-300">Local</span> usa Ollama;
          <span class="text-zinc-300">Cloud</span> requiere <span class="font-mono text-[12px]">OPENAI_API_KEY</span>.
        </p>
      </div>
      <div v-else class="mx-auto flex max-w-3xl flex-col gap-5">
        <ChatMessage
          v-for="m in chat.messages"
          :key="m.id"
          :role="m.role"
          :content="m.content"
          :streaming="m.streaming"
          :citations="m.citations"
          :highlight-path="chat.highlightedSourcePath"
          @select-citation="onSelectCitation"
        />
        <div ref="bottomAnchor" class="h-px w-full scroll-mt-24" />
      </div>
    </ScrollArea>

    <Separator />
    <div class="border-t border-zinc-800/80 p-3">
      <p v-if="chat.lastError" class="mb-2 text-[12px] text-red-400/90">
        {{ chat.lastError }}
      </p>
      <form
        class="mx-auto flex max-w-3xl items-end gap-2"
        @submit.prevent="onSubmit"
      >
        <div class="relative min-w-0 flex-1">
          <textarea
            v-model="input"
            rows="1"
            placeholder="Escribe una pregunta técnica…"
            class="max-h-40 min-h-[44px] w-full resize-none rounded-xl border border-zinc-800 bg-zinc-950/60 px-3 py-3 pr-12 text-[13px] text-zinc-100 shadow-sm placeholder:text-zinc-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-600"
            @keydown.enter.exact.prevent="onSubmit"
          />
          <div class="pointer-events-none absolute bottom-2 right-2 flex items-center gap-1 text-[10px] text-zinc-600">
            <kbd class="rounded border border-zinc-800 bg-zinc-900 px-1.5 py-0.5 font-mono">Enter</kbd>
            enviar
          </div>
        </div>
        <Button
          type="submit"
          class="h-11 w-11 shrink-0 rounded-xl"
          size="icon"
          :disabled="chat.isSending || !repos.activeId"
          :title="chat.isSending ? 'Enviando…' : 'Enviar'"
        >
          <Send v-if="!chat.isSending" class="h-4 w-4" />
          <RefreshCw v-else class="h-4 w-4 animate-spin" />
        </Button>
      </form>
    </div>
  </section>
</template>
