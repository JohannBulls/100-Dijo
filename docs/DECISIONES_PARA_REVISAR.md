# Decisiones que requieren tu revisión

Todo lo de esta lista ya funciona con una opción por defecto razonable. Revísalo antes de la reunión y cambia lo que no te convenza.

El detalle completo está en `datos/preguntas_procesadas.xlsx`, hoja **«Revisión manual»**: 291 notas, una por caso. Se reparten así:
- 133 posibles fusiones que **no** se hicieron.
- 72 respuestas con dos ideas.
- 34 exclusiones.
- 33 interpretaciones ambiguas.
- 8 notas diversas.
- 4 respuestas en revisión de contenido.
- 4 preguntas poco jugables.
- 3 reformulaciones.

El tratamiento de contenido también está en la hoja **«Contenido»**. Para cambiar una agrupación, ver README → «Si cambias una agrupación».

---

## A. Puntuación (cada pregunta vale exactamente 100)

| # | Decisión tomada | Por qué / alternativa |
|---|---|---|
| A1 | **Cada pregunta reparte exactamente 100 puntos** entre las respuestas de su tablero, proporcionalmente a la frecuencia real (método del resto mayor, por grupos de igual frecuencia). | Es lo que pediste: ninguna pregunta suma 56 ni 70. Las 51 preguntas suman 100 (verificado en el Excel y en el juego). |
| A2 | Las respuestas **fuera del tablero** (dichas por 1 sola persona, las que pasan del puesto 8 o las que están en revisión) **no puntúan (0)**. | Si puntuaran, el tablero no llegaría a 100. Siguen visibles en el panel como referencia: si un equipo dice una, es strike. |
| A3 | El tablero lo fija el procesamiento del Excel: **2 o más personas, máximo 8 respuestas**. Ya **no** se puede cambiar en «Reglas y opciones». | Si el juego pudiera cambiar el tablero, los puntos dejarían de sumar 100 o se calcularían distinto que en el Excel. Para cambiarlo, modifica `MIN_FRECUENCIA_TABLERO` / `MAX_TABLERO` en `app/procesar_excel.py` y vuelve a procesar. |
| A4 | **Empates:** respuestas con la misma frecuencia reciben los mismos puntos siempre que sea posible. El sobrante del redondeo va a la respuesta más popular. **Único caso inevitable: P1**, con triple empate en el primer lugar (4 personas cada una): quedan 18, 17 y 17. | 100 no se puede dividir en tres partes iguales sin quitarles puntos a otras respuestas. |
| A5 | **Empate en la 8.ª casilla:** entra la que va primero en orden alfabético. | — |
| A6 | Una pregunta con **una sola** respuesta en el tablero le da los 100 puntos (P25 y P47). Por eso las 4 preguntas «poco jugables» (20, 25, 39 y 47) **no entran en la mezcla**, salvo que marques «Incluir también las preguntas poco jugables». | Evita rondas que se resuelven con una sola respuesta. |
| A7 | Los puntos se calculan **una sola vez** al procesar y se guardan en el Excel consolidado y en el archivo del juego. Si editas a mano los puntos del Excel, el juego no los lee de ahí. | Para cambiar puntos, cambia agrupaciones o la regla y vuelve a ejecutar `PROCESAR_EXCEL.bat`. |
| A8 | En un **robo exitoso**, los puntos de la respuesta robada **se suman** al banco, una sola vez. Aun así, el banco nunca supera 100 (× multiplicador), porque todo el tablero suma 100. | Desactivarlo en «Reglas y opciones». |
| A9 | Decir una respuesta **ya revelada** no es strike: se pide otra. | Contarla como strike pulsando «Strike». |
| A10 | El ganador del cara a cara puede **jugar o pasar**. | Desactivarlo: siempre juega el ganador. |
| A11 | Nombre del juego: **«41 Clouders Dijeron»**. | Cualquier otro (Reglas y opciones). |
| A12 | Si alguien dio **dos ideas en una respuesta**, cuenta **una vez**, en la primera idea (72 casos marcados como «compuesta»). | Contarla en ambas (cambiaría los totales). |

---

## B. Preparación, sorteos, líderes y rondas extra

