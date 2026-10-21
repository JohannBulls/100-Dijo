# Reglas del cara a cara

El cara a cara decide qué equipo controla la ronda. El juego aplica estas reglas solo: el copiloto únicamente registra **quién levantó la mano primero** y **qué respondió cada líder**. El código está en `app/juego.py` (bloque «Cara a cara») y las pruebas en `pruebas/test_cara_a_cara.py`.

## Resumen

| Situación | Resultado |
|---|---|
| El líder con el turno dice la **respuesta n.º 1** del tablero | Gana su equipo de inmediato (motivo «numero_uno»). |
| Dice **otra respuesta válida** y aún no hay referencia | Esa respuesta queda como **referencia**. Responde el otro líder, que debe **superarla en puntos**. |
| El otro líder da una respuesta que vale **más** | Gana el otro líder («supera»). |
| El otro líder da una respuesta que vale **menos** | Gana el equipo de la referencia («no_supera»). |
| El otro líder dice algo que **no está** | Gana el equipo de la referencia («no_supera») y se le anota un error. |
| Dice algo que **no está** y aún no hay referencia | Se le anota un error y responde el otro líder. |
| Hay referencia y el rival **ya agotó sus 2 intentos** | Gana el equipo de la referencia («rival_sin_intentos»). |
| **Empate** en puntos | Según la opción «Empate en el cara a cara» (ver abajo). |
| Los dos líderes **agotan sus 2 intentos** | Cara a cara bloqueado: hay que **cambiar a ambos líderes** y repetir. |

## Paso a paso

1. **Quién responde primero.** El presentador lee la pregunta y los líderes levantan la mano en Google Meet. El copiloto marca en el panel el equipo cuyo líder levantó la mano primero. Ese líder tiene el turno («▶ LE TOCA RESPONDER»). Se puede corregir mientras ningún líder haya respondido; después, se usa «Deshacer».
2. **Solo responde quien tiene el turno.** El panel solo muestra el botón «Lo dijo [equipo]» del equipo con el turno, y el motor rechaza respuestas fuera de turno.
3. **Respuesta válida.** Se revela en el tablero y sus puntos entran al banco una sola vez (multiplicados en una ronda extra).
4. **Respuesta que no está.** Cuenta como **error del cara a cara** (máximo 2 por líder). La pantalla pública muestra «Error n de 2» y las ✗ bajo el nombre del líder.
5. **Ganador.** Aparece la animación del equipo ganador con el motivo. Si la opción «jugar o pasar» está activa, el equipo decide; si no, juega directamente.

## Empates

Dos respuestas distintas pueden valer lo mismo (por ejemplo, dos respuestas que dijeron 4 personas cada una). La regla se elige en **Reglas y opciones → Empate en el cara a cara**, solo antes de empezar o entre rondas:

- **Nueva respuesta de desempate** (por defecto): se borra la referencia y vuelve a responder primero quien levantó la mano primero (si aún tiene intentos). Las casillas reveladas siguen visibles. Si ya no quedan casillas ocultas, gana quien respondió primero.
- **Gana quien respondió primero.**

## Errores y cambio de líderes

- Cada líder tiene **2 intentos** (`ERRORES_MAX_CARA_A_CARA = 2`).
- Si un líder agota sus intentos, el turno queda en el otro líder mientras tenga intentos.
- Si **ambos** llegan a 2 errores sin ganador, el cara a cara queda **bloqueado**. El panel muestra **«🎡 Cambiar a ambos líderes y repetir»**: el servidor sortea un líder nuevo en cada equipo (distinto del actual, de preferencia alguien que no haya sido líder en el ciclo), la pantalla pública muestra la ruleta «¡Cambio de líderes!», y el cara a cara empieza de cero (mano, turno, referencia y errores). El cambio queda en el historial de líderes con el motivo «cambio en el cara a cara».
- Los errores del cara a cara **no son strikes**: la ronda empieza con 0 strikes, y los strikes tampoco cambian los errores del cara a cara.

## Omitir el cara a cara

Mientras los líderes actuales no hayan respondido y no haya casillas reveladas (también justo después de un cambio de líderes), el panel ofrece **«⏭ Omitir cara a cara: empieza [equipo]»**. No se revela ninguna respuesta, no se registran errores, y la ronda empieza con el equipo elegido (sin «jugar o pasar»). En el historial queda `omitido: true`.

## Correcciones del presentador

- **Elegir el ganador manualmente** (para disputas): disponible durante el cara a cara.
- **Corregir el ganador**: en la pantalla «¿juega o pasa?», antes de que empiece la ronda. Pasa el cara a cara al otro equipo sin tocar el banco: nada se pierde ni se suma dos veces.
- **Deshacer**: revierte la última acción, incluida una respuesta del cara a cara mal registrada.

## Qué ve la pantalla pública

Turno actual, referencia (equipo y puntos, sin decir cuál respuesta queda oculta), errores de cada líder, empate, bloqueo, cambio de líderes y ganador con su motivo. Nunca recibe respuestas ocultas.

## Historial

Cada ronda del historial guarda un resumen: `{"ganador", "motivo", "omitido", "errores", "cambios_lider"}`.
