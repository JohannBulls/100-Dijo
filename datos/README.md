# Datos del juego

| Archivo | Qué contiene | ¿Se edita a mano? |
|---|---|---|
| `agrupaciones.json` | Decisiones de agrupación: qué respuestas originales (fila del Excel y texto) forman cada respuesta consolidada, más exclusiones, reformulaciones y notas de revisión. | **Sí.** Es la fuente de las decisiones humanas. |
| `preguntas_procesadas.json` | Preguntas listas para el juego: tablero, frecuencia real y puntos de cada respuesta (cada tablero suma 100). | No: se genera con `PROCESAR_EXCEL.bat`. |
| `preguntas_procesadas.xlsx` | El mismo contenido en Excel, para revisar y auditar: Resumen, Preguntas, Consolidadas, Contenido, Trazabilidad y Revisión manual. | No: se genera con `PROCESAR_EXCEL.bat`. |
| `partida_guardada.json` | Partida en curso. Se crea al jugar y no se publica en GitHub. | No. |

## Privacidad

Estos archivos **no contienen los nombres de quienes respondieron la encuesta**: cada respuesta se identifica solo por su número de fila en el Excel original.

El Excel original sí tiene los nombres. Por eso **no está en el repositorio** (ver `.gitignore`). Para volver a procesar, cópialo en la carpeta principal del proyecto.

## Cambiar una agrupación

1. Abre `agrupaciones.json` con el Bloc de notas.
2. Busca la pregunta por su número. Mueve el bloque `{"fila": …, "texto": "…"}` al grupo correcto, o cambia la `etiqueta`, que es el texto que se ve en el tablero.
3. Para aprobar una respuesta marcada «en revisión», borra su línea `"revision_contenido"`.
4. Ejecuta `PROCESAR_EXCEL.bat`. El programa avisa si alguna fila quedó en dos grupos o sin grupo.

## Esquema de `preguntas_procesadas.json`

```jsonc
{
  "personas_que_respondieron": 41,
  "criterio_puntos": "…",
  "preguntas": [
    {
      "id": "p15", "numero": 15, "texto": "Menciona un electrodoméstico…",
      "respuestas_validas": 41, "respuestas_en_tablero": 5, "puntos_tablero": 100,
      "habilitada": true, "jugable": true,
      "respuestas": [
        {
          "id": "p15-r1", "etiqueta": "Nevera", "frecuencia": 17, "puntos": 45,
          "en_tablero": true, "motivo_fuera": null,
          "originales": [{ "fila": 3, "texto": "Nevera" }, "…"],
          "reformulacion": null, "revision_contenido": null, "nota_contenido": null
        }
      ],
      "excluidas": [{ "fila": 41, "texto": "…", "motivo": "…" }],
      "revision": [{ "tipo": "posible_fusion", "detalle": "…" }]
    }
  ]
}
```
