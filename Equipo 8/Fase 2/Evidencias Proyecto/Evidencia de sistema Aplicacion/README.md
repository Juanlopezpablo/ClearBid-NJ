# 🚀 CoreStream

**CoreStream** es una plataforma de gestión de proyectos y tickets diseñada para equipos de desarrollo. Cuenta con un Workbench estilo Kanban, un Creador de Épicas/Tickets para Líderes de Equipo, notificaciones en tiempo real mediante WebSockets y analíticas de rendimiento para desarrolladores.

El backend funciona con **FastAPI** (Python) utilizando PostgreSQL y Redis. El frontend está construido con **Vue 3** y Vite.

En producción corre en **Google Cloud**: frontend y API en Cloud Run detrás de un balanceador HTTPS, PostgreSQL y Redis en una VM privada, y documentos en Cloud Storage. Disponible en <https://corestream.alloxentric.com>.

## 📚 Documentación

- **[APP-08: inicio adaptado por rol](docs/APP-08-inicio-por-rol.md)** — Resúmenes de administración, gestión por equipo y trabajo personal.

- **[TRV-09: laboratorio local de orquestación](docs/TRV-09-orquestacion-local.md)** — Escalamiento con Docker Swarm, recuperación y [resultados de las pruebas](docs/TRV-09-resultados.md).


Toda la documentación se ha consolidado en el directorio `docs/` para ayudarte a entender el *Cómo*, *Por qué* y *Qué* de CoreStream:

- 🏗️ **[Arquitectura](docs/ARCHITECTURE.md)** - Flujo del sistema, tecnologías e interacción de componentes.
- ⚙️ **[Guía de Instalación](docs/SETUP.md)** - Instrucciones para ejecutar el proyecto localmente vía Docker o de forma manual.
- ☁️ **[Despliegue en GCP](docs/DEPLOYMENT.md)** - Infraestructura, publicación de versiones, respaldos y operación.
- 🔐 **[Permisos (RBAC)](docs/RBAC.md)** - Roles y matriz de autorización.
- 🔮 **[Trabajo Futuro](docs/FUTURE_WORK.md)** - Ideas y tareas planeadas para el desarrollo futuro.
- 🎨 **[Colores de Marca](docs/COLORS.md)** - Pautas para la paleta de colores de la interfaz.

---

*En octubre de 2026 CoreStream se migró de una VM en Azure a Google Cloud. La historia de esa migración está al final de [DEPLOYMENT.md](docs/DEPLOYMENT.md).*
