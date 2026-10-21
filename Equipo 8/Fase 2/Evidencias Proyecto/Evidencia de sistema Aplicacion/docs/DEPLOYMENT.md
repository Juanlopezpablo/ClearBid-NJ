# Despliegue de CoreStream en GCP

CoreStream corre en Google Cloud desde el **2 de octubre de 2026** (antes,
en una VM de Azure con Docker, ya apagada). Este documento describe cómo
está montado y cómo se opera: publicar una versión nueva, cambiar
configuración, entrar a la base, respaldos y restauración.

- **Proyecto:** `corestream-project` · **Región:** `southamerica-east1`
  (São Paulo) · **Zona de la VM:** `southamerica-east1-a`
- **Dominio:** `https://corestream.alloxentric.com`
- **Dónde correr los comandos:** **Cloud Shell** (botón `>_` en la consola
  de GCP). Ya trae `gcloud`, `git` y Python, y está autenticado con tu
  cuenta. El repo está clonado ahí en `~/corestream`.

La infraestructura se creó a mano con `gcloud`, paso a paso. **No vive en
este repositorio**: lo que hay que saber de ella está acá.

## Arquitectura

```text
Usuarios ──HTTPS──► Balanceador HTTPS global (IP 136.68.50.59, certificados de Certificate Manager)
                      ├─ /api/*  ──► Cloud Run "corestream-api" (FastAPI, REST + WebSocket)
                      │                ├─► VM "corestream-data" 10.10.0.10 (Direct VPC egress)
                      │                │     ├─ PostgreSQL 15  :5432
                      │                │     └─ Redis 7        :6379
                      │                ├─► Cloud Storage "corestream-file" (URLs firmadas)
                      │                ├─► Cloud Translation API v3
                      │                └─► SMTP Zoho
                      └─ /*      ──► Cloud Run "corestream-web" (Nginx + build de Vue)

Navegador ──URL firmada──► Cloud Storage (subidas y descargas directas, sin pasar por la API)
VM ──pg_dump diario──► Cloud Storage "corestream-backups" (se borra a los 21 días)
```

Front y API escalan a cero cuando nadie los usa. La VM de datos está
encendida 24/7 y es la única pieza que no escala sola.

## Inventario de recursos

### Red

| Recurso | Nombre | Detalle |
|---|---|---|
| VPC | `corestream-vpc` | Modo custom |
| Subred de datos | `corestream-data` | `10.10.0.0/24`, acceso privado a APIs de Google |
| Subred de Cloud Run | `corestream-run` | `10.10.1.0/24`, salida de Cloud Run hacia la VPC (Direct VPC egress) |
| IP interna fija | `corestream-data-ip` | `10.10.0.10` (la VM) |
| Router + NAT | `corestream-router`, `corestream-nat` | Salida a internet de la VM (apt, imágenes) sin IP pública |
| Firewall | `corestream-allow-data` | `5432` y `6379` **solo** desde `10.10.1.0/24` hacia el tag `corestream-data` |
| Firewall | `corestream-allow-iap` | `22` y `5432` desde `35.235.240.0/20` (IAP) |

### Cuentas de servicio

| Cuenta | Para qué | Permisos |
|---|---|---|
| `corestream-api` | Cloud Run API y Job de migraciones | `cloudtranslate.user` (proyecto); `iam.serviceAccountTokenCreator` sobre sí misma (firmar URLs); `storage.objectAdmin` en `corestream-file`; `secretAccessor` en los 4 secretos |
| `corestream-web` | Cloud Run web | Ninguno (solo sirve estáticos) |
| `corestream-data-vm` | VM de datos | `logging.logWriter`, `monitoring.metricWriter` (proyecto); `storage.objectCreator` y `storage.objectViewer` en `corestream-backups` (puede subir y leer respaldos, **no borrarlos**) |
| `318802276837-compute@developer` | Cloud Build | `artifactregistry.writer` en el repo `corestream`, `storage.objectViewer` en `gs://corestream-project_cloudbuild`, `logging.logWriter` |

Los permisos se dieron sobre cada recurso puntual, no a nivel de proyecto,
salvo los indicados.

### VM de datos `corestream-data`

