"""Pruebas de las reglas del cara a cara (ver docs/REGLAS_CARA_A_CARA.md).

Tablero de prueba (ver test_juego.py): Alfa 46 · Beta 27 · Gamma 18 · Delta 9 (Épsilon fuera del tablero).
"""
import copy
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_juego import A, B, D, G, PREGUNTAS, R, Base, nuevo_juego  # noqa: E402
from juego import ErrorJuego  # noqa: E402
from procesar_excel import repartir_100  # noqa: E402


def preguntas_con_empate():
    """Variante con dos respuestas que valen lo mismo (frecuencias 10, 4, 4, 2) para probar el empate."""
    preguntas = copy.deepcopy(PREGUNTAS)
    puntos = repartir_100([10, 4, 4, 2])
    for p in preguntas:
        tablero = [a for a in p["respuestas"] if a["en_tablero"]]
        for a, f, pts in zip(tablero, [10, 4, 4, 2], puntos):
            a.update(frecuencia=f, puntos=pts)
    return preguntas, puntos


class BaseCaraACara(Base):
    """Ronda iniciada en fase de cara a cara, con los líderes ya sorteados."""

    def setUp(self):
        super().setUp()
        self.a(tipo="sortear_lideres")
        self.a(tipo="iniciar_ronda", pregunta_id="p01")

    @property
    def r(self):
        return self.j.estado["ronda"]

    @property
    def cac(self):
        return self.r["cara_a_cara"]

    def responde(self, equipo, i=None):
        return self.a(tipo="respuesta_cara_a_cara", equipo=equipo, respuesta_id=R("p01", i) if i else None)


class PruebasGanador(BaseCaraACara):
    def test_primero_en_levantar_la_mano_tiene_el_turno(self):
        self.assertIsNone(self.cac["turno"])
        with self.assertRaises(ErrorJuego):          # nadie responde antes de marcar quién levantó la mano
            self.responde(0, 2)
        self.a(tipo="primero_en_responder", equipo=1)
        self.assertEqual((self.cac["primero"], self.cac["turno"]), (1, 1))
        with self.assertRaises(ErrorJuego):          # el otro líder no puede responder fuera de turno
            self.responde(0, 2)

    def test_se_puede_corregir_la_mano_antes_de_responder(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.a(tipo="primero_en_responder", equipo=1)
        self.assertEqual(self.cac["turno"], 1)
        self.responde(1, 3)
        with self.assertRaises(ErrorJuego):
            self.a(tipo="primero_en_responder", equipo=0)

    def test_respuesta_numero_uno_gana_de_inmediato(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 1)
        self.assertEqual(self.j.estado["fase"], "decision")
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (0, "numero_uno"))
        self.assertEqual(self.r["banco"], A)
        self.assertEqual(self.j.estado["evento"]["tipo"], "cara_a_cara_ganado")

    def test_respuesta_valida_menor_queda_como_referencia_y_responde_el_otro(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 3)                          # Gamma 18
        self.assertEqual(self.j.estado["fase"], "cara_a_cara")
        self.assertEqual(self.cac["referencia"], {"equipo": 0, "puntos": G, "respuesta_id": R("p01", 3)})
        self.assertEqual(self.cac["turno"], 1)

    def test_segundo_supera_y_gana(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 3)                          # 18
        self.responde(1, 2)                          # 27 > 18
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (1, "supera"))
        self.assertEqual(self.r["banco"], G + B)     # ambas casillas reveladas suman una sola vez

    def test_segundo_no_supera_y_gana_el_primero(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 2)                          # 27
        self.responde(1, 4)                          # 9 < 27
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (0, "no_supera"))

    def test_segundo_no_esta_y_gana_el_primero(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 4)
        self.responde(1)
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (0, "no_supera"))
        self.assertEqual(self.cac["errores"], [0, 1])

    def test_primero_falla_y_el_segundo_responde(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0)
        self.assertEqual((self.cac["errores"], self.cac["turno"]), ([1, 0], 1))
        self.responde(1, 4)                          # 9: queda como referencia, ahora el primero debe superarla
        self.assertEqual((self.cac["referencia"]["equipo"], self.cac["turno"]), (1, 0))
        self.responde(0, 3)                          # 18 > 9
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (0, "supera"))

    def test_referencia_sin_intentos_del_rival_gana_directo(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0)
        self.responde(1)
        self.responde(0)                             # el líder 0 agotó sus 2 intentos
        self.assertEqual(self.cac["turno"], 1)
        self.responde(1, 4)                          # válida y el rival ya no puede responder
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (1, "rival_sin_intentos"))

    def test_correccion_del_ganador_antes_de_empezar(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 1)
        banco = self.r["banco"]
        self.a(tipo="corregir_ganador_cara_a_cara")
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (1, "correccion"))
        self.assertEqual(self.r["banco"], banco)     # corregir no duplica ni pierde puntos
        self.a(tipo="decidir", jugar=True)
        self.assertEqual(self.r["control"], 1)
        with self.assertRaises(ErrorJuego):          # una vez empezada la ronda ya no se corrige
            self.a(tipo="corregir_ganador_cara_a_cara")

    def test_ganador_manual(self):
        self.a(tipo="ganador_cara_a_cara", equipo=1)
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (1, "manual"))


