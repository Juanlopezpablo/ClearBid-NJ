# NEW-13 — Buscador global unificado (web)

## Alcance

Entrada «Búsqueda global» en el encabezado, ruta `/#/search`. Búsqueda literal
sin distinción de mayúsculas, de 2 a 200 caracteres, por título/nombre,
descripción o identificador de tickets de desarrollo y soporte, aplicaciones,
épicas e incidencias; documentos por nombre y contenido extraído.

Resultados planos, filtro por tipo, total y páginas de 25 elementos. Se muestra
un fragmento alrededor de la coincidencia y se resalta mediante texto escapado,
sin interpretar HTML del archivo. Sin jerarquías. Los detalles se consultan de
nuevo al abrir; los documentos usan las URLs firmadas existentes.

## Contenido de documentos

Nuevas cargas: extracción al confirmar la subida. PDF con texto, DOCX (párrafos
y tablas), texto y código admitidos. No requiere Gemini ni otra API externa.
Imágenes, DOC antiguo y PDF escaneado no tienen reconocimiento de texto:
continúan disponibles por nombre. Un fallo de extracción no impide adjuntar.

La base guarda texto extraído y un estado: pending, ready, empty, unsupported,
unavailable o error. No cambia el almacenamiento de archivos. El índice de
contenido se elimina junto con la fila del documento.

Límites: archivo de hasta 25 MB, primer millón de caracteres, PDF hasta 500
páginas y DOCX expandido hasta 50 MB. El contenido posterior al límite no se
busca. La consulta utiliza SQL literal parametrizado sobre el texto guardado;
no se descarga cada archivo al buscar. Para volúmenes grandes será necesario
medir y añadir índices o un motor dedicado; esta entrega no incluye esa
infraestructura.

## Acceso

Exige sesión y usuario activo. Conserva la política actual de lectura de estos
recursos, accesibles a todos los usuarios activos. No agrega búsqueda de
usuarios ni expone correos, claves o rutas de almacenamiento. No modifica los
permisos de edición ni eliminación. Si se restringe la lectura por equipo en el
futuro, debe aplicarse la misma política al buscador y a las descargas.

## Actualización

Desde backend:

```sh
alembic upgrade head
python -m app.scripts.index_search_documents
```

El segundo comando procesa documentos anteriores y reintenta errores o archivos
no disponibles; no reemplaza sus archivos. Migración o1p2q3r4s5t6 después de NEW-09.
Aplicado al entorno Docker local durante la implementación.

## Validación

Pruebas HTTP con PostgreSQL real: sesión, parámetros, contenido y nombre,
comodines literales, paginación, eliminación e imágenes por nombre. Regresión
del flujo de adjuntos. Pruebas de extracción PDF, DOCX con tablas y límite de
texto. Interfaz: resaltado seguro, paginación con filtros aplicados y errores.
Comprobación de tipos TypeScript y compilación de producción.

## Prueba manual

1. Abrir `http://localhost:5173/#/search` e iniciar sesión si se solicita.
2. Adjuntar un TXT, PDF con texto o DOCX que contenga una palabra distintiva.
3. Buscar esa palabra y filtrar Documentos: comprobar fragmento resaltado.
4. Abrir el documento y comprobar el archivo original.
5. Buscar un ticket y abrir su detalle; probar una búsqueda sin resultados.

El buscador requiere conexión. NEW-09 mantiene su alcance independiente.
