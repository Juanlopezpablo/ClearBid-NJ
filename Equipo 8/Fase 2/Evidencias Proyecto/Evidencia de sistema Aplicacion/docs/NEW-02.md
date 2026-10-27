# NEW-02 — Archivos y evidencia en tickets e incidencias

## Alcance

Solo web. Se reutiliza el sistema de documentos, carga directa con URL firmada y almacenamiento local/GCS. No se agregan videos, audios ni notificaciones por adjuntos.

En el detalle de un ticket (Builder y Workbench) y en «Gestionar Incidente» aparece **Archivos y evidencia**. Permite seleccionar varios archivos, listarlos, descargarlos y mostrar capturas con una vista previa. Cada archivo muestra nombre, tamaño, autor y fecha.

## Formatos y permisos

- Máximo 25 MB por archivo, validado tanto por la API como por el almacenamiento.
- Documentos, código y datos: se mantienen los formatos existentes.
- Capturas: PNG, JPG/JPEG y WebP. No se admite SVG ni multimedia de audio/video.
- Cualquier usuario autenticado y activo puede subir, consultar y descargar, según las reglas de lectura actuales de tickets e incidencias.
- En adjuntos de tickets e incidencias solo eliminan el autor y ADMIN, con confirmación en la web.
- Los documentos asociados exclusivamente a épicas conservan sus permisos previos: autor, ADMIN o TEAM_LEADER.

## API y asociación

Se amplía el flujo existente:

1. `POST /api/documents/upload-url`: agrega `incident_id` (también acepta `incidentId`).
2. `PUT` a la URL firmada.
3. `POST /api/documents/confirm`: el servidor revalida el destino y registra el adjunto.

`GET /api/documents/?incidentId=UUID` lista los archivos de una incidencia. Los filtros `ticketId` y `epicId` siguen disponibles; al combinarse se aplican ambos. Una incidencia no se puede combinar como destino con una épica o ticket. Si se proporcionan épica y ticket, el ticket debe pertenecer a esa épica.

La asociación queda en el token firmado, no en campos que el cliente pueda cambiar al confirmar. La confirmación solo puede hacerla el usuario que inició la carga. La vista previa obtiene el archivo mediante la URL temporal de descarga sin enviar credenciales de sesión al almacenamiento.

## Migración

`k7l8m9n0p1q2`, después de `j6k7l8m9n0p1`, agrega `documents.incident_id`, su índice y clave foránea, y amplía la restricción de destino. Los documentos existentes no se modifican.

El despliegue debe aplicar `alembic upgrade head` antes de servir el nuevo código. El downgrade se detiene si existen adjuntos de incidencias, para evitar perder evidencia.

## Comprobación

- `backend/tests/integration/test_documents.py`: carga, listado, descarga, permisos, tamaños, archivos existentes y nuevas evidencias de incidencias sobre PostgreSQL/Redis reales.
- `frontend/tests/unit/components/FileUpload.spec.ts`: múltiples archivos, autor/fecha/tamaño, confirmación de borrado, vista previa, rechazo de multimedia y respuestas pendientes al cambiar de ticket.
- `frontend/tests/unit/services/documentsSignedUrls.spec.ts`: contrato de carga directa al almacenamiento.

La eliminación del archivo desde la interfaz elimina su objeto almacenado. El borrado del recurso padre elimina sus metadatos por cascada; como en el sistema anterior, la limpieza de objetos huérfanos por borrado del padre no se automatiza en NEW-02.

