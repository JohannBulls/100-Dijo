# 41 Clouders Dijeron — juego de encuestas para la reunión

Juego estilo concurso de televisión («¿qué respondió la gente?») construido con las respuestas reales del formulario `Estudio Sociológico (Respuestas).xlsx`. Está inspirado en ese formato, pero **no es una aplicación oficial** de ningún programa y no usa logotipos, música ni material de televisión.

Funciona **en este computador, sin cuentas y sin pagar nada**. Solo necesita Python, que ya está instalado en este equipo. La primera vez que abres cualquiera de los archivos `.bat`, se crea solo un **entorno del proyecto** (la carpeta `.venv`) y se instala la única dependencia, `openpyxl` (requiere internet **solo esa vez**). Después, el juego funciona sin internet.

---

## Lo más importante en 30 segundos

| Quiero…                    | Haz esto                                                                 |
|----------------------------|--------------------------------------------------------------------------|
| **Iniciar el juego**       | Doble clic en **`INICIAR_JUEGO.bat`**. Se abre una ventana negra y el navegador. |
| **Detener el juego**       | Cierra la ventana negra (o haz clic en ella y pulsa `Ctrl` + `C`).        |
| Abrir la pantalla pública  | En el navegador: `http://localhost:8765/publico`                          |
| Abrir el panel privado     | En el navegador: `http://localhost:8765/presentador`                      |
| Volver a procesar el Excel | Doble clic en **`PROCESAR_EXCEL.bat`**                                    |
| Comprobar que todo funciona| Doble clic en **`EJECUTAR_PRUEBAS.bat`** (debe terminar con `OK`)         |

> **La ventana negra es el motor del juego.** Mientras juegas, déjala abierta (puedes minimizarla). Si la cierras, las pantallas dejan de actualizarse.

La partida se guarda sola después de cada clic: participantes, equipos, orden de preguntas, líderes, rondas, puntos, respuestas reveladas, strikes y robo. Si cierras el navegador, recargas la página o incluso apagas el computador, al volver a iniciar el juego continúa donde quedó, **sin volver a sortear nada**. Reiniciar es siempre una acción explícita que pide confirmación.

---

## Paso a paso para iniciar (primera vez)

1. Abre la carpeta `Game 100 latinos`.
2. Haz doble clic en `INICIAR_JUEGO.bat`.
   - Si Windows muestra «Windows protegió su PC», pulsa **Más información → Ejecutar de todas formas** (es un archivo de texto creado para este proyecto).
3. Se abre el navegador con dos tarjetas:
   - **📺 Pantalla pública** → la que compartirás en Google Meet.
   - **🔒 Panel del presentador** → la que usas tú para controlar. **Nunca la compartas.**
4. En el panel, la pestaña **🧩 Preparación** te guía en 5 pasos:
   1. **Participantes:** escribe los nombres o pega la lista.
   2. **🎲 Sortear equipos.**
   3. **🔀 Mezclar preguntas.**
   4. **Rondas:** principales y adicionales con multiplicador.
   5. **✅ Confirmar e iniciar partida.**
5. Antes de cada ronda pulsa **🎡 Sortear líderes**: una ruleta elige al líder de cada equipo sin repetir.
6. Sigue la **[Guía de usuario](GUIA_DE_USUARIO.md)** para dirigir el juego.

### Comandos exactos (por si prefieres escribirlos)

Lo más sencillo es hacer doble clic en los `.bat`. Si prefieres escribir, abre «Símbolo del sistema» (o PowerShell) **en la carpeta del proyecto** y usa siempre el Python del entorno del proyecto, `.venv\Scripts\python.exe`:

```
.venv\Scripts\python.exe app\servidor.py                         ← inicia el juego (abre el navegador)
.venv\Scripts\python.exe -m unittest discover -s pruebas -v      ← ejecuta las pruebas
.venv\Scripts\python.exe app\procesar_excel.py                   ← vuelve a procesar el Excel
```

Para detener el juego: `Ctrl` + `C` en esa misma ventana.

> **Importante:** no uses solo `python …` para las pruebas. En este computador hay **dos** Python instalados (3.14 y 3.12). Si Windows elige el 3.12, que no tiene `openpyxl`, aparece el error `ModuleNotFoundError: No module named 'openpyxl'`. El Python de `.venv` siempre tiene todo lo necesario. Si la carpeta `.venv` no existe, haz doble clic una vez en `EJECUTAR_PRUEBAS.bat` y se crea sola.

---

## Repositorio en GitHub

El proyecto está en **https://github.com/JohannBulls/100-Dijo** (público), vinculado a esta carpeta. Cada corrección o ajuste se guarda como un *commit* y se sube allí, así queda el historial de cambios.

