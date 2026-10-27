<template>
  <section class="p-6 border-b border-[var(--border-subtle)]" aria-label="Archivos y evidencia">
    <h3 class="text-sm font-semibold text-[var(--text-primary)] mb-3">Archivos y evidencia</h3>
    <FileUpload :key="ticketId || incidentId" :ticket-id="ticketId" :incident-id="incidentId" />
  </section>
</template>

<script setup lang="ts">
import FileUpload from '@/components/FileUpload.vue'

defineProps<{ ticketId?: string; incidentId?: string }>()
</script>

