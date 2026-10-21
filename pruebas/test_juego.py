"""Pruebas del motor del juego: preparación, sorteos, líderes, rondas, puntuación y deshacer."""
import collections
import copy
import json
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app"))
from juego import ErrorJuego, Juego  # noqa: E402
from procesar_excel import repartir_100  # noqa: E402

FRECUENCIAS = [("Alfa", 10), ("Beta", 6), ("Gamma", 4), ("Delta", 2), ("Épsilon", 1)]
TOTAL = sum(f for _, f in FRECUENCIAS)
# El tablero (2+ personas) reparte 100 puntos: 46, 27, 18 y 9. Épsilon queda fuera y no puntúa.
A, B, G, D = repartir_100([f for _, f in FRECUENCIAS[:4]])


def pregunta_prueba(numero):
    pid = f"p{numero:02d}"
    respuestas = []
    for i, (e, f) in enumerate(FRECUENCIAS, 1):
        en_tablero = f >= 2
        respuestas.append({"id": f"{pid}-r{i}", "etiqueta": f"{e} {numero}", "frecuencia": f,
                           "puntos": [A, B, G, D][i - 1] if en_tablero else 0, "en_tablero": en_tablero,
                           "motivo_fuera": None if en_tablero else "Menos de 2 personas", "nota": None,
                           "reformulacion": None, "revision_contenido": None, "nota_contenido": None,
                           "originales": [{"fila": 3 + k, "texto": e} for k in range(f)]})
    return {"id": pid, "numero": numero, "texto": f"Pregunta de prueba {numero}", "respuestas_validas": TOTAL,
            "respuestas_excluidas": 0, "excluidas": [], "revision": [], "habilitada": True, "jugable": True,
            "puntos_tablero": 100, "respuestas": respuestas}


PREGUNTAS = [pregunta_prueba(n) for n in range(1, 31)]
NOMBRES_20 = ["Ana", "Luis", "Carolina", "Pedro", "Sofía", "Daniel", "Marcela", "Jorge", "Paula", "Andrés",
              "Camila", "Felipe", "Laura", "Santiago", "Valentina", "Mateo", "Juliana", "Sebastián", "Natalia", "Tomás"]
R = lambda pid, i: f"{pid}-r{i}"  # noqa: E731


def nuevo_juego(semilla=7, preguntas=PREGUNTAS):
    return Juego(copy.deepcopy(preguntas), rng=random.Random(semilla))


class Base(unittest.TestCase):
    """Partida preparada con 4 participantes (2 contra 2) y, por defecto, sin rondas adicionales."""
    PARTICIPANTES = ["Ana", "Luis", "Carolina", "Pedro"]
    EXTRA = 0
    MULTIPLICADORES = []

    def setUp(self):
        self.j = nuevo_juego()
        self.a(tipo="configurar", cambios={"equipos": [{"nombre": "Azules"}, {"nombre": "Naranjas"}]})
        self.preparar(self.PARTICIPANTES, self.EXTRA, self.MULTIPLICADORES)

    def a(self, **accion):
        return self.j.aplicar(accion, self.j.estado["version"])

    def preparar(self, nombres, extra=0, multiplicadores=(), principales=None):
        self.a(tipo="agregar_participantes", nombres=list(nombres))
        self.a(tipo="sortear_equipos")
        self.a(tipo="mezclar_preguntas")
        self.a(tipo="configurar_partida", rondas_principales=principales, rondas_extra=extra,
               multiplicadores_extra=list(multiplicadores))
        self.a(tipo="confirmar_partida")

    def ronda_hasta_juego(self, pregunta="p01", ganador=0, jugar=True):
        self.a(tipo="sortear_lideres")
        self.a(tipo="iniciar_ronda", pregunta_id=pregunta)
        self.a(tipo="primero_en_responder", equipo=ganador)
        self.a(tipo="respuesta_cara_a_cara", equipo=ganador, respuesta_id=pregunta + "-r2")  # Beta
        self.a(tipo="ganador_cara_a_cara", equipo=ganador)
        self.a(tipo="decidir", jugar=jugar)

    def jugar_ronda(self, pregunta=None, ganador_cac=0, robo_ok=False):
        pregunta = pregunta or self.j.siguiente_pregunta()
        self.ronda_hasta_juego(pregunta, ganador_cac)
        for _ in range(3):
            self.a(tipo="strike")
        self.a(tipo="resolver_robo", respuesta_id=pregunta + "-r1" if robo_ok else None)
        self.a(tipo="asignar_banco")


