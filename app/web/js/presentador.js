/**
 * Panel privado del presentador.
 *
 * - Lee el estado completo (/api/presentador) y las preguntas (/api/preguntas).
 * - Cada botón envía una acción a POST /api/accion junto con la versión del estado que
 *   tenía la pantalla: si otra acción llegó antes (doble clic), el servidor la rechaza.
 * - Pestañas: Preparación, Juego, Preguntas y respuestas, Reglas y opciones, Historial.
 * - Los formularios no se redibujan mientras alguien escribe en ellos.
 */
const $ = (id) => document.getElementById(id);
let estado = null;
let datos = null;            // preguntas procesadas
let ocupado = false;         // evita enviar dos acciones a la vez (doble clic)
let preguntaElegida = null;  // pregunta alternativa elegida para la próxima ronda (opcional)
let detalleId = null;        // pregunta abierta en la pestaña «Preguntas»
let pestana = null;
let ultimoSorteoVisto = null; // para animar el reparto de equipos una sola vez
let ultimaMezclaVista = null;

/** Escapa texto para insertarlo en HTML sin riesgo. */
function esc(t) {
  return String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const nom = (i) => esc(estado.config.equipos[i].nombre || `Equipo ${i + 1}`);
const colorEq = (i) => (i === 0 ? "azul" : "naranja");
const pregunta = (id) => datos.preguntas.find((p) => p.id === id);
const persona = (id) => esc(estado.nombres_participantes[id] || "?");

// Crea un botón que envía una acción. confirmar: texto de confirmación opcional.
function boton(texto, accion, clase = "", confirmar = "", desactivado = false) {
  return `<button class="btn ${clase}" data-accion='${esc(JSON.stringify(accion))}'${confirmar ? ` data-confirmar="${esc(confirmar)}"` : ""}${desactivado ? " disabled" : ""}>${texto}</button>`;
}

/** Muestra un aviso temporal abajo (rojo = error, verde = confirmación). */
function aviso(texto, ok = false) {
  const t = $("toast");
  t.textContent = texto;
  t.className = "toast" + (ok ? " ok" : "");
  clearTimeout(aviso.t);
  aviso.t = setTimeout(() => t.classList.add("oculto"), ok ? 2500 : 7000);
}

/** Envía una acción al servidor; bloquea los botones mientras tanto para evitar dobles clics. */
async function enviar(accion) {
  if (ocupado || !estado) return false;
  ocupado = true;
  let ok = false;
  document.querySelectorAll("button[data-accion], #btn-deshacer").forEach((b) => (b.disabled = true));
  try {
    const resp = await fetch("/api/accion", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ version: estado.version, accion }),
    });
    const r = await resp.json();
    ok = r.ok;
    if (!r.ok) aviso(r.error || "No se pudo aplicar la acción.");
    if (r.estado) estado = r.estado;
  } catch (e) {
    aviso("No hay conexión con el juego. ¿Está abierta la ventana negra del servidor?");
  }
  ocupado = false;
  pintar(true);
  return ok;
}

document.addEventListener("click", async (ev) => {
  const b = ev.target.closest("button[data-accion]");
  if (!b || b.disabled) return;
  if (b.dataset.confirmar && !confirm(b.dataset.confirmar)) return;
  const accion = JSON.parse(b.dataset.accion);
  const ok = await enviar(accion);
  if (ok && accion.tipo === "confirmar_partida") cambiarPestana("juego");
  if (ok && (accion.tipo === "nueva_partida" || accion.tipo === "reiniciar_configuracion")) cambiarPestana("preparacion");
});

// ---------------------------------------------------------------- utilidades de rondas y líderes
const textoRonda = (info) => info.tipo === "extra"
  ? `Ronda extra ${info.extra_n} (×${info.multiplicador}, hasta ${info.maximo} pts)`
  : `Ronda ${info.numero} (principal, hasta ${info.maximo} pts)`;

/** Resumen del ciclo de líderes: cuántos faltan por ser líderes en cada equipo. */
function estadoLideres() {
  const il = estado.info_lideres;
  return `<div class="estado-ronda"><span>♻️ Ciclo de líderes ${estado.lideres.ciclo}</span>
    ${[0, 1].map((i) => `<span title="${il[i].pendientes.map(persona).join(", ")}">${nom(i)}: faltan ${il[i].pendientes.length} de ${il[i].total} por ser líderes</span>`).join("")}</div>`;
}

/** Tarjetas con el resultado del último sorteo de líderes. */
function resultadoSorteo() {
  const s = estado.lideres.sorteo;
  if (!s) return "";
  return `<div class="marcador-p" style="margin-top:10px">${s.equipos.map((x) => `<div class="eq e${x.equipo}">${nom(x.equipo)}
    <b style="font-size:26px">${x.elegido ? esc(x.elegido) : "Elige el equipo"}</b>
    <small>${x.completo ? "Todos ya fueron líderes en este ciclo: no hay nuevo sorteo" : x.candidatos.length === 1 ? "Era el único integrante pendiente" : `Sorteado entre ${x.candidatos.length} integrantes pendientes`}</small></div>`).join("")}</div>
    ${s.nuevo_ciclo ? `<p class="ayuda" style="color:#fbbf24"><b>♻️ Empezó el ciclo ${s.ciclo}:</b> todos ya habían sido líderes, así que vuelven a participar.</p>` : ""}`;
}

/** Desplegable para usar otra pregunta en lugar de la sorteada (excepcional). */
function selectorAlternativo() {
  const usadas = new Set(estado.preguntas_usadas);
  const opciones = datos.preguntas.filter((p) => !usadas.has(p.id) && estado.tableros[p.id].ids.length > 0).map((p) =>
    `<option value="${p.id}" ${p.id === preguntaElegida ? "selected" : ""}>P${p.numero}. ${esc(p.texto.slice(0, 80))}</option>`).join("");
  return `<details style="margin-top:12px"><summary class="ayuda">Usar otra pregunta en lugar de la sorteada (excepcional)</summary>
    <div class="campo" style="margin-top:8px"><select id="sel-alternativa"><option value="">— Usar la pregunta sorteada —</option>${opciones}</select></div></details>`;
}

// ---------------------------------------------------------------- pestaña Juego
function equipoEnTurno() {
  const r = estado.ronda;
  if (!r) return null;
  return { cara_a_cara: r.cara_a_cara.turno, decision: r.cara_a_cara.ganador, juego: r.control,
    robo: r.robo.equipo, resuelta: r.ganador, asignada: r.asignada_a }[estado.fase] ?? null;
}

/** Bloque «Siguiente ronda» con la pregunta sorteada y el botón de la ruleta de líderes. */
function bloqueSiguienteRonda() {
  const e = estado;
  const numero = e.historial_rondas.length + 1;
  const info = e.plan_rondas[numero - 1];
  const p = pregunta(preguntaElegida || e.proxima_pregunta);
  return `<div class="paso"><b class="titulo-paso">Siguiente: ${textoRonda(info)}</b>
      ${p ? `<p class="ayuda">Pregunta sorteada para esta ronda (privado): <b>P${p.numero}. ${esc(p.texto)}</b></p>` : `<p class="ayuda" style="color:#fca5a5">No quedan preguntas sin usar.</p>`}
      ${estadoLideres()}
      <p class="ayuda">Pulsa el botón: la ruleta elige al azar al líder de cada equipo entre quienes aún no lo han sido en este ciclo, y se muestra en la pantalla pública (unos 15 segundos).</p>
      <div class="fila-botones">${boton(`🎡 Sortear líderes de la ronda ${numero}`, { tipo: "sortear_lideres" }, "morado grande")}</div></div>`;
}