- `e2-small` (2 vCPU compartidas, 2 GB), Debian 12, **sin IP pública**,
  tag `corestream-data`, OS Login activado.
- Disco de datos aparte, `corestream-data-disk` (30 GB, `pd-balanced`),
  montado en `/data`: `/data/postgres` y `/data/redis`. Se puede recrear
  la VM sin tocar los datos.
- Docker Compose en `/opt/corestream` con dos contenedores:
  - `corestream-postgres` (`postgres:15`): `max_connections=120`,
    contraseñas SCRAM, `shared_buffers=512MB`.
  - `corestream-redis` (`redis:7-alpine`): `requirepass`, `appendonly yes`,
    `maxmemory 256mb`, `maxmemory-policy noeviction` (si se llena falla la
    escritura, en vez de borrar en silencio claves como las revocaciones de
    sesión).
- Contraseñas en `/opt/corestream/.env` (permisos 600).
- Scripts en `/opt/corestream`: `backup.sh` (respaldo diario, por cron) y
  `restore.sh` (restauración, pide confirmación).
- Ops Agent (métricas de memoria y disco), parches de seguridad automáticos
  (`unattended-upgrades`), zona horaria `America/Santiago`.

### Buckets

| Bucket | Uso | Configuración |
|---|---|---|
| `corestream-file` | Documentos | Privado, acceso uniforme, Standard + Autoclass. CORS (`PUT`) para los dominios de la app. Lifecycle: borra `pending/` a las 24 h (subidas sin confirmar) |
| `corestream-backups` | Respaldos `pg_dump` | Privado, Standard. Lifecycle: borra a los 21 días |

### Secret Manager

| Secreto | Variable en la API |
|---|---|
| `corestream-secret-key` | `SECRET_KEY` |
| `corestream-database-url` | `DATABASE_URL` (`postgresql+asyncpg://corestream:…@10.10.0.10:5432/corestream`) |
| `corestream-redis-url` | `REDIS_URL` (`redis://:…@10.10.0.10:6379/0`) |
| `corestream-smtp-password` | `SMTP_PASSWORD` |

### Imágenes

Artifact Registry `corestream` (Docker, región `southamerica-east1`):
`southamerica-east1-docker.pkg.dev/corestream-project/corestream/{api,web}:<commit>`.
La política de limpieza conserva las 10 versiones más recientes y borra
las de más de 30 días.

### Cloud Run

| | `corestream-api` | `corestream-web` |
|---|---|---|
| Imagen | `api:<commit>` | `web:<commit>` |
| Cuenta | `corestream-api` | `corestream-web` |
| CPU / memoria | 1 / 512Mi | 1 / 256Mi |
| Concurrencia | 100 | 100 |
| Timeout | 3600 s (WebSockets) | por defecto |
| Instancias | 0–10 | 0–3 |
| Ingress | `internal-and-cloud-load-balancing` | `internal-and-cloud-load-balancing` |
| Red | Direct VPC egress `corestream-vpc` / `corestream-run`, `private-ranges-only` | — |
| Variables | `api.env.yaml` + 4 secretos | ninguna |

Además, el **Job `corestream-migrate`**: misma imagen, cuenta, red,
variables y secretos que la API. Corre `alembic upgrade head` (sin
reintentos, timeout 10 min).

`--no-invoker-iam-check`: los servicios no exigen IAM para invocarse (la
organización no permite `allUsers`). La protección real es el ingress: solo
se entra por el balanceador. La URL `*.run.app` no responde desde internet.

`--max-instances=10` en la API no es arbitrario: 10 instancias × (5 + 5)
conexiones del pool = 100, bajo el `max_connections=120` de Postgres. **No
subirlo sin agregar PgBouncer antes** (ver "Cuando crezca el uso").

### Balanceador HTTPS

| Pieza | Nombre |
|---|---|
| IP global | `corestream-ip` = `136.68.50.59` |
| NEGs serverless | `corestream-api-neg`, `corestream-web-neg` |
| Backend services | `corestream-api-be`, `corestream-web-be` (`EXTERNAL_MANAGED`) |
| URL map | `corestream-lb`: `/api/*` → API, todo lo demás → web, cualquier host |
| Proxy HTTPS | `corestream-https` + certificate map `corestream-map`, regla `corestream-https-fr` (443) |
| HTTP → HTTPS | URL map `corestream-http-redirect`, proxy `corestream-http`, regla `corestream-http-fr` (80) |

