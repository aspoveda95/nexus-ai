<script setup lang="ts">
import {
  CheckCircle,
  Folder,
  FolderOpen,
  Loader2,
  Plus,
  RefreshCw,
  Search,
} from 'lucide-vue-next'
import { computed, onMounted, ref } from 'vue'

import Button from '@/components/ui/Button.vue'
import Input from '@/components/ui/Input.vue'
import ScrollArea from '@/components/ui/ScrollArea.vue'
import Separator from '@/components/ui/Separator.vue'
import { cn } from '@/lib/utils'
import { useRepositoriesStore, type RepositoryItem } from '@/stores/repositories'

const repos = useRepositoriesStore()

const addOpen = ref(false)
const newRoot = ref('/data/repos/')
const ingestError = ref<string | null>(null)
const folderPickError = ref<string | null>(null)
const dirInputRef = ref<HTMLInputElement | null>(null)

/** ID válido para api-core: empieza por alfanumérico, [a-zA-Z0-9_-] */
function repositoryIdFromFolderName(name: string): string {
  let id = name.trim().replace(/\s+/g, '-').replace(/[^a-zA-Z0-9_-]/g, '')
  if (!id) id = 'repo'
  if (!/^[a-zA-Z0-9]/.test(id)) id = `r-${id}`
  return id.slice(0, 128)
}

function applyPickedFolder(folderName: string) {
  newRoot.value = `/data/repos/${folderName.trim()}`
  folderPickError.value = null
}

/** Nombre de carpeta tal cual en la ruta (nombre del repo en el volumen). */
const repoFolderName = computed(() => {
  const m = newRoot.value.trim().match(/\/data\/repos\/([^/]+)/)
  return (m?.[1] ?? '').trim()
})

/** ID enviado al backend: derivado del nombre de carpeta. */
const derivedRepositoryId = computed(() => {
  const name = repoFolderName.value
  if (!name) return ''
  return repositoryIdFromFolderName(name)
})

async function pickFolderFromFinder() {
  folderPickError.value = null
  const w = window as Window & {
    showDirectoryPicker?: () => Promise<FileSystemDirectoryHandle>
  }
  if (typeof w.showDirectoryPicker === 'function') {
    try {
      const handle = await w.showDirectoryPicker()
      applyPickedFolder(handle.name)
      return
    } catch (e) {
      if (e instanceof DOMException && e.name === 'AbortError') return
      folderPickError.value =
        'No se pudo usar el selector del sistema. Prueba el botón alternativo o escribe la ruta.'
    }
  }
  dirInputRef.value?.click()
}

function onLegacyDirectoryChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const files = input.files
  input.value = ''
  if (!files?.length) return
  const first = files[0] as File & { webkitRelativePath?: string }
  const rel = first.webkitRelativePath ?? first.name ?? ''
  const rootDir = rel.split('/')[0]?.trim()
  if (!rootDir) {
    folderPickError.value =
      'No se leyó el nombre de la carpeta. Usa Chrome/Edge o escribe /data/repos/… manualmente.'
    return
  }
  applyPickedFolder(rootDir)
}

function openAdd() {
  addOpen.value = true
  newRoot.value = '/data/repos/'
}

onMounted(() => {
  if (repos.items.length === 0) {
    openAdd()
  }
})

async function submitAdd() {
  const id = derivedRepositoryId.value
  if (!id) return
  const label = repoFolderName.value || id
  const ok = repos.addRepository({
    id,
    label,
    rootPath: newRoot.value.trim(),
  })
  if (!ok) return
  addOpen.value = false
  ingestError.value = null
  try {
    await repos.runIngest(id)
  } catch (e) {
    ingestError.value = e instanceof Error ? e.message : 'Error de ingesta'
  }
}

async function ingestActive() {
  const id = repos.activeId
  if (!id) return
  ingestError.value = null
  try {
    await repos.runIngest(id)
  } catch (e) {
    ingestError.value = e instanceof Error ? e.message : 'Error de ingesta'
  }
}

function statusIcon(r: RepositoryItem) {
  if (r.status === 'ingesting') return Loader2
  if (r.status === 'ready') return CheckCircle
  return Folder
}

function rowClass(r: RepositoryItem) {
  return cn(
    'flex w-full items-center gap-2 rounded-lg border px-2 py-2 text-left text-sm transition-colors',
    repos.activeId === r.id
      ? 'border-zinc-600 bg-zinc-900/80 text-zinc-50'
      : 'border-transparent bg-transparent text-zinc-400 hover:border-zinc-800 hover:bg-zinc-900/40 hover:text-zinc-200',
  )
}
</script>

