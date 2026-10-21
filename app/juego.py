"""Motor del juego: preparación, sorteos, máquina de estados, puntuación y deshacer.

No depende de la red ni del navegador, así se puede probar de forma aislada.
Todas las acciones pasan por Juego.aplicar(), que valida la fase actual y la
versión esperada (para que un doble clic no aplique la misma acción dos veces).

Los sorteos (equipos, orden de preguntas y líderes) se hacen AQUÍ, con un generador
aleatorio del sistema operativo. Las animaciones de las pantallas solo muestran el
resultado que ya quedó guardado.
"""
import copy
import random
import time

FASES = {
    "preparacion": "Preparación de la partida",
    "lista": "Partida lista (falta sortear líderes)",
    "lideres": "Líderes sorteados (lista para iniciar la ronda)",
    "cara_a_cara": "Cara a cara",
    "decision": "Jugar o pasar",
    "juego": "Ronda en juego",
    "robo": "Oportunidad de robo",
    "resuelta": "Ronda resuelta (falta asignar el banco)",
    "asignada": "Ronda terminada",
    "fin": "Juego terminado",
}

CONFIG_POR_DEFECTO = {
    "titulo": "100 Dijeron",
    "equipos": [
        {"nombre": "Equipo Azul", "integrantes": []},
        {"nombre": "Equipo Naranja", "integrantes": []},
    ],
    "permitir_pasar": True,            # el ganador del cara a cara puede ceder el turno
    "robo_suma_respuesta": True,       # el robo exitoso suma la respuesta robada al banco
    "empate_cara_a_cara": "desempate", # «desempate»: vuelven a responder · «primero»: gana quien respondió antes
    "sonido": True,                    # interruptor general de audio
    "musica": True,                    # música de entrada
    "efectos": True,                   # efectos (correcta, strike, aplausos…)
    "volumen": 70,                     # 0 a 100
    "animaciones": True,
}
CLAVES_ANTIGUAS = ("modo_puntos", "total_rondas", "max_tablero", "min_frecuencia", "multiplicadores_activos",
                   "multiplicadores")

# Campos que se pueden cambiar en cualquier momento (no afectan la puntuación).
CONFIG_LIBRE = {"titulo", "equipos", "sonido", "musica", "efectos", "volumen", "animaciones"}
# Campos de apariencia y audio: no ocupan un paso de «Deshacer».
CONFIG_SIN_DESHACER = {"sonido", "musica", "efectos", "volumen", "animaciones"}
SONIDOS_DE_PRUEBA = {"musica", "correcta", "strike", "strike2", "robo", "robo_exitoso", "robo_fallido",
                     "puntos", "fanfarria_final", "ruleta", "lider", "ronda_extra"}
FASES_CAMBIO_REGLAS = {"preparacion", "lista", "lideres", "asignada", "fin"}
MAX_PARTICIPANTES = 60
MAX_RONDAS_EXTRA = 10
PUNTOS_POR_PREGUNTA = 100


class ErrorJuego(Exception):
    """Acción no permitida; el mensaje se muestra al presentador."""


def otro(equipo):
    """Devuelve el índice del equipo rival (0 ↔ 1)."""
    return 1 - equipo


def preparacion_inicial():
    """Estado vacío de la pestaña Preparación (participantes, sorteos y rondas)."""
    return {
        "participantes": [],            # [{"id": "j1", "nombre": "Ana"}]
        "siguiente_id": 1,
        "sorteo_equipos": None,         # {"id": n, "secuencia": [{"id": "j3", "equipo": 0}, …]}
        "orden_preguntas": [],          # ids de preguntas en el orden sorteado
        "mezcla": 0,                    # cuántas veces se mezcló (identifica la animación)
        "rondas_principales": None,     # None = automático (tamaño del equipo más numeroso)
        "rondas_extra": 0,
        "multiplicadores_extra": [],
        "confirmada": False,
    }


def lideres_iniciales():
    """Estado vacío del historial de líderes (ciclo 1, nadie ha sido líder)."""
    return {"ciclo": 1, "usados": [[], []], "historial": [], "actuales": [None, None], "sorteo": None,
            "antes_del_sorteo": None}


def estado_inicial(config=None):
    """Estado completo de una partida nueva. Todo es JSON serializable para poder guardarlo."""
    return {
        "version": 0,
        "config": copy.deepcopy(config or CONFIG_POR_DEFECTO),
        "fase": "preparacion",
        "preparacion": preparacion_inicial(),
        "lideres": lideres_iniciales(),
        "puntajes": [0, 0],
        "ronda": None,
        "historial_rondas": [],
        "preguntas_usadas": [],
        "evento": None,
        "bitacora": [],
        "resultado_final": None,
    }