# ====================================================================== puntuación y ronda
class PruebasRonda(Base):
    def test_tablero_de_prueba_suma_100(self):
        self.assertEqual((A, B, G, D), (46, 27, 18, 9))
        self.assertEqual(A + B + G + D, 100)

    def test_tablero_viene_del_archivo_procesado(self):
        self.a(tipo="sortear_lideres")
        self.a(tipo="iniciar_ronda", pregunta_id="p01")
        self.assertEqual(self.j.estado["ronda"]["tablero"], [R("p01", 1), R("p01", 2), R("p01", 3), R("p01", 4)])
        self.assertEqual(self.j.estado["fase"], "cara_a_cara")

    def test_banco_usa_los_puntos_del_archivo(self):
        self.ronda_hasta_juego()
        self.assertEqual(self.j.estado["ronda"]["banco"], B)

    def test_respuesta_correcta_revela_y_suma_al_banco(self):
        self.ronda_hasta_juego()
        self.a(tipo="revelar", respuesta_id=R("p01", 1))
        r = self.j.estado["ronda"]
        self.assertEqual(r["banco"], B + A)
        self.assertEqual(self.j.estado["puntajes"], [0, 0])  # el banco es distinto del marcador
        pub = self.j.vista_publica()["ronda"]["casillas"][0]
        self.assertEqual((pub["revelada"], pub["texto"], pub["puntos"]), (True, "Alfa 1", A))

    def test_respuesta_repetida_no_suma_dos_veces(self):
        self.ronda_hasta_juego()
        self.a(tipo="revelar", respuesta_id=R("p01", 1))
        with self.assertRaises(ErrorJuego):
            self.a(tipo="revelar", respuesta_id=R("p01", 1))
        with self.assertRaises(ErrorJuego):  # ya revelada en el cara a cara
            self.a(tipo="revelar", respuesta_id=R("p01", 2))
        self.assertEqual(self.j.estado["ronda"]["banco"], B + A)

    def test_respuesta_fuera_del_tablero_no_se_puede_revelar(self):
        self.ronda_hasta_juego()
        with self.assertRaises(ErrorJuego):
            self.a(tipo="revelar", respuesta_id=R("p01", 5))

    def test_banco_nunca_supera_100_en_ronda_principal(self):
        self.ronda_hasta_juego()
        for i in (1, 3, 4):
            self.a(tipo="revelar", respuesta_id=R("p01", i))
        self.assertEqual(self.j.estado["ronda"]["banco"], 100)
        self.assertEqual(self.j.estado["ronda"]["maximo"], 100)

    def test_incorrecta_suma_strike_sin_tocar_puntos(self):
        self.ronda_hasta_juego()
        self.a(tipo="strike")
        self.assertEqual((self.j.estado["ronda"]["strikes"], self.j.estado["ronda"]["banco"]), (1, B))
        self.a(tipo="strike")
        self.assertEqual(self.j.estado["evento"]["extra"]["strikes"], 2)

    def test_tres_strikes_habilitan_robo(self):
        self.ronda_hasta_juego(ganador=0)
        for _ in range(3):
            self.a(tipo="strike")
        self.assertEqual(self.j.estado["fase"], "robo")
        self.assertEqual(self.j.estado["ronda"]["robo"]["equipo"], 1)
        with self.assertRaises(ErrorJuego):
            self.a(tipo="strike")

    def test_robo_exitoso_da_banco_al_rival_y_no_supera_100(self):
        self.ronda_hasta_juego(ganador=0)
        self.a(tipo="revelar", respuesta_id=R("p01", 3))
        for _ in range(3):
            self.a(tipo="strike")
        self.a(tipo="resolver_robo", respuesta_id=R("p01", 1))
        self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [0, B + G + A])
        self.assertLessEqual(B + G + A, 100)

    def test_robo_fallido_conserva_banco_para_equipo_en_control(self):
        self.ronda_hasta_juego(ganador=0)
        self.a(tipo="revelar", respuesta_id=R("p01", 1))
        for _ in range(3):
            self.a(tipo="strike")
        self.a(tipo="resolver_robo", respuesta_id=None)
        self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [B + A, 0])

    def test_robo_no_se_puede_repetir(self):
        self.ronda_hasta_juego()
        for _ in range(3):
            self.a(tipo="strike")
        self.a(tipo="resolver_robo", respuesta_id=None)
        with self.assertRaises(ErrorJuego):
            self.a(tipo="resolver_robo", respuesta_id=R("p01", 1))

    def test_banco_se_asigna_una_sola_vez(self):
        self.jugar_ronda("p01")
        with self.assertRaises(ErrorJuego):
            self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [B, 0])

    def test_doble_clic_con_version_vieja_se_rechaza(self):
        self.ronda_hasta_juego()
        v = self.j.estado["version"]
        self.j.aplicar({"tipo": "revelar", "respuesta_id": R("p01", 1)}, v)
        with self.assertRaises(ErrorJuego):
            self.j.aplicar({"tipo": "strike"}, v)
        self.assertEqual(self.j.estado["ronda"]["strikes"], 0)

    def test_tablero_completo_gana_equipo_en_control(self):
        self.ronda_hasta_juego(ganador=1)
        for i in (1, 3, 4):
            self.a(tipo="revelar", respuesta_id=R("p01", i))
        self.assertEqual((self.j.estado["fase"], self.j.estado["ronda"]["ganador"]), ("resuelta", 1))
        self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [0, 100])

    def test_pasar_turno_y_sugerencia(self):
        self.ronda_hasta_juego(ganador=0, jugar=False)
        self.assertEqual(self.j.estado["ronda"]["control"], 1)

    def test_revelar_restantes_no_suma(self):
        self.jugar_ronda("p01")
        self.a(tipo="revelar_restantes")
        self.assertEqual(self.j.estado["puntajes"], [B, 0])


