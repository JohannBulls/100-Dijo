// Animaciones largas de la pantalla pública: sorteo de equipos, mezcla de preguntas,
// ruleta de líderes y entrada a una ronda extra.
// IMPORTANTE: ninguna animación decide nada. Todas dibujan el resultado que el servidor ya
// sorteó y guardó (la secuencia de equipos y el índice del líder elegido llegan en el evento).
const Espectaculo = (() => {
  let turno = 0;                       // si llega otro evento, la animación anterior se cancela
  const capa = () => document.getElementById("espectaculo");
  const e = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function iniciar() {
    turno += 1;
    const c = capa();
    c.innerHTML = "";
    c.classList.remove("oculto", "saliendo");
    return turno;
  }
  const vigente = (t) => t === turno;
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  async function terminar(t, ms = 0) {
    await esperar(ms);
    if (!vigente(t)) return;
    const c = capa();
    c.classList.add("saliendo");
    await esperar(450);
    if (vigente(t)) { c.classList.add("oculto"); c.classList.remove("saliendo"); c.innerHTML = ""; }
  }
  function cancelar() { turno += 1; const c = capa(); c.classList.add("oculto"); c.innerHTML = ""; }

  // ------------------------------------------------------------------ sorteo de equipos
  async function sorteoEquipos(secuencia, nombres, animado) {
    const t = iniciar();
    const total = [0, 1].map((i) => secuencia.filter((s) => s.equipo === i).length);
    capa().innerHTML = `<div class="esp-sorteo">
      <h2 class="esp-titulo">🎲 Sorteo de equipos</h2>
      <div class="esp-columnas">
        <div class="esp-eq e0"><h3>${e(nombres[0])}</h3><div class="esp-cuenta" id="esp-c0">0 / ${total[0]}</div><div class="esp-lista" id="esp-l0"></div></div>
        <div class="esp-centro"><div class="esp-slot" id="esp-slot">…</div><div class="esp-flecha" id="esp-flecha"></div></div>
        <div class="esp-eq e1"><h3>${e(nombres[1])}</h3><div class="esp-cuenta" id="esp-c1">0 / ${total[1]}</div><div class="esp-lista" id="esp-l1"></div></div>
      </div></div>`;
    const todos = secuencia.map((s) => s.nombre);
    const cuenta = [0, 0];
    const paso = Math.max(220, Math.min(520, 7500 / Math.max(1, secuencia.length)));
    for (const s of secuencia) {
      if (!vigente(t)) return;
      const slot = document.getElementById("esp-slot");
      if (animado) { // el nombre «gira» un instante entre los participantes antes de mostrar al sorteado
        for (let k = 0; k < 3; k++) { slot.textContent = todos[Math.floor(Math.random() * todos.length)]; slot.className = "esp-slot girando"; await esperar(paso / 6); }
      }
      if (!vigente(t)) return;
      slot.textContent = s.nombre;
      slot.className = `esp-slot fijo e${s.equipo}`;
      const flecha = document.getElementById("esp-flecha");
      flecha.className = `esp-flecha e${s.equipo}`;
      flecha.textContent = s.equipo === 0 ? `⬅ ${nombres[0]}` : `${nombres[1]} ➡`;
      Sonidos.efecto("sorteo_paso", { equipo: s.equipo });
      cuenta[s.equipo] += 1;
      const chip = document.createElement("div");
      chip.className = "esp-chip entra";
      chip.textContent = s.nombre;
      document.getElementById("esp-l" + s.equipo).appendChild(chip);
      document.getElementById("esp-c" + s.equipo).textContent = `${cuenta[s.equipo]} / ${total[s.equipo]}`;
      await esperar(animado ? paso / 2 : 30);
    }
    if (!vigente(t)) return;
    document.getElementById("esp-slot").textContent = "¡Equipos listos!";
    document.getElementById("esp-slot").className = "esp-slot listo";
    document.getElementById("esp-flecha").textContent = `${total[0]} vs ${total[1]}`;
    document.getElementById("esp-flecha").className = "esp-flecha";
    Sonidos.efecto("sorteo_fin");
    await terminar(t, 3500);
  }

  // ------------------------------------------------------------------ mezcla de preguntas
  async function mezcla(cantidad, animado) {
    const t = iniciar();
    const cartas = Array.from({ length: 12 }, (_, i) =>
      `<div class="esp-carta" style="--dx:${Math.round(Math.random() * 60 - 30)}vw;--dy:${Math.round(Math.random() * 30 - 15)}vh;--rot:${Math.round(Math.random() * 60 - 30)}deg;--d:${(i * 0.06).toFixed(2)}s">?</div>`).join("");
    capa().innerHTML = `<div class="esp-mezcla"><h2 class="esp-titulo">🔀 Mezclando preguntas…</h2><div class="esp-mazo${animado ? " barajando" : ""}">${cartas}</div><div class="esp-sub" id="esp-mezcla-sub">&nbsp;</div></div>`;
    Sonidos.efecto("mezcla", { duracion: 2.2 });
    await esperar(animado ? 2400 : 300);
    if (!vigente(t)) return;
    capa().querySelector(".esp-titulo").textContent = "🔀 ¡Preguntas mezcladas!";
    document.getElementById("esp-mezcla-sub").textContent = `${cantidad} preguntas en un orden nuevo, totalmente al azar`;
    await terminar(t, 2000);
  }

  // ------------------------------------------------------------------ ruleta de líderes
  const COLORES = [["#1d4ed8", "#2563eb", "#3b82f6", "#1e40af"], ["#c2410c", "#ea580c", "#f97316", "#fb923c"]];
  function punto(cx, cy, r, grados) {
    const a = (grados * Math.PI) / 180;
    return [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  }
  function rueda(nombres, equipo) {
    const n = nombres.length, cx = 500, cy = 500, r = 480, seg = 360 / n;
    const largo = Math.min(16, Math.max(...nombres.map((x) => x.length), 4));
    const fs = Math.max(22, Math.min(54, 350 / (largo * 0.58)));
    let s = "";
    nombres.forEach((nom, k) => {
      const color = COLORES[equipo][k % 4];
      if (n === 1) s += `<circle class="seg" data-k="0" cx="${cx}" cy="${cy}" r="${r}" fill="${color}"/>`;
      else {
        const [x1, y1] = punto(cx, cy, r, k * seg), [x2, y2] = punto(cx, cy, r, (k + 1) * seg);
        s += `<path class="seg" data-k="${k}" d="M${cx},${cy} L${x1.toFixed(1)},${y1.toFixed(1)} A${r},${r} 0 ${seg > 180 ? 1 : 0} 1 ${x2.toFixed(1)},${y2.toFixed(1)} Z" fill="${color}"/>`;
      }
      const centro = k * seg + seg / 2;
      const texto = nom.length > 16 ? nom.slice(0, 15) + "…" : nom;
      s += `<text transform="rotate(${(centro - 90).toFixed(2)} ${cx} ${cy})" x="${cx + r * 0.9}" y="${cy}" dy="0.35em" text-anchor="end" font-size="${fs.toFixed(0)}">${e(texto)}</text>`;
    });
    return `<svg viewBox="0 0 1000 1000" class="esp-rueda-svg"><g class="giro">${s}</g><circle cx="500" cy="500" r="80" class="eje"/></svg>`;
  }

  async function girar(t, eqInfo, nombreEquipo, animado) {
    const { candidatos, indice, elegido, equipo } = eqInfo;
    capa().innerHTML = `<div class="esp-ruleta">
      <h2 class="esp-titulo">🎡 Líder de <span class="e${equipo}-txt">${e(nombreEquipo)}</span></h2>
      <div class="esp-sub">${candidatos.length === 1 ? "Único integrante que aún no ha sido líder en este ciclo" : `${candidatos.length} integrantes que aún no han sido líderes en este ciclo`}</div>
      <div class="esp-rueda"><div class="esp-puntero"></div>${rueda(candidatos, equipo)}</div>
      <div class="esp-ganador oculto" id="esp-ganador"></div></div>`;
    const g = capa().querySelector(".giro");
    const seg = 360 / candidatos.length;
    // Ángulo final calculado a partir del índice sorteado por el servidor: el segmento del elegido
    // queda exactamente bajo el puntero (con un pequeño desfase dentro del mismo segmento).
    const desfase = (Math.random() - 0.5) * seg * 0.6;
    const final = 360 * 7 - (indice * seg + seg / 2) + desfase;
    const dur = animado ? 4.6 : 0.01;
    await esperar(350);
    if (!vigente(t)) return;
    Sonidos.efecto("ruleta", { duracion: dur });
    g.style.transition = `transform ${dur}s cubic-bezier(0.15, 0.8, 0.15, 1)`;
    g.style.transform = `rotate(${final}deg)`;
    await esperar(dur * 1000 + 250);
    if (!vigente(t)) return;
    const seg_el = capa().querySelector(`.seg[data-k="${indice}"]`);
    if (seg_el) seg_el.classList.add("elegido");
    const gan = document.getElementById("esp-ganador");
    gan.innerHTML = `<small>¡Líder de ${e(nombreEquipo)}!</small>${e(elegido)}`;
    gan.className = `esp-ganador e${equipo}`;
    Sonidos.efecto("lider");
    if (window.confeti) window.confeti(60);
    await esperar(2600);
  }

  async function ruletaLideres(info, nombres, animado) {
    const t = iniciar();
    const titulo = info.tipo === "extra" ? `⭐ Ronda extra ${info.extra_n} · ×${info.multiplicador}` : `Ronda ${info.numero}`;
    if (info.nuevo_ciclo) {
      capa().innerHTML = `<div class="esp-aviso"><div class="esp-icono">♻️</div><h2 class="esp-titulo">¡Nuevo ciclo de líderes!</h2>
        <div class="esp-sub">Todos ya fueron líderes una vez. Ciclo ${info.ciclo}: todos vuelven a participar.</div></div>`;
      Sonidos.efecto("nuevo_ciclo");
      await esperar(2600);
      if (!vigente(t)) return;
    }
    const cambio = info.motivo === "cambio_cara_a_cara";
    capa().innerHTML = `<div class="esp-aviso"><div class="esp-icono">🎡</div><h2 class="esp-titulo">${cambio ? "¡Cambio de líderes!" : "Sorteo de líderes"}</h2>
      <div class="esp-sub">${cambio ? "Los dos líderes agotaron sus intentos en el cara a cara" : `${e(titulo)} · Ciclo ${info.ciclo}`}</div></div>`;
    await esperar(1300);
    for (const eq of info.equipos) {
      if (!vigente(t)) return;
      if (eq.completo) {
        capa().innerHTML = `<div class="esp-aviso"><div class="esp-icono">✅</div><h2 class="esp-titulo e${eq.equipo}-txt">${e(nombres[eq.equipo])}</h2>
          <div class="esp-sub">Todos sus integrantes ya fueron líderes en este ciclo.<br>No hay nuevo sorteo: el equipo elige a su representante.</div></div>`;
        Sonidos.efecto("turno");
        await esperar(3000);
      } else {
        await girar(t, eq, nombres[eq.equipo], animado);
      }
    }
    if (!vigente(t)) return;
    capa().innerHTML = `<div class="esp-aviso"><h2 class="esp-titulo">Líderes · ${e(titulo)}</h2>
      <div class="esp-resumen">${info.equipos.map((x) => `<div class="esp-res e${x.equipo}"><small>${e(nombres[x.equipo])}</small>${x.elegido ? e(x.elegido) : "Elige el equipo"}</div>`).join("")}</div></div>`;
    await terminar(t, 2600);
  }

  // ------------------------------------------------------------------ ronda extra
  async function rondaExtra(info) {
    const t = iniciar();
    capa().innerHTML = `<div class="esp-extra"><div class="esp-estrellas">⭐ ⭐ ⭐</div><h2>¡RONDA EXTRA ${info.extra_n}!</h2>
      <div class="esp-multi">Puntos ×${info.multiplicador}</div><div class="esp-sub">¡Esta ronda vale hasta ${info.maximo} puntos!</div></div>`;
    Sonidos.efecto("ronda_extra");
    if (window.confeti) window.confeti(80);
    await terminar(t, 3300);
  }

  return { sorteoEquipos, mezcla, ruletaLideres, rondaExtra, cancelar };
})();
