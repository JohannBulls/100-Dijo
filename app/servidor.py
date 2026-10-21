"""Servidor local del juego.

Sirve las páginas (pantalla pública y panel del presentador) y guarda el estado
de la partida. Solo escucha en este computador (127.0.0.1): nadie de la red
puede conectarse. Usa únicamente la biblioteca estándar de Python.

Rutas:
    GET  /                 página de inicio (enlaces a las dos pantallas)
    GET  /publico          pantalla pública (la que se comparte en Google Meet)
    GET  /presentador      panel privado del presentador
    GET  /css/…, /js/…     archivos estáticos de app/web
    GET  /api/publico      estado visible para el público (sin respuestas ocultas)
    GET  /api/presentador  estado completo para el panel
    GET  /api/preguntas    preguntas procesadas (con frecuencias y respuestas originales)
    POST /api/accion       {"version": n, "accion": {"tipo": …}} → aplica una acción

«Espera larga»: /api/publico?esperar=N y /api/presentador?esperar=N no responden
hasta que la versión del estado sea distinta de N (o pasen 20 s). Así las pantallas
se actualizan al instante sin depender de temporizadores del navegador.

Uso:  python app/servidor.py [--puerto 8765] [--no-abrir]
"""
import argparse
import json
import os
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from juego import ErrorJuego, Juego  # noqa: E402

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(RAIZ, "app", "web")
DATOS = os.path.join(RAIZ, "datos")
ARCHIVO_PREGUNTAS = os.path.join(DATOS, "preguntas_procesadas.json")
ARCHIVO_PARTIDA = os.path.join(DATOS, "partida_guardada.json")

TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8",
         ".css": "text/css; charset=utf-8", ".svg": "image/svg+xml", ".png": "image/png",
         ".ico": "image/x-icon"}
PAGINAS = {"/": "inicio.html", "/publico": "publico.html", "/presentador": "presentador.html"}
ESPERA_MAXIMA = 20  # segundos que una pantalla espera un cambio antes de volver a preguntar


class Servicio:
    """Mantiene el juego en memoria, lo protege con un candado y lo guarda en disco."""

    def __init__(self, archivo_preguntas=ARCHIVO_PREGUNTAS, archivo_partida=ARCHIVO_PARTIDA):
        """Carga las preguntas procesadas y, si existe, la partida guardada."""
        with open(archivo_preguntas, encoding="utf-8") as f:
            self.datos = json.load(f)
        self.archivo_partida = archivo_partida
        self.candado = threading.Lock()
        self.cambio = threading.Condition(self.candado)
        estado, pila = None, None
        if archivo_partida and os.path.exists(archivo_partida):
            try:
                with open(archivo_partida, encoding="utf-8") as f:
                    guardado = json.load(f)
                estado, pila = guardado["estado"], guardado.get("deshacer", [])
            except (OSError, ValueError, KeyError):
                print("Aviso: no se pudo leer la partida guardada; se inicia una nueva.")
        self.juego = Juego(self.datos["preguntas"], estado, pila)

    def guardar(self):
        """Guarda la partida en disco de forma atómica (archivo temporal + reemplazo)."""
        if not self.archivo_partida:
            return
        tmp = self.archivo_partida + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"estado": self.juego.estado, "deshacer": self.juego.pila_deshacer}, f, ensure_ascii=False)
        os.replace(tmp, self.archivo_partida)

    def accion(self, cuerpo):
        """Aplica una acción del panel, guarda la partida y avisa a las pantallas en espera."""
        with self.candado:
            version = cuerpo.get("version")
            self.juego.aplicar(cuerpo.get("accion") or {}, version)
            self.guardar()
            self.cambio.notify_all()
            return self.juego.vista_presentador()

    def _esperar(self, version, espera):
        """«Espera larga»: si la pantalla ya tiene la versión actual, espera hasta que cambie.
        Así la pantalla se actualiza al instante aunque el navegador frene los temporizadores
        de las pestañas en segundo plano (por ejemplo, la pestaña compartida en Meet)."""
        if version is not None:
            self.cambio.wait_for(lambda: self.juego.estado["version"] != version, timeout=espera)

    def publico(self, version=None, espera=ESPERA_MAXIMA):
        """Vista pública (sin respuestas ocultas). Con `version`, espera hasta que haya cambios."""
        with self.candado:
            self._esperar(version, espera)
            return self.juego.vista_publica()

    def presentador(self, version=None, espera=ESPERA_MAXIMA):
        """Vista completa para el panel privado. Con `version`, espera hasta que haya cambios."""
        with self.candado:
            self._esperar(version, espera)
            return self.juego.vista_presentador()