class PruebasDeshacer(Base):
    def test_deshacer_recupera_estado_anterior(self):
        self.ronda_hasta_juego()
        antes = json.dumps({k: v for k, v in self.j.estado.items() if k not in ("version", "bitacora", "evento")}, sort_keys=True)
        self.a(tipo="revelar", respuesta_id=R("p01", 1))
        self.a(tipo="deshacer")
        despues = json.dumps({k: v for k, v in self.j.estado.items() if k not in ("version", "bitacora", "evento")}, sort_keys=True)
        self.assertEqual(antes, despues)

    def test_deshacer_asignacion(self):
        self.jugar_ronda("p01")
        self.a(tipo="deshacer")
        self.assertEqual(self.j.estado["puntajes"], [0, 0])
        self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [B, 0])

    def test_deshacer_doble_clic_solo_deshace_una(self):
        self.ronda_hasta_juego()
        self.a(tipo="strike")
        self.a(tipo="strike")
        v = self.j.estado["version"]
        self.j.aplicar({"tipo": "deshacer"}, v)
        with self.assertRaises(ErrorJuego):
            self.j.aplicar({"tipo": "deshacer"}, v)
        self.assertEqual(self.j.estado["ronda"]["strikes"], 1)


# ====================================================================== preparación (escenarios 1-6 y 20)
class PruebasPreparacion(unittest.TestCase):
    def setUp(self):
        self.j = nuevo_juego(semilla=11)

    def a(self, **accion):
        return self.j.aplicar(accion, self.j.estado["version"])

    def test_01_registro_de_20_participantes(self):
        self.a(tipo="agregar_participantes", nombres=NOMBRES_20[:10] + ["", "  "])          # pegar lista (con vacíos)
        for n in NOMBRES_20[10:]:
            self.a(tipo="agregar_participantes", nombres=[n])                                # uno por uno
        self.assertEqual(len(self.j.prep["participantes"]), 20)
        self.a(tipo="agregar_participantes", nombres=["ana", "Nuevo"])                       # duplicado ignorado
        self.assertEqual(len(self.j.prep["participantes"]), 21)
        pid = self.j.prep["participantes"][-1]["id"]
        self.a(tipo="editar_participante", id=pid, nombre="Renombrado")
        self.assertEqual(self.j.nombre_participante(pid), "Renombrado")
        with self.assertRaises(ErrorJuego):
            self.a(tipo="editar_participante", id=pid, nombre="Luis")                        # nombre repetido
        self.a(tipo="eliminar_participante", id=pid)
        self.assertEqual(len(self.j.prep["participantes"]), 20)

    def test_02_sorteo_de_dos_equipos_de_10(self):
        self.a(tipo="agregar_participantes", nombres=NOMBRES_20)
        self.a(tipo="sortear_equipos")
        eq = [e["integrantes"] for e in self.j.cfg["equipos"]]
        self.assertEqual([len(x) for x in eq], [10, 10])
        self.assertEqual(sorted(eq[0] + eq[1]), sorted(p["id"] for p in self.j.prep["participantes"]))
        self.assertFalse(set(eq[0]) & set(eq[1]))
        self.assertEqual(self.j.minimo_principales(), 10)

    def test_03_sorteo_impar(self):
        for n in (2, 3, 7, 9, 21):
            j = nuevo_juego(semilla=n)
            j.aplicar({"tipo": "agregar_participantes", "nombres": NOMBRES_20[:n] + [f"Extra {k}" for k in range(n - 20)]})
            j.aplicar({"tipo": "sortear_equipos"})
            tam = [len(e["integrantes"]) for e in j.cfg["equipos"]]
            self.assertEqual(sum(tam), n)
            self.assertLessEqual(abs(tam[0] - tam[1]), 1, n)
            self.assertEqual(j.minimo_principales(), max(tam))

    def test_04_repetir_sorteo_antes_de_iniciar(self):
        self.a(tipo="agregar_participantes", nombres=NOMBRES_20)
        resultados = set()
        for _ in range(6):
            self.a(tipo="sortear_equipos")
            resultados.add(tuple(sorted(self.j.cfg["equipos"][0]["integrantes"])))
        self.assertGreater(len(resultados), 1)                      # el reparto cambia de un sorteo a otro
        self.assertEqual(self.j.prep["sorteo_equipos"]["id"], 6)
        self.a(tipo="mezclar_preguntas")
        self.a(tipo="confirmar_partida")
        with self.assertRaises(ErrorJuego):                         # tras iniciar, los equipos quedan fijos
            self.a(tipo="sortear_equipos")
        with self.assertRaises(ErrorJuego):
            self.a(tipo="agregar_participantes", nombres=["Tarde"])

    def test_cambiar_participantes_obliga_a_volver_a_sortear(self):
        self.a(tipo="agregar_participantes", nombres=NOMBRES_20[:6])
        self.a(tipo="sortear_equipos")
        self.a(tipo="agregar_participantes", nombres=["Nueva"])
        self.assertIsNone(self.j.prep["sorteo_equipos"])
        self.assertTrue(any("Sortear equipos" in v for v in self.j.validar_preparacion()))

    def test_05_mezcla_aleatoria_de_preguntas(self):
        self.a(tipo="mezclar_preguntas")
        orden1 = list(self.j.prep["orden_preguntas"])
        self.assertEqual(sorted(orden1), sorted(self.j.preguntas_disponibles()))  # una permutación, sin repetir
        self.assertEqual(len(orden1), len(set(orden1)))
        self.assertNotEqual(orden1, sorted(orden1))                 # no es el orden del Excel
        self.a(tipo="mezclar_preguntas")
        self.assertNotEqual(self.j.prep["orden_preguntas"], orden1)  # volver a mezclar cambia el orden
        primeras = collections.Counter()
        j = nuevo_juego(semilla=99)
        for _ in range(300):
            j.aplicar({"tipo": "mezclar_preguntas"})
            primeras[j.prep["orden_preguntas"][0]] += 1
        self.assertGreater(len(primeras), 20)                       # cualquier pregunta puede salir primera

    def test_mezcla_usa_azar_del_sistema_por_defecto(self):
        self.assertIsInstance(Juego(PREGUNTAS).rng, random.SystemRandom)

    def test_20_aviso_si_faltan_preguntas(self):
        self.a(tipo="agregar_participantes", nombres=NOMBRES_20)
        self.a(tipo="sortear_equipos")
        self.a(tipo="mezclar_preguntas")
        self.a(tipo="configurar_partida", rondas_extra=10, multiplicadores_extra=[2] * 10, rondas_principales=25)
        errores = self.j.validar_preparacion()
        self.assertTrue(any("Faltan 5 preguntas" in e for e in errores), errores)  # 35 rondas, 30 preguntas
        with self.assertRaises(ErrorJuego):
            self.a(tipo="confirmar_partida")
        self.a(tipo="configurar_partida", rondas_principales=20)
        self.assertEqual(self.j.validar_preparacion(), [])
        self.a(tipo="confirmar_partida")

    def test_no_se_puede_iniciar_sin_preparar(self):
        for accion in ({"tipo": "confirmar_partida"}, {"tipo": "sortear_lideres"}, {"tipo": "iniciar_ronda"}):
            with self.assertRaises(ErrorJuego):
                self.a(**accion)


