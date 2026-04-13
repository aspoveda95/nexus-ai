<script setup lang="ts">
import { computed, type HTMLAttributes } from 'vue'

import { cn } from '@/lib/utils'

const props = withDefaults(
  defineProps<{
    orientation?: 'horizontal' | 'vertical'
    class?: HTMLAttributes['class']
  }>(),
  { orientation: 'horizontal' },
)

const classes = computed(() =>
  cn(
    'shrink-0 bg-zinc-800',
    props.orientation === 'horizontal' ? 'h-px w-full' : 'h-full w-px',
    props.class,
  ),
)
</script>

<template>
  <div role="separator" :class="classes" />
</template>