- **Lo que se sube:** el programa, las pruebas, la documentación y los datos procesados (`datos/`). Los datos procesados no tienen nombres de participantes: identifican cada respuesta solo por su número de fila.
- **Lo que no se sube (`.gitignore`):**
  - El **Excel original**, porque tiene los nombres de las 41 personas junto a sus respuestas.
  - La carpeta `.venv`.
  - La partida guardada.
- **Quien descargue el repositorio** puede jugar con `INICIAR_JUEGO.bat`, porque los datos procesados están incluidos. Para volver a procesar necesita el Excel original. Sin él, las pruebas del procesamiento se omiten con un aviso y el resto se ejecuta normalmente.

---

## ¿Qué hay en la carpeta?

| Archivo / carpeta | Para qué sirve |
|---|---|
| `Estudio Sociológico (Respuestas).xlsx` | El Excel original. **No se modifica nunca.** **No está en GitHub** (tiene los nombres de quienes respondieron): guárdalo aparte y cópialo en la carpeta principal si necesitas volver a procesarlo. |
| `INICIAR_JUEGO.bat` | Inicia el juego con doble clic. |
| `PROCESAR_EXCEL.bat` | Regenera los archivos de `datos/` a partir del Excel. |
| `EJECUTAR_PRUEBAS.bat` | Ejecuta las 75 pruebas automáticas y muestra qué Python usó. |
| `requirements.txt` | Lista de dependencias del proyecto (solo `openpyxl==3.1.5`). |
| `.venv/` | Entorno del proyecto (se crea solo). Si algo falla con Python, bórrala y vuelve a abrir un `.bat`. |
| `app/preparar_entorno.bat` | Lo usan los `.bat` para crear `.venv` e instalar las dependencias. |
| `GUIA_DE_USUARIO.md` | Cómo dirigir el juego paso a paso durante la reunión. |
| `GUION_PRESENTADORES.md` | Guion para el presentador principal y el copiloto. |
| `DECISIONES_PARA_REVISAR.md` | Agrupaciones dudosas y reglas que debes confirmar. |
| `datos/preguntas_procesadas.xlsx` | **Excel consolidado**: preguntas, respuestas consolidadas, frecuencia real, **puntos asignados (cada pregunta suma 100)**, si va al tablero, respuestas originales, tratamiento de contenido y casos a revisar. |
| `datos/preguntas_procesadas.json` | Las mismas preguntas en el formato que usa el juego. |
| `datos/agrupaciones.json` | Las decisiones de agrupación (qué respuestas originales forman cada respuesta). Es editable. |
| `datos/partida_guardada.json` | Se crea al jugar: guarda la partida en curso. Bórralo solo si quieres empezar totalmente de cero. |
| `app/` | El programa (servidor, motor del juego, procesador del Excel y páginas web). |
| `pruebas/` | Las pruebas automáticas. |

---

## Cómo se procesaron los datos (resumen)

- El Excel tiene **una hoja** («Respuestas de formulario 1»), **41 filas = 41 personas distintas** (cada fila tiene marca de tiempo y nombre diferentes; no hay filas repetidas) y **52 preguntas**. Cada persona dio **una** respuesta por pregunta, así que la **frecuencia = número de personas**.
- La **pregunta 29** («Si Salesforce fuera una mascota…») está **vacía**: nadie la respondió, así que no se usa. Quedan **51 preguntas**.
- Las respuestas que dicen lo mismo con otras palabras o con errores de ortografía se agruparon (por ejemplo «Había trancón», «un trancon», «el tráfico» → **Había trancón**, 28 personas). Cuando no era seguro, **no** se unieron y se dejó una nota para que lo decidas.
- Las respuestas que no responden la pregunta (por ejemplo «No sé», o las 9 respuestas de la pregunta 6 «tipo de oso» que claramente responden otra pregunta) se **excluyeron** y quedan listadas con su motivo.
- Si alguien dio dos ideas en una respuesta («los zapatos o arreglos de navidad»), esa persona cuenta **una sola vez**, en la primera idea, y queda anotado.
- El humor pícaro, escatológico y las groserías **se conservan**. Solo 4 respuestas discriminatorias quedan «en revisión» (se cuentan, pero no salen en el tablero hasta que las apruebes) y 3 se reformularon mínimamente para no mostrar nombres de personas. Ver `DECISIONES_PARA_REVISAR.md`.
- Todo es auditable en `datos/preguntas_procesadas.xlsx` (hojas *Consolidadas*, *Contenido*, *Trazabilidad* y *Revisión manual*).