# ====================================================================== líderes (escenarios 8-12, 17)
class PruebasLideres(unittest.TestCase):
    def preparar(self, n, principales=None, extra=0, mult=(), semilla=3):
        self.j = nuevo_juego(semilla=semilla)
        self.a(tipo="agregar_participantes", nombres=NOMBRES_20[:n])
        self.a(tipo="sortear_equipos")
        self.a(tipo="mezclar_preguntas")
        self.a(tipo="configurar_partida", rondas_principales=principales, rondas_extra=extra, multiplicadores_extra=list(mult))
        self.a(tipo="confirmar_partida")

    def a(self, **accion):
        return self.j.aplicar(accion, self.j.estado["version"])

    def jugar(self):
        """Sortea líderes y juega una ronda rápida (gana el cara a cara el equipo 0, robo fallido)."""
        self.a(tipo="sortear_lideres")
        sorteo = copy.deepcopy(self.j.estado["lideres"]["sorteo"])
        self.a(tipo="iniciar_ronda")
        self.a(tipo="ganador_cara_a_cara", equipo=0)
        self.a(tipo="decidir", jugar=True)
        for _ in range(3):
            self.a(tipo="strike")
        self.a(tipo="resolver_robo", respuesta_id=None)
        self.a(tipo="asignar_banco")
        return sorteo

    def lideres_de(self, equipo):
        return [h["participante"] for h in self.j.estado["lideres"]["historial"] if h["equipo"] == equipo]

    def test_08_primera_ronda_elige_lider_de_cada_equipo(self):
        self.preparar(20)
        self.assertEqual(self.j.estado["fase"], "lista")
        self.a(tipo="sortear_lideres")
        act = self.j.estado["lideres"]["actuales"]
        for i in (0, 1):
            self.assertIn(act[i], self.j.cfg["equipos"][i]["integrantes"])
        self.assertEqual(self.j.estado["fase"], "lideres")
        self.a(tipo="iniciar_ronda")
        self.assertEqual(self.j.estado["ronda"]["lideres"], act)
        pub = self.j.vista_publica()["equipos"]
        self.assertEqual([pub[0]["lider"], pub[1]["lider"]], [self.j.nombre_participante(x) for x in act])

    def test_09_sin_repetir_lideres_10_contra_10(self):
        self.preparar(20)
        self.assertEqual(self.j.total_rondas(), 10)
        for _ in range(10):
            self.jugar()
        for i in (0, 1):
            self.assertEqual(sorted(self.lideres_de(i)), sorted(self.j.cfg["equipos"][i]["integrantes"]))  # los 10, una vez
        self.assertEqual(self.j.estado["lideres"]["ciclo"], 1)

    def test_10_con_5_y_4_se_requieren_5_rondas_principales(self):
        self.j = nuevo_juego()
        self.a(tipo="agregar_participantes", nombres=NOMBRES_20[:9])
        self.a(tipo="sortear_equipos")
        self.a(tipo="mezclar_preguntas")
        self.assertEqual(sorted(self.j.tamanos_equipos()), [4, 5])
        self.assertEqual(self.j.minimo_principales(), 5)
        self.a(tipo="configurar_partida", rondas_principales=4)
        self.assertTrue(any("al menos 5 rondas principales" in e for e in self.j.validar_preparacion()))
        with self.assertRaises(ErrorJuego):
            self.a(tipo="confirmar_partida")
        self.a(tipo="configurar_partida", rondas_principales=None)  # automático = 5
        self.a(tipo="confirmar_partida")
        self.assertEqual(self.j.rondas_principales(), 5)

    def test_11_equipo_pequeno_no_repite_y_queda_sin_seleccion(self):
        self.preparar(9)
        grande = 0 if self.j.tamanos_equipos()[0] == 5 else 1
        chico = 1 - grande
        sorteos = [self.jugar() for _ in range(5)]
        self.assertEqual(len(set(self.lideres_de(grande))), 5)
        self.assertEqual(len(self.lideres_de(chico)), 4)
        self.assertEqual(len(set(self.lideres_de(chico))), 4)          # nadie repite en el primer ciclo
        quinta = sorteos[4]["equipos"]
        self.assertTrue(quinta[chico]["completo"])                       # 5.ª ronda: el equipo de 4 sin nueva selección
        self.assertIsNone(quinta[chico]["elegido"])
        self.assertEqual(len(quinta[grande]["candidatos"]), 1)           # el 5.º integrante, obligatorio
        self.assertFalse(sorteos[4]["nuevo_ciclo"])
        pub = self.j.vista_publica()["equipos"][chico]
        self.assertTrue(pub["sin_lider_nuevo"])

    def test_12_ciclo_se_reinicia_solo_cuando_corresponde(self):
        self.preparar(9, extra=2, mult=(2, 3))
        ciclos = []
        for _ in range(7):
            s = self.jugar()
            ciclos.append((s["ciclo"], s["nuevo_ciclo"]))
        self.assertEqual(ciclos[:5], [(1, False)] * 5)                    # rondas 1-5: primer ciclo
        self.assertEqual(ciclos[5], (2, True))                            # ronda 6 (extra 1): ciclo nuevo, anunciado
        self.assertEqual(ciclos[6], (2, False))
        h = [x for x in self.j.estado["lideres"]["historial"] if x["ciclo"] == 2]
        for i in (0, 1):
            ids = [x["participante"] for x in h if x["equipo"] == i]
            self.assertEqual(len(ids), len(set(ids)))                     # tampoco repite dentro del ciclo 2

    def test_mas_rondas_principales_que_integrantes_inicia_nuevo_ciclo(self):
        self.preparar(4, principales=3)                                   # 2 contra 2, 3 rondas principales
        s = [self.jugar() for _ in range(3)]
        self.assertEqual([x["nuevo_ciclo"] for x in s], [False, False, True])

    def test_17_cancelar_ronda_y_revertir_lideres(self):
        self.preparar(6)
        self.jugar()
        historial_antes = copy.deepcopy(self.j.estado["lideres"]["historial"])
        usados_antes = copy.deepcopy(self.j.estado["lideres"]["usados"])
        self.a(tipo="sortear_lideres")
        self.a(tipo="iniciar_ronda")
        pid = self.j.estado["ronda"]["pregunta_id"]
        self.a(tipo="primero_en_responder", equipo=1)
        self.a(tipo="cancelar_ronda")
        self.assertEqual(self.j.estado["fase"], "lideres")
        self.assertNotIn(pid, self.j.estado["preguntas_usadas"])          # la pregunta vuelve a estar disponible
        self.assertEqual(self.j.siguiente_pregunta(), pid)
        self.assertEqual(self.j.estado["ronda"]["numero"], 1)             # se ve la ronda anterior
        self.a(tipo="revertir_lideres")
        self.assertEqual(self.j.estado["fase"], "asignada")
        self.assertEqual(self.j.estado["lideres"]["historial"], historial_antes)
        self.assertEqual(self.j.estado["lideres"]["usados"], usados_antes)
        self.assertEqual(self.j.estado["puntajes"], [self.j.estado["historial_rondas"][0]["puntos"], 0])

    def test_19_eventos_de_sorteo_representan_el_resultado_real(self):
        self.preparar(20)
        ev_equipos = None
        j = nuevo_juego()
        j.aplicar({"tipo": "agregar_participantes", "nombres": NOMBRES_20})
        j.aplicar({"tipo": "sortear_equipos"})
        ev_equipos = j.estado["evento"]
        for i in (0, 1):  # lo que la animación muestra en cada columna es exactamente lo guardado
            animado = [s["nombre"] for s in ev_equipos["extra"]["secuencia"] if s["equipo"] == i]
            guardado = [j.nombre_participante(x) for x in j.cfg["equipos"][i]["integrantes"]]
            self.assertEqual(animado, guardado)
        self.a(tipo="sortear_lideres")
        ev = self.j.estado["evento"]
        self.assertEqual(ev["tipo"], "sorteo_lideres")
        for eq in ev["extra"]["equipos"]:  # la ruleta se detiene en el índice del líder realmente elegido
            self.assertEqual(eq["candidatos"][eq["indice"]], eq["elegido"])
            self.assertEqual(eq["elegido"], self.j.nombre_participante(self.j.estado["lideres"]["actuales"][eq["equipo"]]))

    def test_sorteo_de_lideres_es_uniforme(self):
        conteo = collections.Counter()
        for semilla in range(400):
            self.preparar(6, semilla=semilla)
            self.a(tipo="sortear_lideres")
            conteo[self.j.estado["lideres"]["sorteo"]["equipos"][0]["indice"]] += 1
        self.assertEqual(set(conteo), {0, 1, 2})
        self.assertTrue(all(c > 80 for c in conteo.values()), conteo)


