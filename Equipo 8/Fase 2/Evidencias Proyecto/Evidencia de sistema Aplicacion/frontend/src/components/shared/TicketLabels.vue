<template>
  <section class="p-5 border-b border-[var(--border-subtle)] space-y-3" aria-label="Etiquetas del ticket">
    <h3 class="font-semibold">Etiquetas</h3>
    <p v-if="loading" role="status">Cargando etiquetas…</p>
    <div class="flex flex-wrap gap-2">
      <span v-for="label in labels" :key="label" class="rounded-full bg-[var(--bg-app)] border border-[var(--border-subtle)] px-3 py-1 text-sm">{{ label }}</span>
      <span v-if="!loading && !labels.length" class="text-sm text-[var(--text-muted)]">Sin etiquetas</span>
    </div>
    <form v-if="canEdit && loaded && !loading" @submit.prevent="save" class="space-y-2">
      <label class="block text-sm">Editar etiquetas (separadas por comas)
        <input v-model="draft" :disabled="busy" maxlength="410" class="w-full mt-1 p-2 rounded border border-[var(--border-subtle)] bg-[var(--bg-app)]" placeholder="Por ejemplo: interfaz, urgente" />
      </label>
      <p class="text-xs text-[var(--text-muted)]">Máximo 10 etiquetas, de 40 caracteres cada una. Vacía el campo para quitarlas.</p>
      <button :disabled="busy" class="rounded bg-[var(--teal)] text-white px-3 py-2 disabled:opacity-50">{{ busy ? 'Guardando…' : 'Guardar etiquetas' }}</button>
    </form>
    <p v-if="error" role="alert" class="text-red-600">{{ error }}</p>
    <p v-if="saved" role="status">Etiquetas guardadas.</p>
  </section>
</template>

<script setup lang="ts">
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import { apiClient } from '@/services/api'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{ ticketId: string }>()
const emit = defineEmits<{ updated: [labels: string[]] }>()
const auth = useAuthStore()
const labels = ref<string[]>([])
const assignee = ref<string | null>(null)
const draft = ref('')
const loading = ref(false)
const loaded = ref(false)
const busy = ref(false)
const error = ref('')
const saved = ref(false)
let generation = 0
const canEdit = computed(() => ['ADMIN', 'TEAM_LEADER'].includes(auth.userRole || '') || (!!auth.user?.id && assignee.value === auth.user.id))
watch(() => props.ticketId, async id => {
  const current = ++generation
  loading.value = true
  loaded.value = false
  busy.value = false
  saved.value = false
  error.value = ''
  labels.value = []
  assignee.value = null
  try {
    const { data } = await apiClient.get(`/tickets/${id}`)
    if (current !== generation) return
    labels.value = data.labels || []
    draft.value = labels.value.join(', ')
    assignee.value = data.assignee_id
    loaded.value = true
  } catch {
    if (current === generation) error.value = 'No se pudieron cargar las etiquetas. Vuelve a abrir el ticket para reintentar.'
  } finally {
    if (current === generation) loading.value = false
  }
}, { immediate: true })
async function save() {
  if (busy.value) return
  const values = draft.value.split(',').map(label => label.trim()).filter(Boolean)
  error.value = ''
  saved.value = false
  if (values.length > 10 || values.some(label => label.length > 40)) {
    error.value = 'Usa hasta 10 etiquetas de 40 caracteres cada una.'
    return
  }
  const current = generation
  busy.value = true
  try {
    const { data } = await apiClient.put(`/tickets/${props.ticketId}`, { labels: values })
    if (current !== generation) return
    labels.value = data.labels
    draft.value = labels.value.join(', ')
    saved.value = true
    emit('updated', labels.value)
  } catch {
    if (current === generation) error.value = 'No se pudieron guardar las etiquetas. Comprueba tus permisos y los valores ingresados.'
  } finally {
    if (current === generation) busy.value = false
  }
}
onBeforeUnmount(() => { generation++ })
</script>