/** Tarjeta principal de la pestaña Juego: muestra solo los botones de la fase actual. */
function pintarControl() {
  const e = estado, r = e.ronda, c = $("control");
  const rondasRestantes = e.total_rondas - e.historial_rondas.length;
  let html = "";
  switch (e.fase) {
    case "preparacion":
      html = `<h2>Prepara la partida</h2>
        <p class="ayuda">Antes de jugar hay que registrar a los participantes, sortear los equipos, mezclar las preguntas y configurar las rondas. Todo se hace en la pestaña <b>🧩 Preparación</b>.</p>
        ${e.validaciones.length ? `<ul class="validaciones">${e.validaciones.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>` : `<p class="ayuda" style="color:#86efac"><b>Todo listo:</b> confirma la partida en la pestaña Preparación.</p>`}
        <div class="fila-botones"><button class="btn azul grande" id="ir-preparacion">🧩 Ir a Preparación</button></div>`;
      break;
    case "lista":
      html = `<h2>¡Partida confirmada!</h2>
        <p class="ayuda">${e.rondas_principales} rondas principales${e.preparacion.rondas_extra ? ` + ${e.preparacion.rondas_extra} adicionales` : ""}. Los equipos y el orden de las preguntas ya no cambian.</p>
        ${bloqueSiguienteRonda()}`;
      break;
    case "lideres": {
      const numero = e.historial_rondas.length + 1;
      const info = e.plan_rondas[numero - 1];
      html = `<h2>Líderes de la ${info.tipo === "extra" ? `ronda extra ${info.extra_n}` : `ronda ${numero}`}</h2>
        ${resultadoSorteo()}
        <p class="ayuda">La ruleta se está mostrando en la pantalla pública. Cuando termine, presenta a los líderes y comienza la ronda.</p>
        <div class="fila-botones">${boton(`▶ Iniciar ${info.tipo === "extra" ? `ronda extra ${info.extra_n}` : `ronda ${numero}`}`, { tipo: "iniciar_ronda" }, "verde grande")}
        ${boton("↩ Revertir sorteo de líderes", { tipo: "revertir_lideres" }, "fantasma", "¿Anular este sorteo de líderes? Los elegidos vuelven a estar disponibles y el historial anterior se conserva.")}</div>
        ${selectorAlternativo()}`;
      break;
    }
    case "cara_a_cara": {
      const cac = r.cara_a_cara;
      const max = e.errores_max_cara_a_cara;
      const lider = (i) => e.equipos_vista[i].lider ? esc(e.equipos_vista[i].lider) : "su líder";
      // Empezado = los líderes actuales ya respondieron (tras un cambio de líderes vuelve a empezar de cero)
      const empezado = cac.intentos.some((x) => x.ronda_lideres === cac.cambios_lider);
      const omitible = !empezado && !cac.bloqueado && Object.keys(r.reveladas).length === 0;
      const estadoLider = (i) => `<div class="eq e${i} ${cac.turno === i ? "turno" : ""}">${nom(i)}<b style="font-size:20px">${lider(i)}</b>
        <small>Intentos: ${[0, 1].map((k) => `<span class="${k < cac.errores[i] ? "x-usada" : "x-libre"}">✗</span>`).join("")} (${cac.errores[i]} de ${max} errores)</small>
        ${cac.turno === i ? '<small class="le-toca">▶ LE TOCA RESPONDER</small>' : ""}</div>`;
      let paso2 = "";
      if (cac.bloqueado) {
        paso2 = `<div class="paso"><b class="titulo-paso">Ninguno acertó: los dos líderes agotaron sus ${max} intentos</b>
          <p class="ayuda">Cambia a ambos líderes (ruleta en la pantalla pública) y repite el cara a cara. Las casillas ya reveladas se quedan; los strikes de la ronda no cambian.</p>
          <div class="fila-botones">${boton("🎡 Cambiar a ambos líderes y repetir", { tipo: "cambiar_lideres_cara_a_cara" }, "morado grande")}</div></div>`;
      } else if (cac.turno !== null) {
        const ref = cac.referencia;
        paso2 = `<div class="paso"><b class="titulo-paso">Paso 2. Responde ${lider(cac.turno)} (${nom(cac.turno)})</b>
          ${ref ? `<p class="ayuda" style="color:#fde68a"><b>${nom(ref.equipo)}</b> dio una respuesta de <b>${ref.puntos} pts</b>: para ganar, ${lider(cac.turno)} debe dar una respuesta que valga <b>más de ${ref.puntos} pts</b>. Si vale menos o no está, gana ${nom(ref.equipo)}.</p>`
            : `<p class="ayuda">Si coincide con una casilla, pulsa <b>«Lo dijo ${nom(cac.turno)}»</b> en esa respuesta (abajo). La respuesta n.º 1 gana de inmediato. Si no está en el tablero:</p>`}
          <div class="fila-botones">${boton(`✗ No está (error ${cac.errores[cac.turno] + 1} de ${max})`, { tipo: "respuesta_cara_a_cara", equipo: cac.turno, respuesta_id: null }, "rojo")}</div></div>`;
      }
      html = `<h2>Cara a cara · ${r.tipo === "extra" ? `Ronda extra ${r.extra_n} ×${r.multiplicador}` : `Ronda ${r.numero}`}</h2>
        <div class="paso ${cac.turno !== null || empezado ? "hecho" : ""}"><b class="titulo-paso">Paso 1. Lee la pregunta. ¿Qué líder levantó la mano primero en Google Meet?</b>
          <div class="fila-botones">${[0, 1].map((i) => boton((cac.primero === i ? "✔ " : "") + `${nom(i)} (${lider(i)})`, { tipo: "primero_en_responder", equipo: i }, colorEq(i), "", cac.bloqueado || (empezado && cac.primero !== null && cac.turno !== null && cac.intentos.some((x) => x.ronda_lideres === cac.cambios_lider)))).join("")}</div></div>
        <div class="marcador-p" style="margin-bottom:12px">${estadoLider(0)}${estadoLider(1)}</div>
        ${paso2}
        <details class="reglas-cac"><summary class="ayuda">Reglas del cara a cara</summary><ul class="ayuda">
          <li>La respuesta <b>n.º 1</b> del tablero gana de inmediato.</li>
          <li>Una respuesta válida queda como referencia: el otro líder debe <b>superarla en puntos</b>. Menos puntos o «no está» → gana la referencia.</li>
          <li>Empate en puntos: ${e.config.empate_cara_a_cara === "desempate" ? "nueva respuesta de desempate (empieza quien levantó la mano primero)" : "gana quien respondió primero"} (se cambia en Reglas y opciones).</li>
          <li>Cada líder tiene <b>${max} intentos</b>. Si ambos los agotan, se cambia a los dos líderes. Estos errores <b>no</b> son strikes de la ronda.</li></ul></details>
        ${omitible ? `<div class="paso"><b class="titulo-paso">¿Prefieres empezar sin cara a cara?</b>
          <p class="ayuda">No se revela ninguna respuesta ni se registran errores. Elige qué equipo empieza la ronda:</p>
          <div class="fila-botones">${[0, 1].map((i) => boton(`⏭ Omitir cara a cara: empieza ${nom(i)}`, { tipo: "omitir_cara_a_cara", equipo: i }, "fantasma", `¿Omitir el cara a cara? Empieza la ronda ${estado.config.equipos[i].nombre}.`)).join("")}</div></div>` : ""}
        <details style="margin-top:6px"><summary class="ayuda">Elegir el ganador manualmente (disputas)</summary>
          <div class="fila-botones" style="margin-top:8px">${[0, 1].map((i) => boton(`🏆 Gana ${nom(i)}`, { tipo: "ganador_cara_a_cara", equipo: i }, colorEq(i) + " chico", `¿Dar el cara a cara a ${estado.config.equipos[i].nombre} por decisión del presentador?`)).join("")}</div></details>`;
      break;
    }
    case "decision": {
      const g = r.cara_a_cara.ganador;
      const motivos = { numero_uno: "dio la respuesta n.º 1", supera: "superó la respuesta rival", no_supera: "el rival no superó su respuesta",
        rival_sin_intentos: "el rival ya no tenía intentos", empate_primero: "empate: respondió primero", manual: "decisión del presentador", correccion: "corrección del presentador" };
      html = `<h2>${nom(g)} ganó el cara a cara</h2><p class="ayuda">Motivo: ${motivos[r.cara_a_cara.motivo] || "—"}. Pregunta al equipo: ¿juegan la ronda o se la pasan al rival?</p>
        <div class="fila-botones">${boton(`▶ ${nom(g)} juega`, { tipo: "decidir", jugar: true }, colorEq(g) + " grande")}
        ${boton(`↪ Pasar a ${nom(1 - g)}`, { tipo: "decidir", jugar: false }, colorEq(1 - g) + " grande")}</div>
        <details style="margin-top:12px"><summary class="ayuda">¿Error? Corregir el ganador del cara a cara</summary>
          <div class="fila-botones" style="margin-top:8px">${boton(`El cara a cara lo ganó ${nom(1 - g)}`, { tipo: "corregir_ganador_cara_a_cara" }, "fantasma chico", `¿Corregir? El cara a cara pasa a ${estado.config.equipos[1 - g].nombre}.`)}</div></details>`;
      break;
    }
    case "juego": {
      const lider = e.equipos_vista[r.control].lider;
      html = `<h2>Juega ${nom(r.control)}${lider ? ` · líder: ${esc(lider)}` : ""}</h2>
        <p class="ayuda">Escucha la respuesta. Si coincide, pulsa <b>✓ Correcta</b> en esa respuesta (abajo). Si no coincide con ninguna del tablero, pulsa <b>Strike</b>. Una respuesta ya revelada no suma otra vez: simplemente pide otra.</p>
        <div class="fila-botones">${boton(`✗ STRIKE (${r.strikes}/3)`, { tipo: "strike" }, "rojo grande")}</div>
        ${r.strikes === 2 ? `<p class="ayuda" style="color:#fca5a5"><b>Dos strikes:</b> avisa a ${nom(1 - r.control)} que se prepare para un posible robo.</p>` : ""}`;
      break;
    }
    case "robo":
      html = `<h2>Oportunidad de robo para ${nom(r.robo.equipo)}</h2>
        <p class="ayuda">El equipo puede deliberar. Luego su líder da <b>una sola</b> respuesta. Si coincide con una respuesta oculta, pulsa <b>Robo con esta</b> en la lista de abajo. Si no coincide:</p>
        <div class="fila-botones">${boton("✗ Robo fallido (no está en el tablero)", { tipo: "resolver_robo", respuesta_id: null }, "rojo grande")}</div>
        <p class="ayuda">Banco en juego: <b>${r.banco}</b> puntos.</p>`;
      break;
    case "resuelta": {
      const otro = 1 - r.ganador;
      const motivo = r.robo.resultado === "exitoso" ? "Robo exitoso." : r.robo.resultado === "fallido" ? "Robo fallido." : "";
      html = `<h2>Ronda resuelta: gana ${nom(r.ganador)}</h2>
        <p class="ayuda">${motivo} Banco: <b>${r.banco}</b> puntos${r.multiplicador > 1 ? ` (ya incluye el ×${r.multiplicador})` : ""}. Puedes mostrar las respuestas que faltan antes o después de asignar.</p>
        <div class="fila-botones">${boton(`💰 Asignar ${r.banco} puntos a ${nom(r.ganador)}`, { tipo: "asignar_banco" }, "verde grande")}
        ${boton("👁 Mostrar respuestas restantes", { tipo: "revelar_restantes" }, "fantasma", "", r.tablero.every((x) => r.reveladas[x]))}</div>
        <details style="margin-top:10px"><summary class="ayuda">¿Corrección? Asignar el banco al otro equipo</summary>
        ${boton(`Asignar a ${nom(otro)}`, { tipo: "asignar_banco", equipo: otro }, "fantasma chico", `¿Seguro? El banco irá a ${estado.config.equipos[otro].nombre} en vez del ganador calculado.`)}</details>`;
      break;
    }
    case "asignada":
      html = `<h2>${r.tipo === "extra" ? `Ronda extra ${r.extra_n}` : `Ronda ${r.numero}`} terminada</h2>
        <p class="ayuda">${nom(r.asignada_a)} recibió <b>${r.puntos_asignados}</b> puntos. Marcador: ${nom(0)} ${e.puntajes[0]} – ${e.puntajes[1]} ${nom(1)}.</p>
        <div class="fila-botones" style="margin-bottom:12px">${boton("👁 Mostrar respuestas restantes", { tipo: "revelar_restantes" }, "fantasma", "", r.tablero.every((x) => r.reveladas[x]))}</div>
        ${rondasRestantes > 0 ? bloqueSiguienteRonda() + `<p class="ayuda">Quedan ${rondasRestantes} ronda(s).</p>` : `<p class="ayuda"><b>Se jugaron todas las rondas configuradas.</b></p>`}
        <div class="fila-botones" style="margin-top:12px">${boton("🏁 Finalizar juego y mostrar ganador", { tipo: "finalizar_juego" }, rondasRestantes > 0 ? "morado" : "morado grande",
          rondasRestantes > 0 ? `Aún quedan ${rondasRestantes} ronda(s). ¿Finalizar el juego ahora?` : "")}</div>`;
      break;
    case "fin": {
      const f = e.resultado_final;
      html = `<h2>🏁 Juego terminado</h2>
        <p style="font-size:22px"><b>${f.ganador === null ? "¡Empate!" : `Gana ${nom(f.ganador)}`}</b> · ${nom(0)} ${f.puntajes[0]} – ${f.puntajes[1]} ${nom(1)}</p>
        <p class="ayuda">La pantalla pública muestra el resultado final con confeti. Para jugar otra vez sin perder las preguntas ni los participantes:</p>
        <div class="fila-botones">${boton("🔄 Nueva partida", { tipo: "nueva_partida" }, "verde grande", "¿Empezar una nueva partida? El marcador vuelve a 0, se conservan participantes, equipos y reglas, y habrá que volver a mezclar las preguntas.")}</div>`;
      break;
    }
  }
  if (["cara_a_cara", "decision", "juego", "robo", "resuelta"].includes(e.fase)) {
    html += `<details style="margin-top:14px"><summary class="ayuda">Opciones avanzadas (disputas y cancelación)</summary>
      ${e.fase !== "resuelta" ? `<p class="ayuda">Cierra la ronda ahora y declara un ganador manualmente. Después podrás asignar el banco.</p>
      <div class="fila-botones">${[0, 1].map((i) => boton(`Cerrar ronda: gana ${nom(i)}`, { tipo: "cerrar_ronda", equipo: i }, "fantasma chico", "¿Cerrar la ronda manualmente?")).join("")}</div>` : ""}
      <p class="ayuda">Cancelar la ronda: no se asignan puntos, la pregunta vuelve a quedar disponible y regresas al paso de líderes (desde allí puedes revertir su sorteo).</p>
      <div class="fila-botones">${boton("⛔ Cancelar esta ronda", { tipo: "cancelar_ronda" }, "fantasma chico", "¿Cancelar la ronda? No se asignarán puntos y la pregunta volverá a estar disponible.")}
      ${boton("Finalizar juego ahora", { tipo: "finalizar_juego", forzar: true }, "fantasma chico", "¿Finalizar el juego ahora? El banco de esta ronda NO se asignará.")}</div></details>`;
  }
  c.innerHTML = html;
  const ir = $("ir-preparacion");
  if (ir) ir.onclick = () => cambiarPestana("preparacion");
  const sel = $("sel-alternativa");
  if (sel) {
    sel.onchange = () => { preguntaElegida = sel.value || null; pintarControl(); };
    const b = c.querySelector('button[data-accion*="iniciar_ronda"]');
    if (b && preguntaElegida) b.dataset.accion = JSON.stringify({ tipo: "iniciar_ronda", pregunta_id: preguntaElegida });
  }
}

/** Desplegable con las respuestas originales de una respuesta consolidada. */
function detalleOriginales(a) {
  return `<details><summary>Ver ${a.originales.length} respuesta(s) original(es)</summary><ul>${a.originales.map((o) => `<li>«${esc(o.texto)}» <span style="color:#64748b">(fila ${o.fila})</span></li>`).join("")}</ul>${a.nota ? `<div class="ayuda">Nota: ${esc(a.nota)}</div>` : ""}
    ${a.reformulacion ? `<div class="ayuda">Reformulada. Original: «${esc(a.reformulacion.etiqueta_original)}». ${esc(a.reformulacion.motivo)}</div>` : ""}
    ${a.revision_contenido ? `<div class="ayuda" style="color:#fca5a5">Pendiente de revisión: ${esc(a.revision_contenido)}</div>` : ""}
    ${a.nota_contenido ? `<div class="ayuda">Contenido: ${esc(a.nota_contenido)}</div>` : ""}</details>`;
}

/** Insignias de contenido: «en revisión» o «reformulada». */
/** Ejemplos reales aceptados y criterio para decidir si una respuesta verbal coincide con la casilla. */
function guiaAceptacion(a) {
  if (!a.ejemplos || !a.ejemplos.length) return "";
  return `<div class="acepta"><b>Se acepta:</b> ${a.ejemplos.map((x) => `«${esc(x)}»`).join(" · ")}
    <div class="criterio">${esc(a.criterio || "")}</div></div>`;
}

function marcasContenido(a) {
  return (a.revision_contenido ? ` <span class="insignia rojo" title="${esc(a.revision_contenido)}">⚠ en revisión · no va al tablero</span>` : "")
    + (a.reformulacion ? ` <span class="insignia oro" title="Original: ${esc(a.reformulacion.etiqueta_original)}">reformulada</span>` : "");
}

const datosPuntos = (a, p) => `Frecuencia real: <b>${a.frecuencia}</b> de ${p.respuestas_validas} personas · ${a.en_tablero ? `Puntos: <b>${a.puntos}</b>` : `No puntúa (${esc(a.motivo_fuera || "fuera del tablero")})`}`;

/** Lista privada de respuestas de la pregunta actual, con sus botones según la fase. */
function pintarRespuestas() {
  const e = estado, r = e.ronda, c = $("respuestas");
  if (!r) {
    c.innerHTML = `<h2>Tablero</h2><p class="ayuda">Aquí aparecerán todas las respuestas de la pregunta actual cuando inicies una ronda.</p>`;
    return;
  }
  const p = pregunta(r.pregunta_id);
  const pts = e.tableros[p.id].puntos;
  const filas = r.tablero.map((id, i) => {
    const a = p.respuestas.find((x) => x.id === id);
    const rev = r.reveladas[id];
    let acciones = "";
    if (rev) {
      const quien = rev.como === "final" ? "mostrada al final, sin puntos" : `${rev.como === "cara_a_cara" ? "cara a cara" : rev.como === "robo" ? "robo" : "en juego"}${rev.equipo !== null ? " · " + nom(rev.equipo) : ""} · +${rev.sumado}`;
      acciones = `<span class="insignia ${rev.como === "final" ? "" : "verde"}">✔ ${quien}</span>`;
    } else if (e.fase === "cara_a_cara") {
      const t = r.cara_a_cara.turno;
      acciones = t === null ? `<span class="insignia">${r.cara_a_cara.bloqueado ? "cambia a los líderes" : "marca quién levantó la mano"}</span>`
        : boton(`Lo dijo ${nom(t)}`, { tipo: "respuesta_cara_a_cara", equipo: t, respuesta_id: id }, colorEq(t) + " chico");
    } else if (e.fase === "juego") {
      acciones = boton("✓ Correcta", { tipo: "revelar", respuesta_id: id }, "verde");
    } else if (e.fase === "robo") {
      acciones = boton("✓ Robo con esta", { tipo: "resolver_robo", respuesta_id: id }, "verde");
    } else if (["resuelta", "asignada", "fin"].includes(e.fase)) {
      acciones = boton("👁 Mostrar", { tipo: "revelar", respuesta_id: id }, "fantasma chico");
    }
    return `<li class="resp ${rev ? (rev.como === "final" ? "final" : "revelada") : ""}"><span class="pos">${i + 1}</span>
      <div><div class="etq">${esc(a.etiqueta)}${marcasContenido(a)}</div><div class="datos">${datosPuntos(a, p)}${r.multiplicador > 1 ? ` (×${r.multiplicador} = ${pts[id] * r.multiplicador} al banco)` : ""}</div></div>
      <div class="acciones">${acciones}</div>${guiaAceptacion(a)}${detalleOriginales(a)}</li>`;
  }).join("");
  const fuera = p.respuestas.filter((a) => !r.tablero.includes(a.id));
  const anterior = ["lista", "lideres"].includes(e.fase) ? " <span class=\"insignia\">ronda anterior</span>" : "";
  c.innerHTML = `<h2>Respuestas de la pregunta ${p.numero} <span class="insignia">privado</span>${anterior}</h2>
    <p style="font-size:18px;margin:0 0 10px;color:#fff"><b>${esc(p.texto)}</b></p>
    <p class="ayuda">El tablero reparte exactamente <b>100 puntos</b> según la frecuencia real${r.multiplicador > 1 ? ` (esta ronda ×${r.multiplicador}: hasta ${r.maximo} pts)` : ""}. ${p.respuestas_validas} respuestas válidas de la encuesta${p.respuestas_excluidas ? ` (${p.respuestas_excluidas} excluidas)` : ""}.</p>
    <ul class="lista-resp">${filas}</ul>
    ${fuera.length ? `<h3>Fuera del tablero (${fuera.length}) · solo de referencia</h3>
      <p class="ayuda">Las dijeron muy pocas personas (o están pendientes de revisión de contenido), así que no están en el tablero ni puntúan. Si un equipo dice una de estas, cuenta como «no está» (strike).</p>
      <ul class="lista-resp">${fuera.map((a) => `<li class="resp fuera"><span class="pos">–</span><div><div class="etq">${esc(a.etiqueta)}${marcasContenido(a)}</div><div class="datos">${datosPuntos(a, p)}</div></div><div></div>${detalleOriginales(a)}</li>`).join("")}</ul>` : ""}`;
}

/** Marcador, banco, strikes y estado del ciclo de líderes. */
function pintarMarcador() {
  const e = estado, r = e.ronda, turno = equipoEnTurno();
  const enRonda = r && !["lista", "lideres", "preparacion"].includes(e.fase);
  $("marcador").innerHTML = `<h2>Marcador</h2>
    <div class="marcador-p">${[0, 1].map((i) => `<div class="eq e${i} ${turno === i ? "turno" : ""}">${nom(i)}<b>${e.puntajes[i]}</b>${e.equipos_vista[i].lider ? `<small>Líder: ${esc(e.equipos_vista[i].lider)}</small>` : e.equipos_vista[i].sin_lider_nuevo ? "<small>Ciclo completo: elige el equipo</small>" : ""}</div>`).join("")}</div>
    <div class="estado-ronda">
      <span>Ronda ${enRonda ? r.numero : e.historial_rondas.length} de ${e.total_rondas}</span>
      ${enRonda ? `<span>Banco: ${r.banco} / ${r.maximo}</span><span class="xs">${"X".repeat(r.strikes) || "Sin strikes"}</span>${r.multiplicador > 1 ? `<span>⭐ Extra ×${r.multiplicador}</span>` : ""}` : ""}
      ${turno !== null && enRonda ? `<span>Turno: ${nom(turno)}</span>` : ""}
    </div>
    ${e.fase !== "preparacion" ? estadoLideres() : ""}`;
}

const NOMBRES_SONIDOS = { musica: "Música de entrada", correcta: "Respuesta correcta", strike: "Strike", strike2: "Segundo strike (tensión)",
  robo: "Tercer strike y suspenso de robo", robo_exitoso: "Robo exitoso", robo_fallido: "Robo fallido",
  puntos: "Puntos ganados (fanfarria y aplausos)", ruleta: "Ruleta de líderes", lider: "Revelación del líder",
  ronda_extra: "Entrada a ronda extra", fanfarria_final: "Final del juego" };

/** Tarjeta de sonido: interruptores, volumen, música y prueba de efectos. */
function pintarAudio(forzar) {
  if (!forzar && formularioOcupado("audio")) return;
  const c = estado.config;
  $("audio").dataset.editando = "0";
  $("audio").innerHTML = `<h2>🔊 Sonido y música</h2>
    <p class="ayuda">Los sonidos suenan en la <b>pantalla pública</b>. Si allí aparece «Clic aquí para activar el sonido», haz clic una vez en esa pestaña. Para que los participantes lo oigan, en Meet comparte esa <b>pestaña</b> marcando «Compartir también el audio de la pestaña».</p>
    <div class="fila-botones">
      <label class="check"><input type="checkbox" id="chk-sonido" ${c.sonido ? "checked" : ""}> Sonido (general)</label>
      <label class="check"><input type="checkbox" id="chk-musica" ${c.musica ? "checked" : ""}> Música de entrada</label>
      <label class="check"><input type="checkbox" id="chk-efectos" ${c.efectos ? "checked" : ""}> Efectos</label>
      <label class="check"><input type="checkbox" id="chk-anim" ${c.animaciones ? "checked" : ""}> Animaciones</label>
    </div>
    <div class="campo"><label for="volumen">Volumen: <b id="vol-valor">${c.volumen}</b>%</label>
      <input type="range" id="volumen" min="0" max="100" step="5" value="${c.volumen}" style="width:100%"></div>
    <div class="fila-botones">${boton("🎵 Música de entrada", { tipo: "musica" }, "morado", "", !c.sonido || !c.musica)}</div>
    <div class="campo" style="margin-top:12px"><label for="sel-sonido">Probar un efecto en la pantalla pública</label>
      <div class="fila-botones"><select id="sel-sonido" class="buscador" style="flex:1;min-width:200px">${Object.entries(NOMBRES_SONIDOS).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select>
      <button class="btn azul" id="probar-sonido" ${!c.sonido ? "disabled" : ""}>▶ Probar</button></div></div>`;
  const cambio = (k) => (ev) => enviar({ tipo: "configurar", cambios: { [k]: ev.target.checked } });
  $("chk-sonido").onchange = cambio("sonido");
  $("chk-musica").onchange = cambio("musica");
  $("chk-efectos").onchange = cambio("efectos");
  $("chk-anim").onchange = cambio("animaciones");
  $("volumen").oninput = (ev) => ($("vol-valor").textContent = ev.target.value);
  $("volumen").onchange = (ev) => { $("audio").dataset.editando = "0"; ev.target.blur(); enviar({ tipo: "configurar", cambios: { volumen: parseInt(ev.target.value, 10) } }); };
  $("probar-sonido").onclick = () => enviar({ tipo: "probar_sonido", nombre: $("sel-sonido").value });
}

// Los formularios no se redibujan mientras alguien escribe en ellos.
function formularioOcupado(id) {
  const el = $(id);
  return el.contains(document.activeElement) || el.dataset.editando === "1";
}
/** Marca un formulario como «en edición» al escribir en él. */
function marcarEdicion(id) {
  const el = $(id);
  el.addEventListener("input", () => (el.dataset.editando = "1"));
}

/** Integrantes de cada equipo con su estado de líder (👑 actual, ✔ ya fue líder). */
function pintarEquiposForm() {
  const iv = estado.equipos_vista;
  $("equipos-form").innerHTML = `<h2>Equipos</h2>
    ${iv.map((x, i) => `<div style="margin-bottom:10px"><b class="color-eq e${i}">${nom(i)}</b> <span class="ayuda">(${x.integrantes.length} integrantes)</span>
      <div class="chips">${estado.config.equipos[i].integrantes.map((id) => {
        const usado = estado.lideres.usados[i].includes(id);
        const actual = estado.lideres.actuales[i] === id && estado.fase !== "lista";
        return `<span class="chip-p ${actual ? "actual" : usado ? "usado" : ""}" title="${actual ? "Líder actual" : usado ? "Ya fue líder en este ciclo" : "Aún no ha sido líder en este ciclo"}">${actual ? "👑 " : usado ? "✔ " : ""}${persona(id)}</span>`;
      }).join("") || '<span class="ayuda">Sin sortear</span>'}</div></div>`).join("")}
    <p class="ayuda">👑 líder actual · ✔ ya fue líder en este ciclo. Los nombres de los equipos se cambian en la pestaña Preparación.</p>`;
}

/** Formulario de ajuste manual del marcador. */
function pintarAjuste(forzar) {
  if (!forzar && formularioOcupado("ajuste")) return;
  $("ajuste").dataset.editando = "0";
  $("ajuste").innerHTML = `<h2>Ajuste manual de puntos</h2>
    <p class="ayuda">Solo para corregir errores. Usa números negativos para restar (por ejemplo, -10). Queda registrado en el historial.</p>
    <div class="dos-col"><div class="campo"><label>Equipo</label><select id="aj-equipo"><option value="0">${nom(0)}</option><option value="1">${nom(1)}</option></select></div>
    <div class="campo"><label>Puntos (+/-)</label><input id="aj-delta" type="number" step="1" value="0"></div></div>
    <div class="campo"><label>Motivo (opcional)</label><input id="aj-motivo" maxlength="120"></div>
    <button class="btn oro" id="aj-aplicar">Aplicar ajuste</button>`;
  $("aj-aplicar").onclick = () => {
    const delta = parseInt($("aj-delta").value, 10);
    const eqi = parseInt($("aj-equipo").value, 10);
    if (!delta) return aviso("Escribe un número distinto de cero.");
    if (!confirm(`¿Aplicar ${delta > 0 ? "+" : ""}${delta} puntos a ${estado.config.equipos[eqi].nombre}?`)) return;
    $("ajuste").dataset.editando = "0";
    enviar({ tipo: "ajustar_puntaje", equipo: eqi, delta, motivo: $("aj-motivo").value });
  };
}

/** Últimas `n` acciones registradas. */
function pintarBitacora(id, n) {
  const items = estado.bitacora.slice(-n).reverse();
  $(id).innerHTML = items.length ? items.map((b) => `<div><time>${b.hora}</time>${esc(b.texto)}</div>`).join("") : `<p class="ayuda">Aún no hay acciones.</p>`;
}

// ---------------------------------------------------------------- pestaña Preparación
function pintarPreparacion(forzar) {
  const e = estado, p = e.preparacion;
  const editable = e.fase === "preparacion";
  const dis = editable ? "" : "disabled";

  // 1. Participantes
  if (forzar || !formularioOcupado("prep-participantes")) {
    $("prep-participantes").dataset.editando = "0";
    $("prep-participantes").innerHTML = `<h2>👥 1. Participantes <span class="insignia ${p.participantes.length ? "verde" : ""}">${p.participantes.length} registrados</span></h2>
      ${editable ? `<p class="ayuda">Escribe un nombre y pulsa «Agregar», o pega una lista con <b>un nombre por línea</b>.</p>
      <div class="fila-botones"><input id="p-uno" class="buscador" style="flex:1;min-width:180px" maxlength="40" placeholder="Nombre de la persona">
        <button class="btn verde" id="p-agregar-uno">➕ Agregar</button></div>
      <details style="margin:10px 0"><summary class="ayuda" style="cursor:pointer"><b>📋 Pegar una lista de nombres</b></summary>
        <textarea id="p-lista" class="buscador" rows="8" placeholder="Ana María&#10;Luis&#10;Carolina&#10;…" style="margin-top:8px"></textarea>
        <button class="btn verde" id="p-agregar-lista" style="margin-top:8px">➕ Agregar todos</button></details>` :
        `<p class="ayuda">La partida ya está confirmada: la lista no se puede cambiar. Para modificarla, usa «Reiniciar configuración» (abajo).</p>`}
      <div class="lista-part">${p.participantes.map((x, i) => `<div class="part"><span class="n">${i + 1}</span>
        <input data-id="${x.id}" value="${esc(x.nombre)}" maxlength="40" ${dis} class="p-nombre">
        ${editable ? `<button class="btn fantasma chico p-borrar" data-id="${x.id}" title="Eliminar">✕</button>` : ""}</div>`).join("") || '<p class="ayuda">Todavía no hay participantes.</p>'}</div>
      ${editable && p.participantes.length ? boton("🗑 Vaciar la lista", { tipo: "vaciar_participantes" }, "fantasma chico", "¿Borrar a todos los participantes? (Se puede deshacer)") : ""}`;
    if (editable) {
      const agregarUno = () => { const v = $("p-uno").value.trim(); if (v) { $("prep-participantes").dataset.editando = "0"; enviar({ tipo: "agregar_participantes", nombres: [v] }); } };
      $("p-agregar-uno").onclick = agregarUno;
      $("p-uno").onkeydown = (ev) => { if (ev.key === "Enter") agregarUno(); };
      $("p-agregar-lista").onclick = () => {
        const nombres = $("p-lista").value.split(/\r?\n/).map((x) => x.trim()).filter(Boolean);
        if (!nombres.length) return aviso("Pega al menos un nombre (uno por línea).");
        $("prep-participantes").dataset.editando = "0";
        enviar({ tipo: "agregar_participantes", nombres });
      };
      $("prep-participantes").querySelectorAll(".p-nombre").forEach((inp) => {
        inp.onchange = () => { $("prep-participantes").dataset.editando = "0"; enviar({ tipo: "editar_participante", id: inp.dataset.id, nombre: inp.value }); };
      });
      $("prep-participantes").querySelectorAll(".p-borrar").forEach((b) => {
        b.onclick = () => { if (confirm(`¿Eliminar a ${estado.nombres_participantes[b.dataset.id]}?`)) enviar({ tipo: "eliminar_participante", id: b.dataset.id }); };
      });
    }
  }

  // 2. Equipos
  if (forzar || !formularioOcupado("prep-equipos")) {
    const sorteo = p.sorteo_equipos;
    const animar = sorteo && ultimoSorteoVisto !== null && sorteo.id !== ultimoSorteoVisto;
    ultimoSorteoVisto = sorteo ? sorteo.id : 0;
    const orden = {};
    if (sorteo) sorteo.secuencia.forEach((s, i) => (orden[s.id] = i));
    $("prep-equipos").dataset.editando = "0";
    $("prep-equipos").innerHTML = `<h2>🎲 2. Equipos ${sorteo ? `<span class="insignia verde">${e.tamanos_equipos[0]} vs ${e.tamanos_equipos[1]}</span>` : ""}</h2>
      <div class="dos-col">${[0, 1].map((i) => `<div class="campo"><label>Nombre del equipo ${i + 1}</label><input id="eq-nombre-${i}" maxlength="40" value="${esc(e.config.equipos[i].nombre)}"></div>`).join("")}</div>
      <button class="btn fantasma chico" id="guardar-nombres">💾 Guardar nombres</button>
      ${editable ? `<p class="ayuda" style="margin-top:12px">El sorteo lo hace la aplicación al azar: mezcla a todos y los reparte en partes iguales (si el total es impar, un equipo tiene una persona más). La pantalla pública muestra el reparto con una animación.</p>
      <div class="fila-botones">${boton(sorteo ? "🎲 Volver a sortear equipos" : "🎲 Sortear equipos", { tipo: "sortear_equipos" }, "morado grande", sorteo ? "¿Repetir el sorteo? Los equipos actuales se reemplazan." : "", p.participantes.length < 2)}</div>` : ""}
      ${sorteo ? `<div class="dos-col" style="margin-top:12px">${[0, 1].map((i) => `<div class="tarjeta-eq e${i}"><b>${nom(i)}</b> · ${e.config.equipos[i].integrantes.length} integrantes
        <div class="chips">${e.config.equipos[i].integrantes.map((id) => `<span class="chip-p${animar ? " aparece" : ""}" style="${animar ? `animation-delay:${(orden[id] * 0.12).toFixed(2)}s` : ""}">${persona(id)}</span>`).join("")}</div></div>`).join("")}</div>`
        : `<p class="ayuda">${p.participantes.length < 2 ? "Registra al menos 2 participantes para sortear." : "Aún no se han sorteado los equipos."}</p>`}`;
    $("guardar-nombres").onclick = () => {
      $("prep-equipos").dataset.editando = "0";
      enviar({ tipo: "configurar", cambios: { equipos: [0, 1].map((i) => ({ nombre: $("eq-nombre-" + i).value })) } });
    };
  }

  // 3. Preguntas
  {
    const animar = ultimaMezclaVista !== null && p.mezcla !== ultimaMezclaVista;
    ultimaMezclaVista = p.mezcla;
    const plan = e.plan_rondas;
    const usadas = new Set(e.preguntas_usadas);
    $("prep-preguntas").innerHTML = `<h2>🔀 3. Orden de las preguntas ${p.orden_preguntas.length ? `<span class="insignia verde">mezcladas</span>` : ""}</h2>
      <p class="ayuda">Hay <b>${e.preguntas_disponibles}</b> preguntas habilitadas (con 4 a 10 respuestas). Las ${datos.preguntas.length - e.preguntas_disponibles} pendientes de tu revisión no entran (ver <i>docs/REVISION_DE_PREGUNTAS.md</i>). La aplicación las ordena al azar; cada pregunta se usa una sola vez en la partida. Este orden es privado: la pantalla pública solo muestra una animación de cartas boca abajo.</p>
      ${editable ? `<div class="fila-botones">${boton(p.orden_preguntas.length ? "🔀 Volver a mezclar preguntas" : "🔀 Mezclar preguntas", { tipo: "mezclar_preguntas" }, "morado grande")}</div>` : ""}
      ${p.orden_preguntas.length ? `<ol class="orden-preg${animar ? " barajada" : ""}">${p.orden_preguntas.map((id, i) => {
        const q = pregunta(id), info = plan[i];
        return `<li class="${info ? (info.tipo === "extra" ? "extra" : "") : "reserva"} ${usadas.has(id) ? "usada" : ""}" style="${animar ? `animation-delay:${Math.min(i, 25) * 0.03}s` : ""}">
          <span class="etq-ronda">${info ? (info.tipo === "extra" ? `Extra ${info.extra_n} ×${info.multiplicador}` : `Ronda ${info.numero}`) : "Reserva"}</span>
          <span>P${q.numero}. ${esc(q.texto)}</span></li>`;
      }).join("")}</ol>` : ""}`;
  }

  // 4. Rondas
  if (forzar || !formularioOcupado("prep-rondas")) {
    const auto = p.rondas_principales === null;
    $("prep-rondas").dataset.editando = "0";
    $("prep-rondas").innerHTML = `<h2>🏁 4. Rondas</h2>
      <p class="ayuda">Para que <b>todos</b> sean líderes una vez sin repetir, las rondas principales deben ser al menos el tamaño del equipo más numeroso: <b>${e.minimo_principales}</b> (equipos de ${e.tamanos_equipos[0]} y ${e.tamanos_equipos[1]}). Si un equipo es más pequeño, en las últimas rondas ya no tendrá líderes nuevos y elegirá a su representante.</p>
      <div class="dos-col">
        <div class="campo"><label>Rondas principales (valen hasta 100 pts)</label>
          <label class="check"><input type="checkbox" id="r-auto" ${auto ? "checked" : ""} ${dis}> Automático (= ${e.minimo_principales})</label>
          <input id="r-principales" type="number" min="${e.minimo_principales}" max="60" value="${e.rondas_principales}" ${auto || !editable ? "disabled" : ""}></div>
        <div class="campo"><label>Rondas adicionales (con multiplicador)</label>
          <select id="r-extra" ${dis}>${Array.from({ length: 11 }, (_, n) => `<option value="${n}" ${n === p.rondas_extra ? "selected" : ""}>${n === 0 ? "Ninguna" : n === 1 ? "1 ronda adicional" : `${n} rondas adicionales`}</option>`).join("")}</select></div>
      </div>
      ${p.rondas_extra ? `<div class="campo"><label>Multiplicador de cada ronda adicional</label><div class="fila-botones">${p.multiplicadores_extra.map((m, i) =>
        `<label class="mult">Extra ${i + 1}: ×<input type="number" class="r-mult" min="1" max="10" value="${m}" ${dis}></label>`).join("")}</div></div>` : ""}
      ${editable ? `<button class="btn verde" id="guardar-rondas">💾 Guardar rondas</button>` : ""}
      <h3>Vista previa</h3>
      <table class="tabla"><tr><th>Ronda</th><th>Tipo</th><th>Multiplicador</th><th>Valor máximo</th></tr>
      ${e.plan_rondas.map((r) => `<tr class="${r.tipo === "extra" ? "fila-extra" : ""}"><td>${r.numero}</td><td>${r.tipo === "extra" ? `⭐ Extra ${r.extra_n}` : "Principal"}</td><td>×${r.multiplicador}</td><td><b>${r.maximo}</b> pts</td></tr>`).join("")}</table>
      <p class="ayuda">Total: ${e.rondas_principales} principales + ${p.rondas_extra} adicionales = <b>${e.total_rondas}</b> rondas (necesitan ${e.total_rondas} preguntas; hay ${e.preguntas_disponibles}). Los puntos de cada pregunta siempre suman 100; el multiplicador solo se aplica al banco de la ronda.</p>`;
    if (editable) {
      $("r-auto").onchange = () => { $("r-principales").disabled = $("r-auto").checked; };
      $("guardar-rondas").onclick = () => {
        $("prep-rondas").dataset.editando = "0";
        enviar({ tipo: "configurar_partida", rondas_principales: $("r-auto").checked ? null : parseInt($("r-principales").value, 10),
          rondas_extra: parseInt($("r-extra").value, 10),
          multiplicadores_extra: [...document.querySelectorAll(".r-mult")].map((x) => parseInt(x.value, 10)) });
      };
      $("r-extra").onchange = () => $("guardar-rondas").click();
    }
  }

  // 5. Confirmar
  $("prep-confirmar").innerHTML = editable ? `<h2>✅ 5. Confirmar e iniciar</h2>
      ${e.validaciones.length ? `<p class="ayuda">Antes de iniciar falta:</p><ul class="validaciones">${e.validaciones.map((v) => `<li>${esc(v)}</li>`).join("")}</ul>`
        : `<p class="ayuda" style="color:#86efac"><b>¡Todo listo!</b> ${e.tamanos_equipos[0]} vs ${e.tamanos_equipos[1]} participantes · ${e.rondas_principales} rondas principales + ${p.rondas_extra} adicionales · preguntas mezcladas.</p>`}
      <p class="ayuda">Al confirmar, los equipos y el orden de las preguntas quedan fijos durante toda la partida.</p>
      ${boton("✅ Confirmar e iniciar partida", { tipo: "confirmar_partida" }, "verde grande", "", e.validaciones.length > 0)}`
    : `<h2>✅ Partida confirmada</h2><p class="ayuda">Los equipos y el orden de las preguntas están fijos. Si necesitas cambiar participantes, equipos o rondas, reinicia la configuración: se borran marcador, rondas jugadas y líderes (se conservan participantes y equipos).</p>
      ${boton("↺ Reiniciar configuración", { tipo: "reiniciar_configuracion" }, "rojo", "¿Reiniciar la configuración? Se perderán el marcador, las rondas jugadas y el historial de líderes. Se conservan participantes y equipos. (Se puede deshacer)")}`;
}

// ---------------------------------------------------------------- pestaña Preguntas
function pintarPreguntas() {
  const q = $("buscador").value.trim().toLowerCase();
  const usadas = new Set(estado.preguntas_usadas);
  const lista = datos.preguntas.filter((p) => {
    if ($("filtro-nousadas").checked && usadas.has(p.id)) return false;
    if ($("filtro-jugables").checked && !p.habilitada) return false;
    if (!q) return true;
    return (p.texto + " " + p.respuestas.map((a) => a.etiqueta).join(" ")).toLowerCase().includes(q);
  });
  $("lista-preguntas").innerHTML = lista.map((p) => {
    const n = estado.tableros[p.id].ids.length;
    return `<div class="preg-item ${p.id === detalleId ? "sel" : ""} ${usadas.has(p.id) ? "usada" : ""}" data-preg="${p.id}">
      <span class="n">${p.numero}</span><span>${esc(p.texto)}</span>
      <span>${usadas.has(p.id) ? `<span class="insignia">usada</span>` : ""} ${!p.habilitada ? `<span class="insignia rojo">pendiente de revisión</span>` : `<span class="insignia verde">${n} en tablero · 100 pts</span>`}
      ${p.jugabilidad.estado === "mejorada" ? `<span class="insignia oro">mejorada</span>` : ""}${p.jugabilidad.advertencias.length ? `<span class="insignia oro">⚠ dominante</span>` : ""}
      ${p.revision.length ? `<span class="insignia oro">${p.revision.length} a revisar</span>` : ""}</span></div>`;
  }).join("") || `<p class="ayuda">Sin resultados.</p>`;
  pintarDetalle();
}

/** Detalle de una pregunta: respuestas, puntos, excluidas y notas de revisión. */
function pintarDetalle() {
  const p = detalleId && pregunta(detalleId);
  const c = $("detalle-pregunta");
  if (!p) { c.innerHTML = `<h2>Detalle</h2><p class="ayuda">Elige una pregunta de la lista.</p>`; return; }
  const enTablero = new Set(estado.tableros[p.id].ids);
  const puedeElegir = estado.fase === "lideres" && !estado.preguntas_usadas.includes(p.id) && enTablero.size > 0;
  c.innerHTML = `<h2>Pregunta ${p.numero}</h2><p style="font-size:18px;color:#fff;margin-top:0"><b>${esc(p.texto)}</b></p>
    <p class="ayuda">${p.respuestas_validas} respuestas válidas · ${p.respuestas_excluidas} excluidas · ${p.respuestas.length} respuestas distintas · ${enTablero.size} en el tablero, que suman <b>${p.puntos_tablero} puntos</b>.</p>
    <div class="paso ${p.habilitada ? "hecho" : ""}"><b class="titulo-paso">Jugabilidad: ${esc(p.jugabilidad.estado_nombre)}</b>
      ${p.jugabilidad.detalle ? `<p class="ayuda">${esc(p.jugabilidad.detalle)}</p>` : ""}
      ${p.jugabilidad.advertencias.map((x) => `<p class="ayuda" style="color:#fde68a">⚠ ${esc(x)}</p>`).join("")}
      ${p.jugabilidad.propuesta ? `<p class="ayuda"><b>Propuesta:</b> ${esc(p.jugabilidad.propuesta)}</p>` : ""}
      ${p.texto !== p.texto_original ? `<p class="ayuda">Redacción corregida. Texto original del Excel: «${esc(p.texto_original)}»</p>` : ""}</div>
    ${puedeElegir ? `<button class="btn verde" id="usar-pregunta">Usar en la próxima ronda (en lugar de la sorteada)</button>` : ""}
    <h3>Respuestas consolidadas</h3>
    <ul class="lista-resp">${p.respuestas.map((a, i) => `<li class="resp ${enTablero.has(a.id) ? "" : "fuera"}"><span class="pos">${enTablero.has(a.id) ? i + 1 : "–"}</span>
      <div><div class="etq">${esc(a.etiqueta)}${marcasContenido(a)}</div><div class="datos">${datosPuntos(a, p)}</div></div><div></div>${guiaAceptacion(a)}${detalleOriginales(a)}</li>`).join("")}</ul>
    ${p.excluidas.length ? `<h3>Respuestas excluidas</h3><ul class="ayuda">${p.excluidas.map((x) => `<li>«${esc(x.texto)}» (fila ${x.fila}): ${esc(x.motivo)}</li>`).join("")}</ul>` : ""}
    ${p.revision.length ? `<h3>Notas para revisión manual</h3><ul class="ayuda">${p.revision.map((x) => `<li><b>${esc(x.tipo)}</b>: ${esc(x.detalle)}</li>`).join("")}</ul>` : ""}`;
  const usar = $("usar-pregunta");
  if (usar) usar.onclick = () => { preguntaElegida = p.id; cambiarPestana("juego"); aviso("Pregunta elegida. Pulsa «Iniciar ronda».", true); };
}

$("lista-preguntas").addEventListener("click", (ev) => {
  const it = ev.target.closest("[data-preg]");
  if (it) { detalleId = it.dataset.preg; pintarPreguntas(); }
});
["buscador", "filtro-nousadas", "filtro-jugables"].forEach((id) => $(id).addEventListener("input", pintarPreguntas));

// ---------------------------------------------------------------- pestaña Reglas
function pintarReglas(forzar) {
  if (!forzar && formularioOcupado("reglas")) return;
  const c = estado.config;
  const editable = ["preparacion", "lista", "lideres", "asignada", "fin"].includes(estado.fase);
  const dis = editable ? "" : "disabled";
  $("reglas").dataset.editando = "0";
  $("reglas").innerHTML = `<h2>Reglas y opciones</h2>
    ${editable ? "" : `<p class="ayuda" style="color:#fbbf24"><b>Hay una ronda en curso.</b> Las reglas solo se pueden cambiar entre rondas, para no alterar puntos ya ganados.</p>`}
    <div class="campo"><label>Nombre del juego (se ve en la pantalla pública)</label><input id="r-titulo" maxlength="60" value="${esc(c.titulo)}"></div>
    <p class="ayuda"><b>Puntos:</b> cada pregunta reparte exactamente <b>100 puntos</b> entre las respuestas de su tablero, según su frecuencia real (vienen del Excel consolidado, <i>datos/preguntas_procesadas.xlsx</i>). Las rondas adicionales multiplican el banco (×2 = hasta 200 pts). El número de rondas y los multiplicadores se configuran en la pestaña <b>Preparación</b>.</p>
    <label class="check"><input type="checkbox" id="r-pasar" ${c.permitir_pasar ? "checked" : ""} ${dis}> El ganador del cara a cara puede elegir jugar o pasar el turno</label>
    <label class="check"><input type="checkbox" id="r-robo" ${c.robo_suma_respuesta ? "checked" : ""} ${dis}> En un robo exitoso, los puntos de la respuesta robada se suman al banco (como en televisión)</label>
    <div class="campo" style="margin-top:10px"><label for="r-empate">Empate en el cara a cara (ambas respuestas valen lo mismo)</label>
      <select id="r-empate" ${dis}><option value="desempate" ${c.empate_cara_a_cara === "desempate" ? "selected" : ""}>Nueva respuesta de desempate (recomendado)</option>
      <option value="primero" ${c.empate_cara_a_cara === "primero" ? "selected" : ""}>Gana quien respondió primero</option></select></div>
    <button class="btn verde" id="guardar-reglas">💾 Guardar reglas</button>`;
  $("guardar-reglas").onclick = () => {
    const cambios = { titulo: $("r-titulo").value.trim() || c.titulo };
    if (editable) Object.assign(cambios, { permitir_pasar: $("r-pasar").checked, robo_suma_respuesta: $("r-robo").checked,
      empate_cara_a_cara: $("r-empate").value });
    $("reglas").dataset.editando = "0";
    enviar({ tipo: "configurar", cambios });
  };
  $("peligro").innerHTML = `<h2>Reinicios</h2><p class="ayuda">Ninguna de estas opciones borra las preguntas, los participantes ni los archivos procesados. Ambas se pueden deshacer.</p>
    <div class="fila-botones">${boton("Reiniciar marcador a 0 – 0", { tipo: "reiniciar_marcador" }, "rojo", "¿Poner el marcador en 0 – 0? (Se puede deshacer)")}
    ${boton("↺ Reiniciar configuración (volver a Preparación)", { tipo: "reiniciar_configuracion" }, "rojo", "¿Volver a la preparación? Se borran marcador, rondas jugadas, historial de líderes y orden de preguntas. Se conservan participantes, equipos y reglas. (Se puede deshacer)")}</div>`;
}

// ---------------------------------------------------------------- pestaña Historial
function pintarHistorial() {
  const h = estado.historial_rondas;
  const hl = estado.lideres.historial;
  $("historial").innerHTML = `<h2>Rondas jugadas</h2>${h.length ? `<table class="tabla"><tr><th>Ronda</th><th>Pregunta</th><th>Líderes</th><th>Ganador</th><th>Puntos</th><th>Robo</th></tr>
    ${h.map((x) => `<tr><td>${x.numero}${x.tipo === "extra" ? ` ⭐ ×${x.multiplicador}` : ""}</td><td>${esc(x.pregunta)}</td><td>${(x.lideres || []).map((l) => esc(l || "—")).join(" vs ")}</td><td>${nom(x.ganador)}</td><td>${x.puntos}</td><td>${x.robo ? esc(x.robo) : "—"}</td></tr>`).join("")}</table>` : `<p class="ayuda">Todavía no se ha terminado ninguna ronda.</p>`}
    <h2 style="margin-top:18px">Historial de líderes</h2>${hl.length ? `<table class="tabla"><tr><th>Ronda</th><th>Ciclo</th><th>Equipo</th><th>Líder</th></tr>
    ${hl.map((x) => `<tr><td>${x.ronda}</td><td>${x.ciclo}</td><td>${nom(x.equipo)}</td><td>${esc(x.nombre)}${x.unico ? " <span class=\"insignia\">único pendiente</span>" : ""}</td></tr>`).join("")}</table>` : `<p class="ayuda">Aún no se han sorteado líderes.</p>`}`;
  pintarBitacora("bitacora", 300);
}

// ---------------------------------------------------------------- general
function pintar(forzarFormularios = false) {
  if (!estado || !datos) return;
  if (!pestana) { cambiarPestana(estado.fase === "preparacion" ? "preparacion" : "juego"); return; }
  $("titulo").textContent = estado.config.titulo + " · Panel del presentador";
  $("fase").textContent = estado.fase_nombre;
  const d = $("btn-deshacer");
  d.disabled = !estado.puede_deshacer || ocupado;
  d.title = estado.ultima_deshacible ? "Deshacer: " + estado.ultima_deshacible : "Nada que deshacer";
  if (estado.fase !== "lideres") preguntaElegida = null;
  pintarControl();
  pintarRespuestas();
  pintarMarcador();
  pintarAudio(forzarFormularios);
  pintarEquiposForm();
  pintarAjuste(forzarFormularios);
  pintarBitacora("bitacora-corta", 8);
  if (pestana === "preparacion") pintarPreparacion(forzarFormularios);
  if (pestana === "preguntas") pintarPreguntas();
  if (pestana === "reglas") pintarReglas(forzarFormularios);
  if (pestana === "historial") pintarHistorial();
}

/** Cambia de pestaña y la redibuja. */
function cambiarPestana(t) {
  pestana = t;
  document.querySelectorAll("#pestanas button").forEach((b) => b.classList.toggle("activa", b.dataset.tab === t));
  ["preparacion", "juego", "preguntas", "reglas", "historial"].forEach((x) => $("tab-" + x).classList.toggle("oculto", x !== t));
  pintar(true);
}
$("pestanas").addEventListener("click", (ev) => { const b = ev.target.closest("button[data-tab]"); if (b) cambiarPestana(b.dataset.tab); });

$("btn-deshacer").onclick = () => {
  if (confirm("¿Deshacer la última acción?\n\n" + (estado.ultima_deshacible || ""))) enviar({ tipo: "deshacer" });
};
// Se abre como pestaña normal: así Meet puede compartirla con su audio («Compartir también el audio de la pestaña»).
$("btn-publica").onclick = () => window.open("/publico", "pantalla_publica");

async function sondear() { // «espera larga»: el servidor responde en cuanto algo cambia
  for (;;) {
    let e;
    try {
      const url = estado ? `/api/presentador?esperar=${estado.version}` : "/api/presentador";
      e = await (await fetch(url, { cache: "no-store" })).json();
    } catch (err) { // solo un fallo de red marca la conexión en rojo
      $("conexion").classList.add("mal");
      await new Promise((r) => setTimeout(r, 1000));
      continue;
    }
    $("conexion").classList.remove("mal");
    if (!ocupado && (!estado || e.version !== estado.version)) {
      estado = e;
      try { pintar(); } catch (err) { console.error("Error al dibujar el panel:", err); }
    }
  }
}

(async function iniciar() {
  try {
    datos = await (await fetch("/api/preguntas")).json();
  } catch (e) {
    aviso("No se pudo conectar con el juego. Inicia el servidor con INICIAR_JUEGO.bat");
    return;
  }
  sondear();
})();
["ajuste", "reglas", "audio", "prep-participantes", "prep-equipos", "prep-rondas"].forEach(marcarEdicion);
