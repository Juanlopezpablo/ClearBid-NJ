# CoreStream App 📱

Aplicación móvil de **CoreStream**, plataforma de gestión de proyectos y tickets de **Alloxentric**.

Este proyecto se desarrolla en el contexto de la asignatura **CAPSTONE de Ingeniería en Informática**, y tiene como objetivo adaptar las principales funcionalidades de CoreStream a una aplicación móvil, permitiendo que administradores, líderes y desarrolladores puedan consultar y gestionar su trabajo desde un dispositivo móvil.

---

## 👥 Integrantes del Equipo y Roles

| Nombre Completo | Rol en el Proyecto | Correo Institucional | Perfil GitHub |
|---|---|---|---|
| Juan Pablo López Peña | Backend Lead & API Integration | [jua.lopezp@duocuc.cl](mailto:jua.lopezp@duocuc.cl) | [Juanlopezpablo](https://github.com/Juanlopezpablo) |
| Daniela Belén Cuevas Chávez | Frontend Mobile Lead & UI/UX | [Dani.cuevasc@duocuc.cl](mailto:Dani.cuevasc@duocuc.cl) | [dani-cuevas](https://github.com/dani-cuevas) |

**Empresa colaboradora:** Alloxentric  
**Proyecto:** CoreStream App  
**Asignatura:** CAPSTONE  
**Estado:** En desarrollo

---

## 📌 Descripción del proyecto

CoreStream es un sistema orientado a la gestión de proyectos, épicas, tickets, subtareas e incidencias.

CoreStream App busca llevar las principales funcionalidades del sistema web a dispositivos móviles, facilitando el acceso a la información y permitiendo que los integrantes de un equipo puedan revisar el estado de los proyectos, gestionar tickets, consultar incidencias y recibir notificaciones desde cualquier lugar.

La aplicación mantiene los roles y permisos existentes en CoreStream:

- `ADMIN`
- `GROUP_LEADER`
- `DEVELOPER`

Cada usuario tendrá acceso a diferentes acciones y vistas dependiendo de su rol.

---

## 🎯 Objetivo general

Desarrollar una aplicación móvil integrada con la plataforma CoreStream que permita gestionar y consultar proyectos, tickets e incidencias de manera eficiente, manteniendo los roles, permisos y reglas de negocio existentes en el sistema web.

---

## 🎯 Objetivos específicos

- Adaptar las funcionalidades principales de CoreStream a una interfaz móvil.
- Integrar la aplicación con el backend existente mediante API REST.
- Implementar autenticación y autorización según los roles definidos en CoreStream.
- Permitir la visualización y gestión de proyectos, épicas y tickets.
- Facilitar el seguimiento del trabajo asignado a cada desarrollador.
- Permitir la consulta y gestión de incidencias.
- Incorporar un sistema de notificaciones para eventos importantes.
- Mantener una experiencia de usuario clara y adaptada a dispositivos móviles.
- Aplicar buenas prácticas de desarrollo, seguridad y control de versiones.
- Implementar pruebas que permitan comprobar el correcto funcionamiento de la aplicación.

---

## 📱 Funcionalidades principales

### Inicio

La pantalla principal cambia su contenido dependiendo del rol del usuario.

**ADMIN y GROUP_LEADER**

- Estado general de los proyectos.
- Cantidad de tickets abiertos.
- Tickets bloqueados.
- Tickets atrasados.
- Incidencias abiertas.
- Proyectos que requieren atención.
- Progreso general de los proyectos.

**DEVELOPER**

- Tickets asignados.
- Tickets en progreso.
- Tickets bloqueados.
- Tickets completados recientemente.
- Incidencias asignadas.

---

### Gestión de proyectos

La aplicación permite visualizar:

- Proyectos.
- Épicas.
- Tickets asociados a cada épica.
- Progreso del proyecto.
- Estado de los tickets.
- Prioridad.
- Responsable asignado.
- Fecha de vencimiento.
- Subtareas completadas y pendientes.

---

### Gestión de tickets

Desde el detalle de un ticket se puede consultar:

- Título.
- Descripción.
- Estado.
- Prioridad.
- Proyecto.
- Épica.
- Usuario asignado.
- Fecha de vencimiento.
- Subtareas.
- Historial de eventos.
- Tiempo de trabajo.
- Tiempo bloqueado.

Dependiendo del rol y estado del ticket, el usuario podrá realizar distintas acciones.

Entre ellas:

- Asignar o reasignar tickets.
- Comenzar un ticket.
- Completar un ticket.
- Plantear una pregunta.
- Resolver un bloqueo.
- Redirigir un ticket.
- Modificar subtareas.

Los permisos son calculados por el servidor para evitar que la lógica de autorización dependa solamente de la aplicación móvil.

---

## 🚨 Gestión de incidencias

CoreStream App permite trabajar con el ciclo de vida de las incidencias.

Los usuarios pueden consultar información como:

- Título.
- Descripción.
- Proyecto.
- Severidad.
- Categoría.
- Estado.
- Usuario responsable.
- Fecha de creación.

Según el rol y permisos disponibles también se pueden realizar acciones sobre las incidencias.

---

## 🔔 Notificaciones

La aplicación contempla un sistema de notificaciones para informar al usuario sobre eventos relevantes.

Entre ellos:

- Asignación de tickets.
- Redirección de tickets.
- Preguntas realizadas.
- Tickets completados.
- Nuevas incidencias.
- Cambios importantes dentro de los proyectos.

El backend utiliza WebSocket para las notificaciones en tiempo real y contempla **Firebase Cloud Messaging (FCM)** para las notificaciones push en dispositivos móviles.

---

## 👤 Roles del sistema

### ADMIN

Posee los permisos administrativos principales del sistema.

Puede, entre otras acciones:

- Visualizar el estado general de los proyectos.
- Gestionar tickets.
- Asignar tickets.
- Consultar la carga de trabajo del equipo.
- Gestionar incidencias.
- Acceder a información global.

### GROUP_LEADER

Permite gestionar y supervisar el trabajo del equipo.

Puede:

- Revisar proyectos.
- Asignar y reasignar tickets.
- Supervisar tickets bloqueados.
- Consultar la carga del equipo.
- Gestionar incidencias.
- Resolver situaciones que bloqueen el trabajo de los desarrolladores.

### DEVELOPER

Está orientado al trabajo diario de desarrollo.

Puede:

- Consultar sus tickets.
- Iniciar tickets asignados.
- Completar tickets.
- Gestionar subtareas.
- Plantear preguntas.
- Redirigir tickets.
- Consultar las incidencias relacionadas con su trabajo.

---

## 🛠️ Tecnologías

### Aplicación móvil

- Flutter
- Dart
- Riverpod
- Dio
- SharedPreferences
- WebSocket

### Backend

- Python
- FastAPI
- SQLAlchemy Async
- PostgreSQL
- Redis
- JWT

### Notificaciones

- Firebase Cloud Messaging
- WebSocket
- Redis Pub/Sub

### Herramientas

- Git
- GitHub
- Visual Studio Code
- Android Studio
- Flutter SDK
- Postman / Swagger

---

## 🏗️ Arquitectura general

La aplicación móvil consume los servicios proporcionados por el backend de CoreStream.

```text
┌───────────────────────────┐
│      CoreStream App       │
│        Flutter            │
└─────────────┬─────────────┘
              │
              │ REST API / WebSocket
              │
┌─────────────▼─────────────┐
│       Backend API         │
│         FastAPI           │
└───────┬─────────┬─────────┘
        │         │
        │         │
┌───────▼───┐ ┌───▼────────┐
│PostgreSQL │ │   Redis    │
└───────────┘ └────┬───────┘
                   │
             ┌─────▼─────┐
             │    FCM    │
             │ Firebase  │
             └───────────┘
```

La aplicación utiliza un enfoque **Backend for Frontend (BFF)** mediante endpoints específicos bajo `/mobile`, permitiendo obtener en una sola solicitud la información necesaria para cada pantalla móvil.

---

## 📂 Estructura principal de la aplicación

```text
lib/
│
├── main.dart
├── providers.dart
│
├── core/
│   ├── config.dart
│   ├── theme.dart
│   └── i18n.dart
│
├── models/
│   └── models.dart
│
├── data/
│   ├── repository.dart
│   ├── demo_repository.dart
│   └── api_repository.dart
│
├── services/
│   └── push_service.dart
│
└── ui/
    ├── login_screen.dart
    ├── home_shell.dart
    ├── dashboard_screen.dart
    ├── projects_screens.dart
    ├── ticket_detail_screen.dart
    ├── ticket_sheets.dart
    ├── incidents_screens.dart
    ├── team_screen.dart
    ├── notifications_screen.dart
    ├── settings_sheet.dart
    └── widgets.dart
```

---

## 🔌 Integración con el backend

La aplicación puede trabajar en dos modalidades.

### Modo Demo

Permite utilizar la aplicación sin conectarse al backend.

```bash
flutter run
```

Este modo utiliza datos locales de demostración y permite probar:

- Roles.
- Proyectos.
- Tickets.
- Incidencias.
- Navegación.
- Permisos.
- Notificaciones simuladas.

Los cambios realizados en modo Demo no son persistentes.

---

### Modo API

Permite conectar la aplicación al backend real de CoreStream.

Ejemplo para un emulador Android:

```bash
flutter run --dart-define=CS_API_URL=http://10.0.2.2:8000
```

`10.0.2.2` corresponde al localhost de la máquina anfitriona visto desde un emulador Android.

---

## 🚀 Instalación

### 1. Clonar el repositorio

```bash
git clone URL_DEL_REPOSITORIO
```

### 2. Entrar al proyecto

```bash
cd corestream_mobile
```

### 3. Instalar dependencias

```bash
flutter pub get
```

### 4. Verificar el proyecto

```bash
flutter analyze
```

### 5. Ejecutar pruebas

```bash
flutter test
```

### 6. Ejecutar la aplicación

```bash
flutter run
```

Si las carpetas de plataforma `android/` o `ios/` no se encuentran generadas, ejecutar previamente:

```bash
flutter create .
flutter pub get
```

---

## 🧪 Pruebas

El proyecto contempla pruebas para validar funcionalidades importantes de la aplicación.

```text
test/
├── permissions_test.dart
├── demo_repository_test.dart
└── widget_smoke_test.dart
```

### permissions_test.dart

Verifica los permisos disponibles según:

- Rol.
- Usuario asignado.
- Estado del ticket.

### demo_repository_test.dart

Verifica operaciones principales como:

- Asignar tickets.
- Completar tickets.
- Plantear preguntas.
- Redirigir tickets.
- Generar notificaciones.

### widget_smoke_test.dart

Realiza una prueba básica del flujo:

```text
Login → Dashboard → Logout
```

Para ejecutar todas las pruebas:

```bash
flutter test
```

---

## 🗺️ Requerimientos y mejoras del proyecto

Dentro del alcance de trabajo existen funcionalidades que serán desarrolladas o mejoradas durante el proyecto.

### Dashboard por rol

El dashboard debe entregar información distinta según el rol del usuario y concentrar los datos necesarios en una sola llamada al backend.

Actualmente existe implementación para proyectos y tickets, mientras que la integración completa de incidencias requiere ajustes en el backend existente.

### Comentarios y menciones

Se busca incorporar comentarios directamente en los tickets.

También se contempla permitir menciones utilizando:

```text
@usuario
```

Cuando un usuario sea mencionado deberá recibir una notificación.

### Archivos y evidencias

Se proyecta permitir adjuntar:

- Imágenes.
- Capturas de pantalla.
- Documentos.
- Fotografías tomadas desde el dispositivo.

Los archivos deberán quedar relacionados con el ticket o incidencia correspondiente.

### Etiquetas y búsqueda avanzada

Se contempla implementar etiquetas para organizar tickets e incidencias y realizar búsquedas utilizando filtros como:

- Texto.
- Etiqueta.
- Estado.
- Usuario asignado.

### Sprints

Se contempla incorporar planificación mediante sprints o iteraciones.

Cada sprint podrá contener tickets y tendrá:

- Fecha de inicio.
- Fecha de término.
- Tickets asociados.
- Métricas de avance.

### Modo offline

Una futura mejora permitirá utilizar la aplicación cuando no exista conexión a Internet.

La aplicación deberá poder:

- Mostrar la última información almacenada.
- Indicar que se encuentra sin conexión.
- Guardar temporalmente acciones.
- Sincronizar los cambios al recuperar conexión.

### Buscador global

Se contempla desarrollar un buscador que permita encontrar desde un único lugar:

- Proyectos.
- Tickets.
- Incidencias.
- Documentos.
- Usuarios.

Los resultados deberán respetar los permisos del usuario autenticado.

---

## 🔐 Seguridad

CoreStream App utiliza las reglas de seguridad definidas por CoreStream.

La solución contempla:

- Autenticación mediante JWT.
- Access Token.
- Refresh Token.
- Control de acceso basado en roles.
- Validación de permisos en backend.
- Revocación de sesión.
- WebSocket autenticado.
- Separación de responsabilidades entre aplicación y servidor.

La aplicación puede utilizar la información de permisos entregada por el backend para mostrar u ocultar acciones, pero la autorización siempre debe ser validada nuevamente por el servidor.

---

## 🌐 Internacionalización

La aplicación contempla soporte de idiomas mediante un sistema de internacionalización.

Actualmente se considera:

- Español 🇨🇱
- Inglés 🇺🇸

La interfaz también contempla:

- Tema claro.
- Tema oscuro.

---

## 📋 Estados de los tickets

Los tickets pueden pasar por los siguientes estados:

```text
TODO
   ↓
IN_PROGRESS
   ↓
DONE
```

Durante el proceso también pueden existir los estados:

```text
BLOCKED
REDIRECTED
```

Esto permite representar situaciones donde un desarrollador necesita ayuda o donde un ticket debe ser reasignado.

---

## 🔄 Flujo general de trabajo

```text
Proyecto
   │
   ▼
Épica
   │
   ▼
Ticket
   │
   ├── Subtareas
   │
   ├── Usuario asignado
   │
   ├── Historial
   │
   ├── Temporizador
   │
   └── Estado
          │
          ├── TODO
          ├── IN_PROGRESS
          ├── BLOCKED
          ├── REDIRECTED
          └── DONE
```

---

## 📌 Estado del proyecto

CoreStream App se encuentra actualmente en desarrollo.

Durante el proyecto CAPSTONE se continuará trabajando en:

```text
[✓] Análisis inicial del sistema CoreStream
[✓] Wireframe funcional
[✓] Base de aplicación Flutter
[✓] Navegación según rol
[✓] Modo Demo
[✓] Integración inicial con API
[✓] Gestión base de proyectos y tickets
[ ] Ajustes pendientes del dashboard
[ ] Comentarios y menciones
[ ] Adjuntos y evidencias
[ ] Etiquetas y búsqueda avanzada
[ ] Planificación mediante sprints
[ ] Buscador global
[ ] Modo offline
[ ] Integración completa de notificaciones push
[ ] Pruebas finales
[ ] Documentación final
```

El estado de estas funcionalidades será actualizado a medida que avance el desarrollo.

---

## 🤝 Metodología de trabajo

El desarrollo del proyecto se realizará utilizando Git y GitHub para mantener un registro verificable de los cambios realizados por cada integrante.

El flujo general será:

```text
Crear tarea
      ↓
Crear rama
      ↓
Desarrollar funcionalidad
      ↓
Realizar pruebas
      ↓
Commit
      ↓
Push
      ↓
Pull Request
      ↓
Revisión
      ↓
Merge
```

Cada integrante deberá realizar sus propios commits para mantener trazabilidad sobre su participación en el proyecto.

---

## 📝 Convención de commits

Se recomienda utilizar mensajes de commit descriptivos.

Ejemplos:

```bash
git commit -m "feat: agregar comentarios en tickets"
git commit -m "feat: implementar buscador de tickets"
git commit -m "fix: corregir permisos del developer"
git commit -m "test: agregar pruebas de asignacion de tickets"
git commit -m "docs: actualizar README del proyecto"
```

Prefijos recomendados:

```text
feat:     nueva funcionalidad
fix:      corrección de error
docs:     documentación
test:     pruebas
refactor: modificación interna del código
style:    cambios visuales o de formato
chore:    configuración o mantenimiento
```

---

## 📚 Documentación relacionada

El proyecto utiliza como referencia la documentación proporcionada por Alloxentric:

- Especificación API CoreStream Mobile.
- Wireframe funcional CoreStream Mobile.
- Requerimientos de CoreStream App.
- Estándares transversales de Alloxentric.
- Documentación del backend CoreStream.
- Documentación correspondiente al Proyecto CAPSTONE.

---

## 🏢 Organización

Proyecto desarrollado en colaboración con **Alloxentric** como parte del proyecto académico **CAPSTONE de Ingeniería en Informática**.

**Equipo de desarrollo:** Daniela y JP.

---

## 📄 Licencia

Este repositorio corresponde a un proyecto académico desarrollado en colaboración con Alloxentric.

El código, documentación y recursos del proyecto deben utilizarse de acuerdo con las condiciones definidas por la organización y el equipo responsable.