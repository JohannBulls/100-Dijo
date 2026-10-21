# Diccionario de datos

Todos estos archivos se generan con `PROCESAR_EXCEL.bat` (`app/procesar_excel.py`) a partir del Excel de la encuesta y de las decisiones de `datos/agrupaciones.json`. El juego lee `preguntas_procesadas.json`; el Excel consolidado tiene el mismo contenido para revisarlo. Ninguno incluye los nombres de quienes respondieron.

## Excel consolidado: `datos/preguntas_procesadas.xlsx`

### Hoja «Resumen»

| Columna | Descripción |
|---|---|
| Dato / Valor | Archivo y hoja de origen, personas que respondieron, preguntas procesadas, habilitadas y pendientes, y el criterio de puntos. |

### Hoja «Preguntas» (una fila por pregunta)

| Columna | Descripción |
|---|---|
| N° | Número de la pregunta en la encuesta. |
| Pregunta (como se muestra en el juego) | Texto con la ortografía corregida (`texto_juego`). |
| Texto original del Excel | Texto exacto de la encuesta. |
| Respuestas válidas | Respuestas que se agruparon. |
| Excluidas | Respuestas que no responden la pregunta (por ejemplo, «No sé»). |
| Respuestas distintas | Grupos consolidados (en el tablero o fuera de él). |
| Respuestas en el tablero | Grupos dichos por 2 o más personas, sin revisión de contenido pendiente (máximo 10). |
| SUMA DE PUNTOS DEL TABLERO | Siempre 100 en las preguntas habilitadas. |
| ¿Habilitada? | «Sí» si el tablero tiene de 4 a 10 respuestas y no está pendiente. |
| Estado de jugabilidad | Lista para jugar · Lista, con advertencia · Mejorada en la revisión · Pendiente de tu decisión. |
| Casos para revisar | Cantidad de filas de esa pregunta en la hoja «Revisión manual». |

### Hoja «Jugabilidad» (estado detallado)

| Columna | Descripción |
|---|---|
| N° / Pregunta | Pregunta. |
| Estado | Igual que en «Preguntas». |
| Respuestas en el tablero | Tamaño del tablero. |
| Detalle | Por qué tiene ese estado. |
| Advertencias | Por ejemplo, si una respuesta concentra más del 60 % (el cara a cara se decide casi siempre con la primera respuesta). |
| Propuesta | Qué se sugiere hacer (solo en mejoradas y pendientes). |

### Hoja «Consolidadas» (una fila por respuesta consolidada)

| Columna | Descripción |
|---|---|
| N° / Pregunta | Pregunta. |
| Posición | Orden en el tablero (1 = más popular). |
| Respuesta consolidada (en pantalla) | Texto que aparece en el tablero. |
| Frecuencia real (personas) | Cuántas personas dieron esa respuesta. |
| Respuestas válidas de la pregunta | Total de respuestas válidas. |
| PUNTOS ASIGNADOS (suman 100 por pregunta) | Puntos de la casilla (0 si está fuera del tablero). |
| ¿Va al tablero? | «Sí» o el motivo por el que queda fuera. |
| Ejemplos de respuestas aceptadas | Hasta 6 textos **reales** de la encuesta, distintos entre sí, empezando por los más repetidos. |
| Criterio para aceptar variantes | Guía para el presentador: qué aceptar como equivalente y con qué otra casilla no confundirla. |
| Respuestas originales agrupadas | Todos los textos originales del grupo. |
| Filas del Excel | Filas de origen (trazabilidad). |
| Nota de agrupación | Por qué se agruparon. |
| Reformulación aplicada | Texto original si la etiqueta se reformuló. |
| Revisión de contenido | Tratamiento de contenido sensible, si aplica. |

### Hojas «Contenido», «Trazabilidad» y «Revisión manual»

| Hoja | Columnas |
|---|---|
| Contenido | Respuestas con humor adulto o sensible: N°, Pregunta, Respuesta, Frecuencia, Puntos, Tratamiento, Detalle. |
| Trazabilidad | Una fila por respuesta original: N°, Fila del Excel, Respuesta original, Se agrupó en, Estado (Válida o Excluida). |
| Revisión manual | Casos dudosos: exclusiones, posibles fusiones y reasignaciones (N°, Pregunta, Tipo, Detalle). |

## JSON del juego: `datos/preguntas_procesadas.json`

### Pregunta

| Campo | Tipo | Descripción |
|---|---|---|
| `id`, `numero` | texto, entero | `p15`, `15`. |
| `texto` | texto | Texto que se muestra en el juego. |
| `texto_original` | texto | Texto exacto del Excel. |
| `respuestas_validas`, `respuestas_excluidas`, `respuestas_vacias` | entero | Conteos (las vacías son celdas sin respuesta). |
| `respuestas_en_tablero`, `puntos_tablero` | entero | Tamaño del tablero y suma de puntos (100). |
| `habilitada` (`jugable`) | booleano | Si entra en la mezcla de la partida. |
| `jugabilidad` | objeto | `estado`, `estado_nombre`, `detalle`, `propuesta`, `advertencias[]`. |
| `respuestas` | lista | Respuestas consolidadas, ordenadas por frecuencia. |
| `excluidas` | lista | `{fila, texto, motivo}`. |
| `revision` | lista | `{tipo, detalle}`: casos para revisar. |

### Respuesta consolidada

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | texto | `p15-r1`. |
| `etiqueta` | texto | Texto del tablero. |
| `frecuencia` | entero | Personas que la dieron (= cantidad de `originales`). |
| `puntos` | entero | Puntos de la casilla (0 fuera del tablero). |
| `en_tablero`, `motivo_fuera` | booleano, texto | Si está en el tablero y, si no, por qué. |
| `originales` | lista | `{fila, texto}`: respuestas originales (con «[nombre]» si nombraban a alguien). |
| `ejemplos` | lista de texto | Ejemplos reales de respuestas aceptadas (subconjunto de `originales`). |
| `criterio` | texto | Criterio para aceptar variantes. |
| `nota` | texto | Nota de agrupación. |
| `reformulacion` | objeto | `{etiqueta_original, motivo}` si se reformuló. |
| `revision_contenido`, `nota_contenido` | texto | Tratamiento de contenido sensible. |

## Decisiones humanas: `datos/agrupaciones.json`

Por pregunta: `grupos` (etiqueta, nota, originales y `anonimizado: true` si se ocultó el nombre de una persona), `excluidas`, y opcionalmente `texto_juego` (redacción corregida) y `revision_jugabilidad` (`estado`, `detalle`, `propuesta`). Ver [PREGUNTAS_PENDIENTES.md](PREGUNTAS_PENDIENTES.md).

## Archivos privados (no se publican)

| Archivo | Contenido |
|---|---|
| Excel original (carpeta principal) | Respuestas con los nombres de quienes respondieron. |
| `datos/privado/nombres_a_ocultar.json` | Nombres de personas mencionadas en las respuestas, para reemplazarlos por «[nombre]». |
| `datos/partida_guardada.json` | Partida en curso (participantes y marcador). |