| # | Decisión tomada | Por qué / alternativa |
|---|---|---|
| B1 | Todos los sorteos (equipos, orden de preguntas, líderes) los hace el **servidor** con el generador aleatorio del sistema operativo (`random.SystemRandom`). Las animaciones solo muestran el resultado ya guardado. | Así la animación no puede «decidir» nada ni contradecir lo guardado (comprobado en las pruebas y en el navegador). |
| B2 | **Reparto de equipos:** se baraja a todas las personas y se asignan alternando equipos. El equipo que empieza también es al azar. | Garantiza 10 y 10 (o una de diferencia si el total es impar) y cualquier reparto equilibrado es igual de probable. |
| B3 | Si agregas o quitas participantes después del sorteo, **el sorteo se anula** y hay que repetirlo. | Evita personas fuera de equipo o duplicadas. |
| B4 | **Ciclo de líderes común a los dos equipos.** Cada equipo tiene su historial. Un equipo que ya tuvo a todos sus integrantes como líderes **se queda sin nuevo sorteo** (elige a su representante) hasta que el otro equipo también complete su ciclo. Solo entonces empieza un ciclo nuevo para ambos, y se anuncia. | Es el comportamiento que describiste para el ejemplo 5 contra 4: en la ronda 5 solo el equipo de 5 sortea, y el ciclo se reinicia en la ronda 6. |
| B5 | Rondas principales por defecto = **tamaño del equipo más numeroso**. Se pueden poner más, pero no menos (no deja confirmar). | Garantiza que todos sean líderes una vez. |
| B6 | Rondas adicionales: de **0 a 10**. Multiplicadores por defecto **×2, ×3, ×4…** (editables de ×1 a ×10). Valen hasta 100 × multiplicador. | Límite razonable para una reunión. |
| B7 | Las rondas usan la **siguiente pregunta del orden sorteado**. De forma excepcional, el presentador puede usar otra no usada («Usar otra pregunta»); la sorteada queda disponible. | Permite reemplazar una pregunta incómoda sin rehacer la mezcla. |
| B8 | **Cancelar una ronda** devuelve la pregunta y regresa al paso de líderes. Desde allí, **Revertir sorteo de líderes** recupera el historial anterior. | Es lo que pediste: revertir sin perder el historial. |
| B9 | **Nueva partida / Reiniciar configuración** conservan participantes, equipos y reglas, pero exigen volver a **mezclar las preguntas**. | Así una partida nueva no repite el orden de la anterior. |
| B10 | La pantalla pública muestra los **nombres de los integrantes** de cada equipo (portada y sorteo), pero nunca el orden de las preguntas. | Los nombres son de los propios jugadores; el orden de preguntas revelaría el juego. |

---

## C. Humor adulto y contenido sensible

**Criterio aplicado:** el juego es informal y un poco atrevido. Se conserva el humor pícaro y escatológico y las groserías. **Ninguna respuesta se eliminó por ser vulgar o sexual.** Solo se trató lo discriminatorio y lo que nombra a personas concretas. Los textos originales nunca se modifican: siguen completos en el Excel consolidado y en el panel del presentador.

### C1. Se conservan tal cual (solo una nota informativa)

| Pregunta | Respuesta | Frecuencia → puntos (de 100) |
|---|---|---|
| P21 dedo chiquito del pie | **¡Hijueputa!** (agrupa HP, Hpta, Jueputa, Vida hp…; 1.ª respuesta) | 23 → 78 |
| P27 grosería con los reportes | Hijueputa, Mierda, Qué chimbada… | 9 → 44 |
| P12 escondido en el cuarto | Juguetes sexuales («un dildo», «mis juguetitos»…) | 5 → 25 |
| P13 regalo para la suegra | Un consolador | 2 → 9 |
| P52 buscar en incógnito | Pornografía | 2 → 9 |
| P35 / P46 / P1 | Comérselo, Comerse los mocos, Sacarse los mocos | se conservan |
| P17 gimnasio | Tirarse un pedo, Cagarse encima | se conservan |
| P5 puerta | Testigos de Jehová, A un evangélico (broma sobre las visitas puerta a puerta) | 6 → 25 · 2 → 8 |
| P21 | «¡Ay, marica!» (interjección común; el término puede resultar ofensivo para algunas personas) | 1 persona (fuera del tablero, no puntúa) |
| P28 | «Perra» (doble sentido; se toma como animal) | 1 persona (fuera del tablero, no puntúa) |
| P50, P53 | «Ir donde las cariñosas», «Sexting» | 1 persona (fuera del tablero, no puntúa) |

### C2. Reformuladas mínimamente (se conserva la idea, sin nombres de personas)

| Pregunta | Original | En pantalla | Motivo |
|---|---|---|---|
| P23 | «Nico un catorce» | **¡Hágame un catorce!** | Nombra a una persona concreta. |
| P20 | «Hablo con Doriam?» | **¿Hablo con…?** | Nombre propio. |
| P5 | «Al presidente 2026 de Colombia» / «Abelardo de la Espriella» / «Políticos» | **A los políticos** | Nombra a personas concretas. |

### C3. En revisión manual: se cuentan en la frecuencia, pero **no salen en el tablero** hasta que decidas

No se pueden suavizar sin cambiar su sentido, así que no inventé alternativas:

| Pregunta | Respuesta | Motivo |
|---|---|---|
| P5 ¿A quién no le abrirías la puerta? | «A los venezolanos» | Xenófoba hacia una nacionalidad. |
| P12 Escondido en tu cuarto | «Un venezolano» | Broma xenófoba. |
| P5 | «A los de otra religión» | Excluye por religión. |
| P15 Electrodoméstico | «Una mujer» | Chiste sexista. *Antes* estaba excluida. Ahora se cuenta (la frecuencia de la P15 vuelve a 41), pero no se muestra. |

Las cuatro las dijo **una sola persona**, así que con la configuración por defecto tampoco entrarían al tablero. **Para aprobar una:** en `datos/agrupaciones.json` borra su línea `"revision_contenido"` y ejecuta `PROCESAR_EXCEL.bat`.