Certificados (Certificate Manager, administrados por Google, autorizados
por el balanceador: basta el registro A, sin CNAME):

| Certificado | Entrada del map | Dominio |
|---|---|---|
| `corestream-cert` | `corestream-entry` | `corestream.alloxentric.com` |
| `corestream-gcp-cert` | `corestream-gcp-entry` | `corestream-gcp.alloxentric.com` (dominio de prueba de la migración; se elimina, ver más abajo) |

El DNS de `alloxentric.com` está en DreamHost y lo administra el dueño de
la empresa. Solo hay registros A hacia `136.68.50.59`. La renovación de los
certificados es automática **mientras el registro A siga apuntando al
balanceador**.

## Configuración de la API

### Variables (`api.env.yaml`)

Están en Cloud Shell, en `~/deploy/api.env.yaml`. Ese archivo no tiene
secretos, pero tampoco está en el repo:

| Variable | Valor |
|---|---|
| `ENVIRONMENT` | `production` |
| `DEBUG` | `"false"` |
| `LOG_LEVEL` | `info` |
| `ALLOWED_ORIGINS` | `https://corestream.alloxentric.com` (+ el dominio de prueba mientras exista) |
| `XFF_CLIENT_POSITION` | `"2"` (penúltima entrada de `X-Forwarded-For`, verificado en producción) |
| `GCP_PROJECT_ID` | `corestream-project` |
| `STORAGE_BACKEND` / `GCS_BUCKET` | `gcs` / `corestream-file` |
| `TRANSLATION_LOCATION` | `global` |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` | `5` / `5` |
| `WS_IDLE_TIMEOUT_SECONDS` | `1200` |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USE_SSL` | `smtppro.zoho.eu` / `587` / `"false"` |
| `SMTP_USER`, `MAIL_FROM`, `MAIL_FROM_NAME` | Cuenta de Zoho |

`UVICORN_WORKERS=1` y `FORWARDED_ALLOW_IPS=*` vienen por defecto en la
imagen (`backend/Dockerfile`).

### Cambiar una variable

Crea una revisión nueva al instante. Hay que cambiarla en la API **y** en
el Job, porque comparten configuración:

```bash
gcloud run services update corestream-api --region=southamerica-east1 \
  --update-env-vars=LOG_LEVEL=debug
gcloud run jobs update corestream-migrate --region=southamerica-east1 \
  --update-env-vars=LOG_LEVEL=debug
```

Si el valor lleva comas (como `ALLOWED_ORIGINS`), hay que cambiar el
separador con `^@^`:

```bash
--update-env-vars="^@^ALLOWED_ORIGINS=https://a.alloxentric.com,https://b.alloxentric.com"
```

Después de cambiarla, actualizar también `~/deploy/api.env.yaml`, para que
siga siendo la referencia.

### Rotar un secreto

```bash
printf '%s' "NUEVO_VALOR" | gcloud secrets versions add corestream-smtp-password --data-file=-
gcloud run services update corestream-api --region=southamerica-east1   # nueva revisión lee "latest"
```

- **`SECRET_KEY`:** si cambia, todos los usuarios tienen que volver a
  iniciar sesión.
- **Contraseñas de Postgres o Redis:** cambiarlas primero en la VM
  (`/opt/corestream/.env` y en la base) y después en el secreto.

## Publicar una versión nueva

Por ahora es manual, desde Cloud Shell. Automatizarlo en el CI está
pendiente (ver [`FUTURE_WORK.md`](./FUTURE_WORK.md)).

