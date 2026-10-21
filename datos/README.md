# Datos del juego

| Archivo | Qué contiene | ¿Se edita a mano? |
|---|---|---|
| `agrupaciones.json` | Decisiones de agrupación: qué respuestas originales (fila del Excel y texto) forman cada respuesta consolidada, más exclusiones, reformulaciones y notas de revisión. | **Sí.** Es la fuente de las decisiones humanas. |
| `preguntas_procesadas.json` | Preguntas listas para el juego: tablero, frecuencia real, puntos, ejemplos aceptados y criterio de cada respuesta, y estado de jugabilidad (cada tablero habilitado suma 100). | No: se genera con `PROCESAR_EXCEL.bat`. |
| `preguntas_procesadas.xlsx` | El mismo contenido en Excel, para revisar y auditar: Resumen, Preguntas, Jugabilidad, Consolidadas, Contenido, Trazabilidad y Revisión manual. | No: se genera con `PROCESAR_EXCEL.bat`. |
| `privado/nombres_a_ocultar.json` | Nombres de personas mencionadas en respuestas, que se reemplazan por «[nombre]». No se publica en GitHub. | Sí. |
| `partida_guardada.json` | Partida en curso. Se crea al jugar y no se publica en GitHub. | No. |

## Privacidad

Estos archivos **no contienen los nombres de quienes respondieron la encuesta**: cada respuesta se identifica solo por su número de fila en el Excel original. Si una respuesta mencionaba a una persona, su nombre aparece como «[nombre]».

El Excel original sí tiene los nombres. Por eso **no está en el repositorio** (ver `.gitignore`). Para volver a procesar, cópialo en la carpeta principal del proyecto.

## Cambiar una agrupación

1. Abre `agrupaciones.json` con el Bloc de notas.
2. Busca la pregunta por su número. Mueve el bloque `{"fila": …, "texto": "…"}` al grupo correcto, o cambia la `etiqueta`, que es el texto que se ve en el tablero.
3. Para aprobar una respuesta marcada «en revisión», borra su línea `"revision_contenido"`.
4. Ejecuta `PROCESAR_EXCEL.bat`. El programa avisa si alguna fila quedó en dos grupos o sin grupo.

Para las preguntas con menos de 4 respuestas, ver [docs/PREGUNTAS_PENDIENTES.md](../docs/PREGUNTAS_PENDIENTES.md). Todas las columnas y campos están en [docs/DICCIONARIO_DE_DATOS.md](../docs/DICCIONARIO_DE_DATOS.md).

## Esquema de `preguntas_procesadas.json`

```jsonc
{
  "personas_que_respondieron": 41,
  "criterio_puntos": "…",
  "preguntas": [
    {
      "id": "p15", "numero": 15, "texto": "Menciona un electrodoméstico…",
      "respuestas_validas": 41, "respuestas_en_tablero": 5, "puntos_tablero": 100,
      "texto_original": "…", "habilitada": true, "jugable": true,
      "jugabilidad": { "estado": "lista", "estado_nombre": "Lista para jugar", "detalle": "", "propuesta": "", "advertencias": [] },
      "respuestas": [
        {
          "id": "p15-r1", "etiqueta": "Nevera", "frecuencia": 17, "puntos": 45,
          "en_tablero": true, "motivo_fuera": null,
          "originales": [{ "fila": 3, "texto": "Nevera" }, "…"],
          "ejemplos": ["Nevera", "La nevera"],
          "criterio": "Acepta cualquier forma de decir «Nevera» o una idea equivalente.",
          "reformulacion": null, "revision_contenido": null, "nota_contenido": null
        }
      ],
      "excluidas": [{ "fila": 41, "texto": "…", "motivo": "…" }],
      "revision": [{ "tipo": "posible_fusion", "detalle": "…" }]
    }
  ]
}
```