class PruebasEmpate(BaseCaraACara):
    def setUp(self):
        preguntas, self.puntos = preguntas_con_empate()
        self.assertEqual(self.puntos[1], self.puntos[2])
        self.j = nuevo_juego(preguntas=preguntas)
        self.a(tipo="configurar", cambios={"equipos": [{"nombre": "Azules"}, {"nombre": "Naranjas"}]})
        self.preparar(self.PARTICIPANTES)

    def iniciar(self):
        self.a(tipo="sortear_lideres")
        self.a(tipo="iniciar_ronda", pregunta_id="p01")

    def test_empate_con_desempate_por_defecto(self):
        self.assertEqual(self.j.cfg["empate_cara_a_cara"], "desempate")
        self.iniciar()
        self.a(tipo="primero_en_responder", equipo=1)
        self.responde(1, 2)
        self.responde(0, 3)                          # mismos puntos
        self.assertEqual(self.j.estado["fase"], "cara_a_cara")
        self.assertEqual(self.j.estado["evento"]["tipo"], "empate_cara_a_cara")
        self.assertIsNone(self.cac["referencia"])
        self.assertEqual(self.cac["turno"], 1)       # desempata primero quien levantó la mano primero
        self.responde(1, 4)
        self.responde(0)                             # el rival no supera la nueva referencia
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (1, "no_supera"))

    def test_empate_gana_quien_respondio_primero_si_se_configura(self):
        self.a(tipo="configurar", cambios={"empate_cara_a_cara": "primero"})   # se configura entre rondas
        self.iniciar()
        self.a(tipo="primero_en_responder", equipo=1)
        self.responde(1, 2)
        self.responde(0, 3)
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (1, "empate_primero"))

    def test_regla_de_empate_invalida(self):
        with self.assertRaises(ErrorJuego):
            self.a(tipo="configurar", cambios={"empate_cara_a_cara": "moneda"})