<template>
  <aside
    class="flex h-full min-h-0 w-full flex-col border-r border-zinc-800/80 bg-zinc-950/40 backdrop-blur-sm"
  >
    <div class="flex items-center justify-between gap-2 px-3 py-3">
      <div class="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.2em] text-zinc-500">
        Repositorios
      </div>
      <Button variant="ghost" size="icon" class="h-8 w-8" title="Añadir repositorio" @click="openAdd">
        <Plus class="h-4 w-4" />
      </Button>
    </div>
    <div class="px-3 pb-2">
      <div class="relative">
        <Search
          class="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-600"
          aria-hidden="true"
        />
        <Input v-model="repos.searchQuery" placeholder="Buscar proyectos…" class="pl-8 text-[13px]" />
      </div>
    </div>
    <Separator class="mx-3" />
    <ScrollArea class="flex-1 px-2 py-2">
      <div class="mb-2 flex items-center justify-between gap-2 px-1">
        <span class="text-[10px] font-medium uppercase tracking-wide text-zinc-600">Ingesta</span>
        <Button
          variant="outline"
          size="sm"
          class="h-7 gap-1.5 px-2 text-[11px]"
          :disabled="!repos.activeId"
          title="Vectorizar repositorio activo"
          @click="ingestActive"
        >
          <Loader2
            v-if="repos.items.find((r) => r.id === repos.activeId)?.status === 'ingesting'"
            class="h-3.5 w-3.5 animate-spin"
          />
          <RefreshCw v-else class="h-3.5 w-3.5" />
          Sync
        </Button>
      </div>
      <p v-if="ingestError" class="mb-2 px-1 text-[11px] text-red-400/90">{{ ingestError }}</p>
      <div
        v-if="repos.items.length === 0 && !addOpen"
        class="mx-1 rounded-lg border border-dashed border-zinc-800 bg-zinc-950/50 px-3 py-6 text-center"
      >
        <p class="text-[12px] leading-relaxed text-zinc-500">
          Añade un repo con <span class="text-zinc-400">+</span>: puedes
          <strong class="font-medium text-zinc-400">elegir la carpeta en el Finder</strong>. El nombre de
          esa carpeta debe ser el mismo que dentro de la ruta que montaste en Docker (p. ej.
          <span class="font-mono text-[11px]">NEXUS_HOST_REPOS</span>).
        </p>
        <Button variant="subtle" size="sm" class="mt-3" @click="openAdd"> Añadir repositorio </Button>
      </div>
      <div v-if="repos.items.length > 0" class="space-y-1">
        <button
          v-for="r in repos.filtered"
          :key="r.id"
          type="button"
          :class="rowClass(r)"
          @click="repos.setActive(r.id)"
        >
          <component
            :is="statusIcon(r)"
            :class="
              cn(
                'h-4 w-4 shrink-0',
                r.status === 'ingesting' && 'animate-spin text-sky-400',
                r.status === 'ready' && 'text-emerald-400',
                r.status === 'idle' && 'text-zinc-500',
                r.status === 'error' && 'text-red-400',
              )
            "
            aria-hidden="true"
          />
          <span class="min-w-0 flex-1 truncate font-medium">{{ r.label }}</span>
        </button>
      </div>
    </ScrollArea>

    <div v-if="addOpen" class="border-t border-zinc-800 p-3">
      <input
        ref="dirInputRef"
        type="file"
        class="sr-only"
        tabindex="-1"
        webkitdirectory
        multiple
        @change="onLegacyDirectoryChange"
      />
      <p class="mb-2 text-[11px] font-medium uppercase tracking-wide text-zinc-500">Nuevo repositorio</p>
      <p class="mb-2 text-[11px] leading-relaxed text-zinc-600">
        El navegador no puede ver la ruta completa de tu Mac; usamos el
        <span class="text-zinc-400">nombre de la carpeta</span> para armar
        <span class="font-mono text-zinc-500">/data/repos/&lt;nombre&gt;</span> dentro de Docker. Esa
        carpeta debe existir bajo tu
        <span class="font-mono text-zinc-500">NEXUS_HOST_REPOS</span>.
      </p>
      <Button variant="outline" size="sm" class="mb-3 w-full gap-2" @click="pickFolderFromFinder">
        <FolderOpen class="h-3.5 w-3.5" />
        Elegir carpeta (Finder)…
      </Button>
      <p v-if="folderPickError" class="mb-2 text-[11px] text-amber-400/90">{{ folderPickError }}</p>
      <div class="space-y-2">
        <div
          class="rounded-md border border-zinc-800 bg-zinc-950/60 px-3 py-2 text-[12px] text-zinc-400"
        >
          <span class="text-[10px] font-medium uppercase tracking-wide text-zinc-600">Nombre (carpeta)</span>
          <p class="mt-0.5 font-mono text-[13px] text-zinc-200">
            {{ repoFolderName || '—' }}
          </p>
          <span class="mt-2 block text-[10px] font-medium uppercase tracking-wide text-zinc-600">ID en API</span>
          <p class="mt-0.5 font-mono text-[13px] text-sky-300/90">
            {{ derivedRepositoryId || '—' }}
          </p>
          <p class="mt-1 text-[11px] leading-snug text-zinc-600">
            El nombre en la lista es el de la carpeta; el ID se normaliza para el backend.
          </p>
        </div>
        <Input
          v-model="newRoot"
          placeholder="/data/repos/mi-clone"
          class="font-mono text-[12px]"
        />
        <div class="flex gap-2 pt-1">
          <Button class="flex-1" size="sm" :disabled="!derivedRepositoryId" @click="submitAdd">
            Guardar
          </Button>
          <Button variant="outline" size="sm" @click="addOpen = false"> Cancelar </Button>
        </div>
      </div>
    </div>
  </aside>
</template>
