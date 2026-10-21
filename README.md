# Capstone CoreStream App — Alloxentric

Repositorio del proyecto Capstone **CoreStream App de Alloxentric**, organizado por fases y evidencias del Equipo 8.

CoreStream es una aplicación web para gestionar proyectos y tickets de equipos de desarrollo. Centraliza aplicaciones/proyectos, épicas, tickets y subtareas, con un tablero de trabajo Kanban, seguimiento de tiempos, notificaciones internas en tiempo real y analíticas del equipo.

## Funcionalidades y tecnologías

- Gestión de aplicaciones, épicas, tickets, subtareas y asignaciones.
- Workbench Kanban para organizar y seguir el trabajo.
- Autenticación y permisos por rol: `ADMIN`, `TEAM_LEADER` y `DEVELOPER`.
- Notificaciones mediante WebSockets y Redis.
- Gestión de documentos, reuniones, incidentes y tickets de soporte.
- Frontend: Vue 3, TypeScript, Vite, Pinia y Tailwind CSS.
- Backend: FastAPI, SQLAlchemy y Alembic; persistencia en PostgreSQL.

La documentación de despliegue describe una infraestructura en Google Cloud con frontend y API en Cloud Run, PostgreSQL y Redis en una VM privada y documentos en Cloud Storage.

## Ubicación del proyecto

El código ejecutable y su documentación están en:

[`Equipo 8/Fase 2/Evidencias Proyecto/Evidencia de sistema Aplicacion/`](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/)

| Ruta dentro de la aplicación | Contenido |
|---|---|
| [`backend/`](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/backend/) | API, modelos, servicios, migraciones y pruebas |
| [`frontend/`](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/frontend/) | Interfaz web y pruebas del cliente |
| [`docs/`](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docs/) | Arquitectura, instalación, despliegue y permisos |
| [`docker-compose.yml`](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docker-compose.yml) y [`docker-compose.dev.yml`](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docker-compose.dev.yml) | Configuración de contenedores y entorno de desarrollo |

Las carpetas `Equipo 8/Fase 1/` y `Equipo 8/Fase 2/` reúnen las evidencias académicas del Capstone.

## Ejecución local

Se requiere Docker con Docker Compose. Desde la raíz de este repositorio, entrar primero a la carpeta de la aplicación:

```bash
cd "Equipo 8/Fase 2/Evidencias Proyecto/Evidencia de sistema Aplicacion"
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

En PowerShell, usar `Copy-Item .env.example .env` para copiar el archivo de entorno.

- Interfaz web: <http://localhost:5173>
- API: <http://localhost:8000>
- Documentación interactiva de la API en desarrollo: <http://localhost:8000/api/docs>

Consultar la guía de instalación para crear el primer administrador, configurar el entorno y ejecutar las pruebas.

## Documentación

- [Presentación de la aplicación](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/README.md)
- [Arquitectura](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docs/ARCHITECTURE.md)
- [Instalación y pruebas](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docs/SETUP.md)
- [Despliegue y operación en Google Cloud](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docs/DEPLOYMENT.md)
- [Roles y permisos (RBAC)](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docs/RBAC.md)
- [Trabajo futuro](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docs/FUTURE_WORK.md)
- [Colores de marca](Equipo%208/Fase%202/Evidencias%20Proyecto/Evidencia%20de%20sistema%20Aplicacion/docs/COLORS.md)