# ====================================================================== partida y rondas extra (13-15)
class PruebasPartida(Base):
    EXTRA = 2
    MULTIPLICADORES = [2, 3]

    def test_plan_de_rondas(self):
        plan = self.j.plan_rondas()
        self.assertEqual([(r["tipo"], r["multiplicador"], r["maximo"]) for r in plan],
                         [("principal", 1, 100), ("principal", 1, 100), ("extra", 2, 200), ("extra", 3, 300)])

    def test_13_14_rondas_extra_multiplican_el_banco_sin_cambiar_puntos_base(self):
        base = copy.deepcopy(self.j.preguntas)
        self.jugar_ronda("p01")                 # principal: +B
        self.jugar_ronda("p02")                 # principal: +B
        self.jugar_ronda("p03")                 # extra ×2
        self.assertEqual(self.j.estado["ronda"]["multiplicador"], 2)
        self.assertEqual(self.j.estado["puntajes"], [B + B + 2 * B, 0])
        self.ronda_hasta_juego("p04")           # extra ×3
        for i in (1, 3, 4):
            self.a(tipo="revelar", respuesta_id=R("p04", i))
        self.assertEqual(self.j.estado["ronda"]["banco"], 300)    # todo el tablero: 100 × 3
        self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [4 * B + 300, 0])
        self.assertEqual(self.j.preguntas, base)                    # las puntuaciones originales no cambian
        pub = self.j.vista_publica()["ronda"]
        self.assertEqual((pub["tipo"], pub["extra_n"], pub["maximo"]), ("extra", 2, 300))
        self.assertEqual(pub["casillas"][0]["puntos"], A)             # el tablero muestra los puntos base
        self.assertEqual(self.j.estado["evento"]["tipo"], "ronda_ganada")

    def test_15_banco_de_ronda_extra_se_adjudica_una_vez(self):
        for p in ("p01", "p02"):
            self.jugar_ronda(p)
        self.jugar_ronda("p03")
        with self.assertRaises(ErrorJuego):
            self.a(tipo="asignar_banco")
        self.assertEqual(self.j.estado["puntajes"], [4 * B, 0])

    def test_06_sin_preguntas_repetidas_en_la_partida(self):
        for _ in range(4):
            self.jugar_ronda()
        usadas = self.j.estado["preguntas_usadas"]
        self.assertEqual(len(usadas), len(set(usadas)))
        self.assertEqual(usadas, self.j.prep["orden_preguntas"][:4])  # en el orden sorteado
        with self.assertRaises(ErrorJuego):
            self.a(tipo="sortear_lideres")                           # no hay más rondas configuradas

    def test_iniciar_con_pregunta_usada_requiere_confirmacion(self):
        self.jugar_ronda("p01")
        self.a(tipo="sortear_lideres")
        with self.assertRaises(ErrorJuego):
            self.a(tipo="iniciar_ronda", pregunta_id="p01")

    def test_marcador_final_y_empate(self):
        self.jugar_ronda("p01", robo_ok=True)
        self.a(tipo="finalizar_juego")
        self.assertEqual(self.j.estado["resultado_final"], {"ganador": 1, "puntajes": [0, B + A]})

    def test_nueva_partida_conserva_participantes_y_equipos_pero_exige_mezclar(self):
        equipos = copy.deepcopy(self.j.cfg["equipos"])
        self.jugar_ronda("p01")
        self.a(tipo="finalizar_juego")
        self.a(tipo="nueva_partida")
        e = self.j.estado
        self.assertEqual((e["fase"], e["puntajes"], e["preguntas_usadas"]), ("preparacion", [0, 0], []))
        self.assertEqual(self.j.cfg["equipos"], equipos)
        self.assertEqual(len(self.j.prep["participantes"]), 4)
        self.assertEqual(self.j.prep["orden_preguntas"], [])
        self.assertEqual(self.j.estado["lideres"]["historial"], [])
        self.assertEqual(e["evento"]["tipo"], "partida_lista")

    def test_ajuste_manual_y_reinicio_de_marcador(self):
        self.jugar_ronda("p01")
        self.a(tipo="ajustar_puntaje", equipo=1, delta=5)
        self.assertEqual(self.j.estado["puntajes"], [B, 5])
        self.a(tipo="reiniciar_marcador")
        self.a(tipo="deshacer")
        self.assertEqual(self.j.estado["puntajes"], [B, 5])

    def test_estado_antiguo_se_actualiza(self):
        viejo = json.loads(json.dumps(self.j.estado))
        viejo["config"].update(modo_puntos="frecuencia", total_rondas=5, multiplicadores=[1])
        viejo["config"]["equipos"][0]["lider"] = "x"
        j2 = Juego(PREGUNTAS, viejo)
        for k in ("modo_puntos", "total_rondas", "multiplicadores"):
            self.assertNotIn(k, j2.cfg)
        self.assertNotIn("lider", j2.cfg["equipos"][0])


