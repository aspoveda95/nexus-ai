<script setup lang="ts">
import { type HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

defineProps<{
  class?: HTMLAttributes['class']
}>()
</script>

<template>
  <div :class="cn('min-h-0 min-w-0 overflow-y-auto overflow-x-hidden', $props.class)">
    <slot />
  </div>
</template>
