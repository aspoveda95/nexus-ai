<script setup lang="ts">
import { Bot, User } from 'lucide-vue-next'
import { computed } from 'vue'

import MarkdownRenderer from '@/components/chat/MarkdownRenderer.vue'
import { cn } from '@/lib/utils'
import type { ChatCitation } from '@/types/api'

const props = defineProps<{
  role: 'user' | 'assistant'
  content: string
  streaming?: boolean
  citations?: ChatCitation[]
  highlightPath?: string | null
}>()

const emit = defineEmits<{
  selectCitation: [path: string]
}>()

const chips = computed(() => props.citations ?? [])

function chipClass(path: string) {
  return cn(
    'rounded-md border px-2 py-0.5 font-mono text-[11px] transition-colors',
    props.highlightPath === path
      ? 'border-sky-500/60 bg-sky-950/40 text-sky-200'
      : 'border-zinc-800 bg-zinc-900/50 text-zinc-400 hover:border-zinc-700 hover:text-zinc-200',
  )
}
</script>

<template>
  <div
    :class="
      cn(
        'flex gap-3',
        role === 'user' ? 'flex-row-reverse' : 'flex-row',
      )
    "
  >
    <div
      :class="
        cn(
          'mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border',
          role === 'user'
            ? 'border-zinc-700 bg-zinc-900 text-zinc-200'
            : 'border-zinc-800 bg-zinc-950 text-sky-300',
        )
      "
    >
      <User v-if="role === 'user'" class="h-4 w-4" aria-hidden="true" />
      <Bot v-else class="h-4 w-4" aria-hidden="true" />
    </div>
    <div class="min-w-0 flex-1 space-y-2">
      <div
        :class="
          cn(
            'rounded-2xl border px-4 py-3',
            role === 'user'
              ? 'border-zinc-800 bg-zinc-900/40 text-zinc-100'
              : 'border-zinc-800/80 bg-zinc-950/40 text-zinc-100',
          )
        "
      >
        <div v-if="role === 'user'" class="whitespace-pre-wrap text-[13px] leading-relaxed">
          {{ content }}
        </div>
        <div v-else class="space-y-2">
          <MarkdownRenderer :source="content" />
          <div v-if="streaming" class="flex items-center gap-2 text-[11px] text-zinc-500">
            <span class="inline-flex h-1.5 w-1.5 animate-pulse rounded-full bg-sky-400" />
            Generando…
          </div>
        </div>
      </div>
      <div
        v-if="role === 'assistant' && chips.length"
        class="flex flex-wrap gap-1.5 pl-1"
      >
        <button
          v-for="c in chips"
          :key="c.source_path"
          type="button"
          :data-citation-anchor="c.source_path"
          :class="chipClass(c.source_path)"
          @click="emit('selectCitation', c.source_path)"
        >
          {{ c.source_path }}
        </button>
      </div>
    </div>
  </div>
</template>