class PruebasAudio(Base):
    def test_controles_de_audio_no_ocupan_pasos_de_deshacer(self):
        pila = len(self.j.pila_deshacer)
        self.a(tipo="configurar", cambios={"volumen": 35, "musica": False})
        self.assertEqual(len(self.j.pila_deshacer), pila)
        self.assertEqual(self.j.vista_publica()["volumen"], 35)

    def test_musica_y_prueba_de_sonido(self):
        self.a(tipo="musica")
        self.assertEqual(self.j.vista_publica()["evento"]["tipo"], "musica")
        self.a(tipo="probar_sonido", nombre="ruleta")
        self.assertEqual(self.j.vista_publica()["evento"]["extra"]["sonido"], "ruleta")
        with self.assertRaises(ErrorJuego):
            self.a(tipo="probar_sonido", nombre="desconocido")


# ====================================================================== pantalla pública (18)
class PruebasVistaPublica(Base):
    def test_18_vista_publica_no_contiene_informacion_privada(self):
        self.a(tipo="sortear_lideres")
        texto = json.dumps(self.j.vista_publica(), ensure_ascii=False)
        for pid in self.j.prep["orden_preguntas"]:                 # ni el orden ni los textos de las preguntas
            self.assertNotIn(f'"{pid}"', texto)
            self.assertNotIn(self.j.preguntas[pid]["texto"], texto)
        self.a(tipo="iniciar_ronda", pregunta_id="p05")
        texto = json.dumps(self.j.vista_publica(), ensure_ascii=False)
        for a in self.j.preguntas["p05"]["respuestas"]:
            self.assertNotIn(a["etiqueta"], texto)
            self.assertNotIn(a["id"], texto)
        for clave in ("frecuencia", "originales", "orden_preguntas", "usados", "antes_del_sorteo"):
            self.assertNotIn(clave, texto)
        self.a(tipo="primero_en_responder", equipo=0)
        self.a(tipo="respuesta_cara_a_cara", equipo=0, respuesta_id=R("p05", 2))
        texto = json.dumps(self.j.vista_publica(), ensure_ascii=False)
        self.assertIn("Beta 5", texto)
        for oculta in ("Alfa 5", "Gamma 5", "Delta 5"):
            self.assertNotIn(oculta, texto)

    def test_vista_presentador_tiene_todo(self):
        v = self.j.vista_presentador()
        self.assertEqual(v["tableros"]["p01"]["ids"], [R("p01", i) for i in (1, 2, 3, 4)])
        self.assertEqual(sum(v["tableros"]["p01"]["puntos"][R("p01", i)] for i in (1, 2, 3, 4)), 100)
        self.assertEqual(len(v["plan_rondas"]), 2)


if __name__ == "__main__":
    unittest.main()