class PruebasErroresYCambioDeLideres(BaseCaraACara):
    def bloquear(self):
        self.a(tipo="primero_en_responder", equipo=0)
        for eq in (0, 1, 0, 1):
            self.responde(eq)

    def test_maximo_dos_errores_por_lider_y_bloqueo(self):
        self.bloquear()
        self.assertEqual(self.cac["errores"], [2, 2])
        self.assertTrue(self.cac["bloqueado"])
        self.assertIsNone(self.cac["turno"])
        self.assertEqual(self.j.estado["evento"]["tipo"], "cara_a_cara_bloqueado")
        for eq in (0, 1):
            with self.assertRaises(ErrorJuego):
                self.responde(eq, 2)

    def test_cambio_de_ambos_lideres_y_repetir(self):
        with self.assertRaises(ErrorJuego):          # solo cuando ambos agotaron sus intentos
            self.a(tipo="cambiar_lideres_cara_a_cara")
        antes = list(self.r["lideres"])
        self.bloquear()
        self.a(tipo="cambiar_lideres_cara_a_cara")
        despues = self.r["lideres"]
        for i in (0, 1):
            self.assertNotEqual(antes[i], despues[i])
            self.assertIn(despues[i], self.j.cfg["equipos"][i]["integrantes"])
        self.assertEqual(self.j.estado["lideres"]["actuales"], despues)
        self.assertEqual(self.cac["errores"], [0, 0])
        self.assertEqual((self.cac["primero"], self.cac["turno"], self.cac["bloqueado"]), (None, None, False))
        self.assertEqual(self.cac["cambios_lider"], 1)
        ev = self.j.estado["evento"]
        self.assertEqual((ev["tipo"], ev["extra"]["motivo"]), ("sorteo_lideres", "cambio_cara_a_cara"))
        cambios = [h for h in self.j.estado["lideres"]["historial"] if h.get("motivo")]
        self.assertEqual(len(cambios), 2)
        # Se repite el cara a cara con los líderes nuevos
        self.a(tipo="primero_en_responder", equipo=1)
        self.responde(1, 1)
        self.assertEqual((self.cac["ganador"], self.cac["motivo"]), (1, "numero_uno"))

    def test_errores_del_cara_a_cara_no_son_strikes(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0)
        self.responde(1)
        self.responde(0, 4)
        self.responde(1)                             # 3 errores en total + gana el equipo 0
        self.assertEqual(self.cac["errores"], [1, 2])
        self.assertEqual(self.r["strikes"], 0)
        self.a(tipo="decidir", jugar=True)
        self.a(tipo="strike")
        self.assertEqual(self.r["strikes"], 1)
        self.assertEqual(self.cac["errores"], [1, 2])  # los strikes tampoco tocan los errores del cara a cara

    def test_historial_registra_el_cara_a_cara(self):
        self.bloquear()
        self.a(tipo="cambiar_lideres_cara_a_cara")
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 1)
        self.a(tipo="decidir", jugar=True)
        for i in (2, 3, 4):
            self.a(tipo="revelar", respuesta_id=R("p01", i))
        self.a(tipo="asignar_banco")
        h = self.j.estado["historial_rondas"][-1]
        self.assertEqual(h["cara_a_cara"], {"ganador": 0, "motivo": "numero_uno", "omitido": False,
                                            "errores": [0, 0], "cambios_lider": 1})
        self.assertEqual(h["puntos"], 100)


class PruebasOmitir(BaseCaraACara):
    def test_omitir_cara_a_cara(self):
        self.a(tipo="omitir_cara_a_cara", equipo=1)
        self.assertEqual(self.j.estado["fase"], "juego")
        self.assertEqual(self.r["control"], 1)
        self.assertEqual(self.r["reveladas"], [] if isinstance(self.r["reveladas"], list) else {})
        self.assertEqual((self.r["banco"], self.cac["errores"]), (0, [0, 0]))
        self.assertTrue(self.cac["omitido"])

    def test_no_se_omite_si_ya_hubo_respuestas(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0)
        with self.assertRaises(ErrorJuego):
            self.a(tipo="omitir_cara_a_cara", equipo=0)

    def test_se_puede_omitir_tras_cambiar_a_los_lideres(self):
        self.a(tipo="primero_en_responder", equipo=0)
        for eq in (0, 1, 0, 1):
            self.responde(eq)
        with self.assertRaises(ErrorJuego):          # bloqueado: primero hay que cambiar a los líderes
            self.a(tipo="omitir_cara_a_cara", equipo=0)
        self.a(tipo="cambiar_lideres_cara_a_cara")
        self.a(tipo="omitir_cara_a_cara", equipo=0)
        self.assertEqual((self.j.estado["fase"], self.r["control"], self.r["strikes"]), ("juego", 0, 0))

    def test_no_se_omite_si_hay_casillas_reveladas(self):
        preguntas, _ = preguntas_con_empate()
        self.j = nuevo_juego(preguntas=preguntas)
        self.a(tipo="configurar", cambios={"equipos": [{"nombre": "Azules"}, {"nombre": "Naranjas"}]})
        self.preparar(self.PARTICIPANTES)
        self.a(tipo="sortear_lideres")
        self.a(tipo="iniciar_ronda", pregunta_id="p01")
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 2)
        self.responde(1, 3)                          # empate: desempate con casillas ya reveladas
        self.responde(0)
        self.responde(1)
        self.responde(0)
        self.responde(1)                             # ambos agotaron sus intentos
        self.a(tipo="cambiar_lideres_cara_a_cara")
        with self.assertRaises(ErrorJuego):
            self.a(tipo="omitir_cara_a_cara", equipo=0)

    def test_ronda_omitida_se_juega_completa(self):
        self.a(tipo="omitir_cara_a_cara", equipo=0)
        for i in (1, 2):
            self.a(tipo="revelar", respuesta_id=R("p01", i))
        for _ in range(3):
            self.a(tipo="strike")
        self.a(tipo="resolver_robo", respuesta_id=R("p01", 3))   # robo exitoso del equipo 1
        self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [0, A + B + G])
        self.assertTrue(self.j.estado["historial_rondas"][-1]["cara_a_cara"]["omitido"])


