# Publicación de la interfaz en Vercel

## Configuración del proyecto

El repositorio contiene evidencias y código en subcarpetas. En Vercel, abrir el proyecto y configurar **Settings → Build and Deployment → Root Directory** con esta ruta, sin comillas:

```text
Equipo 8/Fase 2/Evidencias Proyecto/Evidencia de sistema Aplicacion/frontend
```

Seleccionar **Vite** como framework. El archivo `frontend/vercel.json` fija la instalación con `npm ci`, la compilación con `npm run build` y la salida en `dist`. Se omite la descarga del ejecutable de Cypress, que no se necesita para publicar la interfaz.

Seleccionar para el despliegue una rama que contenga esta configuración y los requisitos que se quieren revisar. Los cambios se prepararon en `Daniela`. Una vez guardada la carpeta raíz, crear un nuevo despliegue; las URL de despliegues anteriores no se actualizan.

No hace falta una regla que envíe todas las rutas a `index.html`: la aplicación usa rutas con `#`. Una regla general podría ocultar los errores de `/api` devolviendo HTML en vez de respuestas de la API.

## Comprobación del 404

En **Deployments**, abrir el nuevo despliegue y revisar que sus registros ejecuten Vite y generen `dist/index.html`. Si el despliegue no contiene esa salida, comprobar la carpeta raíz y las opciones de compilación. Un error 404 por sí solo no confirma la causa.

## API y datos de revisión pendientes

Publicar esta carpeta sirve la interfaz; no publica automáticamente la API FastAPI ni las bases locales de Docker. Para iniciar sesión y probar comentarios, incidencias y adjuntos se necesita además:

- Una API de revisión publicada con esta versión del código y las migraciones aplicadas.
- PostgreSQL y Redis accesibles por esa API.
- Almacenamiento persistente de archivos.
- Enrutamiento de `/api` y WebSockets, cookies de sesión y orígenes permitidos correctamente configurados.

La configuración de este primer paso mantiene `/api` relativo. No apunta a `localhost` ni conecta por defecto con el sistema de producción de Alloxentric. No compartir el enlace como una revisión funcional completa hasta comprobar el acceso a la API y sus servicios.

No agregar contraseñas, claves de base de datos ni secretos a variables `VITE_*`: se incluyen en el JavaScript público. Las credenciales del entorno local tampoco crean cuentas en una base de revisión nueva.

Si el despliegue pide iniciar sesión en Vercel, tiene protección de acceso. Revisar qué mecanismo permite compartirlo con los evaluadores antes de distribuir el enlace; no es lo mismo que la autenticación de CoreStream.
