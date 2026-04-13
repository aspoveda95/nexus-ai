<script setup lang="ts">
import { Cloud, Cpu } from 'lucide-vue-next'
import { SwitchRoot, SwitchThumb } from 'radix-vue'
import { computed } from 'vue'

import { cn } from '@/lib/utils'
import type { ChatMode } from '@/types/api'

const mode = defineModel<ChatMode>({ required: true })

const cloudOn = computed({
  get: () => mode.value === 'cloud',
  set: (v: boolean) => {
    mode.value = v ? 'cloud' : 'local'
  },
})
</script>

<template>
  <div class="flex items-center gap-3 rounded-lg border border-zinc-800 bg-zinc-950/50 px-2 py-1.5">
    <div
      :class="
        cn(
          'flex items-center gap-1.5 text-xs font-medium transition-colors',
          !cloudOn ? 'text-zinc-100' : 'text-zinc-500',
        )
      "
    >
      <Cpu class="h-3.5 w-3.5" aria-hidden="true" />
      Local
    </div>
    <SwitchRoot
      v-model:checked="cloudOn"
      class="relative h-6 w-11 cursor-default rounded-full border border-zinc-700 bg-zinc-900 outline-none data-[state=checked]:bg-zinc-700"
    >
      <SwitchThumb
        class="block h-5 w-5 translate-x-0.5 rounded-full bg-zinc-100 transition-transform will-change-transform data-[state=checked]:translate-x-[1.375rem]"
      />
    </SwitchRoot>
    <div
      :class="
        cn(
          'flex items-center gap-1.5 text-xs font-medium transition-colors',
          cloudOn ? 'text-zinc-100' : 'text-zinc-500',
        )
      "
    >
      <Cloud class="h-3.5 w-3.5" aria-hidden="true" />
      Cloud
    </div>
  </div>
</template>