### C4. Corrección de agrupación

- P46: «Comer mocos» estaba unida a «Sacarse los mocos». Son ideas distintas, así que ahora es «Comerse los mocos».

---

## D. Datos excluidos (no son respuestas)

| # | Pregunta | Qué se hizo |
|---|---|---|
| D1 | **P29** «Si Salesforce fuera una mascota…» | Columna **vacía**: nadie respondió. No se usa. |
| D2 | **P6** «Menciona un tipo de oso» | **9 respuestas** responden otra pregunta («Una caída en la calle», «Reírse en misa»…; en Colombia «hacer el oso» es hacer el ridículo). Se excluyeron junto con «Oso», que es demasiado vaga. |
| D3 | Varias | «No sé», «Ni idea», «Nn», «N se» y similares. P24 (Chatter) es la más afectada: 15 de 41. |
| D4 | **P28** | «Ninguno» (3 personas) se excluyó. Podría ser un grupo propio. |
| D5 | **P41**, **P52** | «Nada» se excluyó como no-respuesta. En P13 y P16, en cambio, «Nada» sí responde la pregunta y se dejó. |

En total se excluyeron **92 respuestas de 2.091**, cada una con su motivo en la hoja «Trazabilidad». Ninguna por ser grosera (lo verifica una prueba automática).

---

## E. Agrupaciones dudosas más importantes (cambian el tablero)

Se dejaron **separadas** salvo que se indique lo contrario.

| # | Pregunta | Caso | Si se unen |
|---|---|---|---|
| E1 | P3 dónde se duerme la gente | «En el bus» (13) y «En el transporte público» (9) | 22 personas |
| E2 | P42 pregunta en la reunión | «Pedir que repitan la pregunta» (11), «Culpar a la conexión» (9), «Decir que no entendió» (3) | hasta 23 |
| E3 | P37 saliva al jefe | «Pedir disculpas» (22) y «¡Uy, qué pena!» (4), que en Colombia es una disculpa | 26 |
| E4 | P53 redes a las 2 a. m. | «Stalkear gente» (9), «Stalkear al ex» (3), «Chismosear» (1) | 13 |
| E5 | P50 día de pago | «Pagar deudas» (17) y «Pagar cuentas» (2) | 19 |
| E6 | P27 grosería | «Mierda» (6) con «Esta mierda no sirve» (2); «Hijueputa» (9) con «Vida hijueputa» (2) | 8 / 11 |
| E7 | P14 profesión | **Se unieron** «Neurocirujano» y «Oncólogo» con «Médico» (28) | — |
| E8 | P6 tipo de oso | «Hormiguero» y «Perezoso» se dejaron como válidas (en español se dice «oso hormiguero» y «oso perezoso») | — |
| E9 | P18 baño sin celular | «Nunca meto el celular» (5) se dejó como respuesta | — |
| E10 | P52 incógnito | «Trabajo» (2) se interpretó como «buscar otro trabajo» | — |

---

## F. Sonidos: origen y licencia

- **Referencia que enviaste** (myinstants, «Correcto - 100 mexicanos dijeron»): la revisé. Es un clip subido por un usuario («kevin7279»), **sin ninguna licencia indicada**, y por su nombre proviene del programa de televisión *100 Mexicanos Dijeron*, que tiene derechos de autor. Como no puedo verificar que se pueda reutilizar, **no lo descargué ni lo incorporé**.
- **Lo que usa el juego:** todos los efectos y la música de entrada son **originales**, sintetizados en el navegador con Web Audio (`app/web/js/sonidos.js`). Están inspirados en el estilo de concurso (un «¡ding-ding!» alegre para la respuesta correcta, un timbre de error, aplausos, fanfarrias), pero no copian ningún sonido existente. No hay archivos de audio, servicios externos ni costos.
- Si en el futuro quieres usar un sonido grabado, elige uno con licencia libre verificada (por ejemplo CC0) y guárdalo junto con su licencia. Puedo integrarlo.

---

## G. Preguntas poco jugables

Con la configuración por defecto, estas tienen menos de 3 casillas con 2 o más personas:
- **P20:** «Aló» 30, «Hola» 6.
- **P25:** casi todas las respuestas son únicas.
- **P39:** «Borrarla» 32.
- **P47:** casi todas las respuestas son únicas.

**P4** («Había trancón», 88 de 100 puntos) y **P14** («Médico», 82 de 100) tienen una respuesta dominante: el cara a cara se decide casi siempre con la primera respuesta.

---

## H. Otras notas

- La numeración del formulario salta del 48 al 50 (no existe la pregunta 49). Se conservó la numeración original.
- La columna «Nombre» del Excel no se usa ni se muestra. La trazabilidad usa el **número de fila**.
- Los textos de las preguntas se muestran tal cual están en el Excel (por ejemplo «Que excusa comun…»). Si quieres corregir su ortografía, dímelo y lo ajusto sin tocar el Excel.
- **Python:** en este computador hay dos Python (3.14 y 3.12). Los `.bat` usan siempre el entorno del proyecto (`.venv`), con `openpyxl` 3.1.5 instalado según `requirements.txt`.
