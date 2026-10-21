# Guía de Instalación de CoreStream

Esta guía explica cómo ejecutar el proyecto CoreStream localmente, tanto
para desarrollo como para probar el perfil de producción antes de
desplegarlo. Producción corre en GCP (Cloud Run + VM de datos); para
publicar versiones y operar la infraestructura, ver
[`DEPLOYMENT.md`](./DEPLOYMENT.md).

## Requisitos previos

- **Docker y Docker Compose** (todo lo demás se ejecuta dentro de contenedores)
- Node.js y Python locales solo son necesarios si se quiere ejecutar algo
  fuera de Docker (por ejemplo, el editor con autocompletado de tipos).

## Estructura de los ficheros de Compose

Hay dos ficheros de Compose que se combinan, no se sustituyen:

- `docker-compose.yml` — perfil de **producción**: las mismas imágenes que
  se despliegan en Cloud Run (sin bind mounts, sin `--reload`), más un
  servicio `migrate` que corre `alembic upgrade head` antes del backend.
  No corre Postgres ni Redis propios: hay que pasarle `DATABASE_URL` y
  `REDIS_URL`. En GCP no se usa (ahí hay Cloud Run); sirve para probar las
  imágenes en local.
- `docker-compose.dev.yml` — overlay de **desarrollo**: añade bind mounts
  con recarga en caliente, el servidor de Vite (no la build de Nginx), y
  sus propios Postgres/Redis descartables, publicados en `127.0.0.1`, y
  guarda los documentos en disco (`STORAGE_BACKEND=local`), sin necesitar
  GCP.

Para desarrollo local siempre se usan los dos juntos:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Inicio rápido (desarrollo)

1. Copiar las variables de entorno (en la raíz del repositorio, **no** en `backend/`):

   ```bash
   cp .env.example .env
   ```

   Los valores por defecto de `docker-compose.dev.yml` ya son seguros para
   desarrollo local (contraseñas de ejemplo, `ENVIRONMENT=development`);
   normalmente no hace falta editar nada de `.env` solo para levantar el
   entorno de desarrollo. `.env` sí es obligatorio y debe rellenarse con
   valores reales para probar el perfil de producción (ver más abajo).

2. Levantar el stack:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
   ```

   Antes del backend corre el servicio `migrate` (`alembic upgrade head`,
   una sola vez). El backend solo arranca si la migración termina bien
   (por diseño — no hay arranque silencioso contra un esquema a medio
   migrar). Es el mismo rol que cumple el Cloud Run Job
   `corestream-migrate` en GCP.

3. Comprobar que todo está sano:

   ```bash
   docker compose ps                        # 4 servicios "healthy" + migrate "Exited (0)"
   curl http://localhost:8000/api/health    # {"status":"ok", "checks": {...}}
   ```

**URLs de acceso (desarrollo):**

- Frontend: <http://localhost:5173> (servidor de Vite, con HMR)
- Backend: <http://localhost:8000>
- Documentación interactiva de la API: <http://localhost:8000/api/docs>
  (Swagger UI — deshabilitada automáticamente si `ENVIRONMENT=production`)

## Primer usuario administrador

No existe ningún usuario por defecto ni seeder que cree uno: es deliberado
(antes había credenciales conocidas — `admin@example.com` — que se
recreaban en cada arranque). El primer ADMIN se crea a mano, una vez:

```bash
docker compose exec backend python -m app.scripts.create_admin \
    --email tu-email@empresa.com --password "unaClaveSegura123!"
```

El script se niega a correr si ya existe un ADMIN. El resto de usuarios se
crean por invitación: como ADMIN, desde **Equipo → Invitar**, se genera un
enlace de un solo uso que el invitado usa para elegir su propia contraseña.

## Ejecutar la suite de tests

```bash
# Tests unitarios (lógica pura, SQLite en memoria, rápidos)
docker compose exec backend pytest tests/ --ignore=tests/integration -q

# Tests de integración (Postgres y Redis reales, más lentos)
docker compose exec backend pytest tests/integration -q

# Lint
docker compose exec backend ruff check app/ tests/
```

Los tests de integración crean y migran su propia base de datos
(`corestream_test`) en cada sesión — no tocan los datos de desarrollo.

## Traducción de documentos en local

La traducción usa Google Cloud Translation con las credenciales de Google
del entorno. En local, para probarla:

```bash
gcloud auth application-default login
```

y `GCP_PROJECT_ID=corestream-project` en el entorno del backend. Sin
credenciales, traducir responde 503 "no configurada" y el resto de la app
funciona igual.

## Probar el perfil de producción en local

Antes de desplegar, vale la pena levantar las imágenes de producción tal
cual corren en Cloud Run (sin el overlay de desarrollo):

```bash
cp .env.example .env
# Rellenar DATABASE_URL, REDIS_URL (una instancia de Postgres/Redis real,
# aunque sea local — el perfil de producción no levanta la suya propia),
# SECRET_KEY (openssl rand -hex 32), ALLOWED_ORIGINS, y dejar
# ENVIRONMENT=production

docker compose up -d --build
curl http://127.0.0.1:8010/api/health
curl -H "Host: tu-dominio-real.com" http://127.0.0.1:8080/   # debe dar 200
```

Con `ENVIRONMENT=production`, el backend **aborta el arranque** si
`SECRET_KEY` sigue siendo un placeholder, si `DEBUG=true`, si
`ALLOWED_ORIGINS` es `"*"`, o si no hay `STORAGE_BACKEND=gcs` con un
`GCS_BUCKET` — es intencional, no un bug. Firmar URLs del bucket requiere
una cuenta de servicio (como en Cloud Run); con credenciales de usuario
la app arranca pero las subidas y descargas de documentos fallan. Usar un
bucket de pruebas, nunca `corestream-file`.

## Backups

Los respaldos de producción los hace la VM de datos de GCP (snapshot
diario del disco y `pg_dump` diario al bucket `corestream-backups`). Ver
[`DEPLOYMENT.md`](./DEPLOYMENT.md#respaldos). En desarrollo no hay
respaldos: los Postgres/Redis del overlay son descartables.
