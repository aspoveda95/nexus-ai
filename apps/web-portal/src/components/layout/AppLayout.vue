<script setup lang="ts">
import { Folder, PanelRight } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { useMediaQuery } from '@vueuse/core'

import Button from '@/components/ui/Button.vue'
import CenterChat from '@/components/layout/CenterChat.vue'
import LeftSidebar from '@/components/layout/LeftSidebar.vue'
import RightInspector from '@/components/layout/RightInspector.vue'
import { cn } from '@/lib/utils'

const wide = useMediaQuery('(min-width: 1280px)')
const leftOpen = ref(false)
const rightOpen = ref(false)
const rightCollapsed = ref(false)

const showInspector = computed(() => wide.value || rightOpen.value)

function closeLeft() {
  leftOpen.value = false
}

function closeRight() {
  rightOpen.value = false
}
</script>

<template>
  <div class="flex h-dvh flex-col overflow-hidden bg-zinc-950 text-zinc-100">
    <header
      class="flex shrink-0 items-center justify-between border-b border-zinc-800/80 px-3 py-2 xl:hidden"
    >
      <Button variant="outline" size="sm" class="gap-2" @click="leftOpen = true">
        <Folder class="h-4 w-4" />
        Repos
      </Button>
      <span class="text-[11px] font-semibold uppercase tracking-[0.25em] text-zinc-500">
        Nexus-AI
      </span>
      <Button variant="outline" size="sm" class="gap-2" @click="rightOpen = true">
        <PanelRight class="h-4 w-4" />
        Fuentes
      </Button>
    </header>

    <div class="relative flex min-h-0 min-w-0 flex-1 flex-row">
      <div class="hidden h-full min-h-0 w-[280px] shrink-0 border-r border-zinc-800/80 xl:flex">
        <LeftSidebar />
      </div>

      <div v-if="!wide && leftOpen" class="fixed inset-0 z-50 flex xl:hidden">
        <div class="h-full w-[min(100%,320px)] border-r border-zinc-800 bg-zinc-950 shadow-2xl">
          <LeftSidebar />
        </div>
        <button
          type="button"
          class="min-w-0 flex-1 bg-black/60 backdrop-blur-sm"
          aria-label="Cerrar"
          @click="closeLeft"
        />
      </div>

      <CenterChat class="min-h-0 min-w-0 flex-1" />

      <button
        v-if="!wide && rightOpen"
        type="button"
        class="fixed inset-0 z-40 bg-black/50 backdrop-blur-[1px] xl:hidden"
        aria-label="Cerrar inspector"
        @click="closeRight"
      />

      <RightInspector
        v-show="showInspector"
        v-model:collapsed="rightCollapsed"
        :class="
          cn(
            'min-h-0 border-l border-zinc-800/80 bg-zinc-950/30',
            wide &&
              'flex h-full w-[min(100%,420px)] shrink-0',
            !wide &&
              rightOpen &&
              'fixed bottom-0 right-0 top-12 z-50 w-[min(100%,440px)] overflow-hidden shadow-2xl shadow-black/50',
          )
        "
      />
    </div>
  </div>
</template>
