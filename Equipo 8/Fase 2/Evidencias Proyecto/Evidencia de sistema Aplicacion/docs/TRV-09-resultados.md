# TRV-09 — Resultados de validación local

Fecha: 23 de noviembre de 2026. Docker Desktop Linux, Swarm de un nodo,
8 CPU lógicas y aproximadamente 3,68 GiB de memoria disponibles para Docker.
Ejecutado con las imágenes compiladas del proyecto y la configuración
`deploy/trv09/stack.yml`.

## Escalamiento y distribución

Cada medición: 120 consultas autenticadas al mismo ticket, concurrencia 6.

| Etapa | Réplicas | Errores | Distribución | Solicitudes/s | Mediana | p95 |
|---|---:|---:|---|---:|---:|---:|
| Una réplica | 1 | 0 | 120 en una instancia | 38,77 | 127,35 ms | 291,23 ms |
| Después de escalar | 3 | 0 | 40 por instancia | 17,83 | 64,33 ms | 2022,71 ms |
| Después del reemplazo | 3 | 0 | 40 por instancia | 73,37 | 46,64 ms | 265,45 ms |
| Después de reiniciar el laboratorio | 3 | 0 | 40 por instancia | 69,22 | 57,35 ms | 201,27 ms |

Las cuatro etapas comprobaron además la descarga idéntica de un archivo desde
todas las instancias y la renovación de sesión. Las 480 lecturas no registraron
errores.

**Interpretación:** se verificó la distribución y el funcionamiento con varias
réplicas. Los tiempos variaron; la primera medición con tres instancias fue
más lenta que la de una instancia. Esta muestra breve comparte CPU, memoria,
base y disco en un único equipo y no incluye un protocolo de calentamiento ni
repeticiones estadísticas. No demuestra una mejora fija de rendimiento ni
una capacidad productiva determinada.

## Recuperación automática

Se detuvo el contenedor `709b129b38de` de la API del laboratorio.
Swarm lo sustituyó por `b298ed8921c3` y volvió a mantener tres contenedores
saludables. El archivo y el ticket siguieron disponibles en la comprobación
posterior, que repitió 120 lecturas sin errores.

La prueba mide recuperación de una instancia del backend y verificación
posterior. No mide el tiempo de interrupción ni garantiza que las solicitudes
en curso sobrevivan a la caída. No simula la caída del computador ni de la base.

## Persistencia al reiniciar

Se ejecutaron Stop y Start conservando los volúmenes y secretos. Una segunda
lectura del mismo ticket (UUID `17652657-0618-4fb8-800f-a04d2ecf87c9`)
verificó que los datos y el archivo original se conservaron. También se probó
el despliegue con etiquetas de imagen basadas en su contenido.

## Evidencias reproducibles

Detalle sin credenciales ni tokens: [resultados.json](evidencias/trv09/resultados.json).
La orden `trv09.ps1 -Action Verify` vuelve a generar los informes originales
locales en `deploy/trv09/reports/`.

La interfaz se sirve en `http://127.0.0.1:18080/#/login`; se usa 127.0.0.1 para
separar las cookies de la aplicación de desarrollo que se abre en localhost.
No se publicó este entorno en Internet ni se modificó la infraestructura GCP.