```bash
cd ~/corestream && git pull
TAG=$(git rev-parse --short HEAD)
AR=southamerica-east1-docker.pkg.dev/corestream-project/corestream

# 1. Imágenes (Cloud Build, no hace falta Docker)
gcloud builds submit backend  --region=southamerica-east1 --tag=$AR/api:$TAG
gcloud builds submit frontend --region=southamerica-east1 --tag=$AR/web:$TAG

# 2. Migraciones de base de datos (siempre antes de la API)
gcloud run jobs update corestream-migrate --region=southamerica-east1 --image=$AR/api:$TAG
gcloud run jobs execute corestream-migrate --region=southamerica-east1 --wait

# 3. Servicios
gcloud run services update corestream-api --region=southamerica-east1 --image=$AR/api:$TAG
gcloud run services update corestream-web --region=southamerica-east1 --image=$AR/web:$TAG
```

- Si el Job de migraciones falla, **no seguir con el paso 3**. Revisar el
  log en Cloud Run → Jobs → `corestream-migrate`.
- Las migraciones tienen que ser compatibles con la versión anterior de la
  API: durante unos segundos conviven la versión vieja y el esquema nuevo.

### Volver a la versión anterior

Cloud Run guarda las revisiones anteriores:

```bash
gcloud run revisions list --service=corestream-api --region=southamerica-east1
gcloud run services update-traffic corestream-api --region=southamerica-east1 \
  --to-revisions=corestream-api-000NN-xxx=100
```

Esto no deshace migraciones de base de datos. Si la versión nueva trajo
una migración que rompe la anterior, hay que bajarla a mano
(`alembic downgrade`) o restaurar un respaldo.

## Operar la VM de datos

Entrar por SSH (por IAP, la VM no tiene IP pública):

```bash
gcloud compute ssh corestream-data --zone=southamerica-east1-a --tunnel-through-iap
```

Dentro de la VM:

```bash
cd /opt/corestream
sudo docker compose ps                                            # ambos "healthy"
sudo docker exec -it corestream-postgres psql -U corestream -d corestream
sudo docker exec -it corestream-redis redis-cli                   # la clave ya va en REDISCLI_AUTH
df -h /data                                                       # espacio del disco de datos
```

### Conectarse a Postgres desde Cloud Shell

Para scripts de mantenimiento (`create_admin`, `migrate_documents_to_gcs`,
consultas), con un túnel IAP en una terminal aparte:

```bash
gcloud compute start-iap-tunnel corestream-data 5432 \
  --local-host-port=localhost:15432 --zone=southamerica-east1-a
```

En otra terminal, con el entorno de Python de Cloud Shell:

```bash
source ~/venv-cs/bin/activate
cd ~/corestream/backend
DATABASE_URL="postgresql+asyncpg://corestream:<POSTGRES_PASSWORD>@localhost:15432/corestream" \
  python -m app.scripts.<script> ...
```

Si `~/venv-cs` no existe (Cloud Shell se reinició):

```bash
python3 -m venv ~/venv-cs
~/venv-cs/bin/pip install -r ~/corestream/backend/requirements.txt
```

Los scripts que tocan el bucket necesitan además
`gcloud auth application-default login`.

### Cambiar el tamaño de la VM

Para pasar a `e2-medium` (4 GB), hay unos minutos sin servicio:

```bash
gcloud compute instances stop corestream-data --zone=southamerica-east1-a
gcloud compute instances set-machine-type corestream-data --zone=southamerica-east1-a --machine-type=e2-medium
gcloud compute instances start corestream-data --zone=southamerica-east1-a
```

Con 4 GB conviene subir `shared_buffers` a `1GB` y `effective_cache_size`
a `2GB`, con `PG_SHARED_BUFFERS` y `PG_EFFECTIVE_CACHE` en
`/opt/corestream/.env`, y después `sudo docker compose up -d`.

## Respaldos

Hay dos capas, ambas con **21 días** de retención (15 días hábiles):

| Capa | Qué | Cuándo | Dónde |
|---|---|---|---|
| Snapshot del disco | Disco de datos completo (Postgres + Redis) | Diario, 03:00 Chile (política `corestream-daily`) | Snapshots de Compute Engine |
| `pg_dump` | Base `corestream`, formato custom | Diario, 03:15 Chile (`/etc/cron.d/corestream-backup`) | `gs://corestream-backups/db/corestream_<fecha UTC>.dump` |

- `backup.sh` primero genera el dump en `/data/backup-tmp` y lo verifica
  con `pg_restore --list`. Solo si está bien lo sube al bucket. Así nunca
  queda un respaldo vacío o truncado.
