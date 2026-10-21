// Pantalla pública: solo lee /api/publico (que nunca contiene respuestas ocultas).
const $ = (id) => document.getElementById(id);
let estado = null;
let ultimoEvento = null;
let claveTablero = "";
let temporizadorCapa = null;

function esc(t) {
  return String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
const nombre = (e, i) => (e.equipos[i].nombre || `Equipo ${i + 1}`);

function equipoEnTurno(e) {
  const r = e.ronda;
  if (!r) return null;
  switch (e.fase) {
    case "cara_a_cara": return r.cara_a_cara.primero;
    case "decision": return r.cara_a_cara.ganador;
    case "juego": return r.control;
    case "robo": return r.robo.equipo;
    case "resuelta": return r.ganador;
    case "asignada": return r.asignada_a;
    default: return null;
  }
}

function textoFase(e) {
  const r = e.ronda;
  if (!r) return "";
  const n = (i) => nombre(e, i);
  switch (e.fase) {
    case "cara_a_cara": return r.cara_a_cara.primero === null ? "Cara a cara · ¡levanten la mano en Meet!" : `Cara a cara · responde primero ${n(r.cara_a_cara.primero)}`;
    case "decision": return `${n(r.cara_a_cara.ganador)} ganó el cara a cara: ¿juega o pasa?`;
    case "juego": return `Juega ${n(r.control)}`;
    case "robo": return `Oportunidad de robo para ${n(r.robo.equipo)}`;
    case "resuelta": return `Gana la ronda: ${n(r.ganador)}`;
    case "asignada": return `${n(r.asignada_a)} se lleva ${r.puntos_asignados} puntos`;
    default: return "";
  }
}

function pintarTablero(r) {
  const tablero = $("tablero");
  const clave = r ? `${r.numero}-${r.casillas.length}` : "";
  if (clave !== claveTablero) {
    claveTablero = clave;
    tablero.innerHTML = "";
    if (!r) return;
    const filas = Math.max(4, Math.ceil(r.casillas.length / 2));
    tablero.style.gridTemplateRows = `repeat(${filas}, 1fr)`;
    for (let i = 0; i < filas * 2; i++) {
      const d = document.createElement("div");
      d.className = "casilla" + (i >= r.casillas.length ? " vacia" : "");
      d.innerHTML = `<div class="cara frente"><span class="num">${i + 1}</span></div><div class="cara reverso"><span class="txt"></span><span class="pts"></span></div>`;
      tablero.appendChild(d);
    }
  }
  if (!r) return;
  r.casillas.forEach((c, i) => {
    const d = tablero.children[i];
    if (c.revelada) {
      d.querySelector(".txt").textContent = c.texto;
      d.querySelector(".pts").textContent = c.puntos;
    } else {
      d.querySelector(".txt").textContent = "";
      d.querySelector(".pts").textContent = "";
    }
    d.classList.toggle("revelada", c.revelada);
    d.classList.toggle("final", !!c.revelada && c.como === "final");
  });
}

function pintar(e) {
  document.body.classList.toggle("sin-animaciones", !e.animaciones);
  document.title = e.titulo;
  $("logo").textContent = e.titulo;
  const r = e.ronda;
  $("chip-ronda").textContent = r ? (r.tipo === "extra" ? `⭐ Ronda extra ${r.extra_n} · ${r.numero} de ${e.total_rondas}` : `Ronda ${r.numero} de ${e.total_rondas}`)
    : `${e.total_rondas} rondas`;
  $("chip-multi").classList.toggle("oculto", !r);
  $("chip-multi").classList.toggle("multi", !!r && r.multiplicador > 1);
  if (r) $("chip-multi").textContent = r.multiplicador > 1 ? `×${r.multiplicador} · hasta ${r.maximo} pts` : `Hasta ${r.maximo} pts`;
  $("banco").textContent = r ? r.banco : 0;
  $("fase-aviso").textContent = textoFase(e);
  $("texto-pregunta").textContent = r ? r.pregunta : "";
  const turno = equipoEnTurno(e);
  [0, 1].forEach((i) => {
    $("nombre" + i).textContent = nombre(e, i);
    $("puntos" + i).textContent = e.puntajes[i];
    const lider = e.equipos[i].lider;
    const sinNuevo = e.equipos[i].sin_lider_nuevo;
    $("lider" + i).innerHTML = lider ? `Líder en juego<b>${esc(lider)}</b>` : sinNuevo ? `Ciclo de líderes completo<b>Elige el equipo</b>` : "";
    $("lider" + i).classList.toggle("oculto", !lider && !sinNuevo);
    $("eq" + i).classList.toggle("turno", turno === i);
    const ganadas = e.historial.filter((h) => h.ganador === i).length;
    $("hist" + i).textContent = e.historial.length ? `Rondas ganadas: ${ganadas}` : "";
  });
  pintarTablero(r);
  const strikes = r && ["juego", "robo", "resuelta", "asignada"].includes(e.fase) ? r.strikes : 0;
  [...$("strikes").children].forEach((x, i) => x.classList.toggle("activa", i < strikes));

  const franja = $("franja");
  let texto = "", tipo = "";
  if (r && e.fase === "juego" && r.strikes === 2) { texto = `¡Dos strikes! ${nombre(e, 1 - r.control)}, prepárense para un posible robo`; tipo = "alerta"; }
  else if (r && e.fase === "robo") { texto = `Turno de robo de ${nombre(e, r.robo.equipo)}: una sola respuesta para llevarse ${r.banco} puntos`; tipo = "alerta"; }
  else if (r && e.fase === "resuelta" && r.robo.resultado) { texto = r.robo.resultado === "exitoso" ? "¡Robo exitoso!" : "Robo fallido"; tipo = "oro"; }
  franja.textContent = texto;
  franja.className = "franja " + tipo + (texto ? "" : " oculto");

  pintarPortada(e);
  const necesitaClic = e.sonido && (e.efectos || e.musica) && e.volumen > 0 && !Sonidos.listo();
  $("activar-sonido").classList.toggle("oculto", !necesitaClic);
}

function pintarPortada(e) {
  const p = $("portada");
  const integrantes = (i) => e.equipos_sorteados
    ? `<div class="miembros">${e.equipos[i].integrantes.map((n) => `<span>${esc(n)}</span>`).join("")}</div>` : "";
  if (e.fase === "preparacion") {
    p.classList.remove("oculto");
    p.innerHTML = `<div><h1${e.equipos_sorteados ? ' class="chico"' : ""}>${esc(e.titulo)}</h1>
      <div class="sub">${e.equipos_sorteados ? "¡Estos son los equipos!" : "¡Encuestamos a nuestra gente! ¿Adivinarás qué respondieron?"}</div>
      <div class="vs"><div class="eq e0">${esc(nombre(e, 0))}${integrantes(0)}</div>
      <div class="contra">VS</div><div class="eq e1">${esc(nombre(e, 1))}${integrantes(1)}</div></div>
      ${e.equipos_sorteados ? "" : `<div class="sub">${e.participantes ? `${e.participantes} participantes registrados · sorteo de equipos en preparación` : "Preparando la partida…"}</div>`}</div>`;
  } else if ((e.fase === "lista" || e.fase === "lideres") && e.proxima_ronda) {
    p.classList.remove("oculto");
    const pr = e.proxima_ronda;
    const lider = (i) => e.fase === "lista" ? "Sorteo de líder pendiente"
      : e.equipos[i].lider ? `Líder: <b>${esc(e.equipos[i].lider)}</b>` : "Ciclo completo · elige el equipo";
    p.innerHTML = `<div class="previa${pr.tipo === "extra" ? " extra" : ""}">
      <div class="sub">${pr.tipo === "extra" ? `⭐ Ronda extra ${pr.extra_n} · Puntos ×${pr.multiplicador}` : `Ronda principal ${pr.numero} de ${e.rondas_principales}`}</div>
      <h1>${pr.tipo === "extra" ? "¡Ronda extra!" : `Ronda ${pr.numero}`}</h1>
      <div class="sub">¡Esta ronda vale hasta <b>${pr.maximo}</b> puntos!</div>
      <div class="vs">${[0, 1].map((i) => `<div class="eq e${i}">${esc(nombre(e, i))}<small style="font-size:5vh;font-family:var(--fuente-titulo)">${e.puntajes[i]} pts</small>
        <small>${lider(i)}</small><small class="pendientes">Ciclo ${e.ciclo_lideres} · faltan ${e.equipos[i].lideres_pendientes} por ser líderes</small></div>`).join('<div class="contra">VS</div>')}</div>
      </div>`;
  } else if (e.fase === "fin") {
    p.classList.remove("oculto");
    const f = e.resultado_final || { ganador: null, puntajes: e.puntajes };
    const titulo = f.ganador === null ? "¡Empate!" : `¡${esc(nombre(e, f.ganador))}!`;
    const clase = (i) => (f.ganador === null ? "" : f.ganador === i ? " ganador-eq" : " perdedor-eq");
    p.innerHTML = `<div class="final${f.ganador === null ? "" : " con-ganador"}"><div class="sub">Resultado final</div>
      ${f.ganador === null ? "" : `<div class="trofeo">🏆</div>`}<h1>${titulo}</h1>
      ${f.ganador === null ? "" : `<div class="ganador">¡Equipo ganador!</div>`}
      <div class="vs"><div class="eq e0${clase(0)}">${esc(nombre(e, 0))}<small style="font-size:6vh;font-family:var(--fuente-titulo)">${f.puntajes[0]}</small></div>
      <div class="contra">–</div><div class="eq e1${clase(1)}">${esc(nombre(e, 1))}<small style="font-size:6vh;font-family:var(--fuente-titulo)">${f.puntajes[1]}</small></div></div>
      <div class="sub">¡Gracias por jugar!</div></div>`;
  } else {
    p.classList.add("oculto");
  }
}

function mostrarCapa(html, ms) {
  const capa = $("capa");
  clearTimeout(temporizadorCapa);
  capa.innerHTML = html;
  temporizadorCapa = setTimeout(() => {
    const m = capa.firstElementChild;
    if (m && estado.animaciones) { m.classList.add("salir"); setTimeout(() => (capa.innerHTML = ""), 350); }
    else capa.innerHTML = "";
  }, ms);
}
const mensaje = (texto, sub = "", clase = "") => `<div class="mensaje ${clase}">${esc(texto)}${sub ? `<small>${esc(sub)}</small>` : ""}</div>`;
const granX = (n, sub) => `<div style="text-align:center"><div class="gran-x">${"<span>X</span>".repeat(n)}</div>${sub ? mensaje(sub, "", "malo") : ""}</div>`;

function confeti(cantidad = 140) {
  if (!estado || !estado.animaciones) return;
  const c = $("confeti");
  c.innerHTML = "";
  const colores = ["#fbbf24", "#3b82f6", "#f97316", "#22c55e", "#ec4899", "#fff"];
  for (let i = 0; i < cantidad; i++) {
    const p = document.createElement("i");
    p.style.left = Math.random() * 100 + "vw";
    p.style.background = colores[i % colores.length];
    p.style.animationDuration = 2.5 + Math.random() * 3 + "s";
    p.style.animationDelay = Math.random() * 1.5 + "s";
    c.appendChild(p);
  }
  setTimeout(() => (c.innerHTML = ""), 7500);
}

window.confeti = confeti;
const sonar = (nombreSonido) => Sonidos.efecto(nombreSonido);

function sacudir() {
  if (!estado.animaciones) return;
  const el = $("escenario");
  el.classList.remove("sacudir");
  void el.offsetWidth;
  el.classList.add("sacudir");
}

function animarEvento(ev, e) {
  const eq = ev.equipo;
  const nom = eq === null || eq === undefined ? "" : nombre(e, eq);
  switch (ev.tipo) {
    case "correcta": {
      sonar("correcta");
      const casilla = $("tablero").children[(ev.extra.posicion || 1) - 1];
      if (casilla) { casilla.classList.remove("brillo"); void casilla.offsetWidth; casilla.classList.add("brillo"); }
      mostrarCapa(mensaje(ev.texto, nom, "bueno"), 1300);
      break;
    }
    case "revelar_final": sonar("revelar"); break;
    case "strike":
      sonar(ev.extra.strikes === 2 ? "strike2" : "strike");
      sacudir();
      mostrarCapa(granX(ev.extra.strikes, ev.texto), ev.extra.strikes === 2 ? 2200 : 1700);
      break;
    case "no_esta": sonar("no_esta"); sacudir(); mostrarCapa(granX(1, ev.texto), 1500); break;
    case "robo_oportunidad": sonar("robo"); sacudir();
      mostrarCapa(`<div style="text-align:center"><div class="gran-x"><span>X</span><span>X</span><span>X</span></div>${mensaje(ev.texto, nom + " puede robar")}</div>`, 3000); break;
    case "robo_exitoso": sonar("robo_exitoso"); mostrarCapa(mensaje("¡Robo exitoso!", `${nom} se lleva ${ev.extra.banco} puntos`, "bueno"), 3200); break;
    case "robo_fallido": sonar("robo_fallido"); mostrarCapa(mensaje("¡Robo fallido!", `El banco es para ${nom}`, "malo"), 3000); break;
    case "tablero_completo": sonar("tablero"); mostrarCapa(mensaje("¡Tablero completo!", `${nom} gana la ronda`, "bueno"), 2600); break;
    case "manual": sonar("turno"); mostrarCapa(mensaje(ev.texto), 2000); break;
    case "ronda_ganada": sonar("puntos"); mostrarCapa(mensaje(ev.texto, `+${ev.extra.puntos} puntos`, "bueno"), 3000); break;
    case "nueva_ronda":
      Sonidos.detenerMusica();
      if (ev.extra.tipo === "extra" && e.animaciones) { Espectaculo.rondaExtra(ev.extra); break; }
      sonar(ev.extra.tipo === "extra" ? "ronda_extra" : "nueva_ronda");
      mostrarCapa(mensaje(ev.texto, ev.extra.multiplicador > 1 ? `¡Puntos ×${ev.extra.multiplicador}! Hasta ${ev.extra.maximo} puntos` : "¡Atentos a la pregunta!"), 1800); break;
    case "sorteo_equipos": Espectaculo.sorteoEquipos(ev.extra.secuencia, [nombre(e, 0), nombre(e, 1)], e.animaciones); break;
    case "mezcla_preguntas": Espectaculo.mezcla(ev.extra.cantidad, e.animaciones); break;
    case "sorteo_lideres": Espectaculo.ruletaLideres(ev.extra, [nombre(e, 0), nombre(e, 1)], e.animaciones); break;
    case "lideres_revertidos": Espectaculo.cancelar(); mostrarCapa(mensaje("Sorteo de líderes anulado", "Se repetirá el sorteo"), 1800); break;
    case "ronda_cancelada": Espectaculo.cancelar(); mostrarCapa(mensaje("Ronda cancelada", "No se asignaron puntos"), 1800); break;
    case "partida_confirmada": Sonidos.musica();
      mostrarCapa(mensaje("¡Comienza el juego!", `${ev.extra.principales} rondas principales${ev.extra.extra ? ` + ${ev.extra.extra} extra` : ""}`, "bueno"), 2600); break;
    case "cara_a_cara_ganado": sonar("cara_a_cara"); mostrarCapa(mensaje(ev.texto, "¿Juega o pasa?"), 2000); break;
    case "turno": sonar("turno"); mostrarCapa(mensaje(ev.texto), 1500); break;
    case "fin_juego": sonar("fanfarria_final"); confeti(); break;
    case "musica": case "partida_lista": Sonidos.musica(); break;
    case "prueba_sonido": ev.extra.sonido === "musica" ? Sonidos.musica() : sonar(ev.extra.sonido); break;
    default: break;
  }
}

function recibir(e) {
  const primera = !estado;
  estado = e;
  Sonidos.configurar({ sonido: e.sonido, musica: e.musica, efectos: e.efectos, volumen: e.volumen });
  pintar(e);
  const ev = e.evento;
  if (ev && ev.id !== ultimoEvento) {
    if (!primera) animarEvento(ev, e); // al abrir o recargar la página no se repite el último efecto
    ultimoEvento = ev.id;
  }
}

// «Espera larga»: el servidor responde en cuanto hay un cambio. La siguiente consulta se lanza
// al recibir la respuesta (sin temporizadores), así la pestaña compartida en Meet se actualiza
// al instante aunque el navegador la tenga en segundo plano.
async function actualizar() {
  for (;;) {
    try {
      const url = estado ? `/api/publico?esperar=${estado.version}` : "/api/publico";
      const e = await (await fetch(url, { cache: "no-store" })).json();
      $("sin-conexion").classList.add("oculto");
      if (!estado || e.version !== estado.version) recibir(e);
    } catch (err) {
      $("sin-conexion").classList.remove("oculto");
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
}

let musicaInicialSonada = false;
function activarAudio() {
  Sonidos.activar();
  setTimeout(() => {
    if (!estado) return;
    pintar(estado);
    // Al habilitar el sonido con la portada en pantalla, suena la música de entrada una vez.
    if (!musicaInicialSonada && estado.fase === "preparacion" && Sonidos.listo()) {
      musicaInicialSonada = true;
      Sonidos.musica();
    }
  }, 150);
}
$("activar-sonido").addEventListener("click", (ev) => { ev.stopPropagation(); activarAudio(); });
document.addEventListener("click", () => { if (!Sonidos.listo()) activarAudio(); });
actualizar();