Resultado: 51 preguntas procesadas, **47 jugables** con la configuración por defecto (las 4 restantes tienen menos de 3 respuestas dichas por 2 o más personas: 20, 25, 39 y 47).

### Cómo se asignan los puntos (cada pregunta vale exactamente 100)

**Cada pregunta reparte exactamente 100 puntos entre las respuestas de su tablero, en proporción a su frecuencia real.**

1. **El tablero:** entran las respuestas que dijeron 2 o más personas (sin revisión de contenido pendiente), con un máximo de 8. Las demás se ven en el panel como «fuera del tablero» y no puntúan (0).
2. **El reparto:** a cada respuesta se le da la parte entera de *frecuencia ÷ suma de frecuencias del tablero × 100*.
3. **El ajuste:** los puntos que faltan para llegar a 100 se dan a las respuestas con mayor parte decimal, por grupos completos de igual frecuencia. Así los empates conservan los mismos puntos. Si un grupo empatado ya no cabe completo, el sobrante va a la respuesta más popular.

| Ejemplo real (pregunta 15) | Frecuencia real | Puntos |
|---|---:|---:|
| Nevera | 17 | 45 |
| Licuadora | 9 | 24 |
| Estufa | 7 | 18 |
| Cafetera | 3 | 8 |
| Horno | 2 | 5 |
| **Total** | 38 | **100** |

- **Garantías:** la suma de cada pregunta es **siempre 100**, sin importar si su tablero tiene 3, 4, 6 u 8 respuestas. Todos los puntos son enteros positivos, y una respuesta más popular nunca tiene menos puntos que una menos popular.
- **Un único empate partido:** en la P1, tres respuestas empatan en el primer lugar (4 personas cada una). 100 no se puede repartir en partes iguales, así que quedan 18, 17 y 17 por orden alfabético.
- **Un solo cálculo:** los puntos se calculan una vez, al procesar el Excel. Se guardan en el Excel consolidado (columna **«PUNTOS ASIGNADOS (suman 100 por pregunta)»**; la hoja *Preguntas* muestra la suma: 100 en todas) y en el archivo que lee el juego. El juego los usa tal cual.
- **Rondas adicionales:** su multiplicador se aplica al banco (×2 = hasta 200 pts) sin cambiar los puntos del Excel.
- **Auditoría:** la frecuencia real se conserva al lado de cada respuesta.

### Si cambias una agrupación

1. Abre `datos/agrupaciones.json` con el Bloc de notas.
2. Busca la pregunta (por su número) y mueve el bloque `{"fila": …, "texto": "…"}` al grupo correcto (o cambia la `etiqueta`, que es el texto que aparece en el tablero).
3. Guarda y haz doble clic en `PROCESAR_EXCEL.bat`. Si algo quedó mal (una respuesta en dos grupos, una fila que falta), el programa lo avisa.
4. Reinicia el juego.

---

## Pruebas realizadas

Las ejecuté con `EJECUTAR_PRUEBAS.bat` y **pasaron las 75** (0 fallos, 0 omitidas). Antes eran 61: se reescribieron las que dependían del flujo anterior (ahora las rondas empiezan desde la preparación) y se agregaron nuevas. No se eliminó ninguna comprobación. Cubren, entre otras cosas:

**Preparación, sorteos y líderes (los 20 escenarios pedidos):**
1. Registro de 20 participantes (pegados o uno por uno), con duplicados ignorados, edición y eliminación.
2. Sorteo de 10 contra 10: todos asignados una vez y sin repetir.
3. Sorteos impares (3, 7, 9, 21): la diferencia es como máximo de una persona.
4. Repetir el sorteo cambia el reparto. Tras confirmar, los equipos quedan fijos.
5. Mezcla de preguntas: es una permutación real; volver a mezclar cambia el orden y, en 300 mezclas, más de 20 preguntas distintas salieron primeras.
6. Ninguna pregunta se repite en la partida y se usan en el orden sorteado.
7. Todas las preguntas suman exactamente 100 (y el Excel también). Hay tableros de 3, 4, 5, 6 y 8 respuestas. Se verificaron además 20.000 repartos aleatorios.
8. La primera ronda sortea un líder de cada equipo.
9. En un 10 contra 10, los 20 integrantes son líderes una vez en 10 rondas, sin repetir.
10. Con 5 contra 4 se exigen 5 rondas principales (con 4 no deja confirmar).
11. El equipo de 4 no repite líderes y en la 5.ª ronda queda sin nuevo sorteo; el 5.º del otro equipo sale obligatoriamente.
12. El ciclo se reinicia solo cuando ambos equipos agotaron sus integrantes (en la ronda 6 del ejemplo 5 contra 4) y se anuncia.
13. y 14. Las rondas extra multiplican el banco (×2, ×3) sin cambiar los puntos base, y el marcador suma bien.
15. El banco se asigna una sola vez, también en rondas extra.
16. Al recargar o reiniciar el servidor se conservan equipos, orden, líderes, ronda, respuestas, strikes y robo.
17. Cancelar una ronda devuelve la pregunta, y revertir el sorteo de líderes recupera el historial anterior.
18. La pantalla pública no recibe el orden de preguntas, sus textos, las respuestas ocultas ni datos internos.
19. Las animaciones reciben el resultado real: la secuencia del sorteo de equipos coincide con los equipos guardados y la ruleta se detiene en el índice del líder elegido. Además, la elección de líder es estadísticamente uniforme.
20. Si faltan preguntas, avisa cuántas («Faltan 5 preguntas») y no deja confirmar.

