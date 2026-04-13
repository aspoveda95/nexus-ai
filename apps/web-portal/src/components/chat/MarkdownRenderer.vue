<script setup lang="ts">
import DOMPurify from 'dompurify'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'
import { computed, nextTick, ref, watch } from 'vue'

import { cn } from '@/lib/utils'

const utils = new MarkdownIt().utils

function escapeHtml(s: string): string {
  return utils.escapeHtml(s)
}

function highlightCode(code: string, lang: string): string {
  const language = lang && hljs.getLanguage(lang) ? lang : 'plaintext'
  try {
    const highlighted =
      language === 'plaintext'
        ? escapeHtml(code)
        : hljs.highlight(code, { language, ignoreIllegals: true }).value
    return `<pre class="nexus-code" data-language="${escapeHtml(language)}"><code class="hljs language-${escapeHtml(language)}">${highlighted}</code></pre>`
  } catch {
    return `<pre class="nexus-code"><code class="hljs">${escapeHtml(code)}</code></pre>`
  }
}

const props = defineProps<{
  source: string
  class?: string
}>()

const root = ref<HTMLElement | null>(null)

const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: highlightCode,
})

const html = computed(() => {
  const raw = md.render(props.source || '')
  return DOMPurify.sanitize(raw, {
    ADD_ATTR: ['data-language', 'class', 'data-copy'],
  })
})

function enhanceCodeBlocks() {
  const el = root.value
  if (!el) return
  el.querySelectorAll('pre.nexus-code').forEach((pre) => {
    if (pre.parentElement?.classList.contains('nexus-code-wrap')) return
    const wrap = document.createElement('div')
    wrap.className =
      'nexus-code-wrap group relative my-3 overflow-hidden rounded-lg border border-zinc-800 bg-zinc-950/80'
    const parent = pre.parentNode
    if (!parent) return
    parent.insertBefore(wrap, pre)
    wrap.appendChild(pre)
    pre.classList.add(
      '!m-0',
      '!rounded-none',
      '!border-0',
      '!bg-zinc-950',
      'p-4',
      'pt-10',
      'text-sm',
      'leading-relaxed',
    )

    const btn = document.createElement('button')
    btn.type = 'button'
    btn.className =
      'nexus-copy-btn absolute right-2 top-2 inline-flex h-8 items-center gap-1 rounded-md border border-zinc-800 bg-zinc-900/90 px-2 text-[11px] font-medium text-zinc-300 opacity-0 transition-opacity hover:bg-zinc-800 group-hover:opacity-100'
    btn.textContent = 'Copiar'
    btn.addEventListener('click', async () => {
      const code = pre.querySelector('code')
      const text = code?.textContent ?? ''
      try {
        await navigator.clipboard.writeText(text)
        btn.textContent = 'Copiado'
        setTimeout(() => {
          btn.textContent = 'Copiar'
        }, 1600)
      } catch {
        btn.textContent = 'Error'
        setTimeout(() => {
          btn.textContent = 'Copiar'
        }, 1600)
      }
    })
    wrap.appendChild(btn)
  })
}

watch(
  () => html.value,
  async () => {
    await nextTick()
    enhanceCodeBlocks()
  },
  { immediate: true },
)
</script>

<template>
  <div
    ref="root"
    :class="
      cn(
        'markdown-body text-[13px] leading-relaxed text-zinc-200',
        '[&_a]:text-sky-400 [&_a]:underline [&_a]:underline-offset-4',
        '[&_p]:my-2 [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-0.5',
        '[&_h1]:text-base [&_h1]:font-semibold [&_h2]:mt-4 [&_h2]:text-sm [&_h2]:font-semibold',
        '[&_p>code]:rounded [&_p>code]:bg-zinc-900 [&_p>code]:px-1.5 [&_p>code]:py-0.5 [&_p>code]:font-mono [&_p>code]:text-[12px]',
        '[&_pre_code]:bg-transparent [&_pre_code]:p-0',
        props.class,
      )
    "
    v-html="html"
  />
</template>
