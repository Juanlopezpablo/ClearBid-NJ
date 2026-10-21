<template>
  <section class="p-6 border-b border-[var(--border-subtle)] text-[var(--text-primary)]" aria-label="Comentarios">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-sm font-semibold">Comentarios</h3>
      <button type="button" class="text-sm underline" :disabled="busy || loading" @click="load()">Actualizar</button>
    </div>
    <p v-if="error" role="alert" class="text-red-500 text-sm mb-3">{{ error }}</p>
    <p v-if="loading" role="status" class="text-sm">Cargando comentarios…</p>
    <p v-else-if="!comments.length" class="text-sm text-[var(--text-muted)]">Todavía no hay comentarios.</p>
    <article v-for="comment in comments" :key="comment.id" class="py-3 border-b border-[var(--border-subtle)]">
      <div class="flex justify-between gap-2 text-xs text-[var(--text-secondary)]">
        <strong>{{ comment.author_name }}</strong>
        <time :datetime="comment.created_at">{{ new Date(comment.created_at).toLocaleString() }}</time>
      </div>
      <p class="whitespace-pre-wrap break-words text-sm my-2">{{ readable(comment.body) }}</p>
      <p v-if="comment.updated_at !== comment.created_at" class="text-xs text-[var(--text-muted)]">Editado</p>
      <div class="flex gap-3 text-xs">
        <button v-if="comment.author_id === auth.user?.id" type="button" class="underline" :disabled="busy" @click="edit(comment)">Editar</button>
        <button v-if="auth.isAdmin" type="button" class="underline" :disabled="busy" @click="remove(comment.id)">Eliminar</button>
      </div>
    </article>
    <button v-if="hasMore" type="button" class="text-sm underline my-3" :disabled="loading" @click="loadMore">Cargar más comentarios</button>
    <form class="mt-4 space-y-3" @submit.prevent="save">
      <label class="block text-sm font-medium" :for="editorId">{{ editing ? 'Editar comentario' : 'Nuevo comentario' }}</label>
      <textarea :id="editorId" v-model="body" :disabled="busy" maxlength="5000" rows="3" required
        class="w-full p-3 rounded-lg bg-[var(--bg-input)] border border-[var(--border-subtle)]"
        placeholder="Escribe un comentario…" />
      <label class="block text-sm" :for="mentionId">Mencionar a un usuario activo</label>
      <input :id="mentionId" v-model="search" :disabled="busy || mentions.length >= 20" type="search" maxlength="100"
        class="w-full p-2 rounded-lg bg-[var(--bg-input)] border border-[var(--border-subtle)]"
        placeholder="Buscar por nombre…" @input="searchUsers" />
      <p v-if="searching" class="text-xs" role="status">Buscando usuarios…</p>
      <p v-if="searchError" class="text-xs" role="alert">{{ searchError }}</p>
      <p v-if="searched && !searching && !searchError && !results.length" class="text-xs">No se encontraron usuarios activos.</p>
      <ul v-if="results.length" class="max-h-40 overflow-auto rounded border border-[var(--border-subtle)]">
        <li v-for="user in results" :key="user.id">
          <button type="button" class="w-full p-2 text-left text-sm hover:bg-[var(--bg-panel)]" :disabled="busy" @click="mention(user)">{{ user.full_name }}</button>
        </li>
      </ul>
      <div class="flex flex-wrap gap-2">
        <button v-for="user in mentions" :key="user.id" type="button" :disabled="busy"
          class="px-2 py-1 text-xs rounded bg-[var(--bg-panel)]"
          :aria-label="'Quitar mención a ' + user.full_name" @click="mentions = mentions.filter(item => item.id !== user.id)">
          @{{ user.full_name }} ×
        </button>
      </div>
      <p class="text-xs text-[var(--text-muted)]">Las personas mencionadas recibirán una notificación interna.</p>
      <div class="flex gap-3">
        <button type="submit" class="px-3 py-2 rounded bg-[var(--teal)] text-white text-sm" :disabled="busy || loading || !body.trim()">
          {{ busy ? 'Guardando…' : editing ? 'Guardar cambios' : 'Comentar' }}
        </button>
        <button v-if="editing" type="button" :disabled="busy" class="text-sm underline" @click="reset">Cancelar edición</button>
      </div>
    </form>
  </section>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useDialogStore } from '@/stores/dialog'

