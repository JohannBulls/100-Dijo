# Preguntas pendientes: cómo revisarlas

Una pregunta se habilita para jugar solo si su tablero tiene **entre 4 y 10 respuestas** dichas por **2 o más personas**. Las que no llegan a 4 quedan **pendientes** y deshabilitadas: no entran en la mezcla de la partida hasta que decidas qué hacer con ellas.

El estado de cada pregunta, con su detalle y una propuesta, está en **[REVISION_DE_PREGUNTAS.md](REVISION_DE_PREGUNTAS.md)** (se genera solo al procesar). En el panel del presentador, la pestaña **Preguntas** muestra la misma información con la insignia «pendiente de revisión».

## Reglas de la revisión

- **No se inventan respuestas ni frecuencias** para llegar a 4.
- Solo se unen respuestas que expresan **la misma idea** (por ejemplo, «No pasaba el bus» y «Se varó el bus» → «Problemas con el transporte»). Cada unión queda anotada en `datos/agrupaciones.json` con una `nota`.
- Si cambias la redacción de una pregunta, se guarda en `texto_juego` y el texto original del Excel se conserva en `texto_original`.
- Una pregunta no se reemplaza por otra diferente sin dejar constancia.

## Opciones para una pregunta pendiente

En `datos/agrupaciones.json`, cada pregunta pendiente tiene un bloque como este:

```json
"revision_jugabilidad": {
  "estado": "pendiente",
  "detalle": "Solo 3 respuestas con respaldo…",
  "propuesta": "Opciones: (a) aceptarla con 3 respuestas como excepción; (b) …"
}
```

1. **Unir respuestas equivalentes.** Mueve los bloques `{"fila": …, "texto": "…"}` al grupo correcto y añade una `nota`. Luego cambia `"estado"` a `"mejorada"` y explica el cambio en `detalle`.
2. **Dejarla fuera.** No hagas nada: sigue deshabilitada.
3. **Reemplazarla.** Hazlo en una nueva encuesta. No mezcles respuestas de otra pregunta.

Si una pregunta mejorada sigue teniendo menos de 4 respuestas, el programa la mantiene deshabilitada aunque digas «mejorada».

Después de cualquier cambio, ejecuta **`PROCESAR_EXCEL.bat`** (necesita el Excel original en la carpeta principal) y luego **`EJECUTAR_PRUEBAS.bat`**. El reporte, el JSON y el Excel consolidado se regeneran juntos, así que el juego y el Excel siempre usan la misma fuente.

## Nombres de personas en las respuestas

Si una respuesta nombra a alguien, añade el nombre en `datos/privado/nombres_a_ocultar.json` (archivo que **no se publica**):

```json
{ "preguntas": { "20": { "¿Hablo con…?": ["Nombre"] } } }
```

Al procesar, el nombre se reemplaza por «[nombre]» en todo lo generado. El Excel original no se modifica.