class Juego:
    """Partida en curso: estado, reglas y acciones.

    Fases (ver FASES): preparacion → lista → lideres → cara_a_cara → decision → juego
    → robo → resuelta → asignada → (lideres → … ) → fin.

    Cada acción del panel se envía como {"tipo": "...", ...} a aplicar(), que la delega
    en el método _a_<tipo>. Los métodos _a_* devuelven un texto para la bitácora (y la
    acción se puede deshacer) o None (acciones de apariencia que no se deshacen).
    """

    def __init__(self, preguntas, estado=None, deshacer=None, rng=None):
        """Crea el juego.

        preguntas: lista de preguntas procesadas (datos/preguntas_procesadas.json).
        estado / deshacer: partida guardada a recuperar (o None para empezar de cero).
        rng: generador aleatorio; por defecto el del sistema operativo. Las pruebas pasan
             uno con semilla para obtener resultados reproducibles.
        """
        self.preguntas = {p["id"]: p for p in preguntas}
        self.rng = rng or random.SystemRandom()  # azar real del sistema operativo
        self.estado = estado or estado_inicial()
        # Completa claves nuevas y quita las antiguas si el estado guardado es de una versión anterior.
        cfg = self.estado["config"]
        for k, v in CONFIG_POR_DEFECTO.items():
            cfg.setdefault(k, copy.deepcopy(v))
        for k in CLAVES_ANTIGUAS:
            cfg.pop(k, None)
        for eq in cfg["equipos"]:
            eq.pop("lider", None)
            eq.setdefault("integrantes", [])
        self.estado.setdefault("preparacion", preparacion_inicial())
        self.estado.setdefault("lideres", lideres_iniciales())
        self.pila_deshacer = deshacer or []
        self._evento_id = (self.estado.get("evento") or {}).get("id", 0)

    # ------------------------------------------------------------------ utilidades
    @property
    def cfg(self):
        """Configuración (nombres de equipos, reglas y audio)."""
        return self.estado["config"]

    @property
    def prep(self):
        """Datos de la preparación (participantes, sorteos, orden de preguntas, rondas)."""
        return self.estado["preparacion"]

    def nombre(self, equipo):
        """Nombre visible del equipo 0 o 1."""
        return self.cfg["equipos"][equipo]["nombre"] or f"Equipo {equipo + 1}"

    def nombre_participante(self, pid):
        """Nombre de un participante a partir de su identificador («j1», «j2»…)."""
        for p in self.prep["participantes"]:
            if p["id"] == pid:
                return p["nombre"]
        return "?"

    def pregunta_actual(self):
        """Pregunta de la ronda en curso (o None si aún no hay ronda)."""
        r = self.estado["ronda"]
        return self.preguntas[r["pregunta_id"]] if r else None

    @staticmethod
    def puntos_respuesta(respuesta):
        """Puntos calculados una sola vez al procesar el Excel (cada tablero suma 100); el juego no los recalcula."""
        return respuesta["puntos"]

    @staticmethod
    def tablero_de(pregunta):
        """Respuestas del tablero, tal como las fijó el procesamiento del Excel (suman 100 puntos)."""
        return [a for a in pregunta["respuestas"] if a.get("en_tablero")]

    def tamanos_equipos(self):
        """Integrantes de cada equipo; antes del sorteo, el reparto previsto."""
        if self.prep["sorteo_equipos"]:
            return [len(e["integrantes"]) for e in self.cfg["equipos"]]
        n = len(self.prep["participantes"])
        return [(n + 1) // 2, n // 2]

    def minimo_principales(self):
        """Rondas necesarias para que todos los integrantes del equipo más numeroso sean líderes una vez."""
        return max(1, max(self.tamanos_equipos()))

    def rondas_principales(self):
        """Rondas principales configuradas (automático = equipo más numeroso)."""
        return self.prep["rondas_principales"] or self.minimo_principales()

    def total_rondas(self):
        """Rondas principales + adicionales."""
        return self.rondas_principales() + self.prep["rondas_extra"]

    def preguntas_disponibles(self):
        """Preguntas que pueden salir en la mezcla: solo las habilitadas (4 a 10 respuestas en el tablero)."""
        return [pid for pid, p in self.preguntas.items() if p.get("habilitada", True)]

    def multiplicador(self, numero_ronda):
        """Multiplicador del banco para la ronda indicada (1 en las principales)."""
        principales = self.rondas_principales()
        if numero_ronda <= principales:
            return 1
        extras = self.prep["multiplicadores_extra"]
        i = numero_ronda - principales - 1
        return extras[i] if i < len(extras) else (extras[-1] if extras else 1)

    def info_ronda(self, numero):
        """Tipo, multiplicador y valor máximo de la ronda indicada."""
        principales = self.rondas_principales()
        extra = numero - principales if numero > principales else 0
        m = self.multiplicador(numero)
        return {"numero": numero, "tipo": "extra" if extra else "principal", "extra_n": extra,
                "multiplicador": m, "maximo": PUNTOS_POR_PREGUNTA * m}

    def plan_rondas(self):
        """Lista con la información de todas las rondas configuradas (vista previa)."""
        return [self.info_ronda(n) for n in range(1, self.total_rondas() + 1)]

    def validar_preparacion(self):
        """Mensajes que impiden confirmar la partida (lista vacía = todo correcto)."""
        errores = []
        n = len(self.prep["participantes"])
        if n < 2:
            errores.append("Registra al menos 2 participantes (uno por equipo).")
        if not self.prep["sorteo_equipos"]:
            errores.append("Pulsa «Sortear equipos» para repartir a los participantes.")
        if not self.prep["orden_preguntas"]:
            errores.append("Pulsa «Mezclar preguntas» para sortear el orden de las preguntas.")
        minimo = self.minimo_principales()
        if self.rondas_principales() < minimo:
            errores.append(f"Se necesitan al menos {minimo} rondas principales para que todos los integrantes del "
                           f"equipo más numeroso sean líderes una vez (configuraste {self.rondas_principales()}).")
        disponibles = len(self.preguntas_disponibles())
        total = self.total_rondas()
        if total > disponibles:
            errores.append(f"Faltan {total - disponibles} preguntas: configuraste {total} rondas y solo hay "
                           f"{disponibles} preguntas habilitadas. Reduce las rondas o aprueba preguntas pendientes "
                           "(ver docs/REVISION_DE_PREGUNTAS.md).")
        return errores

    def siguiente_pregunta(self):
        """Primera pregunta del orden sorteado que todavía no se ha usado."""
        usadas = set(self.estado["preguntas_usadas"])
        for pid in self.prep["orden_preguntas"]:
            if pid not in usadas and pid in self.preguntas:
                return pid
        return None

    def _evento(self, tipo, texto, equipo=None, extra=None):
        """Registra el último evento: la pantalla pública lo usa para animaciones y sonidos."""
        self._evento_id += 1
        self.estado["evento"] = {"id": self._evento_id, "tipo": tipo, "texto": texto,
                                 "equipo": equipo, "extra": extra or {}}

    def _log(self, texto):
        """Añade una línea a la bitácora visible en el panel (se guardan las últimas 300)."""
        self.estado["bitacora"].append({"hora": time.strftime("%H:%M:%S"), "texto": texto})
        self.estado["bitacora"] = self.estado["bitacora"][-300:]

    def _exigir_fase(self, *fases):
        """Lanza ErrorJuego si la acción no corresponde a la fase actual."""
        if self.estado["fase"] not in fases:
            permitidas = ", ".join(FASES[f] for f in fases)
            raise ErrorJuego(f"Esta acción solo se puede usar en: {permitidas}. "
                             f"Fase actual: {FASES[self.estado['fase']]}.")

    def _equipo(self, valor):
        """Valida que el equipo sea 0 o 1."""
        if valor not in (0, 1):
            raise ErrorJuego("Equipo no válido.")
        return valor

    def _respuesta_oculta(self, respuesta_id):
        """Devuelve la respuesta si está en el tablero y aún oculta; si no, lanza ErrorJuego."""
        r = self.estado["ronda"]
        if respuesta_id not in r["tablero"]:
            raise ErrorJuego("Esa respuesta no está en el tablero de esta ronda.")
        if respuesta_id in r["reveladas"]:
            raise ErrorJuego("Esa respuesta ya está revelada; no suma puntos otra vez.")
        return self._buscar_respuesta(respuesta_id)

    def _buscar_respuesta(self, respuesta_id):
        """Busca una respuesta de la pregunta actual por su identificador."""
        for a in self.pregunta_actual()["respuestas"]:
            if a["id"] == respuesta_id:
                return a
        raise ErrorJuego("Respuesta desconocida.")

    def _revelar(self, respuesta_id, equipo, como, sumar):
        """Marca una respuesta como revelada y, si corresponde, suma sus puntos (× multiplicador) al banco."""
        r = self.estado["ronda"]
        a = self._buscar_respuesta(respuesta_id)
        pts = self.puntos_respuesta(a)
        sumado = pts * r["multiplicador"] if sumar else 0
        r["reveladas"][respuesta_id] = {"equipo": equipo, "como": como, "puntos": pts, "sumado": sumado}
        r["banco"] += sumado
        return a, pts, sumado

    def _todas_reveladas(self):
        """True si ya no quedan casillas ocultas en el tablero."""
        r = self.estado["ronda"]
        return all(x in r["reveladas"] for x in r["tablero"])

    # ------------------------------------------------------------------ acciones
    def aplicar(self, accion, version_esperada=None):
        """Aplica una acción. Devuelve el estado nuevo o lanza ErrorJuego."""
        if version_esperada is not None and version_esperada != self.estado["version"]:
            raise ErrorJuego("La pantalla estaba desactualizada (posible doble clic). "
                             "No se aplicó la acción; revisa el estado y vuelve a intentar.")
        tipo = accion.get("tipo")
        if tipo == "deshacer":
            return self._deshacer()
        manejador = getattr(self, "_a_" + str(tipo), None)
        if manejador is None:
            raise ErrorJuego(f"Acción desconocida: {tipo}")
        respaldo = copy.deepcopy(self.estado)
        try:
            descripcion = manejador(accion)
        except ErrorJuego:
            self.estado = respaldo
            raise
        except (KeyError, TypeError, ValueError) as e:
            self.estado = respaldo
            raise ErrorJuego(f"Datos de la acción no válidos ({e}).")
        if descripcion:  # las acciones que solo cambian apariencia no se deshacen
            respaldo["_descripcion"] = descripcion
            self.pila_deshacer.append(respaldo)
            self.pila_deshacer[:] = self.pila_deshacer[-150:]
            self._log(descripcion)
        self.estado["version"] += 1
        return self.estado

    def _deshacer(self):
        """Restaura el estado anterior a la última acción deshacible (conserva la bitácora)."""
        if not self.pila_deshacer:
            raise ErrorJuego("No hay acciones para deshacer.")
        anterior = self.pila_deshacer.pop()
        descripcion = anterior.pop("_descripcion", "acción")
        version = self.estado["version"]
        bitacora = self.estado["bitacora"]
        self.estado = anterior
        self.estado["version"] = version + 1
        self.estado["bitacora"] = bitacora
        self._log(f"↩ Se deshizo: {descripcion}")
        self._evento("deshacer", "")
        return self.estado

    def _a_configurar(self, accion):
        """Cambia nombre del juego, nombres de equipos, reglas o audio."""
        cambios = accion["cambios"]
        reglas = set(cambios) - CONFIG_LIBRE
        desconocidas = set(cambios) - set(CONFIG_POR_DEFECTO)
        if desconocidas:
            raise ErrorJuego(f"Opciones desconocidas: {', '.join(sorted(desconocidas))}")
        if reglas and self.estado["fase"] not in FASES_CAMBIO_REGLAS:
            raise ErrorJuego("Las reglas de puntuación solo se pueden cambiar antes de empezar "
                             "o entre rondas (después de asignar el banco).")
        if "equipos" in cambios:  # solo los nombres: los integrantes los define el sorteo
            eq = cambios["equipos"]
            if not (isinstance(eq, list) and len(eq) == 2):
                raise ErrorJuego("Debe haber exactamente dos equipos.")
            cambios["equipos"] = [{"nombre": str(e.get("nombre", "")).strip()[:40],
                                   "integrantes": self.cfg["equipos"][i]["integrantes"]} for i, e in enumerate(eq)]
        if "volumen" in cambios:
            cambios["volumen"] = max(0, min(100, int(cambios["volumen"])))
        if "empate_cara_a_cara" in cambios and cambios["empate_cara_a_cara"] not in ("desempate", "primero"):
            raise ErrorJuego("Criterio de empate no válido (usa «desempate» o «primero»).")
        for k in ("permitir_pasar", "robo_suma_respuesta", "sonido", "musica", "efectos", "animaciones"):
            if k in cambios:
                cambios[k] = bool(cambios[k])
        self.cfg.update(cambios)
        if set(cambios) - CONFIG_SIN_DESHACER:
            return "Configuración actualizada: " + ", ".join(sorted(cambios))
        return None  # audio/animaciones: no ocupa un paso de deshacer

    def _a_musica(self, accion):
        """Música de entrada en la pantalla pública (no altera el juego ni ocupa un paso de deshacer)."""
        self._evento("musica", "")
        return None

    def _a_probar_sonido(self, accion):
        """Pide a la pantalla pública que reproduzca un efecto de prueba."""
        nombre = accion.get("nombre")
        if nombre not in SONIDOS_DE_PRUEBA:
            raise ErrorJuego("Sonido desconocido.")
        self._evento("prueba_sonido", "", extra={"sonido": nombre})
        return None

    # ------------------------------------------------------------------ preparación
    def _exigir_preparacion(self):
        """Las acciones de preparación solo valen antes de confirmar la partida."""
        self._exigir_fase("preparacion")

    def _invalidar_sorteo_equipos(self):
        """Anula el sorteo de equipos (cuando cambia la lista de participantes)."""
        if self.prep["sorteo_equipos"]:
            self.prep["sorteo_equipos"] = None
            for eq in self.cfg["equipos"]:
                eq["integrantes"] = []
            return " · los equipos se deben volver a sortear"
        return ""

    def _a_agregar_participantes(self, accion):
        """Registra uno o varios nombres (ignora vacíos y repetidos sin distinguir mayúsculas)."""
        self._exigir_preparacion()
        existentes = {p["nombre"].casefold() for p in self.prep["participantes"]}
        agregados, repetidos = [], []
        for nombre in accion["nombres"]:
            nombre = " ".join(str(nombre).split())[:40]
            if not nombre:
                continue
            if nombre.casefold() in existentes:
                repetidos.append(nombre)
                continue
            if len(self.prep["participantes"]) >= MAX_PARTICIPANTES:
                raise ErrorJuego(f"El máximo es {MAX_PARTICIPANTES} participantes.")
            pid = f"j{self.prep['siguiente_id']}"
            self.prep["siguiente_id"] += 1
            self.prep["participantes"].append({"id": pid, "nombre": nombre})
            existentes.add(nombre.casefold())
            agregados.append(nombre)
        if not agregados:
            raise ErrorJuego("No se agregó a nadie" + (f": ya estaban registrados ({', '.join(repetidos)})." if repetidos
                                                        else ": escribe al menos un nombre."))
        aviso = f" (ya estaban: {', '.join(repetidos)})" if repetidos else ""
        return f"Se registraron {len(agregados)} participante(s){aviso}" + self._invalidar_sorteo_equipos()

    def _a_editar_participante(self, accion):
        """Corrige el nombre de un participante."""
        self._exigir_preparacion()
        nombre = " ".join(str(accion["nombre"]).split())[:40]
        if not nombre:
            raise ErrorJuego("El nombre no puede quedar vacío.")
        for p in self.prep["participantes"]:
            if p["id"] != accion["id"] and p["nombre"].casefold() == nombre.casefold():
                raise ErrorJuego(f"Ya hay un participante llamado «{nombre}».")
        for p in self.prep["participantes"]:
            if p["id"] == accion["id"]:
                anterior, p["nombre"] = p["nombre"], nombre
                return f"Participante renombrado: «{anterior}» → «{nombre}»"
        raise ErrorJuego("Participante no encontrado.")

    def _a_eliminar_participante(self, accion):
        """Quita a un participante de la lista."""
        self._exigir_preparacion()
        antes = len(self.prep["participantes"])
        nombre = self.nombre_participante(accion["id"])
        self.prep["participantes"] = [p for p in self.prep["participantes"] if p["id"] != accion["id"]]
        if len(self.prep["participantes"]) == antes:
            raise ErrorJuego("Participante no encontrado.")
        return f"Se eliminó a «{nombre}»" + self._invalidar_sorteo_equipos()

    def _a_vaciar_participantes(self, accion):
        """Borra toda la lista de participantes."""
        self._exigir_preparacion()
        if not self.prep["participantes"]:
            raise ErrorJuego("No hay participantes registrados.")
        self.prep["participantes"] = []
        self._invalidar_sorteo_equipos()
        return "Se borró la lista de participantes"

    def _a_sortear_equipos(self, accion):
        """Reparto aleatorio y equitativo: se baraja a todos y se asignan alternando equipos
        (el equipo que empieza también es al azar). Diferencia máxima: una persona."""
        self._exigir_preparacion()
        personas = [p["id"] for p in self.prep["participantes"]]
        if len(personas) < 2:
            raise ErrorJuego("Registra al menos 2 participantes antes de sortear.")
        self.rng.shuffle(personas)
        primero = self.rng.randrange(2)
        secuencia = [{"id": pid, "equipo": (primero + i) % 2} for i, pid in enumerate(personas)]
        for i, eq in enumerate(self.cfg["equipos"]):
            eq["integrantes"] = [s["id"] for s in secuencia if s["equipo"] == i]
        anterior = self.prep["sorteo_equipos"]
        self.prep["sorteo_equipos"] = {"id": (anterior["id"] + 1) if anterior else 1, "secuencia": secuencia}
        self._evento("sorteo_equipos", "", extra={
            "id": self.prep["sorteo_equipos"]["id"],
            "secuencia": [{"nombre": self.nombre_participante(s["id"]), "equipo": s["equipo"]} for s in secuencia]})
        a, b = self.tamanos_equipos()
        return f"Sorteo de equipos: {self.nombre(0)} {a} · {self.nombre(1)} {b}"

    def _a_mezclar_preguntas(self, accion):
        """Ordena al azar las preguntas disponibles (el orden queda guardado y es privado)."""
        self._exigir_preparacion()
        disponibles = self.preguntas_disponibles()
        if not disponibles:
            raise ErrorJuego("No hay preguntas habilitadas para jugar.")
        orden = list(disponibles)
        self.rng.shuffle(orden)
        self.prep["orden_preguntas"] = orden
        self.prep["mezcla"] += 1
        self._evento("mezcla_preguntas", "", extra={"cantidad": len(orden), "id": self.prep["mezcla"]})
        return f"Preguntas mezcladas al azar ({len(orden)} disponibles)"

    def _a_configurar_partida(self, accion):
        """Configura rondas principales, adicionales y sus multiplicadores."""
        self._exigir_preparacion()
        p = self.prep
        if "rondas_principales" in accion:
            v = accion["rondas_principales"]
            if v in (None, "", "auto"):
                p["rondas_principales"] = None
            else:
                v = int(v)
                if not 1 <= v <= 60:
                    raise ErrorJuego("Las rondas principales deben estar entre 1 y 60.")
                p["rondas_principales"] = v
        if "rondas_extra" in accion:
            n = int(accion["rondas_extra"])
            if not 0 <= n <= MAX_RONDAS_EXTRA:
                raise ErrorJuego(f"Las rondas adicionales deben estar entre 0 y {MAX_RONDAS_EXTRA}.")
            p["rondas_extra"] = n
        mult = [int(x) for x in accion.get("multiplicadores_extra", p["multiplicadores_extra"])]
        mult = mult[: p["rondas_extra"]]
        while len(mult) < p["rondas_extra"]:
            mult.append(min(10, len(mult) + 2))  # por defecto: ×2, ×3, ×4…
        if any(not 1 <= m <= 10 for m in mult):
            raise ErrorJuego("Los multiplicadores deben ser números enteros entre 1 y 10.")
        p["multiplicadores_extra"] = mult
        return (f"Rondas: {self.rondas_principales()} principales + {p['rondas_extra']} adicionales"
                + (f" (×{', ×'.join(map(str, mult))})" if mult else ""))

    def _a_confirmar_partida(self, accion):
        """Valida la preparación y fija equipos, orden de preguntas y número de rondas."""
        self._exigir_preparacion()
        errores = self.validar_preparacion()
        if errores:
            raise ErrorJuego("Aún no se puede iniciar: " + " ".join(errores))
        self.prep["confirmada"] = True
        self.prep["rondas_principales"] = self.rondas_principales()  # se fija el número
        self.estado["fase"] = "lista"
        self._evento("partida_confirmada", "¡Todo listo!", extra={"principales": self.rondas_principales(),
                                                                  "extra": self.prep["rondas_extra"]})
        return (f"Partida confirmada: {self.rondas_principales()} rondas principales y "
                f"{self.prep['rondas_extra']} adicionales")

    def _a_nueva_partida(self, accion):
        """Vuelve a la preparación conservando participantes, equipos, nombres y reglas.
        Borra marcador, rondas, líderes y el orden de preguntas (hay que volver a mezclar)."""
        config = copy.deepcopy(self.cfg)
        prep = copy.deepcopy(self.prep)
        prep.update(confirmada=False, orden_preguntas=[])
        bitacora = self.estado["bitacora"]
        version = self.estado["version"]
        self.estado = estado_inicial(config)
        self.estado.update(version=version, bitacora=bitacora, preparacion=prep)
        self._evento("partida_lista", "")
        return "Configuración reiniciada: nueva partida (se conservan participantes, equipos y reglas)"

    _a_reiniciar_configuracion = _a_nueva_partida

    # ------------------------------------------------------------------ líderes
    def info_lideres(self):
        """Para cada equipo: integrantes que aún no han sido líderes en el ciclo actual."""
        lid = self.estado["lideres"]
        info = []
        for i, eq in enumerate(self.cfg["equipos"]):
            usados = set(lid["usados"][i])
            pendientes = [pid for pid in eq["integrantes"] if pid not in usados]
            info.append({"pendientes": pendientes, "total": len(eq["integrantes"]), "usados": lid["usados"][i]})
        return info

    def _a_sortear_lideres(self, accion):
        """Elige al azar el líder de cada equipo entre quienes aún no lo han sido en este ciclo.
        Si un equipo ya completó su ciclo, se queda sin nueva selección. Si ambos lo completaron,
        empieza un ciclo nuevo para los dos."""
        self._exigir_fase("lista", "asignada")
        numero = len(self.estado["historial_rondas"]) + 1
        if numero > self.total_rondas():
            raise ErrorJuego("Ya se jugaron todas las rondas configuradas. Finaliza el juego.")
        lid = self.estado["lideres"]
        antes = {"lideres": copy.deepcopy({k: v for k, v in lid.items() if k != "antes_del_sorteo"}),
                 "fase": self.estado["fase"]}
        info = self.info_lideres()
        nuevo_ciclo = all(not x["pendientes"] for x in info)
        if nuevo_ciclo:
            lid["ciclo"] += 1
            lid["usados"] = [[], []]
            info = self.info_lideres()
        equipos = []
        for i in (0, 1):
            candidatos = info[i]["pendientes"]
            elegido = self.rng.choice(candidatos) if candidatos else None
            if elegido:
                lid["usados"][i].append(elegido)
                lid["historial"].append({"ronda": numero, "ciclo": lid["ciclo"], "equipo": i, "participante": elegido,
                                         "nombre": self.nombre_participante(elegido), "unico": len(candidatos) == 1})
            lid["actuales"][i] = elegido
            equipos.append({"equipo": i, "candidatos": [self.nombre_participante(c) for c in candidatos],
                            "indice": candidatos.index(elegido) if elegido else None,
                            "elegido": self.nombre_participante(elegido) if elegido else None,
                            "completo": elegido is None})
        lid["sorteo"] = {"ronda": numero, "ciclo": lid["ciclo"], "nuevo_ciclo": nuevo_ciclo, "equipos": equipos}
        lid["antes_del_sorteo"] = antes
        self.estado["fase"] = "lideres"
        self._evento("sorteo_lideres", "", extra=dict(lid["sorteo"], **self.info_ronda(numero)))
        partes = [f"{self.nombre(e['equipo'])}: {e['elegido'] or 'sin nueva selección (ciclo completo)'}" for e in equipos]
        return f"Sorteo de líderes de la ronda {numero}" + (" · ¡nuevo ciclo!" if nuevo_ciclo else "") + " · " + " · ".join(partes)

    def _a_revertir_lideres(self, accion):
        """Anula el sorteo de líderes de la ronda que aún no empezó (se recupera el historial anterior)."""
        self._exigir_fase("lideres")
        antes = self.estado["lideres"]["antes_del_sorteo"]
        self.estado["lideres"] = dict(copy.deepcopy(antes["lideres"]), antes_del_sorteo=None)
        self.estado["fase"] = antes["fase"]
        self._evento("lideres_revertidos", "")
        return "Se revirtió el sorteo de líderes (vuelven a estar disponibles)"

    # ------------------------------------------------------------------ rondas
    def _a_iniciar_ronda(self, accion):
        """Empieza la ronda con la siguiente pregunta sorteada (o la indicada) y los líderes sorteados."""
        self._exigir_fase("lideres")
        jugadas = len(self.estado["historial_rondas"])
        numero = jugadas + 1
        if numero > self.total_rondas():
            raise ErrorJuego("Ya se jugaron todas las rondas configuradas.")
        pid = accion.get("pregunta_id") or self.siguiente_pregunta()
        if not pid:
            raise ErrorJuego("No quedan preguntas sin usar en el orden sorteado.")
        if pid not in self.preguntas:
            raise ErrorJuego("Pregunta no encontrada.")
        if pid in self.estado["preguntas_usadas"] and not accion.get("repetir"):
            raise ErrorJuego("Esa pregunta ya se usó en esta partida.")
        pregunta = self.preguntas[pid]
        tablero = [a["id"] for a in self.tablero_de(pregunta)]
        if not tablero:
            raise ErrorJuego("Esta pregunta no tiene respuestas válidas para el tablero; revísala antes de usarla.")
        anterior = copy.deepcopy(self.estado["ronda"])
        if anterior:
            anterior.pop("anterior", None)
        info = self.info_ronda(numero)
        self.estado["ronda"] = {
            "numero": numero,
            "pregunta_id": pid,
            "tipo": info["tipo"],
            "extra_n": info["extra_n"],
            "multiplicador": info["multiplicador"],
            "maximo": info["maximo"],
            "lideres": list(self.estado["lideres"]["actuales"]),
            "tablero": tablero,
            "reveladas": {},
            "banco": 0,
            "cara_a_cara": self.cara_a_cara_inicial(),
            "control": None,
            "strikes": 0,
            "robo": {"equipo": None, "resultado": None, "respuesta_id": None},
            "ganador": None,
            "asignada": False,
            "asignada_a": None,
            "puntos_asignados": 0,
            "anterior": anterior,              # para poder cancelar la ronda
        }
        if pid not in self.estado["preguntas_usadas"]:
            self.estado["preguntas_usadas"].append(pid)
        self.estado["fase"] = "cara_a_cara"
        titulo = f"¡Ronda extra {info['extra_n']}!" if info["tipo"] == "extra" else f"Ronda {numero}"
        self._evento("nueva_ronda", titulo, extra=info)
        return f"Inicia la ronda {numero}" + (f" (extra ×{info['multiplicador']})" if info["tipo"] == "extra" else "") + \
            f" con la pregunta {pregunta['numero']}"

    def _a_cancelar_ronda(self, accion):
        """Cancela la ronda en curso antes de asignar el banco: la pregunta vuelve a quedar disponible
        y se regresa al paso «líderes sorteados» (desde allí también se puede revertir el sorteo)."""
        self._exigir_fase("cara_a_cara", "decision", "juego", "robo", "resuelta")
        r = self.estado["ronda"]
        if r["pregunta_id"] in self.estado["preguntas_usadas"]:
            self.estado["preguntas_usadas"].remove(r["pregunta_id"])
        self.estado["ronda"] = r["anterior"]
        self.estado["fase"] = "lideres"
        self._evento("ronda_cancelada", "Ronda cancelada")
        return f"Ronda {r['numero']} cancelada (no se asignaron puntos; la pregunta vuelve a estar disponible)"

    # ------------------------------------------------------------------ cara a cara
    # Reglas (ver docs/REGLAS_CARA_A_CARA.md):
    #  1. Responde primero el líder que levantó la mano primero en Google Meet (lo marca el presentador).
    #  2. Si da la respuesta n.º 1 del tablero, su equipo gana de inmediato.
    #  3. Una respuesta válida queda como «referencia»: el otro líder debe SUPERARLA en puntos.
    #     Más puntos → gana el segundo; menos puntos o «no está» → gana el de la referencia.
    #     Mismos puntos → desempate configurable («desempate»: vuelven a responder; «primero»: gana quien respondió antes).
    #  4. Sin referencia, una respuesta que no está suma un error al líder y pasa el turno al otro.
    #     Cada líder tiene como máximo 2 errores. Si ambos llegan a 2, hay que cambiar a los dos líderes.
    #  5. Los errores del cara a cara son independientes de los 3 strikes de la ronda.
    ERRORES_MAX_CARA_A_CARA = 2

    @staticmethod
    def cara_a_cara_inicial():
        """Estado vacío del cara a cara de una ronda."""
        return {"primero": None, "turno": None, "intentos": [], "referencia": None, "errores": [0, 0],
                "ganador": None, "motivo": None, "omitido": False, "bloqueado": False, "cambios_lider": 0}

    def _cac(self):
        """Estado del cara a cara de la ronda en curso."""
        return self.estado["ronda"]["cara_a_cara"]

    def _siguiente_turno(self, despues_de):
        """Pasa el turno al otro líder; si ya agotó sus errores, sigue el mismo; si ambos los agotaron, se bloquea."""
        cac = self._cac()
        rival = otro(despues_de)
        if cac["errores"][rival] < self.ERRORES_MAX_CARA_A_CARA:
            cac["turno"] = rival
        elif cac["errores"][despues_de] < self.ERRORES_MAX_CARA_A_CARA:
            cac["turno"] = despues_de
        else:
            cac["turno"] = None
            cac["bloqueado"] = True

    def _ganar_cara_a_cara(self, eq, motivo):
        """Cierra el cara a cara con un ganador y pasa a «jugar o pasar» (o directamente a la ronda)."""
        r = self.estado["ronda"]
        cac = r["cara_a_cara"]
        cac.update(ganador=eq, motivo=motivo, turno=None, bloqueado=False)
        textos = {"numero_uno": "¡Dio la respuesta número 1!", "supera": "¡Superó la respuesta rival!",
                  "no_supera": "El rival no superó su respuesta", "rival_sin_intentos": "El rival ya no tiene intentos",
                  "empate_primero": "Empate: gana quien respondió primero", "manual": "Decisión del presentador",
                  "correccion": "Corregido por el presentador"}
        if self.cfg["permitir_pasar"]:
            self.estado["fase"] = "decision"
        else:
            r["control"] = eq
            self.estado["fase"] = "juego"
        self._evento("cara_a_cara_ganado", f"¡{self.nombre(eq)} gana el cara a cara!", eq,
                     {"motivo": motivo, "detalle": textos.get(motivo, ""), "decide": self.cfg["permitir_pasar"]})
        return textos.get(motivo, "")

    def _a_primero_en_responder(self, accion):
        """Registra qué líder levantó la mano primero en Google Meet: le toca responder.
        Se puede corregir mientras no haya respondido nadie (desde el último cambio de líderes)."""
        self._exigir_fase("cara_a_cara")
        cac = self._cac()
        eq = self._equipo(accion["equipo"])
        if cac["intentos"] and any(i["ronda_lideres"] == cac["cambios_lider"] for i in cac["intentos"]):
            raise ErrorJuego("Ya respondió un líder: para corregir quién levantó la mano primero usa «Deshacer».")
        cac.update(primero=eq, turno=eq)
        self._evento("turno", f"Responde primero: {self.nombre(eq)}", eq)
        return f"Cara a cara: {self.nombre(eq)} levantó la mano primero"

    def _a_respuesta_cara_a_cara(self, accion):
        """Respuesta del líder que tiene el turno: una casilla del tablero o «no está» (respuesta_id = None)."""
        self._exigir_fase("cara_a_cara")
        r = self.estado["ronda"]
        cac = r["cara_a_cara"]
        eq = self._equipo(accion["equipo"])
        if cac["bloqueado"]:
            raise ErrorJuego("Los dos líderes agotaron sus 2 intentos: cambia a ambos líderes para repetir el desempate.")
        if cac["turno"] is None:
            raise ErrorJuego("Primero marca qué líder levantó la mano primero en Google Meet.")
        if eq != cac["turno"]:
            raise ErrorJuego(f"Ahora le toca responder al líder de {self.nombre(cac['turno'])}.")
        rid = accion.get("respuesta_id")
        intento = {"equipo": eq, "respuesta_id": rid, "puntos": 0, "ronda_lideres": cac["cambios_lider"]}
        cac["intentos"].append(intento)
        if not rid:
            cac["errores"][eq] += 1
            self._evento("no_esta", "¡No está en el tablero!", eq,
                         {"errores": cac["errores"][eq], "maximo": self.ERRORES_MAX_CARA_A_CARA})
            desc = f"Cara a cara: la respuesta de {self.nombre(eq)} no está (error {cac['errores'][eq]} de {self.ERRORES_MAX_CARA_A_CARA})"
            if cac["referencia"]:
                return desc + " · " + self._ganar_cara_a_cara(cac["referencia"]["equipo"], "no_supera")
            self._siguiente_turno(eq)
            if cac["bloqueado"]:
                self._evento("cara_a_cara_bloqueado", "¡Ninguno acertó!", None, {"errores": cac["errores"]})
                desc += " · ambos líderes agotaron sus intentos"
            return desc
        a = self._respuesta_oculta(rid)
        _, pts, _ = self._revelar(rid, eq, "cara_a_cara", True)
        intento["puntos"] = pts
        pos = r["tablero"].index(rid) + 1
        self._evento("correcta", "¡Respuesta correcta!", eq, {"posicion": pos})
        desc = f"Cara a cara: {self.nombre(eq)} encontró «{a['etiqueta']}» ({pts} pts)"
        maximo = self.puntos_respuesta(self._buscar_respuesta(r["tablero"][0]))
        if pts >= maximo:
            return desc + " · " + self._ganar_cara_a_cara(eq, "numero_uno")
        ref = cac["referencia"]
        if ref is None:
            cac["referencia"] = {"equipo": eq, "puntos": pts, "respuesta_id": rid}
            rival = otro(eq)
            if cac["errores"][rival] >= self.ERRORES_MAX_CARA_A_CARA:
                return desc + " · " + self._ganar_cara_a_cara(eq, "rival_sin_intentos")
            cac["turno"] = rival
            return desc + f" · {self.nombre(rival)} debe superar {pts} pts"
        if pts > ref["puntos"]:
            return desc + " · " + self._ganar_cara_a_cara(eq, "supera")
        if pts < ref["puntos"]:
            return desc + " · " + self._ganar_cara_a_cara(ref["equipo"], "no_supera")
        # Empate en puntos
        quedan = any(x not in r["reveladas"] for x in r["tablero"])
        if self.cfg["empate_cara_a_cara"] == "desempate" and quedan:
            cac["referencia"] = None
            primero = cac["primero"] if cac["primero"] is not None else ref["equipo"]
            cac["turno"] = primero if cac["errores"][primero] < self.ERRORES_MAX_CARA_A_CARA else otro(primero)
            self._evento("empate_cara_a_cara", "¡Empate! Nueva respuesta de desempate", None, {"puntos": pts})
            return desc + f" · empate a {pts} pts: desempate, responde {self.nombre(cac['turno'])}"
        return desc + " · " + self._ganar_cara_a_cara(ref["equipo"], "empate_primero")

    def _a_ganador_cara_a_cara(self, accion):
        """Decisión manual del presentador sobre el ganador del cara a cara (por ejemplo, en una disputa)."""
        self._exigir_fase("cara_a_cara")
        eq = self._equipo(accion["equipo"])
        self._ganar_cara_a_cara(eq, "manual")
        return f"{self.nombre(eq)} gana el cara a cara (decisión del presentador)"

    def _a_corregir_ganador_cara_a_cara(self, accion):
        """Corrige el ganador antes de que empiece la ronda: el cara a cara pasa al otro equipo."""
        self._exigir_fase("decision")
        r = self.estado["ronda"]
        nuevo = otro(r["cara_a_cara"]["ganador"])
        self._ganar_cara_a_cara(nuevo, "correccion")
        return f"Corrección: el cara a cara lo gana {self.nombre(nuevo)}"

    def _a_omitir_cara_a_cara(self, accion):
        """Salta el cara a cara: el presentador elige qué equipo empieza la ronda. No revela nada ni registra errores."""
        self._exigir_fase("cara_a_cara")
        r = self.estado["ronda"]
        cac = r["cara_a_cara"]
        # Se puede omitir mientras los líderes actuales no hayan respondido y no haya casillas reveladas
        # (por ejemplo, justo después de cambiar a ambos líderes).
        if any(i["ronda_lideres"] == cac["cambios_lider"] for i in cac["intentos"]) or r["reveladas"]:
            raise ErrorJuego("El cara a cara ya empezó (hay respuestas registradas). Usa «Deshacer» o elige el ganador manualmente.")
        eq = self._equipo(accion["equipo"])
        r["cara_a_cara"].update(omitido=True, turno=None, ganador=eq, motivo="omitido")
        r["control"] = eq
        self.estado["fase"] = "juego"
        self._evento("turno", f"¡{self.nombre(eq)} empieza la ronda!", eq, {"omitido": True})
        return f"Cara a cara omitido: empieza {self.nombre(eq)}"

    def _sortear_lider_equipo(self, equipo, excluir):
        """Elige al azar un nuevo líder del equipo (distinto del actual), preferentemente entre quienes aún no lo
        han sido en este ciclo. Devuelve (elegido, candidatos); si el equipo tiene una sola persona, la repite."""
        lid = self.estado["lideres"]
        miembros = self.cfg["equipos"][equipo]["integrantes"]
        candidatos = [m for m in miembros if m not in lid["usados"][equipo] and m != excluir]
        if not candidatos:
            candidatos = [m for m in miembros if m != excluir] or list(miembros)
        elegido = self.rng.choice(candidatos)
        if elegido not in lid["usados"][equipo]:
            lid["usados"][equipo].append(elegido)
        return elegido, candidatos

    def _a_cambiar_lideres_cara_a_cara(self, accion):
        """Cuando ambos líderes agotaron sus 2 errores: sortea dos líderes nuevos y reinicia el cara a cara
        (las casillas ya reveladas siguen reveladas; los strikes de la ronda no cambian)."""
        self._exigir_fase("cara_a_cara")
        r = self.estado["ronda"]
        cac = r["cara_a_cara"]
        if not cac["bloqueado"]:
            raise ErrorJuego("Solo se cambian los líderes cuando ambos agotaron sus 2 intentos en el cara a cara.")
        lid = self.estado["lideres"]
        equipos = []
        for i in (0, 1):
            anterior = r["lideres"][i]
            elegido, candidatos = self._sortear_lider_equipo(i, anterior)
            r["lideres"][i] = lid["actuales"][i] = elegido
            lid["historial"].append({"ronda": r["numero"], "ciclo": lid["ciclo"], "equipo": i, "participante": elegido,
                                     "nombre": self.nombre_participante(elegido), "unico": len(candidatos) == 1,
                                     "motivo": "cambio en el cara a cara"})
            equipos.append({"equipo": i, "candidatos": [self.nombre_participante(c) for c in candidatos],
                            "indice": candidatos.index(elegido), "elegido": self.nombre_participante(elegido),
                            "completo": False})
        cac.update(primero=None, turno=None, referencia=None, errores=[0, 0], bloqueado=False,
                   cambios_lider=cac["cambios_lider"] + 1)
        self._evento("sorteo_lideres", "", extra=dict(self.info_ronda(r["numero"]), ronda=r["numero"], ciclo=lid["ciclo"],
                                                      nuevo_ciclo=False, equipos=equipos, motivo="cambio_cara_a_cara"))
        return "Cambio de líderes en el cara a cara: " + " · ".join(f"{self.nombre(e['equipo'])}: {e['elegido']}" for e in equipos)

    def _a_decidir(self, accion):
        """El ganador del cara a cara juega la ronda o se la pasa al rival."""
        self._exigir_fase("decision")
        r = self.estado["ronda"]
        ganador = r["cara_a_cara"]["ganador"]
        juega = ganador if accion["jugar"] else otro(ganador)
        r["control"] = juega
        self.estado["fase"] = "juego"
        if self._todas_reveladas():
            return self._resolver(juega, "tablero_completo")
        self._evento("turno", f"¡{self.nombre(juega)} juega la ronda!", juega)
        return f"{self.nombre(ganador)} decide {'jugar' if accion['jugar'] else 'pasar'}: juega {self.nombre(juega)}"

    def _a_revelar(self, accion):
        """Respuesta correcta durante la ronda (o revelar al final, sin puntos)."""
        rid = accion["respuesta_id"]
        fase = self.estado["fase"]
        if fase in ("resuelta", "asignada", "fin", "lideres") and self.estado["ronda"]:
            a = self._respuesta_oculta(rid)
            self._revelar(rid, None, "final", False)
            self._evento("revelar_final", "", extra={"posicion": self.estado["ronda"]["tablero"].index(rid) + 1})
            return f"Se mostró «{a['etiqueta']}» al final (sin puntos)"
        self._exigir_fase("juego")
        r = self.estado["ronda"]
        a = self._respuesta_oculta(rid)
        _, pts, sumado = self._revelar(rid, r["control"], "juego", True)
        pos = r["tablero"].index(rid) + 1
        self._evento("correcta", "¡Respuesta correcta!", r["control"], {"posicion": pos})
        desc = f"{self.nombre(r['control'])} encontró «{a['etiqueta']}» (+{sumado} al banco)"
        if self._todas_reveladas():
            self._resolver(r["control"], "tablero_completo")
            desc += " · tablero completo"
        return desc

    def _a_revelar_restantes(self, accion):
        """Muestra todas las casillas que nadie encontró (sin sumar puntos)."""
        self._exigir_fase("resuelta", "asignada", "fin")
        r = self.estado["ronda"]
        ocultas = [rid for rid in r["tablero"] if rid not in r["reveladas"]]
        if not ocultas:
            raise ErrorJuego("No quedan respuestas ocultas.")
        for rid in ocultas:
            self._revelar(rid, None, "final", False)
        self._evento("revelar_final", "", extra={"posicion": r["tablero"].index(ocultas[0]) + 1})
        return f"Se mostraron {len(ocultas)} respuestas restantes (sin puntos)"

    def _a_strike(self, accion):
        """Respuesta incorrecta; al tercer strike se abre la oportunidad de robo."""
        self._exigir_fase("juego")
        r = self.estado["ronda"]
        if r["strikes"] >= 3:
            raise ErrorJuego("Ya hay tres strikes.")
        r["strikes"] += 1
        n = r["strikes"]
        if n == 3:
            r["robo"]["equipo"] = otro(r["control"])
            self.estado["fase"] = "robo"
            self._evento("robo_oportunidad", "¡Oportunidad de robo!", r["robo"]["equipo"], {"strikes": 3})
            return f"Strike 3 para {self.nombre(r['control'])}: oportunidad de robo para {self.nombre(otro(r['control']))}"
        texto = "¡Un strike!" if n == 1 else "¡Segundo strike! El rival se prepara para robar"
        self._evento("strike", texto, r["control"], {"strikes": n})
        return f"Strike {n} para {self.nombre(r['control'])}"

    def _a_resolver_robo(self, accion):
        """Resultado del único intento de robo del equipo rival."""
        self._exigir_fase("robo")
        r = self.estado["ronda"]
        if r["robo"]["resultado"] is not None:
            raise ErrorJuego("El robo ya se resolvió.")
        ladron = r["robo"]["equipo"]
        rid = accion.get("respuesta_id")
        if rid:
            a = self._respuesta_oculta(rid)
            self._revelar(rid, ladron, "robo", self.cfg["robo_suma_respuesta"])
            r["robo"].update(resultado="exitoso", respuesta_id=rid)
            self._resolver(ladron, "robo_exitoso")
            return f"Robo exitoso de {self.nombre(ladron)} con «{a['etiqueta']}»"
        r["robo"]["resultado"] = "fallido"
        self._resolver(r["control"], "robo_fallido")
        return f"Robo fallido de {self.nombre(ladron)}"

    def _resolver(self, ganador, motivo):
        """Cierra la ronda con un ganador (falta asignar el banco)."""
        r = self.estado["ronda"]
        r["ganador"] = ganador
        self.estado["fase"] = "resuelta"
        textos = {
            "robo_exitoso": f"¡Robo exitoso! {self.nombre(ganador)} se lleva el banco",
            "robo_fallido": f"¡Robo fallido! El banco es para {self.nombre(ganador)}",
            "tablero_completo": f"¡Tablero completo! {self.nombre(ganador)} gana la ronda",
            "manual": f"{self.nombre(ganador)} gana la ronda",
        }
        self._evento(motivo, textos[motivo], ganador, {"banco": r["banco"]})
        return textos[motivo]

    def _a_cerrar_ronda(self, accion):
        """Cierre manual por decisión de los presentadores (por ejemplo, una disputa)."""
        self._exigir_fase("cara_a_cara", "decision", "juego", "robo")
        eq = self._equipo(accion["equipo"])
        self._resolver(eq, "manual")
        return f"Ronda cerrada manualmente: gana {self.nombre(eq)}"

    def _a_asignar_banco(self, accion):
        """Suma el banco al marcador del ganador (una sola vez) y lo anota en el historial."""
        self._exigir_fase("resuelta")
        r = self.estado["ronda"]
        if r["asignada"]:
            raise ErrorJuego("El banco de esta ronda ya fue asignado.")
        eq = r["ganador"] if accion.get("equipo") is None else self._equipo(accion["equipo"])
        self.estado["puntajes"][eq] += r["banco"]
        r.update(asignada=True, asignada_a=eq, puntos_asignados=r["banco"])
        self.estado["fase"] = "asignada"
        p = self.pregunta_actual()
        self.estado["historial_rondas"].append({
            "numero": r["numero"], "pregunta_id": p["id"], "pregunta": p["texto"], "tipo": r["tipo"],
            "ganador": eq, "puntos": r["banco"], "multiplicador": r["multiplicador"],
            "robo": r["robo"]["resultado"],
            "cara_a_cara": {"ganador": r["cara_a_cara"]["ganador"], "motivo": r["cara_a_cara"]["motivo"],
                            "omitido": r["cara_a_cara"]["omitido"], "errores": r["cara_a_cara"]["errores"],
                            "cambios_lider": r["cara_a_cara"]["cambios_lider"]},
            "lideres": [self.nombre_participante(x) if x else None for x in r["lideres"]],
        })
        self._evento("ronda_ganada", f"¡{self.nombre(eq)} gana la ronda!", eq, {"puntos": r["banco"]})
        return f"Banco de {r['banco']} pts asignado a {self.nombre(eq)}"

    def _a_ajustar_puntaje(self, accion):
        """Corrección manual del marcador (queda registrada en la bitácora)."""
        if self.estado["fase"] in ("preparacion", "lista") and not self.estado["historial_rondas"]:
            raise ErrorJuego("Aún no ha empezado el juego.")
        eq = self._equipo(accion["equipo"])
        delta = int(accion["delta"])
        if delta == 0:
            raise ErrorJuego("El ajuste no puede ser cero.")
        self.estado["puntajes"][eq] += delta
        motivo = str(accion.get("motivo", "")).strip()[:120]
        return f"Ajuste manual {delta:+d} pts a {self.nombre(eq)}" + (f" ({motivo})" if motivo else "")

    def _a_finalizar_juego(self, accion):
        """Termina la partida y calcula el ganador (o empate)."""
        fase = self.estado["fase"]
        if fase == "fin":
            raise ErrorJuego("El juego ya terminó.")
        if fase not in ("asignada", "preparacion", "lista", "lideres") and not accion.get("forzar"):
            raise ErrorJuego("Hay una ronda sin terminar. Asigna el banco primero o confirma el cierre forzado.")
        a, b = self.estado["puntajes"]
        ganador = None if a == b else (0 if a > b else 1)
        self.estado["fase"] = "fin"
        self.estado["resultado_final"] = {"ganador": ganador, "puntajes": [a, b]}
        texto = "¡Empate!" if ganador is None else f"¡{self.nombre(ganador)} es el equipo ganador!"
        self._evento("fin_juego", texto, ganador)
        return "Juego finalizado: " + texto

    def _a_reiniciar_marcador(self, accion):
        """Pone el marcador en 0 - 0 (se puede deshacer)."""
        self.estado["puntajes"] = [0, 0]
        return "Marcador reiniciado a 0 - 0"

    # ------------------------------------------------------------------ vistas
    def _equipos_publicos(self):
        """Equipos tal como se muestran al público: nombre, líder actual e integrantes."""
        actuales = self.estado["lideres"]["actuales"]
        en_ronda = self.estado["fase"] not in ("preparacion", "lista")
        info = self.info_lideres()
        salida = []
        for i, eq in enumerate(self.cfg["equipos"]):
            lider = actuales[i] if en_ronda else None
            salida.append({
                "nombre": self.nombre(i),
                "lider": self.nombre_participante(lider) if lider else "",
                "sin_lider_nuevo": en_ronda and lider is None and self.estado["lideres"]["sorteo"] is not None,
                "integrantes": [self.nombre_participante(x) for x in eq["integrantes"]],
                "lideres_pendientes": len(info[i]["pendientes"]),
            })
        return salida

    def vista_publica(self):
        """Solo lo que puede ver el público. Nunca incluye respuestas ocultas ni el orden de las preguntas."""
        e = self.estado
        r = e["ronda"]
        ronda = None
        if r:
            p = self.pregunta_actual()
            por_id = {a["id"]: a for a in p["respuestas"]}
            casillas = []
            for i, rid in enumerate(r["tablero"]):
                rev = r["reveladas"].get(rid)
                if rev:
                    casillas.append({"posicion": i + 1, "revelada": True, "texto": por_id[rid]["etiqueta"],
                                     "puntos": rev["puntos"], "equipo": rev["equipo"], "como": rev["como"]})
                else:
                    casillas.append({"posicion": i + 1, "revelada": False})
            ronda = {
                "numero": r["numero"], "pregunta": p["texto"], "multiplicador": r["multiplicador"],
                "tipo": r["tipo"], "extra_n": r["extra_n"], "maximo": r["maximo"],
                "casillas": casillas, "banco": r["banco"], "strikes": r["strikes"], "control": r["control"],
                "cara_a_cara": {k: r["cara_a_cara"][k] for k in ("primero", "turno", "errores", "ganador", "motivo",
                                                                 "omitido", "bloqueado")}
                | {"referencia": {"equipo": r["cara_a_cara"]["referencia"]["equipo"],
                                  "puntos": r["cara_a_cara"]["referencia"]["puntos"]} if r["cara_a_cara"]["referencia"] else None},
                "robo": dict(r["robo"], respuesta_id=None), "ganador": r["ganador"],
                "asignada": r["asignada"], "asignada_a": r["asignada_a"], "puntos_asignados": r["puntos_asignados"],
            }
        c = self.cfg
        jugadas = len(e["historial_rondas"])
        proxima = self.info_ronda(jugadas + 1) if jugadas < self.total_rondas() else None
        sorteo = self.prep["sorteo_equipos"]
        return {
            "version": e["version"], "titulo": c["titulo"], "fase": e["fase"],
            "equipos": self._equipos_publicos(), "puntajes": e["puntajes"], "total_rondas": self.total_rondas(),
            "rondas_principales": self.rondas_principales(), "rondas_extra": self.prep["rondas_extra"],
            "rondas_jugadas": jugadas, "proxima_ronda": proxima, "partida_confirmada": self.prep["confirmada"],
            "equipos_sorteados": bool(sorteo), "participantes": len(self.prep["participantes"]),
            "ciclo_lideres": e["lideres"]["ciclo"],
            "sonido": c["sonido"], "animaciones": c["animaciones"],
            "musica": c["musica"], "efectos": c["efectos"], "volumen": c["volumen"],
            "ronda": ronda, "evento": e["evento"], "resultado_final": e["resultado_final"],
            "historial": [{"numero": h["numero"], "ganador": h["ganador"], "puntos": h["puntos"]} for h in e["historial_rondas"]],
        }

    def vista_presentador(self):
        """Todo el estado más datos calculados para el panel privado (nunca se envía al público)."""
        e = copy.deepcopy(self.estado)
        e["nombres_fases"] = FASES
        e["fase_nombre"] = FASES[e["fase"]]
        e["puede_deshacer"] = bool(self.pila_deshacer)
        e["ultima_deshacible"] = self.pila_deshacer[-1].get("_descripcion") if self.pila_deshacer else None
        e["errores_max_cara_a_cara"] = self.ERRORES_MAX_CARA_A_CARA
        e["tableros"] = {pid: {"ids": [a["id"] for a in self.tablero_de(p)],
                               "puntos": {a["id"]: self.puntos_respuesta(a) for a in p["respuestas"]}}
                         for pid, p in self.preguntas.items()}
        e["nombres_participantes"] = {p["id"]: p["nombre"] for p in self.prep["participantes"]}
        e["validaciones"] = self.validar_preparacion() if e["fase"] == "preparacion" else []
        e["minimo_principales"] = self.minimo_principales()
        e["rondas_principales"] = self.rondas_principales()
        e["total_rondas"] = self.total_rondas()
        e["plan_rondas"] = self.plan_rondas()
        e["tamanos_equipos"] = self.tamanos_equipos()
        e["preguntas_disponibles"] = len(self.preguntas_disponibles())
        e["proxima_pregunta"] = self.siguiente_pregunta()
        e["info_lideres"] = self.info_lideres()
        e["equipos_vista"] = self._equipos_publicos()
        if e["ronda"]:
            e["ronda"].pop("anterior", None)  # copia interna para cancelar; el panel no la necesita
        return e
