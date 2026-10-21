# Historial de cambios

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/). Versiones según [SemVer](https://semver.org/lang/es/).

## [1.4.0] — 2026-10-21

### Añadido
- Identidad **100 Dijeron**: logo e icono originales (SVG), títulos de las páginas, portada, inicio y panel.
- **Cara a cara con reglas automáticas:** turno para quien levantó la mano primero en Meet, la respuesta n.º 1 gana de inmediato, la respuesta de referencia que el rival debe superar, regla de empate configurable (desempate o «gana el primero»), 2 intentos por líder, cambio de ambos líderes si los dos fallan, animación del ganador con su motivo y corrección del ganador antes de empezar la ronda.
- Botón **«Omitir cara a cara»**: el organizador elige qué equipo empieza.
- **Revisión de jugabilidad:** cada pregunta habilitada tiene de 4 a 10 respuestas. Las que no llegan quedan pendientes, con detalle y propuesta, en `docs/REVISION_DE_PREGUNTAS.md` y en la hoja «Jugabilidad».
- **Ejemplos de respuestas aceptadas** (textos reales de la encuesta) y **criterio para aceptar variantes** en el panel, el JSON y el Excel consolidado.
- Documentos: `REGLAS_CARA_A_CARA.md`, `DICCIONARIO_DE_DATOS.md`, `PREGUNTAS_PENDIENTES.md` y `PRUEBAS.md`.
- Pruebas: `test_cara_a_cara.py` y `test_datos_e_identidad.py`.

### Cambiado
- Nombre del proyecto: «100 Dijeron» (se retiró el nombre anterior).
- P4 y P26: se unieron respuestas que expresan la misma idea para llegar a 4 respuestas.
- Ortografía de 12 preguntas corregida (`texto_juego`); el texto original se conserva.
- Solo las preguntas habilitadas entran en la mezcla (se quitó la opción de incluir preguntas poco jugables).

### Privacidad
- Los nombres de personas mencionadas en respuestas se reemplazan por «[nombre]». La lista está en `datos/privado/`, que no se publica.

## [1.3.0] — 2026-10-21

### Añadido
- Licencia MIT, este historial de cambios, `docs/ARQUITECTURA.md` y `datos/README.md`.
- Pruebas automáticas en GitHub Actions en cada cambio.
- Capturas de pantalla en `docs/img/`.
- Documentación en el código: descripción de cada función de Python y JavaScript.

### Cambiado
- Estructura de carpetas: documentación en `docs/`, estilos en `app/web/css/`, scripts de las páginas en `app/web/js/` y preparación del entorno en `scripts/`.
- README rediseñado.

## [1.2.0] — 2026-10-21

### Añadido
- Pestaña **Preparación**: registro de participantes (uno por uno o lista pegada), sorteo animado de equipos, mezcla aleatoria de preguntas, rondas principales y adicionales con multiplicador, validaciones y confirmación.
- **Ruleta de líderes** antes de cada ronda, sin repetir dentro de cada ciclo. Indica cuando un equipo agotó a sus integrantes y anuncia los ciclos nuevos.
- Rondas extra con animación especial y valor máximo visible (×2 = hasta 200 pts).
- Cancelar una ronda y revertir el sorteo de líderes sin perder el historial.
- Sonidos de ruleta, revelación del líder, sorteo de equipos, mezcla, ronda extra y nuevo ciclo.

### Cambiado
- **Cada pregunta reparte exactamente 100 puntos** entre las respuestas de su tablero (método del resto mayor, conservando empates).
- El tablero (2+ personas, máximo 8 respuestas) queda fijado en los datos procesados.

## [1.1.0] — 2026-10-21

### Añadido
- Efectos de sonido y música de entrada originales, con control de volumen.
- Tratamiento de contenido: humor adulto conservado, respuestas discriminatorias en revisión, reformulaciones mínimas documentadas.
- Entorno de Python del proyecto (`.venv` + `requirements.txt`) y sincronización por «espera larga».

### Corregido
- `ModuleNotFoundError: openpyxl` al ejecutar las pruebas con otro intérprete de Python.

## [1.0.0] — 2026-10-21

### Añadido
- Primera versión: procesamiento del Excel de la encuesta, pantalla pública y panel privado sincronizados, cara a cara, strikes, robo, deshacer, guía de usuario, guion para presentadores y pruebas automáticas.
