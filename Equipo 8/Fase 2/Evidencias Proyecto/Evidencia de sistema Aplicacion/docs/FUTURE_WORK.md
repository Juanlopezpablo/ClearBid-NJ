# Trabajo Futuro

Este documento contiene ideas, características y planes que fueron propuestos durante los sprints iniciales de desarrollo pero que fueron pospuestos, perdieron prioridad, o se identificaron como mejoras futuras.

## Características y Mejoras

1. **Analíticas Avanzadas y Reportes (S8)**
   - **Gráficos Burndown**: Implementar un gráfico de líneas que muestre el progreso real vs. ideal de una Épica a lo largo del tiempo.
   - **KPIs de Rendimiento**: Calcular índices de eficiencia, bloqueo y rotación (tickets completados/horas trabajadas, preguntas planteadas/tickets procesados, redirecciones/tickets asignados) con indicadores visuales (verde/amarillo/rojo).
   - **Exportación a PDF/CSV**: Permitir exportar los dashboards de analíticas a PDF (resumen visual) y CSV (tabla de rendimiento) directamente desde el navegador.

2. **Internacionalización y Accesibilidad (S8, S10)**
   - **Soporte Multi-idioma (i18n)**: Externalizar por completo todos los textos hacia archivos JSON soportando Español, Inglés, Francés, Alemán y Portugués.
   - ~~**Autotraducción de Documentos**~~: implementada con Google Cloud Translation v3 en la migración a GCP (`services/translation_service.py`).
   - **Cumplimiento WCAG AA**: Navegación completa por teclado, pruebas con lectores de pantalla y relaciones de contraste estrictas (4.5:1).

3. **Mejoras del Módulo Code & Docs (S8)**
   - **Vista de Repositorio por Proyecto**: Un dashboard para archivos específicos del proyecto, métricas de código y contribuidores.
   - **Subida de Archivos con Previsualizaciones**: Soportar la subida de `.js`, `.ts`, `.py`, `.md`, `.pdf`, `.docx` con previsualizaciones markdown integradas y visores de PDF.

4. **Preferencias de Usuario e Interfaz (S9)**
   - **Modo Oscuro**: Implementar un tema oscuro con transiciones suaves, persistiendo la preferencia del usuario en el backend y `localStorage`.
   - **Panel de Configuración de Usuario**: Una página completa de ajustes de perfil para avatares, zonas horarias, preferencias de notificaciones y temas.

## Infraestructura (pendiente tras la migración a GCP)

1. **Despliegue automático (CI/CD)**: hoy se publica a mano desde Cloud Shell (ver `DEPLOYMENT.md`). Agregar al CI de GitHub Actions: build → Artifact Registry → Job `corestream-migrate` → deploy de `corestream-api` y `corestream-web`, autenticando con Workload Identity Federation (sin claves de cuenta de servicio en GitHub).
2. **Alertas en Cloud Monitoring**: VM `corestream-data` caída, disco de datos > 80 %, memoria de la VM > 90 %, errores 5xx de la API > 1 % durante 5 min, y falta de `BACKUP_OK` en los logs por más de 26 h (o aparición de `BACKUP_FAILED`).
3. **Versionar los archivos de la VM**: `docker-compose.yml`, `backup.sh` y `restore.sh` viven solo en `/opt/corestream` (disco de sistema, que no entra en los snapshots), y `setup-vm.sh` solo en la copia local con la que se montó la VM. Guardar una copia versionada (por ejemplo `infra/vm/` en este repo) para poder recrear la VM.
4. **Ensayo de restauración periódico**: restaurar un `pg_dump` y un snapshot en una base/VM de prueba al menos una vez por trimestre.
5. **Quitar el dominio de prueba** `corestream-gcp.alloxentric.com`: certificado, entrada del map, `ALLOWED_ORIGINS`, CORS del bucket y registro DNS (pasos en `DEPLOYMENT.md`).
6. **Actualizar imágenes de la VM**: `postgres:15` y `redis:7-alpine`, planificado cada trimestre.
7. **Dependencias del frontend**: `npm audit` reporta vulnerabilidades pendientes de revisar.
8. **Escalar cuando crezca el uso**: `min-instances=1` y Cloud Armor; PgBouncer antes de subir `max-instances` sobre 10; Cloud SQL con alta disponibilidad y Memorystore si la VM como punto único de falla deja de ser aceptable.
9. **Limpieza del repositorio**: `backend/scripts/backup_db.sh` y `restore_db.sh` son del despliegue de Azure, y `docker-compose.yml` todavía expone `BACKEND_PORT`/`FRONTEND_PORT` y el volumen `storage-data` de esa época. Se pueden simplificar.

## Riesgos Identificados y Deuda Técnica a Monitorear

- **Complejidad del Drag & Drop**: Monitorear problemas de rendimiento y sincronización de estados al arrastrar tickets entre columnas.
- **Consistencia de la Máquina de Estados**: Asegurar que las ediciones concurrentes no rompan las transiciones de estado de los tickets (TODO -> IN_PROGRESS -> DONE / BLOCKED_QUESTION / REDIRECTED).
- **Estabilidad de WebSocket**: La lógica de reconexión y los latidos (heartbeat de 30s) deben ser robustos en producción para evitar notificaciones perdidas. Tras una reconexión, las vistas recargan con `ws-resync`; cualquier vista nueva que consuma `ws-update` debe escucharlo también.
- **VM de datos como punto único de falla**: si `corestream-data` cae, caen Postgres y Redis juntos. Mitigado con snapshots diarios y disco de datos separado, no con alta disponibilidad.
- **Rendimiento Analítico de Consultas**: A medida que los datos crecen, monitorear las consultas pesadas. Considerar el uso de vistas materializadas para los dashboards complejos.
