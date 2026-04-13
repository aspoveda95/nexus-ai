<script setup lang="ts">
import { type HTMLAttributes, computed } from 'vue'

import { cn } from '@/lib/utils'

type Variant = 'default' | 'ghost' | 'outline' | 'subtle' | 'destructive'
type Size = 'default' | 'sm' | 'icon'

const props = withDefaults(
  defineProps<{
    variant?: Variant
    size?: Size
    class?: HTMLAttributes['class']
    type?: 'button' | 'submit'
    disabled?: boolean
  }>(),
  { variant: 'default', size: 'default', type: 'button', disabled: false },
)

const classes = computed(() =>
  cn(
    'inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-md text-sm font-medium transition-colors',
    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-950',
    'disabled:pointer-events-none disabled:opacity-40',
    props.variant === 'default' && 'bg-zinc-100 text-zinc-950 hover:bg-white',
    props.variant === 'ghost' && 'text-zinc-300 hover:bg-zinc-800/80 hover:text-zinc-50',
    props.variant === 'outline' && 'border border-zinc-700 bg-transparent text-zinc-200 hover:bg-zinc-900',
    props.variant === 'subtle' && 'border border-zinc-800 bg-zinc-900/60 text-zinc-100 hover:bg-zinc-800/90',
    props.variant === 'destructive' && 'bg-red-900/80 text-red-50 hover:bg-red-800',
    props.size === 'default' && 'h-9 px-4 py-2',
    props.size === 'sm' && 'h-8 px-3 text-xs',
    props.size === 'icon' && 'h-9 w-9',
    props.class,
  ),
)
</script>

<template>
  <button :type="type" :disabled="disabled" :class="classes">
    <slot />
  </button>
</template>