class PruebasJugarPasarRoboYExtra(BaseCaraACara):
    def test_jugar_o_pasar_tras_el_cara_a_cara(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 2)
        self.responde(1, 4)
        self.assertEqual(self.cac["ganador"], 0)
        self.a(tipo="decidir", jugar=False)
        self.assertEqual(self.r["control"], 1)

    def test_robo_tras_cara_a_cara_sin_duplicar_puntos(self):
        self.a(tipo="primero_en_responder", equipo=1)
        self.responde(1, 3)
        self.responde(0, 2)                          # gana 0 (27 > 18); banco 45
        self.a(tipo="decidir", jugar=True)
        for _ in range(3):
            self.a(tipo="strike")
        with self.assertRaises(ErrorJuego):          # una casilla ya revelada no se puede robar otra vez
            self.a(tipo="resolver_robo", respuesta_id=R("p01", 2))
        self.a(tipo="resolver_robo", respuesta_id=R("p01", 1))
        self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [0, B + G + A])

    def test_deshacer_respuesta_del_cara_a_cara(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 3)
        self.a(tipo="deshacer")
        self.assertEqual((self.r["banco"], self.cac["intentos"], self.cac["referencia"]), (0, [], None))
        self.assertEqual(self.cac["turno"], 0)
        self.responde(0, 3)
        self.assertEqual(self.r["banco"], G)


class PruebasRondaExtra(Base):
    EXTRA = 1
    MULTIPLICADORES = [2]

    def test_cara_a_cara_en_ronda_extra_con_multiplicador(self):
        for _ in range(2):
            self.jugar_ronda()
        pid = self.j.siguiente_pregunta()
        self.a(tipo="sortear_lideres")
        self.a(tipo="iniciar_ronda", pregunta_id=pid)
        r = self.j.estado["ronda"]
        self.assertEqual((r["tipo"], r["multiplicador"]), ("extra", 2))
        self.a(tipo="primero_en_responder", equipo=0)
        self.a(tipo="respuesta_cara_a_cara", equipo=0, respuesta_id=R(pid, 4))
        self.a(tipo="respuesta_cara_a_cara", equipo=1, respuesta_id=R(pid, 1))  # n.º 1 gana aunque haya referencia
        self.assertEqual((r["cara_a_cara"]["ganador"], r["cara_a_cara"]["motivo"]), (1, "numero_uno"))
        self.assertEqual(r["banco"], 2 * (D + A))


class PruebasPrivacidad(BaseCaraACara):
    def test_vista_publica_del_cara_a_cara(self):
        self.a(tipo="primero_en_responder", equipo=0)
        self.responde(0, 3)
        pub = self.j.vista_publica()
        cac = pub["ronda"]["cara_a_cara"]
        self.assertEqual(cac["referencia"], {"equipo": 0, "puntos": G})   # sin el id de la respuesta
        self.assertEqual((cac["turno"], cac["errores"]), (1, [0, 0]))
        texto = json.dumps(pub, ensure_ascii=False)
        self.assertNotIn(R("p01", 3), texto)
        for oculta in ("Alfa 1", "Beta 1", "Delta 1"):
            self.assertNotIn(oculta, texto)
        self.assertIn("Gamma 1", texto)


if __name__ == "__main__":
    unittest.main()