interface Comment {
  id: string
  ticket_id: string
  author_id: string | null
  author_name: string
  body: string
  created_at: string
  updated_at: string
}
interface MentionUser { id: string; full_name: string }
const props = defineProps<{ ticketId: string }>()
const auth = useAuthStore()
const dialog = useDialogStore()
const comments = ref<Comment[]>([])
const body = ref('')
const editing = ref<string | null>(null)
const mentions = ref<MentionUser[]>([])
const search = ref('')
const results = ref<MentionUser[]>([])
const error = ref('')
const searchError = ref('')
const searched = ref(false)
const searching = ref(false)
const busy = ref(false)
const loading = ref(false)
const hasMore = ref(false)
const editorId = computed(() => 'comment-body-' + props.ticketId)
const mentionId = computed(() => 'comment-mention-' + props.ticketId)
let generation = 0
let searchGeneration = 0
let timer: ReturnType<typeof setTimeout> | undefined
const mentionPattern = /@\[([^\]\r\n]{1,255})\]\(([0-9a-fA-F-]{36})\)/g
const readable = (text: string) => text.replace(mentionPattern, '@$1')
const url = (ticketId: string) => '/tickets/' + ticketId + '/comments'
function message(cause: unknown): string {
  const detail = (cause as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : 'No se pudo completar la operación. Inténtalo de nuevo.'
}
function reset() {
  editing.value = null
  body.value = ''
  mentions.value = []
  search.value = ''
  results.value = []
  searchError.value = ''
  searched.value = false
  searching.value = false
  searchGeneration++
  clearTimeout(timer)
}
async function load(append = false) {
  if (append && loading.value) return
  const ticketId = props.ticketId
  const current = ++generation
  loading.value = true
  error.value = ''
  try {
    const { data } = await apiClient.get<Comment[]>(url(ticketId), {
      params: { offset: append ? comments.value.length : 0, limit: 50 },
    })
    if (current !== generation) return
    comments.value = append ? [...comments.value, ...data] : data
    hasMore.value = data.length === 50
  } catch (cause) {
    if (current === generation) error.value = message(cause)
  } finally {
    if (current === generation) loading.value = false
  }
}
const loadMore = () => load(true)
function edit(comment: Comment) {
  reset()
  editing.value = comment.id
  const users = new Map<string, MentionUser>()
  body.value = comment.body.replace(mentionPattern, (_match, name: string, id: string) => {
    users.set(id, { id, full_name: name })
    return ''
  }).trim()
  mentions.value = [...users.values()]
}
function mention(user: MentionUser) {
  if (mentions.value.length < 20 && !mentions.value.some(item => item.id === user.id)) mentions.value.push(user)
  search.value = ''
  results.value = []
  searched.value = false
  searchGeneration++
}
function searchUsers() {
  clearTimeout(timer)
  const current = ++searchGeneration
  results.value = []
  searched.value = false
  searchError.value = ''
  searching.value = false
  if (!search.value.trim()) return
  timer = setTimeout(async () => {
    searching.value = true
    try {
      const { data } = await apiClient.get<MentionUser[]>('/tickets/comment-mentions', { params: { q: search.value } })
      if (current === searchGeneration) {
        results.value = data.filter(user => !mentions.value.some(item => item.id === user.id))
        searched.value = true
      }
    } catch (cause) {
      if (current === searchGeneration) searchError.value = message(cause)
    } finally {
      if (current === searchGeneration) searching.value = false
    }
  }, 250)
}
async function save() {
  if (busy.value || !body.value.trim()) return
  const ticketId = props.ticketId
  busy.value = true
  error.value = ''
  const text = [body.value.trim(), ...mentions.value.map(user =>
    '@[' + user.full_name.replace(/[\[\]\r\n]/g, ' ') + '](' + user.id + ')')].join('\n')
  try {
    if (editing.value) await apiClient.patch(url(ticketId) + '/' + editing.value, { body: text })
    else await apiClient.post(url(ticketId), { body: text })
    if (ticketId === props.ticketId) {
      reset()
      await load()
    }
  } catch (cause) {
    if (ticketId === props.ticketId) error.value = message(cause)
  } finally { busy.value = false }
}
async function remove(id: string) {
  const ticketId = props.ticketId
  if (!await dialog.confirm('¿Eliminar este comentario?')) return
  if (ticketId !== props.ticketId) return
  busy.value = true
  error.value = ''
  try {
    await apiClient.delete(url(ticketId) + '/' + id)
    if (ticketId === props.ticketId) {
      if (editing.value === id) reset()
      await load()
    }
  } catch (cause) {
    if (ticketId === props.ticketId) error.value = message(cause)
  } finally { busy.value = false }
}
watch(() => props.ticketId, () => {
  reset()
  comments.value = []
  hasMore.value = false
  void load()
}, { immediate: true })
onBeforeUnmount(() => { generation++; searchGeneration++; clearTimeout(timer) })
</script>