**Lo que ya existía y se sigue comprobando:**
- Procesamiento del Excel sin modificar el original.
- La respuesta correcta revela la casilla y el strike suma una X.
- Tres strikes habilitan el robo; el robo exitoso o fallido adjudica bien el banco.
- No hay puntos duplicados y el doble clic se rechaza.
- «Deshacer» recupera el estado anterior.
- El marcador final identifica al ganador.
- El humor y las groserías se conservan.
- Sincronización por «espera larga», controles de audio y recorrido completo por HTTP.

**En el navegador real (Edge sin ventana):**
- Registré a 20 personas y sorteé los equipos. Cada nombre apareció en la animación en el mismo equipo donde quedó guardado, y el sorteo tardó unos 8 segundos.
- Mezclé las preguntas: la pantalla pública no mostró ningún texto de pregunta.
- Sorteé los líderes y medí el ángulo final de la ruleta: el puntero apuntaba exactamente al segmento del líder sorteado, con su nombre anunciado.
- Jugué las 10 rondas: cada integrante fue líder una vez.
- En la ronda extra vi el anuncio «¡Nuevo ciclo de líderes!», la animación de ronda extra y «×2 · hasta 200 pts» en la pantalla pública.
- Probé el caso 5 contra 4 en pantalla.
- Sonaron todos los efectos nuevos y no hubo errores de JavaScript.

---

## Problemas frecuentes

| Problema | Solución |
|---|---|
| «No se encontró Python» | Instala Python desde https://www.python.org/downloads/ marcando **Add python.exe to PATH**. |
| `ModuleNotFoundError: No module named 'openpyxl'` | Ejecutaste las pruebas con otro Python (por ejemplo el 3.12). Usa `EJECUTAR_PRUEBAS.bat` o `.venv\Scripts\python.exe -m unittest discover -s pruebas -v`. |
| «No se pudo instalar openpyxl» | La primera preparación necesita internet. Conéctate y vuelve a abrir el `.bat`. (El juego arranca igual; solo el procesamiento del Excel y las pruebas lo necesitan.) |
| «El puerto 8765 ya está en uso» | El juego ya está abierto en otra ventana negra. Usa esa, o ciérrala y vuelve a iniciar. |
| La pantalla pública dice «Sin conexión con el juego» | La ventana negra se cerró. Vuelve a abrir `INICIAR_JUEGO.bat`. |
| No suena nada | Los navegadores bloquean el sonido hasta que haces **un clic** en la pantalla pública: pulsa «🔊 Clic aquí para activar el sonido». Revisa también la tarjeta **Sonido y música** del panel (interruptores y volumen) y usa «▶ Probar». |
| Yo oigo los sonidos, pero los participantes no | En Meet hay que compartir la **pestaña** de la pantalla pública (no «Una ventana» ni «Toda la pantalla») y marcar «Compartir también el audio de la pestaña». Ver la guía, sección 2. |
| Las letras se ven distintas | Las fuentes decorativas se descargan de Google Fonts. Sin internet se usan fuentes del sistema; el juego funciona igual. |
| Quiero empezar de cero | En el panel: pestaña **Reglas y opciones → Nueva partida desde cero**. |

## ¿Puede el copiloto controlar desde otro computador?

**No en esta versión.** Por seguridad, el juego solo acepta conexiones desde el mismo computador donde se inicia (`localhost`), y la sincronización está probada **entre ventanas y pestañas de ese computador**. Habilitarlo para otro computador requeriría abrir el juego a la red local (configurar el cortafuegos de Windows y la dirección del equipo) y no lo he implementado ni probado. La guía explica cómo pueden repartirse el trabajo los dos presentadores con un solo computador.