- Escribe `BACKUP_OK` o `BACKUP_FAILED` en syslog (etiqueta
  `corestream-backup`), que llega a Cloud Logging. El log local está en
  `/var/log/corestream-backup.log`.
- La VM no puede borrar respaldos: si alguien toma control de ella, no
  puede eliminarlos. Solo el lifecycle del bucket los borra.

Correr un respaldo a mano:

```bash
gcloud compute ssh corestream-data --zone=southamerica-east1-a --tunnel-through-iap \
  --command="sudo /opt/corestream/backup.sh"
# Termina con: BACKUP_OK gs://corestream-backups/db/corestream_....dump
```

### Restaurar desde un `pg_dump`

**Sobrescribe la base actual.** El script pide escribir `RESTAURAR`:

```bash
gcloud storage ls gs://corestream-backups/db/
gcloud compute ssh corestream-data --zone=southamerica-east1-a --tunnel-through-iap \
  --command="sudo /opt/corestream/restore.sh gs://corestream-backups/db/corestream_XXXX.dump" -- -t
```

`restore.sh` también acepta un archivo local en la VM (`.dump` o `.gz`).
Después de restaurar, correr el Job `corestream-migrate`, por si el dump es
de una versión anterior del esquema.

### Restaurar desde un snapshot

Recupera el disco de datos completo, incluido Redis. Requiere detener la VM:

```bash
gcloud compute snapshots list --filter="sourceDisk~corestream-data-disk"
gcloud compute instances stop corestream-data --zone=southamerica-east1-a
gcloud compute instances detach-disk corestream-data --zone=southamerica-east1-a --disk=corestream-data-disk
gcloud compute disks create corestream-data-disk-r --zone=southamerica-east1-a \
  --source-snapshot=<SNAPSHOT> --type=pd-balanced
gcloud compute instances attach-disk corestream-data --zone=southamerica-east1-a \
  --disk=corestream-data-disk-r --device-name=corestream-data
gcloud compute instances start corestream-data --zone=southamerica-east1-a
gcloud compute disks add-resource-policies corestream-data-disk-r --zone=southamerica-east1-a \
  --resource-policies=corestream-daily
```

- `--device-name=corestream-data` es obligatorio: la VM monta el disco por
  ese nombre.
- El disco original queda intacto, por si hay que volver atrás.

## Dominios y certificados

### Agregar un dominio

1. Pedir al dueño del DNS un registro **A** `<dominio> → 136.68.50.59`.
2. Crear el certificado y su entrada en el map:

   ```bash
   gcloud certificate-manager certificates create <nombre>-cert --domains=<dominio>
   gcloud certificate-manager maps entries create <nombre>-entry --map=corestream-map \
     --certificates=<nombre>-cert --hostname=<dominio>
   ```

3. Agregar el dominio a `ALLOWED_ORIGINS` (API y Job) y al CORS del bucket
   `corestream-file`.
4. Esperar a que el certificado pase a `ACTIVE`, entre 15 y 60 minutos:

   ```bash
   gcloud certificate-manager certificates describe <nombre>-cert \
     --format="value(managed.state,managed.authorizationAttemptInfo)"
   ```

### Quitar el dominio de prueba `corestream-gcp`

```bash
gcloud certificate-manager maps entries delete corestream-gcp-entry --map=corestream-map
gcloud certificate-manager certificates delete corestream-gcp-cert

gcloud run services update corestream-api --region=southamerica-east1 \
  --update-env-vars="^@^ALLOWED_ORIGINS=https://corestream.alloxentric.com"
gcloud run jobs update corestream-migrate --region=southamerica-east1 \
  --update-env-vars="^@^ALLOWED_ORIGINS=https://corestream.alloxentric.com"
```

Después:
- Quitar `https://corestream-gcp.alloxentric.com` del CORS de
  `corestream-file`. Para ver la configuración actual:
  `gcloud storage buckets describe gs://corestream-file --format="default(cors_config)"`.
- Pedir al dueño del DNS que borre el registro A de `corestream-gcp`.

## Monitoreo y logs

