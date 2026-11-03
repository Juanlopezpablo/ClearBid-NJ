# NEW-05 — Planificación de sprints o iteraciones (solo web)

## Alcance aprobado

Un sprint pertenece a una aplicación y agrupa tickets de desarrollo de sus distintas épicas. Las épicas mantienen su estructura: asignar un sprint no mueve ni duplica los tickets. ADMIN y TEAM_LEADER administran la planificación; DEVELOPER consulta los sprints y trabaja sus tickets con los permisos existentes.

Cada sprint tiene nombre, objetivo y fechas de inicio y término (días de calendario). Sus estados son Planificado, Activo y Finalizado. Solo puede existir un sprint activo por aplicación. No se incorporan puntos de historia, cálculo de capacidad ni cambios en aplicaciones móviles.

## Uso en la web

1. Abrir **Sprints** en el encabezado (`/#/sprints`) y elegir una aplicación.
2. ADMIN o TEAM_LEADER crea un sprint con nombre, objetivo y fechas válidas. Puede corregir el plan mientras esté Planificado.
3. Agregar tickets desde el backlog: son tickets de desarrollo no completados, de la misma aplicación y sin sprint. Pueden tener responsable; «sin sprint» es independiente de «sin asignar». El backlog permite buscar por título y paginar.
4. Iniciar el sprint. Debe contener al menos un ticket y no puede haber otro activo en la aplicación. Las fechas expresan el plan; las acciones de inicio y cierre son manuales y registran su instante real.
5. Abrir un ticket por su título para consultar sus detalles y trabajar mediante el panel existente. El avance se refresca al actualizar el ticket o cerrar su panel; el botón **Actualizar** permite consultar cambios de otros usuarios. Agregar o retirar tickets sigue siendo posible mientras el sprint esté Planificado o Activo.
6. Finalizar el sprint mediante la confirmación. Los pendientes quedan sin sprint y mantienen estado, responsable, épica y datos de trabajo. Los completados conservan la asociación al sprint finalizado.

El seguimiento muestra completados sobre total y porcentaje. Al finalizar se guarda una fotografía de esos contadores, incluido el número de pendientes liberados: el resumen histórico no se reduce cuando los pendientes pasan al siguiente sprint. La lista del sprint finalizado conserva los tickets completados que aún existan; no ofrece un historial detallado de los tickets que volvieron al backlog. Los planes finalizados no se editan ni se reabren.

## API y persistencia

- `GET /api/sprints?application_id=…`: lista paginada con resumen de avance.
- `POST /api/sprints`: crea un plan; `GET /api/sprints/{id}` consulta su resumen.
- `PUT /api/sprints/{id}`: edita nombre, objetivo y fechas antes de iniciar.
- `POST /api/sprints/{id}/start` y `/finish`: cambian el ciclo de vida.
- `GET /api/sprints/{id}/tickets`: lista paginada de tickets del sprint. `available=true` consulta el backlog disponible; `q` busca por título literal.
- `PUT /api/sprints/{id}/tickets/{ticket_id}` agrega; `DELETE` retira sin borrar el ticket.

Los accesos de lectura requieren sesión. Las mutaciones verifican ADMIN o TEAM_LEADER en el servidor. El backend rechaza tickets de otra aplicación, de soporte, completados o que ya pertenezcan a otro sprint. La edición genérica del ticket no permite cambiar `sprint_id`.

La migración `m9n0p1q2r3s4` crea `sprints` y añade `tickets.sprint_id`, inicialmente vacío. Una restricción única parcial protege el sprint activo por aplicación; los cambios de planificación se serializan mediante bloqueo de la aplicación y de las filas afectadas. El cierre y la liberación de pendientes se confirman en una sola transacción.

Antes de iniciar el backend actualizado, ejecutar desde la carpeta backend:

```powershell
alembic upgrade head
```

Respaldar antes de revertir la migración: la reversión elimina los planes y las asociaciones a sprints.

## Comprobaciones

`tests/integration/test_sprints.py` usa PostgreSQL y Redis en la base aislada `corestream_test`: valida fechas, permisos, consulta, backlog, pertenencia, concurrencia de dos inicios, transiciones y cierre sin alterar responsables ni estados. La web incluye pruebas de permisos visibles, incorporación de trabajo asignado, cancelación de cierre, conflictos y resumen histórico.

La publicación funcional en Vercel continúa requiriendo el backend y los servicios de revisión pendientes. Esta implementación local no configura ni altera la infraestructura de Alloxentric.
