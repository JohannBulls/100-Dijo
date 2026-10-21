"""Pruebas sobre los datos publicados (datos/preguntas_procesadas.json) y la identidad «100 Dijeron».

No necesitan el Excel original, así que también corren en GitHub Actions.
"""
import json
import os
import re
import subprocess
import sys
import unittest

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RAIZ, "app"))
import procesar_excel  # noqa: E402

NOMBRE = "100 Dijeron"
# Nombre anterior del proyecto (se arma por partes para que este archivo no lo contenga literalmente).
NOMBRE_ANTERIOR = re.compile(r"(?i)41\s+clouders|clouders\s+" + "dijeron")
PREGUNTAS_DE_LAS_CAPTURAS = (20, 25, 39, 47)


def leer_json(*ruta):
    with open(os.path.join(RAIZ, *ruta), encoding="utf-8") as f:
        return json.load(f)


def archivos_publicados():
    """Archivos que se suben a GitHub (los que git sigue o seguiría), excluyendo binarios."""
    try:
        salida = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=RAIZ,
                                capture_output=True, text=True, check=True, encoding="utf-8").stdout
        rutas = [r for r in salida.splitlines() if r]
    except (OSError, subprocess.CalledProcessError):
        rutas = []
    return [r for r in rutas if os.path.splitext(r)[1].lower() in
            (".py", ".md", ".html", ".js", ".css", ".json", ".svg", ".bat", ".txt", ".yml", ".cff", "")]


class PruebasDatosPublicados(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.datos = leer_json("datos", "preguntas_procesadas.json")
        cls.agrupaciones = leer_json("datos", "agrupaciones.json")["preguntas"]
        cls.por_numero = {p["numero"]: p for p in cls.datos["preguntas"]}

    def tablero(self, p):
        return [a for a in p["respuestas"] if a["en_tablero"]]

    def test_habilitadas_tienen_de_4_a_10_respuestas_que_suman_100(self):
        habilitadas = [p for p in self.datos["preguntas"] if p["habilitada"]]
        self.assertGreaterEqual(len(habilitadas), 30)
        for p in habilitadas:
            t = self.tablero(p)
            self.assertTrue(procesar_excel.MIN_TABLERO <= len(t) <= procesar_excel.MAX_TABLERO, p["numero"])
            self.assertEqual(sum(a["puntos"] for a in t), 100, p["numero"])
            self.assertEqual([a["puntos"] for a in t], sorted((a["puntos"] for a in t), reverse=True))
            self.assertTrue(all(a["puntos"] >= 1 and a["frecuencia"] >= 2 for a in t), p["numero"])

    def test_pendientes_estan_deshabilitadas_y_tienen_propuesta(self):
        for p in self.datos["preguntas"]:
            estado = p["jugabilidad"]["estado"]
            self.assertIn(estado, procesar_excel.ESTADOS)
            if estado == "pendiente":
                self.assertFalse(p["habilitada"], p["numero"])
                self.assertTrue(p["jugabilidad"]["detalle"] and p["jugabilidad"]["propuesta"], p["numero"])
            else:
                self.assertTrue(p["habilitada"], p["numero"])
            if len(self.tablero(p)) < procesar_excel.MIN_TABLERO:
                self.assertEqual(estado, "pendiente", p["numero"])  # nunca se habilita con menos de 4

    def test_preguntas_de_las_capturas_revisadas(self):
        for n in PREGUNTAS_DE_LAS_CAPTURAS:
            self.assertIn("revision_jugabilidad", self.agrupaciones[str(n)], n)
            p = self.por_numero[n]
            self.assertTrue(p["jugabilidad"]["detalle"], n)
            if not p["habilitada"]:
                self.assertTrue(p["jugabilidad"]["propuesta"], n)

    def test_trazabilidad_cada_respuesta_viene_de_originales(self):
        for p in self.datos["preguntas"]:
            filas = [o["fila"] for a in p["respuestas"] for o in a["originales"]] + [e["fila"] for e in p["excluidas"]]
            self.assertEqual(len(filas), len(set(filas)), p["numero"])        # ninguna fila se cuenta dos veces
            self.assertEqual(len(filas), p["respuestas_validas"] + p["respuestas_excluidas"])
            for a in p["respuestas"]:
                self.assertEqual(a["frecuencia"], len(a["originales"]), (p["numero"], a["etiqueta"]))

    def test_ejemplos_aceptados_salen_de_respuestas_reales(self):
        for p in self.datos["preguntas"]:
            for a in self.tablero(p):
                originales = {procesar_excel.normalizar(o["texto"]) for o in a["originales"]}
                self.assertTrue(a["ejemplos"], (p["numero"], a["etiqueta"]))
                self.assertLessEqual(len(a["ejemplos"]), procesar_excel.MAX_EJEMPLOS)
                for x in a["ejemplos"]:
                    self.assertIn(procesar_excel.normalizar(x), originales, (p["numero"], x))  # nunca inventados
                self.assertTrue(a["criterio"].startswith("Acepta"), (p["numero"], a["etiqueta"]))

    def test_cambios_de_redaccion_documentados(self):
        for p in self.datos["preguntas"]:
            if p["texto"] != p["texto_original"]:
                self.assertIn("texto_juego", self.agrupaciones[str(p["numero"])], p["numero"])

    def test_sin_nombres_de_personas_en_datos_publicados(self):
        privados = procesar_excel.leer_nombres_privados()
        nombres = [n for q in privados.values() for lista in q.values() for n in lista]
        if not nombres:
            self.skipTest("Sin archivo privado de nombres (normal en GitHub)")
        for ruta in (("datos", "preguntas_procesadas.json"), ("datos", "agrupaciones.json")):
            with open(os.path.join(RAIZ, *ruta), encoding="utf-8") as f:
                texto = f.read()
            for n in nombres:
                self.assertNotRegex(texto, r"(?i)\b" + re.escape(n) + r"\b", ruta)


class PruebasIdentidad(unittest.TestCase):
    def test_paginas_con_el_nombre_100_dijeron(self):
        for pagina in ("inicio.html", "publico.html", "presentador.html"):
            with open(os.path.join(RAIZ, "app", "web", pagina), encoding="utf-8") as f:
                html = f.read()
            self.assertRegex(html, r"<title>[^<]*" + NOMBRE, pagina)
            self.assertIn("img/icono.svg", html, pagina)
        for img in ("logo.svg", "icono.svg"):
            self.assertTrue(os.path.exists(os.path.join(RAIZ, "app", "web", "img", img)))

    def test_titulo_por_defecto_del_motor(self):
        from juego import Juego
        self.assertEqual(Juego([]).estado["config"]["titulo"], NOMBRE)

    def test_no_quedan_referencias_al_nombre_anterior(self):
        rutas = archivos_publicados()
        if not rutas:
            self.skipTest("git no está disponible")
        for r in rutas:
            with open(os.path.join(RAIZ, r), encoding="utf-8", errors="ignore") as f:
                self.assertIsNone(NOMBRE_ANTERIOR.search(f.read()), r)

    def test_nada_privado_se_publica(self):
        rutas = archivos_publicados()
        if not rutas:
            self.skipTest("git no está disponible")
        todos = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard"], cwd=RAIZ,
                               capture_output=True, text=True, encoding="utf-8").stdout.splitlines()
        for r in todos:
            self.assertFalse(r.startswith("datos/privado/"), r)
            self.assertFalse(r.endswith(".env") or r == "datos/partida_guardada.json", r)
            self.assertFalse(r.endswith(".xlsx") and "/" not in r, r)   # el Excel original de la raíz


if __name__ == "__main__":
    unittest.main()
