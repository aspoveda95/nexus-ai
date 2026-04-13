<script setup lang="ts">
import { FileCode, PanelRight } from 'lucide-vue-next'
import { computed } from 'vue'

import Button from '@/components/ui/Button.vue'
import ScrollArea from '@/components/ui/ScrollArea.vue'
import Separator from '@/components/ui/Separator.vue'
import { cn } from '@/lib/utils'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()

const collapsed = defineModel<boolean>('collapsed', { default: false })

const chunks = computed(() => chat.sourceChunks)

function chunkId(path: string, index: number) {
  return `chunk-${index}-${path}`
}

function onSelect(path: string) {
  chat.setHighlightedPath(path)
  const el = document.querySelector(`[data-citation-anchor="${CSS.escape(path)}"]`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
}

function toggle() {
  collapsed.value = !collapsed.value
}
</script>

<template>
  <aside
    :class="
      cn(
        'flex h-full min-h-0 flex-col border-l border-zinc-800/80 bg-zinc-950/30 transition-[width] duration-200',
        collapsed ? 'w-12' : 'w-full min-w-[280px] max-w-[360px] xl:max-w-[400px]',
      )
    "
  >
    <div class="flex items-center justify-between gap-2 px-2 py-3">
      <div
        v-if="!collapsed"
        class="pl-1 text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500"
      >
        Knowledge
      </div>
      <Button variant="ghost" size="icon" class="h-8 w-8 shrink-0" title="Panel lateral" @click="toggle">
        <PanelRight class="h-4 w-4" />
      </Button>
    </div>
    <template v-if="!collapsed">
      <Separator class="mx-2" />
      <ScrollArea class="flex-1 px-2 py-2">
        <div v-if="!chunks.length" class="px-2 py-6 text-center text-[12px] leading-relaxed text-zinc-500">
          Los fragmentos RAG aparecerán aquí tras enviar un mensaje.
        </div>
        <div v-else class="space-y-2">
          <div
            v-for="(ch, idx) in chunks"
            :key="chunkId(ch.source_path, idx)"
            :class="
              cn(
                'rounded-lg border p-3 transition-colors',
                chat.highlightedSourcePath === ch.source_path
                  ? 'border-sky-500/50 bg-sky-950/20'
                  : 'border-zinc-800 bg-zinc-950/50 hover:border-zinc-700',
              )
            "
          >
            <button
              type="button"
              class="flex w-full items-start gap-2 text-left"
              @click="onSelect(ch.source_path)"
            >
              <FileCode class="mt-0.5 h-4 w-4 shrink-0 text-sky-400/90" aria-hidden="true" />
              <div class="min-w-0 flex-1 space-y-1">
                <p class="truncate font-mono text-[11px] text-zinc-300">{{ ch.source_path }}</p>
                <p v-if="ch.language" class="text-[10px] uppercase tracking-wide text-zinc-600">
                  {{ ch.language }}
                </p>
                <pre
                  class="max-h-40 overflow-auto whitespace-pre-wrap break-words font-mono text-[11px] leading-relaxed text-zinc-500"
                  >{{ ch.content }}</pre
                >
              </div>
            </button>
          </div>
        </div>
      </ScrollArea>
    </template>
  </aside>
</template>
