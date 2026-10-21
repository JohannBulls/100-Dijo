# Pruebas

## Cómo ejecutarlas

```bat
EJECUTAR_PRUEBAS.bat
```

o, desde la carpeta del proyecto:

```bat
.venv\Scripts\python.exe -m unittest discover -s pruebas -v
```

En GitHub Actions se ejecutan en cada cambio (Windows y Linux, Python 3.12 y 3.14). Allí no están el Excel original ni `datos/privado/`, así que las pruebas que los necesitan se omiten con un aviso.

## Archivos

| Archivo | Qué verifica |
|---|---|
| `pruebas/test_juego.py` | Motor: preparación, sorteos de equipos y líderes, ciclos, rondas principales y extra, puntuación, strikes, robo, deshacer, doble clic, audio y privacidad de la pantalla pública. |
| `pruebas/test_cara_a_cara.py` | Reglas del cara a cara (ver [REGLAS_CARA_A_CARA.md](REGLAS_CARA_A_CARA.md)). |
| `pruebas/test_datos_e_identidad.py` | Datos publicados (4 a 10 respuestas, 100 puntos, trazabilidad, ejemplos reales) e identidad «100 Dijeron». No necesita el Excel. |
| `pruebas/test_procesamiento_y_servidor.py` | Procesamiento del Excel original (si está presente) y servidor HTTP de punta a punta. |

## Requisitos de la versión 1.4 y su prueba

| # | Requisito | Prueba |
|---|---|---|
| 1 | La interfaz se identifica como «100 Dijeron» | `PruebasIdentidad.test_paginas_con_el_nombre_100_dijeron`, `test_titulo_por_defecto_del_motor` |
| 2 | No quedan referencias al nombre anterior | `PruebasIdentidad.test_no_quedan_referencias_al_nombre_anterior` |
| 3 | P20, P25, P39 y P47 fueron revisadas | `test_preguntas_de_las_capturas_revisadas` |
| 4 | Cada pregunta habilitada tiene de 4 a 10 respuestas | `test_habilitadas_tienen_de_4_a_10_respuestas_que_suman_100`, `test_pendientes_estan_deshabilitadas_y_tienen_propuesta` |
| 5 | Trazabilidad con el Excel original | `test_trazabilidad_cada_respuesta_viene_de_originales`, `test_cada_respuesta_original_se_cuenta_exactamente_una_vez` |
| 6 | Los ejemplos aceptados salen de respuestas reales | `test_ejemplos_aceptados_salen_de_respuestas_reales` |
| 7 | Cada tablero suma 100 | `test_habilitadas_tienen_de_4_a_10_respuestas_que_suman_100`, `test_cada_pregunta_habilitada_suma_exactamente_100` |
| 8 | Solo responde el líder que levantó la mano primero | `test_primero_en_levantar_la_mano_tiene_el_turno`, `test_se_puede_corregir_la_mano_antes_de_responder` |
| 9 | La respuesta n.º 1 gana de inmediato | `test_respuesta_numero_uno_gana_de_inmediato` |
| 10 | Una respuesta válida menor da el turno al otro líder | `test_respuesta_valida_menor_queda_como_referencia_y_responde_el_otro`, `test_primero_falla_y_el_segundo_responde` |
| 11 | El segundo gana si supera la referencia | `test_segundo_supera_y_gana` |
| 12 | El primero gana si el segundo no la supera o falla | `test_segundo_no_supera_y_gana_el_primero`, `test_segundo_no_esta_y_gana_el_primero`, `test_referencia_sin_intentos_del_rival_gana_directo` |
| 13 | Empates | `PruebasEmpate` (desempate por defecto, «gana el primero» configurable, valor inválido) |
| 14 | Máximo 2 errores por líder y cambio de ambos líderes | `test_maximo_dos_errores_por_lider_y_bloqueo`, `test_cambio_de_ambos_lideres_y_repetir` |
| 15 | Los errores del cara a cara no son strikes | `test_errores_del_cara_a_cara_no_son_strikes` |
| 16 | Omitir el cara a cara | `PruebasOmitir` |
| 17 | Jugar o pasar, robo y rondas extra | `test_jugar_o_pasar_tras_el_cara_a_cara`, `test_robo_tras_cara_a_cara_sin_duplicar_puntos`, `PruebasRondaExtra` |
| 18 | Privacidad de la pantalla pública | `PruebasPrivacidad`, `test_18_vista_publica_no_contiene_informacion_privada`, `test_sin_nombres_de_personas_en_datos_publicados`, `test_nada_privado_se_publica` |
| 19 | Correcciones sin pérdida ni duplicación | `test_correccion_del_ganador_antes_de_empezar`, `test_deshacer_respuesta_del_cara_a_cara`, `test_historial_registra_el_cara_a_cara`, `PruebasDeshacer` |

## Prueba manual recomendada antes de la reunión

1. `INICIAR_JUEGO.bat`, abre el panel y la pantalla pública.
2. Prepara una partida de prueba con 4 nombres inventados.
3. En una ronda: marca la mano, registra una respuesta que no es la n.º 1, luego una mayor del otro líder, y comprueba el anuncio del ganador.
4. En otra ronda: registra 4 «No está» seguidos, pulsa «Cambiar a ambos líderes» y comprueba la ruleta.
5. En otra: usa «Omitir cara a cara».
6. Al terminar, usa «Nueva partida» en el panel.
