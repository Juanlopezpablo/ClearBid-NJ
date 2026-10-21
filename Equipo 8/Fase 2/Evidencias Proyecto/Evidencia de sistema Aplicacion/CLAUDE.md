# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Convenciones de colaboración

- Commits: nunca agregar línea de coautoría (ni `Co-Authored-By`). Mensajes cortos y precisos, lo mínimo necesario para entenderse.
- Comentarios en código: siempre en inglés, lo mínimo necesario.

## Qué es esto

CoreStream: plataforma de gestión de proyectos/tickets (Kanban) para equipos de desarrollo. Backend FastAPI (Python 3.11, async de punta a punta) + Vue 3/TS/Vite en el frontend, PostgreSQL 15 y Redis 7, con WebSockets sobre pub/sub de Redis (las notificaciones se publican directo desde la API, sin worker).

## Comandos

Todo corre en Docker; Node/Python locales solo hacen falta para autocompletado del editor.

```bash
# Levantar entorno de desarrollo (bind mounts, hot-reload, Postgres/Redis propios y descartables)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build

# Salud del stack
docker compose ps                        # 4 servicios deben estar "healthy"
curl http://localhost:8000/api/health    # {"status":"ok", "checks": {...}}

# Tests backend
docker compose exec backend pytest tests/ --ignore=tests/integration -q   # unitarios, SQLite en memoria
docker compose exec backend pytest tests/integration -q                    # requieren Postgres/Redis reales
docker compose exec backend pytest tests/test_tickets.py::test_name -q     # un test puntual

# Lint / types backend
docker compose exec backend ruff check app/ tests/
docker compose exec backend mypy app/

# Primer admin (no hay seeder ni usuario por defecto; el resto se crea por invitación)
docker compose exec backend python -m app.scripts.create_admin --email x@y.com --password "..."
```

Frontend (`frontend/`), fuera de Docker si hace falta iterar rápido con tipos:

```bash
npm run dev          # servidor Vite (usado dentro del overlay de dev)
npm run type-check   # vue-tsc --noEmit
npm run test:unit    # vitest
npm run test:e2e     # cypress run
npm run build
```

URLs en desarrollo: frontend `http://localhost:5173`, backend `http://localhost:8000`, Swagger en `http://localhost:8000/api/docs` (deshabilitado si `ENVIRONMENT=production`).

## Los dos perfiles de Docker Compose

No es un fichero con condicionales, son dos que se combinan:

- `docker-compose.yml` — perfil de **producción**: las mismas imágenes que corren en Cloud Run, sin bind mounts ni `--reload`, con un servicio `migrate` (`alembic upgrade head`) del que depende `backend`. **No levanta Postgres ni Redis propios**: recibe `DATABASE_URL`/`REDIS_URL` desde `.env`. En GCP no se usa; sirve para probar las imágenes en local.
- `docker-compose.dev.yml` — overlay de **desarrollo**: bind mounts, servidor de Vite, y Postgres/Redis propios y descartables.

Para desarrollo local siempre se usan los dos juntos (ver comando arriba). Para probar el perfil de producción en local, ver `docs/SETUP.md`. Los puertos `8010`/`8080` y el volumen `storage-data` de `docker-compose.yml` son herencia del despliegue en Azure.

## Despliegue en GCP

Producción corre en GCP desde el 02-10-2026 (Azure apagado). Inventario, configuración y operación en `docs/DEPLOYMENT.md`; la infraestructura se creó a mano con `gcloud` y **no vive en este repo**.

