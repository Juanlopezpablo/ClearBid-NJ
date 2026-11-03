# NEW-03 — Etiquetas y búsqueda avanzada (web)

## Uso

- Abrir un ticket de desarrollo o soporte: la sección **Etiquetas** permite guardar nombres separados por comas. Se admiten hasta 10 etiquetas de 40 caracteres; se normalizan espacios y mayúsculas y se eliminan duplicados. Vaciar el campo retira todas las etiquetas.
- ADMIN y TEAM_LEADER pueden editar las etiquetas de cualquier ticket. Un DEVELOPER puede editar las de sus tickets asignados. Los demás las ven sin poder modificarlas, conforme a los permisos existentes de edición.
- El enlace **Buscar tickets** del encabezado abre `/#/tickets/search`, disponible con sesión iniciada.
- Combinar título/descripción/UUID, etiquetas, estado, prioridad, tipo de ticket, aplicación, responsable y período de creación. El filtro de responsable permite buscar usuarios activos por nombre, además de «Mis tickets» y «Sin asignar».
- Las condiciones se combinan con AND; si se indican varias etiquetas, deben estar todas en el ticket. Las fechas se interpretan en UTC e incluyen ambos días completos.
- Los resultados muestran el total y páginas de 25 tickets. Abrir un resultado permite consultar descripción, etiquetas, comentarios y evidencias. «Limpiar filtros» restaura la consulta general.

## API y persistencia

`TicketCreate`, `TicketUpdate` y `TicketResponse` incorporan `labels`. Actualizar otros campos sin enviar `labels` conserva las etiquetas existentes. Se rechazan valores nulos, vacíos, comas, caracteres invisibles y límites excedidos.

`GET /api/tickets/search` acepta `q`, parámetros `labels` repetidos, `status_filter`, `priority`, `ticket_type`, `application_id`, `assignee_id`, `unassigned`, `created_from`, `created_to`, `skip` y `limit`. Retorna `items`, `total`, `skip`, `limit`. La paginación se aplica después de filtrar y ordenar por creación e ID. Los comodines `%` y `_` del texto se interpretan literalmente. La búsqueda mantiene el alcance de lectura existente de tickets para usuarios autenticados.

La migración `l8m9n0p1q2r3` añade `tickets.labels` con valor inicial vacío e índice GIN en PostgreSQL. Antes de iniciar el backend actualizado, ejecutar desde la carpeta backend:

```powershell
alembic upgrade head
```

La reversión elimina la columna y sus etiquetas; respaldar la base antes de revertir.

## Validación

Las pruebas de integración `tests/integration/test_ticket_search.py` usan PostgreSQL y Redis en una base aislada `corestream_test`: cubren persistencia, permisos, normalización, validación, combinaciones, texto literal, fechas y paginación. Las pruebas de la web cubren edición, lectura sin permisos, respuestas atrasadas, filtros, rango de fechas y paginación.

Este cambio se prepara en JuanPablo. Subirlo a GitHub no conecta la API pendiente de Vercel ni publica automáticamente la rama en main.
