# APP-08 — Panel de inicio adaptado por rol (web)

## Comportamiento

Ruta `/#/home`, enlace Inicio en el encabezado y los menús. Al iniciar sesión
sin un destino explícito se abre este panel. Se conservan los enlaces directos
solicitados antes de iniciar sesión y el cambio obligatorio de contraseña.
El constructor, banco de trabajo, analítica y demás pantallas siguen accesibles.

- ADMIN: resumen general de gestión y selector de equipo.
- TEAM_LEADER: inicio de gestión con el mismo selector; no se atribuyen equipos
  a un líder porque el modelo actual no define esa responsabilidad.
- DEVELOPER: tickets e incidencias asignados a la cuenta autenticada. No permite
  seleccionar equipos ni recibir datos de otro responsable mediante parámetros.

El rol y el usuario se determinan en el servidor, no se aceptan desde el cliente.
El nuevo endpoint exige usuario activo. No se modifican los permisos previos
de lectura, edición, gestión de equipos ni los demás endpoints de la plataforma.

## Datos y alcance

`GET /api/dashboard`: filtros `team_id` (solo gestores), `focus`, `skip`, `limit`.
Los conteos se calculan en SQL sobre el alcance antes de paginar. Lista de diez
por página (API admite hasta 25). Orden por vencimiento ya superado, prioridad,
fecha límite y orden estable. Próximos a vencer: primero la fecha más cercana.

Indicadores:

- Pendientes: todos excepto COMPLETED y RESOLVED.
- En curso: IN_PROGRESS e INVESTIGATING (soporte).
- Bloqueados: BLOCKED y BLOCKED_QUESTION.
- Vencidos: pendientes con fecha límite anterior al instante de consulta.
- Próximos a vencer: pendientes entre ahora y los siguientes siete días.

Los indicadores se superponen: un ticket bloqueado también está pendiente.
Fechas calculadas en UTC; interfaz muestra la hora local del navegador.

Al seleccionar equipo se consideran sus épicas y los tickets de ellas; los
soportes sin épica no se atribuyen a un equipo. Un gestor en vista general
sí incluye los tickets de soporte.

Sprints: solo ACTIVE. En el panel personal se consideran los tickets asignados
al usuario, y en un equipo sus tickets, incluidos los ya completados para que
el porcentaje no aumente por excluir trabajo terminado. No se muestran sprints
ajenos a esos alcances. Máximo cinco en pantalla, ordenados por término.
El avance es del alcance consultado, no se presenta como avance global cuando
se filtra. El acceso lleva a la sección existente de planificación.

Incidencias: solo no resueltas, máximo cinco por gravedad y fecha. DEVELOPER
solo ve sus asignadas. No tienen vínculo directo con equipos, por lo que se
omiten sus conteos al seleccionar un equipo y se explica el motivo; no se
muestra un cero engañoso ni se atribuyen por compartir una aplicación.

Los títulos de tickets abren los paneles existentes del constructor o del banco
de trabajo mediante `ticketId`. Los resúmenes se actualizan al entrar, cambiar
filtro o pulsar Actualizar; no son un tablero en tiempo real ni están disponibles
sin conexión. Errores visibles con reintento; no se muestran ceros ante un fallo.

## Verificación

Pruebas de PostgreSQL real: ADMIN, TEAM_LEADER, dos desarrolladores, aislamiento
de tickets, equipos que comparten aplicación, avance de sprint parcial,
incidencias, soporte, fechas, paginación, parámetros inválidos y usuario inactivo.
Pruebas de interfaz para cada rol, filtros, incidencias sin vínculo y errores.
Comprobación de TypeScript y compilación de producción.

Sin cambios de esquema ni nuevas migraciones. Probar en
`http://localhost:5173/#/home` con las cuentas locales existentes.
El laboratorio Swarm de TRV-09 usa imágenes compiladas: para incorporar cambios
posteriores del código debe reconstruirse con `trv09.ps1 -Action Start`.