- Proyecto `corestream-project`, región `southamerica-east1`, dominio `https://corestream.alloxentric.com`.
- Cloud Run `corestream-api` (concurrencia 100, 0–10 instancias, timeout 3600 s) y `corestream-web` detrás de un balanceador HTTPS global (`/api/*` → API, resto → web; certificados en Certificate Manager).
- Job `corestream-migrate` (`alembic upgrade head`), que se ejecuta antes de cada despliegue de la API.
- VM `corestream-data` (10.10.0.10, sin IP pública, IAP) con Postgres 15 y Redis 7 en Docker Compose (`/opt/corestream`), datos en un disco aparte (`/data`).
- Buckets `corestream-file` (documentos) y `corestream-backups` (`pg_dump` diario, 21 días).
- Secretos en Secret Manager (`SECRET_KEY`, `DATABASE_URL`, `REDIS_URL`, `SMTP_PASSWORD`).
- Detrás del balanceador la IP real del cliente es la penúltima de `X-Forwarded-For`: `XFF_CLIENT_POSITION=2`.
- `max-instances=10` × pool (5 + 5) = 100 conexiones, bajo `max_connections=120`. No subir `max-instances` sin PgBouncer.

`backend/scripts/backup_db.sh`/`restore_db.sh` son del despliegue en Azure y ya no se usan.

## Arquitectura backend (`backend/app/`)

- `routers/` — un módulo por dominio (`auth`, `tickets`, `epics`, `applications`, `subtasks`, `documents`, `notifications`, `invitations`, `teams`, `meetings`, `incidents`, `support_tickets`, `analytics`, `websocket`, `ticket_redirection`).
- `services/` — lógica de negocio: `ticket_state_machine.py`, `ticket_permissions.py`, `ticket_redirection.py`, `notification_service.py`, `translation_service.py`, `timer_service.py`, `transition_audit.py`, `auth_service.py`, `email_service.py`, `storage.py`, `analytics_service.py`.
- `models/base.py` — **toda `relationship()` debe declarar `lazy="raise_on_sql"`** (no `"raise"` a secas, no el `"select"` por defecto). La app usa `AsyncSession` exclusivamente, que no soporta lazy loading implícito; sin esto, una relación no precargada revienta en producción con `MissingGreenlet` al serializar con Pydantic. `raise_on_sql` falla ruidosamente en desarrollo/CI en el momento en que de verdad haría falta una consulta, pero no rompe accesos que se resuelven sin tocar la base (ej. FK a NULL en un `if self.relacion else None`).
- Esquema de BD gestionado únicamente por Alembic. `alembic upgrade head` **no** corre al arrancar el backend: corre una vez por despliegue, antes de la nueva versión (Cloud Run Job `corestream-migrate` en GCP; servicio `migrate` en docker compose, del que depende `backend`). Si la migración falla, el despliegue se detiene.
- No hay worker de tareas en segundo plano: `notification_service.publish_notification()` publica en Redis directo desde la API, tras el commit (se eliminó ARQ en la migración a GCP).

### RBAC (referencia autoritativa en `docs/RBAC.md` — actualizar en el mismo commit que cualquier cambio de autorización)

Roles: `ADMIN` (administra usuarios/estructura, no ejecuta trabajo operativo sobre tickets), `TEAM_LEADER` (gestiona el trabajo de su equipo + todo lo de DEVELOPER sobre tickets propios), `DEVELOPER` (solo actúa sobre tickets/subtareas/documentos propios). El mecanismo en uso es `require_role(...)` de `middleware/auth.py` (el decorador `require_permissions`/`RBACRole` de `middleware/rbac.py` es histórico, sin llamadas activas). Un rol desconocido lanza `ValueError`/`RuntimeError`, nunca deniega en silencio.

Helpers de ownership en `app/services/ticket_permissions.py` (usados por `routers/tickets.py`, `subtasks.py`, `documents.py`): `require_non_admin`, `require_admin_or_leader`, `assert_can_manage_ticket`, `assert_is_current_assignee`, `claim_or_assert_assignee`, `is_admin_or_leader`.

### Tiempo real (Redis pub/sub)

Todos los canales/claves llevan prefijo `corestream:`. Flujo: cambio de estado de ticket → guardado en Postgres → evento publicado (`corestream:tickets:updates` o `corestream:user:{id}:notifications`) → WebSocket lo entrega. El endpoint WS usa dos tareas de larga vida coordinadas con `asyncio.wait(..., return_when=FIRST_COMPLETED)` (evitar volver al patrón de recrear tareas en cada iteración de un loop sin timeout real — saturaba CPU con conexiones inactivas).

