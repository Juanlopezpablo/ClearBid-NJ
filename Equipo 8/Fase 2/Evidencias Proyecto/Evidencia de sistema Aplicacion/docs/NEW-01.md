# NEW-01 — Comentarios y menciones en tickets

Implementación web de comentarios dentro del detalle de ticket (Workbench y panel de ticket).

## Uso y permisos

- Cualquier usuario autenticado y activo puede consultar comentarios y comentar en un ticket existente.
- Cada autor puede editar sus propios comentarios. ADMIN tampoco puede editar comentarios ajenos.
- Solo ADMIN puede eliminar comentarios, con confirmación en la interfaz.
- El formulario permite buscar usuarios activos por nombre y agregarlos como menciones. No expone correos ni datos del directorio administrativo.
- Los comentarios se muestran como texto, sin interpretar HTML.
- Las menciones generan notificaciones internas persistentes asociadas al ticket, entregadas por el WebSocket existente. No se envían correos.
- Una mención repetida en el mismo comentario genera una sola notificación; las automenciones no notifican.
- Al editar, se notifica solo a los usuarios agregados respecto de la versión anterior. Quitar una mención y volver a agregarla en otra edición vuelve a notificar.
- Máximo: 5000 caracteres y 20 usuarios mencionados. La lista se carga de 50 en 50.

## API

Todas las rutas requieren autenticación; las operaciones de NEW-01 rechazan cuentas inactivas.

| Método | Ruta | Acción |
|---|---|---|
| GET | `/api/tickets/comment-mentions?q=nombre` | Buscar hasta 20 usuarios activos (ID y nombre) |
| GET | `/api/tickets/{ticket_id}/comments?offset=0&limit=50` | Listar comentarios (límite máximo 100) |
| POST | `/api/tickets/{ticket_id}/comments` | Crear comentario |
| PATCH | `/api/tickets/{ticket_id}/comments/{comment_id}` | Editar comentario propio |
| DELETE | `/api/tickets/{ticket_id}/comments/{comment_id}` | Eliminar como ADMIN |

POST y PATCH reciben `{"body": "Texto del comentario"}`. Las menciones se representan en el contrato como `@[Nombre](UUID)`: el servidor valida el ID, comprueba que siga activo y guarda su nombre canónico. El formulario gestiona esta representación sin mostrar los IDs al usuario.

Las notificaciones usan el tipo interno existente `SYSTEM`, con título de mención y `ticket_id`, por lo que funcionan con la bandeja y navegación actuales. Comentario y notificaciones se guardan en la misma transacción; la publicación Redis ocurre después del commit.

## Migración y comprobaciones

La migración Alembic `j6k7l8m9n0p1` agrega `ticket_comments`. El despliegue debe ejecutar `alembic upgrade head` mediante el flujo de migración existente antes de servir la nueva versión.

Eliminar un ticket elimina sus comentarios por clave foránea. Eliminar una cuenta conserva el comentario con autor nulo y el rótulo «Usuario eliminado». El downgrade elimina la tabla y sus comentarios.

Comprobaciones desde la carpeta de la aplicación:

```bash
cd backend
python -m pytest tests/ --ignore=tests/integration -q
python -m ruff check app/routers/comments.py app/models/comment.py app/schemas/comment.py tests/test_comments.py alembic/versions/j6k7l8m9n0p1_add_ticket_comments.py
cd ../frontend
pnpm exec vitest run
pnpm exec vue-tsc --noEmit
pnpm exec vite build
```

`backend/tests/test_comments.py` ejercita HTTP y persistencia en SQLite; sustituye únicamente la entrega Redis por un espía. `frontend/tests/unit/components/TicketComments.spec.ts` verifica permisos visibles, confirmación de borrado, edición, selección de menciones, texto seguro, errores y cambios de ticket con respuestas pendientes.

La validación con PostgreSQL y Redis reales requiere los servicios del entorno de integración; las pruebas SQLite y la generación SQL de Alembic no la sustituyen.

