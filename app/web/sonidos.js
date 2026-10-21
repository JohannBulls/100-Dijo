// Efectos de sonido y música de entrada, sintetizados en el navegador con Web Audio.
// Todo es original de este proyecto: no se descarga ni se reproduce audio de terceros.
//
// Cadena de audio:  voces → bus de efectos / bus de música → volumen maestro → compresor → altavoces
// - Un efecto nuevo apaga suavemente el anterior (no se amontonan sonidos).
// - Mientras suena un efecto, la música baja de volumen.
const Sonidos = (() => {
  let ctx = null, maestro = null, busMusica = null, busEfectos = null, ruido = null;
  let vocesEfectos = [];
  let vozMusica = null;
  const conf = { sonido: true, musica: true, efectos: true, volumen: 70 };
  const registro = []; // historial de lo que se pidió reproducir (lo usan las pruebas)

  function contexto() {
    if (!ctx) {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
      const compresor = ctx.createDynamicsCompressor();
      compresor.threshold.value = -14;
      compresor.ratio.value = 6;
      compresor.connect(ctx.destination);
      maestro = ctx.createGain();
      maestro.connect(compresor);
      busMusica = ctx.createGain();
      busMusica.connect(maestro);
      busEfectos = ctx.createGain();
      busEfectos.connect(maestro);
      ruido = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
      const d = ruido.getChannelData(0);
      for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
      aplicarVolumen();
    }
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }

  function aplicarVolumen() {
    if (!ctx) return;
    const v = conf.sonido ? Math.pow(conf.volumen / 100, 2) : 0; // curva perceptual
    maestro.gain.setTargetAtTime(v, ctx.currentTime, 0.05);
  }

  function nuevaVoz(bus) {
    const g = ctx.createGain();
    g.connect(bus);
    return g;
  }

  function apagar(voz, t = 0.06) {
    if (!voz) return;
    const ahora = ctx.currentTime;
    voz.gain.cancelScheduledValues(ahora);
    voz.gain.setTargetAtTime(0, ahora, t);
    setTimeout(() => { try { voz.disconnect(); } catch (e) { /* ya desconectada */ } }, 1500);
  }

  // ------------------------------------------------------------------ instrumentos básicos
  function env(g, t, ataque, vol, dur, final = 0.0001) {
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + ataque);
    g.gain.exponentialRampToValueAtTime(final, t + dur);
  }

  function tono(dest, f, t, dur, tipo = "sine", vol = 0.2, ataque = 0.01) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.type = tipo;
    o.frequency.setValueAtTime(f, t);
    env(g, t, ataque, vol, dur);
    o.connect(g).connect(dest);
    o.start(t);
    o.stop(t + dur + 0.05);
    return o;
  }

  function campana(dest, f, t, vol = 0.3, dur = 1.2) {
    [[1, 1], [2, 0.5], [3.01, 0.3], [4.2, 0.18], [5.4, 0.1]].forEach(([m, a]) =>
      tono(dest, f * m, t, dur / m ** 0.4, "sine", vol * a, 0.003));
  }

  function metal(dest, f, t, dur, vol = 0.18) { // «metales» de fanfarria
    const filtro = ctx.createBiquadFilter(), g = ctx.createGain();
    filtro.type = "lowpass";
    filtro.Q.value = 2;
    filtro.frequency.setValueAtTime(600, t);
    filtro.frequency.exponentialRampToValueAtTime(3500, t + 0.06);
    filtro.frequency.exponentialRampToValueAtTime(1400, t + dur);
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.03);
    g.gain.setValueAtTime(vol * 0.8, t + Math.max(0.05, dur - 0.08));
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur + 0.06);
    filtro.connect(g).connect(dest);
    [-6, 6].forEach((desafino) => {
      const o = ctx.createOscillator();
      o.type = "sawtooth";
      o.frequency.value = f;
      o.detune.value = desafino;
      o.connect(filtro);
      o.start(t);
      o.stop(t + dur + 0.1);
    });
  }

  function acorde(dest, fs, t, dur, vol = 0.12) { fs.forEach((f) => metal(dest, f, t, dur, vol)); }

  function soplo(dest, t, dur, vol, tipoFiltro, f1, f2, q = 1) { // ruido filtrado
    const s = ctx.createBufferSource(), filtro = ctx.createBiquadFilter(), g = ctx.createGain();
    s.buffer = ruido;
    filtro.type = tipoFiltro;
    filtro.Q.value = q;
    filtro.frequency.setValueAtTime(f1, t);
    filtro.frequency.exponentialRampToValueAtTime(f2, t + dur);
    env(g, t, Math.min(0.02, dur / 3), vol, dur);
    s.connect(filtro).connect(g).connect(dest);
    s.start(t, Math.random() * 1.5);
    s.stop(t + dur + 0.05);
  }

  function bombo(dest, t, vol = 0.6) {
    const o = ctx.createOscillator(), g = ctx.createGain();
    o.frequency.setValueAtTime(150, t);
    o.frequency.exponentialRampToValueAtTime(42, t + 0.28);
    env(g, t, 0.003, vol, 0.35);
    o.connect(g).connect(dest);
    o.start(t);
    o.stop(t + 0.4);
  }
  const caja = (dest, t, vol = 0.25) => { soplo(dest, t, 0.16, vol, "highpass", 1500, 1200); tono(dest, 190, t, 0.08, "triangle", vol * 0.6); };
  const platillo = (dest, t, vol = 0.18, dur = 1.6) => soplo(dest, t, dur, vol, "highpass", 6000, 4000);
  const hihat = (dest, t, vol = 0.07) => soplo(dest, t, 0.04, vol, "highpass", 8000, 8000);
  const silbido = (dest, t, dur = 0.5, vol = 0.25) => soplo(dest, t, dur, vol, "bandpass", 300, 4000, 1.5); // cambio de turno

  function aplausos(dest, t, dur = 3, intensidad = 1) {
    const total = Math.round(dur * 70 * intensidad);
    for (let i = 0; i < total; i++) {
      const x = Math.random();                                // forma: sube rápido y se apaga
      const tt = t + dur * (x < 0.15 ? x : 0.15 + (x - 0.15) ** 1.5);
      const peso = tt - t < dur * 0.7 ? 1 : 1 - (tt - t - dur * 0.7) / (dur * 0.3);
      const f = 900 + Math.random() * 1800;
      soplo(dest, tt, 0.015 + Math.random() * 0.03, 0.22 * peso * (0.5 + Math.random() * 0.5), "bandpass", f, f, 1.2);
    }
    soplo(dest, t, dur, 0.05 * intensidad, "bandpass", 1200, 900, 0.6); // murmullo de fondo
  }

  function vitores(dest, t, n = 6) { // «¡uuuh!» del público
    for (let i = 0; i < n; i++) {
      const o = ctx.createOscillator(), g = ctx.createGain(), filtro = ctx.createBiquadFilter();
      const tt = t + Math.random() * 0.6, f = 250 + Math.random() * 250;
      o.type = "sawtooth";
      o.frequency.setValueAtTime(f, tt);
      o.frequency.exponentialRampToValueAtTime(f * 1.8, tt + 0.35);
      o.frequency.exponentialRampToValueAtTime(f * 1.5, tt + 0.9);
      filtro.type = "bandpass";
      filtro.frequency.value = 900;
      filtro.Q.value = 1.5;
      env(g, tt, 0.08, 0.035, 1.0);
      o.connect(filtro).connect(g).connect(dest);
      o.start(tt);
      o.stop(tt + 1.1);
    }
  }

  function zumbador(dest, t, dur = 0.8, vol = 0.28) { // timbre de «error»
    const filtro = ctx.createBiquadFilter(), g = ctx.createGain();
    filtro.type = "lowpass";
    filtro.frequency.value = 1300;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + 0.01);
    g.gain.setValueAtTime(vol, t + dur - 0.05);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    filtro.connect(g).connect(dest);
    [[98, "sawtooth"], [104, "sawtooth"], [49, "square"]].forEach(([f, tipo]) => {
      const o = ctx.createOscillator();
      o.type = tipo;
      o.frequency.value = f;
      o.connect(filtro);
      o.start(t);
      o.stop(t + dur + 0.02);
    });
  }

  function redoble(dest, t, dur = 2, vol = 0.22) { // tambor de suspenso con crescendo
    const golpes = Math.round(dur * 22);
    for (let i = 0; i < golpes; i++) {
      const tt = t + (i / golpes) * dur;
      soplo(dest, tt, 0.06, vol * (0.25 + 0.75 * (i / golpes)), "bandpass", 450, 300, 1.2);
    }
    tono(dest, 55, t, dur, "sine", 0.12, dur * 0.8);
  }

  function tremolo(dest, f, t, dur, vol = 0.08) { // cuerdas nerviosas
    const o = ctx.createOscillator(), lfo = ctx.createOscillator(), lfoG = ctx.createGain();
    const g = ctx.createGain(), filtro = ctx.createBiquadFilter();
    o.type = "sawtooth";
    o.frequency.value = f;
    filtro.type = "lowpass";
    filtro.frequency.value = 900;
    lfo.frequency.value = 9;
    lfoG.gain.value = vol * 0.5;
    g.gain.setValueAtTime(0.0001, t);
    g.gain.exponentialRampToValueAtTime(vol, t + dur * 0.8);
    g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    lfo.connect(lfoG).connect(g.gain);
    o.connect(filtro).connect(g).connect(dest);
    [o, lfo].forEach((x) => { x.start(t); x.stop(t + dur + 0.05); });
  }

  function tromboneTriste(dest, t) {
    const notas = [[392, 0.42], [370, 0.42], [349, 0.42], [330, 1.3]];
    let tt = t;
    notas.forEach(([f, d], i) => {
      const o = ctx.createOscillator(), g = ctx.createGain(), filtro = ctx.createBiquadFilter();
      o.type = "sawtooth";
      o.frequency.setValueAtTime(f / 2, tt);
      if (i === notas.length - 1) { // vibrato y caída final
        const lfo = ctx.createOscillator(), lg = ctx.createGain();
        lfo.frequency.value = 6;
        lg.gain.value = 6;
        lfo.connect(lg).connect(o.frequency);
        lfo.start(tt);
        lfo.stop(tt + d);
        o.frequency.exponentialRampToValueAtTime(f / 2 * 0.94, tt + d);
      }
      filtro.type = "lowpass";
      filtro.frequency.value = 900;
      env(g, tt, 0.04, 0.22, d);
      o.connect(filtro).connect(g).connect(dest);
      o.start(tt);
      o.stop(tt + d + 0.05);
      tt += d;
    });
  }

  // ------------------------------------------------------------------ efectos del juego
  const N = { C4: 261.6, D4: 293.7, E4: 329.6, F4: 349.2, G4: 392, A4: 440, B4: 493.9, C5: 523.3, D5: 587.3,
    E5: 659.3, F5: 698.5, G5: 784, A5: 880, B5: 987.8, C6: 1046.5, D6: 1174.7, E6: 1318.5, G6: 1568 };

  function fanfarriaCorta(d, t) {
    [[N.C5, 0], [N.E5, 0.11], [N.G5, 0.22]].forEach(([f, dt]) => metal(d, f, t + dt, 0.12, 0.14));
    acorde(d, [N.C5, N.E5, N.G5, N.C6], t + 0.36, 0.75, 0.09);
    bombo(d, t + 0.36, 0.5);
    platillo(d, t + 0.36, 0.14, 1.2);
  }

  const efectos = {
    correcta(d, t) { // «¡ding ding!» alegre y contundente
      bombo(d, t, 0.55);
      campana(d, N.E6, t, 0.32);
      campana(d, N.A5 * 2, t + 0.14, 0.36, 1.5);
      [N.E6, N.G6, N.E6 * 2].forEach((f, i) => tono(d, f, t + 0.3 + i * 0.06, 0.18, "sine", 0.05));
      return 1.6;
    },
    revelar(d, t) { campana(d, N.A5, t, 0.18, 0.8); return 0.8; },
    no_esta(d, t) { zumbador(d, t, 0.5); return 0.6; },
    strike(d, t) { zumbador(d, t, 0.85); return 0.9; },
    strike2(d, t) { // error + tensión: latidos y cuerdas nerviosas
      zumbador(d, t, 0.85);
      bombo(d, t + 1.0, 0.45); bombo(d, t + 1.22, 0.35);
      bombo(d, t + 1.75, 0.45); bombo(d, t + 1.97, 0.35);
      tremolo(d, 110, t + 0.95, 1.6);
      tremolo(d, 116.5, t + 0.95, 1.6);
      return 2.6;
    },
    robo(d, t) { // tercer strike → cambio de turno → suspenso
      zumbador(d, t, 0.9);
      silbido(d, t + 0.95, 0.55, 0.3);
      redoble(d, t + 1.4, 2.0);
      metal(d, N.D4, t + 3.4, 0.22, 0.16);
      metal(d, N.D4 * 0.944, t + 3.68, 0.22, 0.16);
      acorde(d, [N.D4 * 0.84, N.F4 * 0.84, N.A4 * 0.84], t + 3.96, 1.1, 0.1);
      return 5.1;
    },
    robo_exitoso(d, t) { // celebración distinta: escalera rápida + ovación
      [N.C5, N.D5, N.E5, N.F5, N.G5, N.A5, N.B5, N.C6].forEach((f, i) => metal(d, f, t + i * 0.055, 0.08, 0.1));
      acorde(d, [N.C5, N.E5, N.G5, N.C6, N.E6 / 2], t + 0.5, 1.2, 0.08);
      bombo(d, t + 0.5, 0.6);
      platillo(d, t + 0.5, 0.22, 2.2);
      aplausos(d, t + 0.55, 3.5, 1.4);
      vitores(d, t + 0.6, 9);
      return 4.2;
    },
    robo_fallido(d, t) { tromboneTriste(d, t); return 2.7; },
    puntos(d, t) { fanfarriaCorta(d, t); aplausos(d, t + 0.3, 2.8, 1); return 3.2; },
    tablero(d, t) {
      [N.C6, N.E6, N.G6, N.E6 * 2].forEach((f, i) => campana(d, f / 2, t + i * 0.09, 0.2, 0.9));
      fanfarriaCorta(d, t + 0.4);
      aplausos(d, t + 0.6, 2.4, 1.1);
      return 3.2;
    },
    nueva_ronda(d, t) {
      silbido(d, t, 0.45, 0.25);
      acorde(d, [N.G4, N.B4, N.D5], t + 0.42, 0.18, 0.1);
      acorde(d, [N.C5, N.E5, N.G5], t + 0.66, 0.6, 0.1);
      bombo(d, t + 0.66, 0.5);
      return 1.4;
    },
    cara_a_cara(d, t) { acorde(d, [N.E5, N.G5, N.C6], t, 0.5, 0.1); bombo(d, t, 0.5); aplausos(d, t + 0.1, 1.3, 0.7); return 1.5; },
    turno(d, t) { silbido(d, t, 0.45, 0.22); return 0.5; },
    fanfarria_final(d, t) {
      const mel = [[N.G4, 0, 0.14], [N.C5, 0.16, 0.14], [N.E5, 0.32, 0.14], [N.G5, 0.48, 0.4], [N.E5, 0.92, 0.14],
        [N.G5, 1.08, 0.8], [N.A5, 1.95, 0.14], [N.G5, 2.11, 0.14], [N.F5, 2.27, 0.14], [N.E5, 2.43, 0.14], [N.D5, 2.59, 0.14]];
      mel.forEach(([f, dt, du]) => metal(d, f, t + dt, du, 0.15));
      [0, 0.48, 1.08, 1.95].forEach((dt) => { bombo(d, t + dt, 0.5); caja(d, t + dt + 0.24, 0.18); });
      acorde(d, [N.C5, N.E5, N.G5, N.C6], t + 2.8, 1.8, 0.1);
      bombo(d, t + 2.8, 0.7);
      platillo(d, t + 2.8, 0.25, 2.5);
      aplausos(d, t + 2.9, 5, 1.5);
      vitores(d, t + 3.0, 12);
      return 8;
    },
    ruleta(d, t, o = {}) { // «tic-tic-tic» que se va frenando, al ritmo de la ruleta
      const dur = o.duracion || 4.5;
      let tt = 0, paso = 0.045, i = 0;
      while (tt < dur) {
        tono(d, i % 2 ? 1900 : 1600, t + tt, 0.03, "square", 0.07, 0.002);
        soplo(d, t + tt, 0.02, 0.08, "highpass", 3000, 3000);
        tt += paso;
        paso *= tt < dur * 0.45 ? 1.02 : 1.09;  // se frena hacia el final
        i++;
      }
      tremolo(d, 147, t, dur, 0.04);             // suspenso de fondo
      return dur;
    },
    lider(d, t) { // revelación del líder: «¡ta-dá!» con aplausos
      bombo(d, t, 0.6);
      acorde(d, [N.C5, N.E5, N.G5], t, 0.16, 0.1);
      acorde(d, [N.E5, N.G5, N.C6], t + 0.18, 0.9, 0.1);
      campana(d, N.C6, t + 0.18, 0.25, 1.2);
      platillo(d, t + 0.18, 0.16, 1.4);
      aplausos(d, t + 0.25, 1.8, 0.9);
      return 2.1;
    },
    sorteo_paso(d, t, o = {}) { // cada nombre que cae en un equipo (tono distinto por equipo)
      const f = o.equipo === 1 ? N.G5 : N.C5;
      tono(d, f, t, 0.12, "triangle", 0.18, 0.004);
      tono(d, f * 1.5, t + 0.05, 0.1, "sine", 0.08, 0.004);
      soplo(d, t, 0.08, 0.06, "bandpass", 2000, 600, 2);
      return 0.15;
    },
    sorteo_fin(d, t) { fanfarriaCorta(d, t); aplausos(d, t + 0.3, 2.2, 1); vitores(d, t + 0.4, 5); return 2.8; },
    mezcla(d, t, o = {}) { // barajar cartas
      const dur = o.duracion || 2.2;
      for (let x = 0; x < dur; x += 0.035 + Math.random() * 0.03) {
        soplo(d, t + x, 0.03, 0.12 * (0.6 + Math.random() * 0.4), "bandpass", 2500 + Math.random() * 2000, 1800, 1.5);
      }
      campana(d, N.E6, t + dur, 0.2, 0.8);
      return dur + 0.8;
    },
    ronda_extra(d, t) { // entrada especial: redoble + fanfarria brillante
      redoble(d, t, 1.4, 0.2);
      [N.G4, N.C5, N.E5, N.G5].forEach((f, i) => metal(d, f, t + 1.4 + i * 0.09, 0.1, 0.14));
      acorde(d, [N.C5, N.E5, N.G5, N.C6, N.E6 / 2], t + 1.8, 1.4, 0.09);
      bombo(d, t + 1.8, 0.7);
      platillo(d, t + 1.8, 0.25, 2.2);
      vitores(d, t + 1.9, 8);
      return 3.4;
    },
    nuevo_ciclo(d, t) { silbido(d, t, 0.6, 0.25); campana(d, N.G5, t + 0.4, 0.22); campana(d, N.C6, t + 0.6, 0.22); return 1.6; },
  };

  function musicaEntrada(d, t) { // jingle original de ~8 s a 132 pulsos por minuto
    const p = 60 / 132;
    const bajo = [N.C4 / 2, N.C4 / 2, N.F4 / 2, N.F4 / 2, N.G4 / 2, N.G4 / 2, N.C4 / 2, N.C4 / 2];
    const acordes = [[N.C5, N.E5, N.G5], [N.F4, N.A4, N.C5], [N.G4, N.B4, N.D5], [N.C5, N.E5, N.G5]];
    const melodia = [[N.E5, 0, 1], [N.G5, 1, 1], [N.C6, 2, 1.5], [N.B5, 3.5, 0.5],
      [N.A5, 4, 1], [N.F5, 5, 0.5], [N.A5, 5.5, 0.5], [N.C6, 6, 2],
      [N.B5, 8, 1], [N.G5, 9, 0.5], [N.D6, 9.5, 1], [N.B5, 10.5, 1.5],
      [N.C6, 12, 0.5], [N.E6, 12.5, 0.5], [N.G6, 13, 2.5]];
    for (let pulso = 0; pulso < 16; pulso++) {
      const tt = t + pulso * p;
      bombo(d, tt, pulso % 4 === 0 ? 0.55 : 0.4);
      if (pulso % 2 === 1) caja(d, tt, 0.16);
      hihat(d, tt + p / 2);
      hihat(d, tt, 0.04);
      tono(d, bajo[Math.floor(pulso / 2)], tt, p * 0.9, "square", 0.07);
      if (pulso % 4 === 1 || pulso % 4 === 3) acorde(d, acordes[Math.floor(pulso / 4)], tt + p / 2, p * 0.35, 0.05);
    }
    melodia.forEach(([f, inicio, dur]) => { metal(d, f, t + inicio * p, dur * p * 0.92, 0.09); tono(d, f * 2, t + inicio * p, dur * p * 0.8, "triangle", 0.03); });
    const fin = t + 16 * p;
    acorde(d, [N.C5, N.E5, N.G5, N.C6], fin, 1.4, 0.1);
    bombo(d, fin, 0.7);
    platillo(d, fin, 0.25, 2);
    return 16 * p + 2;
  }

  // ------------------------------------------------------------------ interfaz pública
  function puedeSonar(tipo) {
    if (!conf.sonido || !conf[tipo] || conf.volumen <= 0) return false;
    if (!ctx || ctx.state !== "running") return false; // el navegador aún no permite audio
    return true;
  }

  return {
    activar() {
      try { contexto(); return true; } catch (e) { return false; }
    },
    listo() { return !!ctx && ctx.state === "running"; },
    configurar(c) {
      Object.keys(conf).forEach((k) => { if (c[k] !== undefined) conf[k] = c[k]; });
      aplicarVolumen();
      if (ctx && (!conf.sonido || !conf.musica)) this.detenerMusica();
    },
    efecto(nombre, opciones = {}) {
      if (!efectos[nombre]) return false;
      if (!puedeSonar("efectos")) { registro.push("omitido:" + nombre); return false; }
      vocesEfectos.forEach((v) => apagar(v));        // un efecto a la vez
      const voz = nuevaVoz(busEfectos);
      vocesEfectos = [voz];
      const dur = efectos[nombre](voz, ctx.currentTime + 0.02, opciones);
      if (vozMusica) {                                 // la música cede el protagonismo
        const ahora = ctx.currentTime;
        busMusica.gain.cancelScheduledValues(ahora);
        busMusica.gain.setTargetAtTime(0.25, ahora, 0.05);
        busMusica.gain.setTargetAtTime(1, ahora + dur, 0.3);
      }
      registro.push(nombre);
      return true;
    },
    musica() {
      if (!puedeSonar("musica")) { registro.push("omitido:musica"); return false; }
      this.detenerMusica();
      vozMusica = nuevaVoz(busMusica);
      busMusica.gain.cancelScheduledValues(ctx.currentTime);
      busMusica.gain.setValueAtTime(1, ctx.currentTime);
      const voz = vozMusica;
      const dur = musicaEntrada(voz, ctx.currentTime + 0.05);
      setTimeout(() => { if (vozMusica === voz) vozMusica = null; }, dur * 1000);
      registro.push("musica");
      return true;
    },
    detenerMusica() {
      if (vozMusica) { apagar(vozMusica, 0.25); vozMusica = null; }
    },
    estado() {
      return { contexto: ctx ? ctx.state : "sin crear", ...conf,
        ganancia: maestro ? Math.round(maestro.gain.value * 1000) / 1000 : null, registro: registro.slice(-30) };
    },
    nombres: Object.keys(efectos),
  };
})();