Traducción de documentos: Google Cloud Translation v3 (`services/translation_service.py`), sin claves: usa las credenciales de Google del entorno (en Cloud Run, la service account con `roles/cloudtranslate.user`; en local, `gcloud auth application-default login`) y factura a `GCP_PROJECT_ID`. Sin credenciales, traducir responde 503 "no configurada".

Documentos: los bytes nunca pasan por la API. Subida en 3 pasos (`POST /api/documents/upload-url` → `PUT` directo al bucket con la URL firmada → `POST /api/documents/confirm`) y descarga con `GET /api/documents/{id}/download-url`. `documents.file_path` guarda la clave del objeto (`documents/<uuid>`). `STORAGE_BACKEND=gcs` en GCP (bucket `corestream-file`, ver `docs/DEPLOYMENT.md`); `local` en desarrollo y tests, que imita las URLs firmadas con `/api/documents/local-storage/{token}`.

Autenticación WS: ticket de un solo uso de 15s (`POST /api/auth/ws-ticket`), no el JWT en el query string (evita que quede en logs de acceso de un proxy).

Inactividad WS (un socket abierto mantiene una instancia de Cloud Run facturando): el front pregunta "¿Sigues ahí?" a los 10 min sin actividad (`components/common/IdlePrompt.vue`) y cierra con código 4000 a los 15; no reconecta solo, el usuario pulsa "Reconectar". Mientras hay actividad manda `{type: 'activity'}` (máx. 1/min); el backend cierra con 4000 si no recibe ninguno en `WS_IDLE_TIMEOUT_SECONDS` (20 min). Los ping/pong automáticos no cuentan como actividad. Tras cualquier reconexión se emite `ws-resync` en el eventBus: las vistas que consumen `ws-update` deben escucharlo y recargar.

### Seguridad

JWT access (corta duración) + refresh (httpOnly, `SameSite=Strict`, solo viaja a `/api/auth/refresh`), claim `type` y `jti` para revocación individual en logout. CSRF por doble envío (cookie `csrf_token` + header `X-CSRF-Token`) en toda mutación que dependa de la cookie de refresh. Contraseñas: bcrypt con pre-hash SHA-256 (evita el límite de 72 bytes de bcrypt sin truncar la contraseña real). Alta de usuarios exclusivamente por invitación, sin registro público.

## Tests backend

- `tests/` (raíz) — unitarios, lógica pura, SQLite en memoria, rápidos.
- `tests/integration/` — requieren Postgres y Redis reales, marcados con `integration`; crean/migran su propia base (`corestream_test`) por sesión, no tocan datos de desarrollo.
- `pytest.ini`: `asyncio_mode = auto`, loop de eventos de ámbito de sesión (los tests de integración comparten un único cliente HTTP/loop en vez de levantar el lifespan completo en cada test).

## Lint (ruff)

Set de reglas deliberadamente acotado (`F`, `E4`, `E7`, `E9`, `I`, `ASYNC`, `B`, `PLE`, `RUF100`) — no el default de ruff, que hoy generaría ~776 avisos de modernización sin ganancia real. `B008` ignorado a propósito (patrón `Depends(...)` de FastAPI en defaults). `B904` ignorado temporalmente (falta `from exc` en `raise HTTPException` dentro de varios `except`; pendiente de una fase de observabilidad). Violaciones `ASYNC230`/`ASYNC240` conocidas están marcadas una a una con `# noqa` explicado, no silenciadas globalmente, para que cualquier violación *nueva* siga rompiendo CI.

## Dependencias

Versiones fijadas en `requirements.txt` a propósito (antes iban sin pin y una reconstrucción de imagen podía traer un mayor incompatible sin avisar). Para actualizar: cambiar el pin, reconstruir la imagen, correr la suite completa de tests, y solo entonces commitear.

## Backups (producción)

Los hace la VM de datos de GCP: snapshot diario del disco de datos y `pg_dump` diario a `gs://corestream-backups/db/` (cron con `/opt/corestream/backup.sh`), ambos con 21 días de retención. Restauración con `/opt/corestream/restore.sh`. Ver `docs/DEPLOYMENT.md`.