- **Logs:** Cloud Logging. La API escribe JSON con `severity`,
  `request_id` y el enlace a la traza de cada request. Los access logs de
  uvicorn están apagados porque Cloud Run ya registra cada request.
- **Métricas:** las nativas de Cloud Run (requests, latencia, instancias)
  y las de la VM por el Ops Agent (CPU, memoria, disco).
- **Salud:** `https://corestream.alloxentric.com/api/health` responde
  `{"status":"ok"}` con `database` y `redis` en `ok`.
- **Alertas:** pendientes de configurar (ver `FUTURE_WORK.md`).

## Problemas conocidos

| Síntoma | Causa | Qué hacer |
|---|---|---|
| `ERR_CONNECTION_CLOSED` justo después de que un certificado pasa a `ACTIVE` | El certificado todavía no llega a todos los front ends de Google | Esperar 5–15 min; probar en incógnito o con `curl -v` desde Cloud Shell |
| Primera request lenta (~6 s) | Arranque en frío: la API escaló a cero | Normal en desarrollo. En producción, `--min-instances=1` |
| `gcloud builds submit` da 403 | La cuenta de Compute que usa Cloud Build no tiene permisos | Ver la tabla de cuentas de servicio |
| Un `.sh` falla con `$'\r': command not found` | El archivo salió de Windows con CRLF | `.gitattributes` fuerza LF; en la VM, `sed -i 's/\r$//' archivo.sh` |
| Login bloqueado para todos a la vez | Rate limit tomando la IP del balanceador en vez de la del cliente | Revisar `XFF_CLIENT_POSITION` (debe ser `2`) |
| Subida de documento falla con error de CORS | Dominio no incluido en el CORS del bucket | Agregarlo (ver "Agregar un dominio") |

## Costos

Estimado en desarrollo: **~60–80 USD/mes** (balanceador ~19, Cloud Run
~15–25, VM ~18–20, discos y snapshots ~5–7, resto menor). Lo cubren los
créditos de GCP (~1 año). Detalle en el plan de migración.

## Cuando crezca el uso

Señales para actuar:
- CPU de la VM sostenida sobre 70 % en horario laboral, o memoria sobre 85 %.
- Conexiones a Postgres cerca de 120.
- La API con varias instancias ocupadas todo el día.

Pasos, en orden de impacto:
1. VM a `e2-medium` (ver más arriba).
2. `--min-instances=1` en la API (sin arranques en frío) y Cloud Armor en
   el balanceador.
3. PgBouncer en la VM **antes** de subir `--max-instances` sobre 10.
4. Postgres a Cloud SQL con alta disponibilidad y Redis a Memorystore,
   cuando la VM como punto único de falla deje de ser aceptable.

## Historia: migración desde Azure

- **Hasta el 02-10-2026:** VM de Azure `spot-development` con Docker
  Compose. Postgres y Redis estaban compartidos con otros proyectos
  (`db-postgre`, `directa-redis-1`), había un worker ARQ, los documentos
  vivían en el volumen `storage-data` y Nginx Proxy Manager estaba delante.
- **Corte:** 02-10-2026, desde las 18:00 (Chile):
  - Se apagó el backend de Azure.
  - `pg_dump` de Azure → `restore.sh` en la VM de GCP → Job
    `corestream-migrate`.
  - Documentos al bucket con `app/scripts/migrate_documents_to_gcs.py`, que
    sube los archivos y actualiza `documents.file_path`.
  - El DNS de `corestream.alloxentric.com` pasó al balanceador.
- **Cambios de código** que vinieron con la migración:
  - Rate limit con la IP real (`XFF_CLIENT_POSITION`).
  - Sin ARQ: publicación directa en Redis.
  - Dockerfiles para Cloud Run.
  - Sin Prometheus: logs para Cloud Logging.
  - Corte de WebSockets inactivos.
  - Documentos con URLs firmadas.
  - Cloud Translation en vez de Azure Translator, que nunca tuvo clave
    configurada.
- `SECRET_KEY` es nueva en GCP, así que todos tuvieron que volver a
  iniciar sesión una vez.
- Azure está apagado. `backend/scripts/backup_db.sh` y `restore_db.sh`
  son de esa época y ya no se usan; quedan solo como referencia.
