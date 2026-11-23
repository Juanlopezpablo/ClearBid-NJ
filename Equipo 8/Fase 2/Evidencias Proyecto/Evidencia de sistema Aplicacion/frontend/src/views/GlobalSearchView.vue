<template>
  <div class="min-h-screen bg-[var(--bg-app)] text-[var(--text-primary)]">
    <AppHeader />
    <main class="max-w-5xl mx-auto p-6 space-y-5">
      <h1 class="text-2xl font-bold">Búsqueda global</h1>
      <p>Encuentra tickets, aplicaciones, épicas, incidencias y documentos desde un solo lugar.</p>
      <form @submit.prevent="search(0)" class="flex flex-wrap gap-3">
        <input v-model="query" aria-label="Texto de búsqueda" minlength="2" maxlength="200" required placeholder="Buscar palabras o identificadores" class="flex-1 min-w-48 border rounded p-3 bg-[var(--bg-panel)]" />
        <select v-model="kind" aria-label="Tipo de resultado" class="border rounded p-3 bg-[var(--bg-panel)]"><option value="all">Todos</option><option v-for="(label, value) in labels" :key="value" :value="value">{{ label }}</option></select>
        <button :disabled="loading" class="rounded px-5 py-2 bg-[var(--teal)] text-white">Buscar</button>
      </form>
      <p class="text-sm">Los documentos se buscan por nombre y texto disponible en PDF, DOCX y archivos de texto. Imágenes, PDF escaneados y archivos antiguos sin indexar se encuentran por nombre.</p>
      <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
      <p v-if="loading" role="status">Buscando…</p>
      <template v-else-if="searched && !error">
        <p role="status">{{ total }} resultados</p>
        <p v-if="!items.length">No se encontraron coincidencias.</p>
        <article v-for="item in items" :key="item.kind + item.id" class="p-4 border rounded-xl bg-[var(--bg-panel)] space-y-2">
          <span class="text-sm">{{ labels[item.kind] }}</span>
          <h2 class="font-bold"><template v-for="(part, index) in highlight(item.title)" :key="index"><mark v-if="part.match">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></h2>
          <p><template v-for="(part, index) in highlight(item.snippet)" :key="index"><mark v-if="part.match">{{ part.text }}</mark><template v-else>{{ part.text }}</template></template></p>
          <button @click="open(item)" class="text-[var(--teal)] underline">{{ item.kind === 'document' ? 'Abrir documento' : 'Ver detalle' }}</button>
        </article>
        <nav aria-label="Paginación" class="flex gap-5"><button :disabled="skip === 0" @click="search(skip - 25)">Anterior</button><span>Página {{ Math.floor(skip / 25) + 1 }}</span><button :disabled="skip + 25 >= total" @click="search(skip + 25)">Siguiente</button></nav>
      </template>
      <section v-if="selected" role="dialog" aria-modal="true" aria-label="Detalle del resultado" class="fixed inset-0 z-[110] bg-black/40 flex items-center justify-center p-5" @click.self="selected = null" @keydown.esc="selected = null">
        <div class="bg-[var(--bg-panel)] p-6 rounded-xl max-w-2xl w-full max-h-[85vh] overflow-auto space-y-4">
          <button @click="selected = null" class="float-right" aria-label="Cerrar">✕</button>
          <h2 class="font-bold text-xl">{{ detail?.title || detail?.name || selected.title }}</h2>
          <p class="whitespace-pre-wrap">{{ detail?.description || 'Sin descripción' }}</p>
          <template v-if="selected.kind === 'ticket'"><TicketComments :ticket-id="selected.id" /><EvidenceFiles :ticket-id="selected.id" /></template>
          <EvidenceFiles v-if="selected.kind === 'incident'" :incident-id="selected.id" />
        </div>
      </section>
    </main>
  </div>
</template>
<script setup lang="ts">
import { ref, onBeforeUnmount } from 'vue'
import AppHeader from '@/components/layout/AppHeader.vue'
import TicketComments from '@/components/shared/TicketComments.vue'
import EvidenceFiles from '@/components/shared/EvidenceFiles.vue'
import { apiClient } from '@/services/api'
interface Result { id: string; kind: string; title: string; snippet: string }
const labels: Record<string, string> = { ticket: 'Tickets', application: 'Aplicaciones', epic: 'Épicas', incident: 'Incidencias', document: 'Documentos' }
const query = ref(''), kind = ref('all'), submitted = ref(''), error = ref('')
const items = ref<Result[]>([]), total = ref(0), skip = ref(0), loading = ref(false), searched = ref(false)
const selected = ref<Result | null>(null), detail = ref<{ title?: string; name?: string; description?: string } | null>(null)
let request = 0
onBeforeUnmount(() => { request++ })
let applied = { q: "", kind: "all" }
async function search(offset: number) {
  if (offset === 0) applied = { q: query.value.trim(), kind: kind.value }
  const text = applied.q
  if (text.length < 2) { error.value = 'Escribe al menos dos caracteres.'; return }
  const id = ++request
  loading.value = true; error.value = ''; selected.value = null
  try {
    const { data } = await apiClient.get('/search', { params: { q: text, kind: applied.kind, skip: offset, limit: 25 } })
    if (id !== request) return
    items.value = data.items; total.value = data.total; skip.value = offset; submitted.value = text; searched.value = true
  } catch { if (id === request) error.value = 'No se pudo completar la búsqueda. Revisa tu conexión e inténtalo nuevamente.' }
  finally { if (id === request) loading.value = false }
}
function highlight(text: string) {
  const needle = submitted.value.toLowerCase(), parts: { text: string; match: boolean }[] = []
  let position = 0, index: number
  if (!needle) return [{ text, match: false }]
  while ((index = text.toLowerCase().indexOf(needle, position)) >= 0) {
    parts.push({ text: text.slice(position, index), match: false }, { text: text.slice(index, index + needle.length), match: true })
    position = index + needle.length
  }
  parts.push({ text: text.slice(position), match: false }); return parts
}
async function open(item: Result) {
  error.value = ''
  try {
    if (item.kind === 'document') {
      const { data } = await apiClient.get(`/documents/${item.id}/download-url`)
      // La URL firmada se obtiene al abrir; nunca se conserva entre búsquedas.
      const link = document.createElement('a'); link.href = data.url; link.target = '_blank'; link.rel = 'noopener noreferrer'; link.click()
      return
    }
    const paths: Record<string, string> = { ticket: 'tickets', application: 'applications', epic: 'epics', incident: 'incidents' }
    const { data } = await apiClient.get(`/${paths[item.kind]}/${item.id}`)
    detail.value = data; selected.value = item
  } catch { error.value = 'No se pudo abrir el resultado. Puede haber sido eliminado o tu sesión expiró.' }
}
</script>
