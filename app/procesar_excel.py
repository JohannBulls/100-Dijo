"""Convierte el Excel de respuestas en preguntas listas para el juego.

Entradas (no se modifican):
  - El Excel original del formulario (por defecto, el .xlsx de la carpeta principal).
  - datos/agrupaciones.json: decisiones de agrupación (qué respuestas originales
    forman cada respuesta consolidada). Es editable a mano.

Salidas:
  - datos/preguntas_procesadas.json  (lo usa el juego)
  - datos/preguntas_procesadas.xlsx  (reporte para revisar y auditar)

Uso:  python app/procesar_excel.py [ruta_del_excel]
"""
import glob
import json
import os
import re
import sys
import unicodedata
from datetime import datetime

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATOS = os.path.join(RAIZ, "datos")
ARCHIVO_AGRUPACIONES = os.path.join(DATOS, "agrupaciones.json")
SALIDA_JSON = os.path.join(DATOS, "preguntas_procesadas.json")
SALIDA_XLSX = os.path.join(DATOS, "preguntas_procesadas.xlsx")

MIN_FRECUENCIA_TABLERO = 2   # una respuesta entra al tablero si la dieron al menos 2 personas…
MAX_TABLERO = 8              # …y solo las 8 más frecuentes (orden: frecuencia y luego alfabético)
MIN_RESPUESTAS_JUGABLE = 3   # con menos casillas la pregunta se marca «poco jugable»
PUNTOS_POR_PREGUNTA = 100
REGLA_PUNTOS = ("Cada pregunta reparte exactamente 100 puntos entre las respuestas de su tablero, en proporción "
                "a su frecuencia real (método del resto mayor): cada respuesta recibe la parte entera de "
                "frecuencia ÷ suma de frecuencias del tablero × 100, y los puntos que faltan para llegar a 100 se "
                "entregan a las respuestas con mayor parte decimal, por grupos completos de igual frecuencia; si "
                "un grupo empatado ya no cabe entero, el sobrante va a la respuesta más popular. Así la suma es "
                "siempre 100, todos los puntos son enteros positivos, los empates conservan los mismos puntos y "
                "una respuesta más frecuente nunca tiene menos puntos. Las respuestas fuera del tablero no "
                "puntúan (0).")