def crear_manejador(servicio):
    """Crea la clase que atiende las peticiones HTTP usando el servicio indicado."""
    class Manejador(BaseHTTPRequestHandler):
        """Atiende páginas, archivos estáticos y la API JSON del juego."""

        def log_message(self, *args):
            """Silencia el registro de cada petición para que la ventana del servidor quede limpia."""
            pass

        def _enviar(self, codigo, cuerpo, tipo="application/json; charset=utf-8"):
            """Envía una respuesta (JSON o archivo) sin caché."""
            datos = cuerpo if isinstance(cuerpo, bytes) else json.dumps(cuerpo, ensure_ascii=False).encode("utf-8")
            try:
                self.send_response(codigo)
                self.send_header("Content-Type", tipo)
                self.send_header("Content-Length", str(len(datos)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(datos)
            except ConnectionError:
                pass  # la pestaña se cerró mientras esperaba: no es un error del juego

        def do_GET(self):
            """GET: páginas, archivos de app/web y vistas del juego (/api/publico, /api/presentador, /api/preguntas)."""
            url = urlparse(self.path)
            ruta = url.path
            if ruta in ("/api/publico", "/api/presentador"):
                try:
                    version = int(parse_qs(url.query)["esperar"][0])
                except (KeyError, ValueError):
                    version = None
                vista = servicio.publico if ruta == "/api/publico" else servicio.presentador
                return self._enviar(200, vista(version))
            if ruta == "/api/preguntas":
                return self._enviar(200, servicio.datos)
            nombre = PAGINAS.get(ruta, ruta.lstrip("/"))
            archivo = os.path.normpath(os.path.join(WEB, nombre))
            if not archivo.startswith(WEB) or not os.path.isfile(archivo):
                return self._enviar(404, b"No encontrado", "text/plain; charset=utf-8")
            with open(archivo, "rb") as f:
                self._enviar(200, f.read(), TIPOS.get(os.path.splitext(archivo)[1], "application/octet-stream"))

        def do_POST(self):
            """POST /api/accion: aplica una acción del panel del presentador."""
            if urlparse(self.path).path != "/api/accion":
                return self._enviar(404, {"error": "No encontrado"})
            try:
                largo = int(self.headers.get("Content-Length", 0))
                cuerpo = json.loads(self.rfile.read(largo) or b"{}")
                self._enviar(200, {"ok": True, "estado": servicio.accion(cuerpo)})
            except ErrorJuego as e:
                self._enviar(409, {"ok": False, "error": str(e), "estado": servicio.presentador()})
            except ValueError:
                self._enviar(400, {"ok": False, "error": "Solicitud no válida."})

    return Manejador


def main():
    """Punto de entrada: lee los argumentos, inicia el servidor y abre el navegador."""
    parser = argparse.ArgumentParser(description="Servidor local del juego")
    parser.add_argument("--puerto", type=int, default=8765)
    parser.add_argument("--no-abrir", action="store_true", help="no abrir el navegador automáticamente")
    args = parser.parse_args()
    if not os.path.exists(ARCHIVO_PREGUNTAS):
        print("No existe datos/preguntas_procesadas.json. Ejecuta primero PROCESAR_EXCEL.bat")
        sys.exit(1)
    servicio = Servicio()
    try:
        httpd = ThreadingHTTPServer(("127.0.0.1", args.puerto), crear_manejador(servicio))
    except OSError:
        print(f"\nEl puerto {args.puerto} ya está en uso. ¿El juego ya está abierto en otra ventana?")
        print(f"Abre http://localhost:{args.puerto} en el navegador, o cierra la otra ventana.\n")
        sys.exit(1)
    url = f"http://localhost:{args.puerto}/"
    print("=" * 60)
    print(f"  {servicio.juego.cfg['titulo']} - juego en marcha")
    print(f"  Inicio:              {url}")
    print(f"  Pantalla pública:    {url}publico")
    print(f"  Panel presentador:   {url}presentador")
    print("  Para DETENER el juego: cierra esta ventana o pulsa Ctrl + C")
    print("=" * 60)
    if not args.no_abrir:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        print("Juego detenido. La partida quedó guardada.")


if __name__ == "__main__":
    main()
