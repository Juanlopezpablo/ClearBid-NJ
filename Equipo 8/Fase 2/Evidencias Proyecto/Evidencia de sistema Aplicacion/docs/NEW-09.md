# NEW-09 — Modo offline y sincronización diferida (solo web)

## Alcance aprobado y uso

La opción **Sin conexión** del encabezado abre `/#/offline`. Guarda copias de los tickets consultados con conexión y permite leerlas y agregar nuevos comentarios pendientes. Las copias pueden estar desactualizadas; no sustituyen el estado del servidor. Los comentarios publicados, responsables, estados de tickets, temporizadores, sprints y archivos siguen requiriendo conexión.

1. Iniciar sesión con conexión y consultar los tickets necesarios. Las consultas de tickets, búsqueda y épicas guardan automáticamente los campos de consulta: título, descripción, estado, prioridad e identificador.
2. Abrir **Sin conexión** y elegir un ticket guardado. Escribir y pulsar **Guardar comentario pendiente**. Solo se muestra la confirmación después de completar la escritura en IndexedDB. Un borrador sin guardar no forma parte de la cola persistente.
3. Recuperar la conexión y mantener o restablecer una sesión válida de la misma cuenta. La sincronización se intenta al recuperar la red, al iniciar sesión y cada 30 segundos con la página visible. También puede solicitarse con **Sincronizar pendientes**.
4. Los comentarios con errores de permisos, ticket eliminado, menciones inválidas o conflictos quedan visibles para revisión. No se sobrescriben datos ni se descartan silenciosamente. Se puede copiar el texto, reintentar expresamente o descartar el pendiente mediante confirmación.

Las menciones se vuelven a validar con los usuarios activos al sincronizar. Un reintento conserva el mismo identificador de operación. El servidor vincula el autor esperado con la sesión y garantiza que la operación solo publique un comentario, incluso con peticiones concurrentes o una respuesta perdida. Si el comentario fue publicado y luego eliminado, no se vuelve a crear.

## Datos locales y cuentas

- IndexedDB conserva hasta **200 copias de tickets por cuenta durante 7 días**. Los límites y el plazo se muestran en la pantalla. La limpieza de copias vencidas ocurre al consultarlas.
- Se admiten hasta **200 comentarios pendientes por cuenta**, de hasta 5000 caracteres. Los pendientes no caducan automáticamente: se retiran al confirmar su envío o descartarlos expresamente. El navegador o el usuario aún pueden borrar los datos del sitio; no es un respaldo externo.
- Se guarda únicamente la identidad mínima de la última cuenta verificada (ID, nombre y fecha), sin roles ni credenciales. No se almacenan tokens ni contraseñas. Esa identidad permite consultar la copia local, no autenticar operaciones en el servidor.
- Al cerrar sesión se informa si hay pendientes y se conservan para esa misma cuenta. Se eliminan la identidad de consulta y sus copias de tickets. Una marca de cierre local evita reabrir automáticamente la sesión si el cierre ocurrió sin red. Para enviar de nuevo se requiere iniciar sesión.
- Al cambiar de cuenta, las copias y pendientes se consultan por el ID de esa cuenta. El servidor también verifica `author_id`, para impedir que una operación en curso se publique como otro usuario durante un cambio de sesión.
- El usuario puede borrar las copias sin borrar los comentarios pendientes.

## Reapertura sin conexión

La compilación de producción genera `sw.js`, que precarga el documento y los archivos públicos compilados, incluidos los módulos de las pantallas. No intercepta ni guarda respuestas de `/api`, credenciales o subidas de archivos. Tras una visita completa con conexión y la instalación del service worker, la web puede reabrirse sin internet y dirige las rutas privadas al espacio de consulta offline. Una actualización del service worker espera al cierre de las pestañas anteriores.

Este comportamiento requiere HTTPS (o localhost) y almacenamiento permitido en el navegador. **El servidor Vite de desarrollo en 5173 no instala el service worker**: sirve para desarrollar y probar la cola, pero para comprobar la reapertura sin red hay que usar la compilación de producción.

Para probarla localmente desde frontend:

```powershell
node node_modules/vite/bin/vite.js build
node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 4173
```

La vista previa reenvía `/api` a `http://localhost:8000` por defecto, con Docker encendido. Se puede cambiar con `VITE_API_TARGET`. Visitar `http://localhost:4173`, iniciar sesión, consultar tickets y abrir `/#/offline` antes de desconectar la red en las herramientas del navegador. Guardar un comentario, cerrar/reabrir y reconectar; verificar que se publique una sola vez. Los datos locales de 4173 y 5173 son independientes porque son orígenes distintos.

La sincronización no se ejecuta con el navegador completamente cerrado; se retoma cuando se vuelve a abrir la web con conexión y sesión válida. El indicador de red utiliza la señal del navegador: un servidor caído puede producir un error aunque esa señal indique conexión; en ese caso la cola se conserva para reintentar.

## Backend y migración

`POST /api/tickets/{ticket_id}/comments/offline` acepta `client_id`, `author_id` y `body`. La migración `n0p1q2r3s4t5` añade los comprobantes de idempotencia con unicidad por autor y operación. El comentario, sus notificaciones y su comprobante se confirman en una transacción. Los comprobantes permanecen aunque un administrador elimine el comentario, para no resucitarlo al reintentar.

Aplicar desde backend antes de iniciar la versión nueva:

```powershell
alembic upgrade head
```

No revertir esta migración con operaciones aún pendientes: quitar los comprobantes elimina la protección de reintentos históricos.

## Validación

Las pruebas cubren IndexedDB y reapertura, separación de cuentas, caducidad de copias, retención de pendientes, cuota, pérdida de respuesta, sesión vencida y conflictos. La prueba del service worker verifica la recuperación del documento sin red y que nunca intercepte la API. Las pruebas de integración con PostgreSQL verifican peticiones concurrentes, autor incorrecto, comentario eliminado, ticket eliminado y autenticación. La pantalla se prueba sin sesión simulada y conserva el editor cuando falla el almacenamiento.

NEW-09 se prepara en la rama Daniela para su revisión antes de integrarlo a main.