def repartir_100(frecuencias, total=PUNTOS_POR_PREGUNTA):
    """Reparte `total` puntos enteros entre las frecuencias dadas (ordenadas de mayor a menor), proporcionalmente.

    Método del resto mayor (Hamilton) con aritmética entera: la suma es exactamente `total`, cada valor
    es al menos 1 y se respeta el orden de popularidad (más frecuencia ⇒ igual o más puntos)."""
    if not frecuencias:
        return []
    if any(f <= 0 for f in frecuencias):
        raise ValueError("Las frecuencias deben ser mayores que cero.")
    if len(frecuencias) > total:
        raise ValueError("Hay más respuestas que puntos para repartir.")
    suma = sum(frecuencias)
    base = [f * total // suma for f in frecuencias]
    restos = [f * total % suma for f in frecuencias]
    faltan = total - sum(base)
    # Los puntos sobrantes se dan por grupos de igual frecuencia (mismo resto), del mayor resto al menor.
    # Si un grupo empatado ya no cabe entero, el sobrante va a la respuesta más popular: así no se
    # rompen empates ni se altera el orden de popularidad.
    grupos = {}
    for i, f in enumerate(frecuencias):
        grupos.setdefault(f, []).append(i)
    for f in sorted(grupos, key=lambda f: (-restos[grupos[f][0]], -f)):
        if faltan == 0 or len(grupos[f]) > faltan:
            break
        for i in grupos[f]:
            base[i] += 1
        faltan -= len(grupos[f])
    for k in range(faltan):  # resto: a las más populares (si hay empate arriba, por posición)
        base[k % len(grupos[frecuencias[0]])] += 1
    # Garantiza el mínimo de 1 punto quitándolo a la respuesta con más puntos (solo con frecuencias extremas).
    for i in range(len(base)):
        while base[i] < 1:
            mayor = max(range(len(base)), key=lambda j: (base[j], j))  # la última del bloque con más puntos
            base[mayor] -= 1
            base[i] += 1
    return base


def normalizar(texto):
    """Texto en minúsculas, sin tildes ni signos: sirve para comparar respuestas."""
    t = unicodedata.normalize("NFD", texto.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^\w\s]", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def leer_excel(ruta):
    """Devuelve (lista de preguntas con respuestas por fila, total de filas de personas)."""
    import openpyxl
    wb = openpyxl.load_workbook(ruta, read_only=True, data_only=True)
    for ws in wb.worksheets:
        filas = list(ws.iter_rows(values_only=True))
        for i, fila in enumerate(filas):
            if fila and isinstance(fila[0], str) and fila[0].strip().lower() == "marca temporal":
                encabezados, numeros = fila, (filas[i - 1] if i > 0 else [None] * len(fila))
                datos = [(i + 1 + k + 1, f) for k, f in enumerate(filas[i + 1:]) if f and f[0] is not None]
                preguntas = []
                for c, enc in enumerate(encabezados):
                    if c == 0 or not isinstance(enc, str) or not enc.strip():
                        continue
                    if enc.strip().lower() in ("nombre", "correo", "correo electrónico", "email"):
                        continue
                    num = numeros[c] if c < len(numeros) else None
                    num = int(num) if isinstance(num, (int, float)) else c
                    respuestas = []
                    for nfila, f in datos:
                        v = f[c] if c < len(f) else None
                        respuestas.append({"fila": nfila, "texto": None if v is None else str(v)})
                    preguntas.append({"numero": num, "columna": c, "texto": enc.strip(), "respuestas": respuestas})
                return ws.title, preguntas, len(datos)
    raise SystemExit("No se encontró una hoja con la columna 'Marca temporal'.")


def procesar(ruta_excel, ruta_agrupaciones=ARCHIVO_AGRUPACIONES):
    """Lee el Excel y las agrupaciones y devuelve las preguntas consolidadas con sus puntos.

    No modifica ningún archivo: solo calcula. main() es quien escribe los resultados.
    """
    hoja, preguntas_excel, total_personas = leer_excel(ruta_excel)
    with open(ruta_agrupaciones, encoding="utf-8") as f:
        agrup = json.load(f)["preguntas"]

    preguntas, omitidas, avisos = [], [], []
    for pe in preguntas_excel:
        num = pe["numero"]
        textos = {r["fila"]: r["texto"].strip() for r in pe["respuestas"] if r["texto"] and r["texto"].strip()}
        vacias = [r["fila"] for r in pe["respuestas"] if not (r["texto"] and r["texto"].strip())]
        if not textos:
            omitidas.append({"numero": num, "texto": pe["texto"], "motivo": "Nadie respondió esta pregunta (columna vacía)."})
            continue
        dec = agrup.get(str(num))
        revision = list(dec.get("revision", [])) if dec else []
        grupos, excluidas, usadas = [], [], set()
        if dec:
            for g in dec["grupos"]:
                originales = []
                for r in g["respuestas"]:
                    fila = r["fila"]
                    if fila not in textos:
                        avisos.append(f"P{num}: la fila {fila} ya no tiene respuesta en el Excel; se ignora.")
                        continue
                    if normalizar(textos[fila]) != normalizar(r["texto"]):
                        avisos.append(f"P{num}: el texto de la fila {fila} cambió en el Excel "
                                      f"(«{r['texto']}» → «{textos[fila]}»); revisar su grupo.")
                        revision.append({"tipo": "otra", "detalle": f"Fila {fila} cambió de texto en el Excel; revisar su grupo."})
                    if fila in usadas:
                        avisos.append(f"P{num}: la fila {fila} aparece en dos grupos; se cuenta solo una vez.")
                        continue
                    usadas.add(fila)
                    originales.append({"fila": fila, "texto": textos[fila]})
                if originales:
                    grupos.append({"etiqueta": g["etiqueta"], "nota": g.get("nota"), "originales": originales,
                                   "reformulacion": g.get("reformulacion"),
                                   "revision_contenido": g.get("revision_contenido"),
                                   "nota_contenido": g.get("nota_contenido")})
            for e in dec.get("excluidas", []):
                if e["fila"] in textos and e["fila"] not in usadas:
                    usadas.add(e["fila"])
                    excluidas.append({"fila": e["fila"], "texto": textos[e["fila"]], "motivo": e["motivo"]})
        # Respuestas sin decisión previa (por ejemplo, filas nuevas en el Excel): se agrupan
        # solo si su texto normalizado es idéntico, y se marcan para revisión.
        pendientes = {}
        for fila, t in textos.items():
            if fila not in usadas:
                pendientes.setdefault(normalizar(t), []).append({"fila": fila, "texto": t})
        for clave, originales in pendientes.items():
            grupos.append({"etiqueta": originales[0]["texto"][:35].capitalize(), "nota": "Sin clasificar: agrupada solo por texto idéntico.",
                           "originales": originales, "reformulacion": None, "revision_contenido": None, "nota_contenido": None})
            revision.append({"tipo": "sin_clasificar", "detalle": f"Respuesta nueva sin agrupar: «{originales[0]['texto']}» (filas {', '.join(str(o['fila']) for o in originales)})."})

        validas = sum(len(g["originales"]) for g in grupos)
        grupos.sort(key=lambda g: (-len(g["originales"]), normalizar(g["etiqueta"])))
        pid = f"p{num:02d}"
        respuestas = []
        for i, g in enumerate(grupos, 1):
            freq = len(g["originales"])
            respuestas.append({
                "id": f"{pid}-r{i}", "etiqueta": g["etiqueta"], "frecuencia": freq,
                "puntos": 0, "en_tablero": False, "motivo_fuera": None,
                "nota": g["nota"], "originales": sorted(g["originales"], key=lambda o: o["fila"]),
                "reformulacion": g["reformulacion"], "revision_contenido": g["revision_contenido"],
                "nota_contenido": g["nota_contenido"],
            })
        # Tablero: respuestas con 2+ personas, sin revisión de contenido pendiente, máximo 8.
        candidatas = []
        for r in respuestas:
            if r["revision_contenido"]:
                r["motivo_fuera"] = "Pendiente de revisión de contenido"
            elif r["frecuencia"] < MIN_FRECUENCIA_TABLERO:
                r["motivo_fuera"] = f"Menos de {MIN_FRECUENCIA_TABLERO} personas"
            elif len(candidatas) >= MAX_TABLERO:
                r["motivo_fuera"] = f"El tablero ya tiene {MAX_TABLERO} respuestas más frecuentes"
            else:
                candidatas.append(r)
        for r, pts in zip(candidatas, repartir_100([r["frecuencia"] for r in candidatas])):
            r.update(en_tablero=True, puntos=pts)
        if len(candidatas) < MIN_RESPUESTAS_JUGABLE:
            revision.append({"tipo": "poco_jugable", "detalle": f"Solo {len(candidatas)} respuesta(s) con {MIN_FRECUENCIA_TABLERO}+ personas en el tablero; "
                             "no entra en la mezcla de preguntas salvo que se incluyan las poco jugables."})
        preguntas.append({
            "id": pid, "numero": num, "texto": pe["texto"], "respuestas_validas": validas,
            "respuestas_excluidas": len(excluidas), "respuestas_vacias": len(vacias),
            "respuestas_en_tablero": len(candidatas), "puntos_tablero": sum(r["puntos"] for r in candidatas),
            "habilitada": bool(candidatas), "jugable": len(candidatas) >= MIN_RESPUESTAS_JUGABLE,
            "respuestas": respuestas, "excluidas": sorted(excluidas, key=lambda e: e["fila"]), "revision": revision,
        })

    resultado = {
        "generado": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "archivo_origen": os.path.basename(ruta_excel), "hoja_origen": hoja,
        "personas_que_respondieron": total_personas,
        "criterio_puntos": REGLA_PUNTOS,
        "preguntas": preguntas, "preguntas_omitidas": omitidas, "avisos": avisos,
    }
    return resultado


def escribir_xlsx(res, ruta):
    """Escribe el Excel consolidado de revisión (hojas Resumen, Preguntas, Consolidadas, Contenido, Trazabilidad y Revisión manual)."""
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = openpyxl.Workbook()
    negrita, relleno = Font(bold=True, color="FFFFFF"), PatternFill("solid", fgColor="1F3A93")

    def hoja(titulo, encabezados, filas, anchos):
        """Crea una hoja con encabezado en color, anchos de columna y filas ajustadas."""
        ws = wb.create_sheet(titulo)
        ws.append(encabezados)
        for c in ws[1]:
            c.font, c.fill = negrita, relleno
            c.alignment = Alignment(wrap_text=True, vertical="center")
        for f in filas:
            ws.append(f)
        for i, a in enumerate(anchos):
            ws.column_dimensions[openpyxl.utils.get_column_letter(i + 1)].width = a
        for fila in ws.iter_rows(min_row=2):
            for c in fila:
                c.alignment = Alignment(wrap_text=True, vertical="top")
        ws.freeze_panes = "A2"
        return ws

    wb.remove(wb.active)
    ps = res["preguntas"]
    hoja("Resumen", ["Dato", "Valor"], [
        ["Archivo de origen (no modificado)", res["archivo_origen"]],
        ["Hoja", res["hoja_origen"]],
        ["Personas que respondieron (filas)", res["personas_que_respondieron"]],
        ["Preguntas procesadas", len(ps)],
        ["Preguntas jugables (3+ respuestas con 2+ personas)", sum(p["jugable"] for p in ps)],
        ["Preguntas omitidas", "; ".join(f"P{o['numero']}: {o['motivo']}" for o in res["preguntas_omitidas"]) or "Ninguna"],
        ["Criterio de puntos", res["criterio_puntos"]],
        ["Generado", res["generado"]],
    ], [45, 100])
    hoja("Preguntas", ["N°", "Pregunta", "Respuestas válidas", "Excluidas", "Respuestas distintas",
                       "Respuestas en el tablero", "SUMA DE PUNTOS DEL TABLERO", "¿Jugable?", "Casos para revisar"],
         [[p["numero"], p["texto"], p["respuestas_validas"], p["respuestas_excluidas"], len(p["respuestas"]),
           p["respuestas_en_tablero"], p["puntos_tablero"],
           "Sí" if p["jugable"] else ("Poco jugable" if p["habilitada"] else "No (sin respuestas válidas)"), len(p["revision"])]
          for p in ps],
         [6, 70, 12, 10, 12, 12, 14, 14, 12])

    def en_tablero(r):
        """Texto «Sí» o «No (motivo)» para la columna «¿Va al tablero?»."""
        return "Sí" if r["en_tablero"] else f"No ({r['motivo_fuera']})"

    ws = hoja("Consolidadas", ["N°", "Pregunta", "Posición", "Respuesta consolidada (en pantalla)", "Frecuencia real (personas)",
                               "Respuestas válidas de la pregunta", "PUNTOS ASIGNADOS (suman 100 por pregunta)", "¿Va al tablero?",
                               "Respuestas originales agrupadas", "Filas del Excel", "Nota de agrupación",
                               "Reformulación aplicada", "Revisión de contenido"],
              [[p["numero"], p["texto"], i, r["etiqueta"], r["frecuencia"], p["respuestas_validas"], r["puntos"], en_tablero(r),
                " | ".join(o["texto"] for o in r["originales"]), ", ".join(str(o["fila"]) for o in r["originales"]), r["nota"] or "",
                (f"Original: «{r['reformulacion']['etiqueta_original']}». {r['reformulacion']['motivo']}" if r["reformulacion"] else ""),
                r["revision_contenido"] or r["nota_contenido"] or ""]
               for p in ps for i, r in enumerate(p["respuestas"], 1)],
              [6, 45, 9, 30, 12, 12, 14, 22, 70, 18, 40, 45, 50])
    for c in ws["G"][1:]:
        c.font = Font(bold=True)
        c.fill = PatternFill("solid", fgColor="FFF2CC")
    hoja("Contenido", ["N°", "Pregunta", "Respuesta consolidada", "Frecuencia", "Puntos", "Tratamiento", "Detalle"],
         [[p["numero"], p["texto"], r["etiqueta"], r["frecuencia"], r["puntos"],
           "Pendiente de revisión (fuera del tablero)" if r["revision_contenido"] else "Reformulada" if r["reformulacion"] else "Se conserva",
           r["revision_contenido"] or (f"Original: «{r['reformulacion']['etiqueta_original']}». {r['reformulacion']['motivo']}"
                                       if r["reformulacion"] else r["nota_contenido"])]
          for p in ps for r in p["respuestas"] if r["revision_contenido"] or r["reformulacion"] or r["nota_contenido"]],
         [6, 45, 30, 10, 8, 30, 90])
    hoja("Trazabilidad", ["N°", "Fila del Excel", "Respuesta original", "Se agrupó en", "Estado"],
         sorted([[p["numero"], o["fila"], o["texto"], r["etiqueta"], "Válida"] for p in ps for r in p["respuestas"] for o in r["originales"]]
                + [[p["numero"], e["fila"], e["texto"], "—", "Excluida: " + e["motivo"]] for p in ps for e in p["excluidas"]],
                key=lambda f: (f[0], f[1])),
         [6, 10, 50, 30, 50])
    hoja("Revisión manual", ["N°", "Pregunta", "Tipo", "Detalle"],
         [[p["numero"], p["texto"], r["tipo"], r["detalle"]] for p in ps for r in p["revision"]]
         + [[o["numero"], o["texto"], "omitida", o["motivo"]] for o in res["preguntas_omitidas"]],
         [6, 50, 16, 90])
    if res["avisos"]:
        hoja("Avisos", ["Aviso"], [[a] for a in res["avisos"]], [120])
    wb.save(ruta)


def main():
    """Punto de entrada de PROCESAR_EXCEL.bat: procesa el Excel y escribe los archivos de datos/."""
    if len(sys.argv) > 1:
        ruta = sys.argv[1]
    else:
        candidatos = [p for p in glob.glob(os.path.join(RAIZ, "*.xlsx")) if not os.path.basename(p).startswith("~$")]
        if len(candidatos) != 1:
            raise SystemExit(f"Se esperaba un único Excel en la carpeta principal y hay {len(candidatos)}. "
                             "Indica la ruta: python app/procesar_excel.py \"archivo.xlsx\"")
        ruta = candidatos[0]
    res = procesar(ruta)
    os.makedirs(DATOS, exist_ok=True)
    with open(SALIDA_JSON, "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=1)
    escribir_xlsx(res, SALIDA_XLSX)
    ps = res["preguntas"]
    print(f"Excel leído: {os.path.basename(ruta)} ({res['personas_que_respondieron']} personas)")
    print(f"Preguntas procesadas: {len(ps)}  ·  jugables: {sum(p['jugable'] for p in ps)}  ·  omitidas: {len(res['preguntas_omitidas'])}")
    print(f"Casos para revisión manual: {sum(len(p['revision']) for p in ps)}")
    for a in res["avisos"]:
        print("AVISO:", a)
    print(f"Archivos generados:\n  {SALIDA_JSON}\n  {SALIDA_XLSX}")


if __name__ == "__main__":
    main()
