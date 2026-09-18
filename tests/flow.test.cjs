const { test } = require('node:test');
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const { randomUUID } = require('node:crypto');
const E = require('../engine.js');

// Contrato mínimo de DOM para probar el flujo sin requerir un navegador instalado.
// No sustituye revisión visual, accesibilidad real ni pruebas de síntesis de voz.
function app(saved, telemetry) {
  const nodes = new Map(),
    listeners = {},
    timers = [];
  let now = 0,
    storage = saved || null;
  function node(id) {
    const n = {
      id,
      dataset: {},
      listeners: {},
      hidden: false,
      value: '',
      textContent: '',
      disabled: false,
      setAttribute() {},
      addEventListener(t, f) {
        this.listeners[t] = f;
      },
      showModal() {
        this.open = true;
      },
      close() {
        this.open = false;
      },
      classList: {
        toggle() {},
        contains() {
          return false;
        },
      },
    };
    Object.defineProperty(n, 'innerHTML', {
      set(html) {
        this.html = html;
        for (const m of html.matchAll(/id="([^"]+)"/g)) nodes.set(m[1], node(m[1]));
      },
      get() {
        return this.html || '';
      },
    });
    return n;
  }
  for (const id of ['app', 'modal', 'live', 'pause', 'sound', 'family']) nodes.set(id, node(id));
  const document = {
    hidden: false,
    querySelector: (s) => nodes.get(s.slice(1)) || null,
    querySelectorAll: () => [],
    addEventListener(t, f) {
      listeners[t] = f;
    },
  };
  const sandbox = {
    console,
    Luma: E,
    LumaRuntime: require('../runtime.js'),
    queueMicrotask() {},
    crypto: { randomUUID },
    document,
    performance: { now: () => now },
    localStorage: {
      getItem: () => storage,
      setItem: (k, v) => {
        storage = v;
      },
    },
    setInterval: (f, ms) => timers.push({ f, ms }),
    setTimeout() {},
    innerWidth: 1200,
    innerHeight: 800,
    matchMedia: () => ({ matches: false }),
    addEventListener() {},
    Date,
    Blob,
    URL,
  };
  sandbox.window = sandbox;
  sandbox.URLSearchParams = URLSearchParams;
  sandbox.location = telemetry?.location || { search: '', origin: 'https://isla-luma.test' };
  // Inyectado solo cuando una prueba pasa `telemetry`: por defecto
  // window.LumaTelemetryClient no existe, igual que en las demas pruebas de
  // este archivo, y app.js cae a su cliente inerte de reemplazo.
  if (telemetry) {
    sandbox.LumaTelemetryClient = telemetry.client;
    sandbox.LumaTelemetryConfig = { config: telemetry.config || { enabled: false } };
  }
  const context = vm.createContext(sandbox);
  vm.runInContext(fs.readFileSync(require.resolve('../app.js'), 'utf8'), context);
  const read = () => {
    vm.runInContext('store.flush()', context);
    return JSON.parse(storage);
  };
  function click(action, data = {}) {
    const target = { dataset: { action, ...data }, disabled: false };
    target.closest = () => target;
    listeners.pointerdown({ type: 'pointerdown', pointerType: 'mouse', target });
    nodes.get('app').listeners.click({ target });
  }
  function advance(ms, interact = false) {
    for (let i = 0; i < ms; i += 250) {
      now += 250;
      if (interact && i % 20000 === 0)
        listeners.pointerdown({
          type: 'pointerdown',
          pointerType: 'mouse',
          target: { closest: () => null },
        });
      for (const t of timers) if (now % t.ms === 0) t.f();
    }
  }
  return {
    read,
    click,
    advance,
    nodes,
    context,
    document,
    visibility(h) {
      document.hidden = h;
      listeners.visibilitychange();
    },
    submit(value) {
      nodes.get('answer').value = value;
      nodes.get('answer-form').listeners.submit({ preventDefault() {} });
    },
    save: () => {
      read();
      return storage;
    },
  };
}
test('aventura de 300 segundos activos y ninguna evidencia matemática', () => {
  const a = app();
  a.click('start');
  a.advance(299000, true);
  assert.equal(a.read().phase, 'play');
  a.advance(1000, true);
  assert.equal(a.read().phase, 'bridge');
  assert.equal(a.read().playMs, 300000);
  assert.deepEqual(a.read().knowledge, E.newKnowledge());
  const events = a.read().events;
  assert.equal(events.filter((e) => e.type === 'scene_entered').length, 4);
  assert.equal(events.filter((e) => e.type === 'playtest_completed').length, 1);
});
test('ocultar pestaña no consume tiempo ni registra un fallo', () => {
  const a = app();
  a.click('start');
  a.advance(10000, true);
  a.visibility(true);
  const before = a.read().playMs;
  a.advance(120000);
  assert.equal(a.read().playMs, before);
  a.visibility(false);
  a.advance(1000, true);
  assert(a.read().playMs >= before);
  assert(!a.read().events.some((e) => e.type === 'attempt'));
});
test('inactividad abre pausa y reanudar no cuenta el descanso', () => {
  const a = app();
  a.click('start');
  a.advance(46000);
  assert.equal(a.nodes.get('modal').open, true);
  const before = a.read().playMs;
  a.advance(60000);
  assert.equal(a.read().playMs, before);
  a.nodes.get('resume').onclick();
  a.advance(1000, true);
  assert.equal(a.nodes.get('modal').open, false);
  assert(a.read().events.some((e) => e.type === 'pause_ended'));
});
test('tres errores no matemáticos generan apoyo y no alteran conocimiento', () => {
  const a = app();
  a.click('start');
  a.advance(60000, true);
  a.click('creature', { index: '0' });
  for (let i = 0; i < 3; i++) a.click('shelter', { index: '1' });
  assert(a.read().events.some((e) => e.type === 'adaptation' && e.data.rule === 'three_failures'));
  assert.deepEqual(a.read().knowledge, E.newKnowledge());
});
test('recarga conserva tiempo, respuestas asistidas y evita doble evidencia', () => {
  const a = app();
  a.click('start');
  a.advance(300000, true);
  a.click('math_start');
  a.click('hint');
  const b = app(a.save());
  b.submit('1/4');
  assert.equal(b.read().knowledge.meaning.n, 0);
  assert(b.read().current.solved);
  b.click('next');
  const task = b.read().current.task;
  b.submit(task.answer.join('/'));
  assert.equal(b.read().knowledge.meaning.n, 1);
  const c = app(b.save());
  c.submit(task.answer.join('/'));
  assert.equal(c.read().knowledge.meaning.n, 1);
});
test('cada intento independiente actualiza solo la habilidad ejercitada', () => {
  const a = app();
  a.click('start');
  a.advance(300000, true);
  a.click('math_start');
  for (let i = 0; i < 3; i++) {
    a.submit(a.read().current.task.answer.join('/'));
    a.click('next');
  }
  assert(E.mastered(a.read().knowledge.meaning));
  assert.equal(a.read().current.task.stage, 'transfer');
  a.submit(a.read().current.task.answer.join('/'));
  a.click('next');
  assert.notEqual(a.read().current.task.id, 'meaning');
  assert.equal(a.read().knowledge.add_diff.n, 0);
});
test('formato inválido no disminuye dominio ni registra un intento', () => {
  const a = app();
  a.click('start');
  a.advance(300000, true);
  a.click('math_start');
  a.submit('1/0');
  assert.equal(a.read().knowledge.meaning.n, 0);
  assert(a.read().events.some((e) => e.type === 'input_validation'));
  assert(!a.read().events.some((e) => e.type === 'attempt'));
});

test('la pista escrita por audio no disponible cuenta como asistencia', () => {
  const a = app();
  a.click('start');
  a.advance(300000, true);
  a.click('math_start');
  a.click('support', { mode: 'audio' });
  assert.equal(a.read().current.assisted, true);
  a.submit('1/4');
  assert.equal(a.read().knowledge.meaning.n, 0);
  const fallback = a.read().events.findLast((e) => e.type === 'support_selected');
  assert.equal(fallback.data.voluntary, false);
  assert.equal(fallback.data.reason, 'audio_unavailable');
});

test('latencia activa persiste al recargar y migra registros antiguos', () => {
  const a = app();
  a.click('start');
  a.advance(300000, true);
  a.click('math_start');
  a.advance(30000, true);
  for (const legacy of [false, true]) {
    const saved = JSON.parse(a.save());
    if (legacy) delete saved.current.taskOpened;
    const b = app(JSON.stringify(saved));
    b.advance(10000, true);
    b.submit('1/4');
    assert.equal(b.read().events.findLast((e) => e.type === 'attempt').data.latencyMs, 40000);
  }
});

// --- P2-6: el panel de Familias debe reflejar el estado real del envio ---

function activeTelemetryClient(status) {
  return {
    create: () => ({
      flushOnHide() {},
      getStatus: () => ({
        state: 'en linea',
        pending: 0,
        lastConfirmedAt: null,
        reason: null,
        ...status,
      }),
      stop() {},
    }),
  };
}

test('con la telemetria desactivada (por defecto), Familias sigue diciendo que no se envian datos', () => {
  const a = app();
  a.nodes.get('family').onclick();
  const html = a.nodes.get('modal').html;
  assert.match(html, /no envía datos a un servidor/);
  assert.doesNotMatch(html, /ACTIVADO/);
});

test('con la telemetria activa, Familias dice que el envio esta activado y a que destino', () => {
  const a = app(null, {
    client: activeTelemetryClient(),
    config: { enabled: true, baseUrl: 'https://telemetria.isla-luma.test' },
  });
  a.nodes.get('family').onclick();
  const html = a.nodes.get('modal').html;
  assert.match(html, /ACTIVADO/);
  assert.match(html, /telemetria\.isla-luma\.test/);
  assert.doesNotMatch(html, /no envía datos a un servidor/);
});

test('con destino de mismo origen (baseUrl vacio), Familias muestra el origen de la propia pagina', () => {
  const a = app(null, {
    client: activeTelemetryClient(),
    config: { enabled: true, baseUrl: '' },
    location: { search: '', origin: 'https://abejorro.ai' },
  });
  a.nodes.get('family').onclick();
  const html = a.nodes.get('modal').html;
  assert.match(html, /ACTIVADO/);
  assert.match(html, /abejorro\.ai/);
});

test('el texto de Familias se recalcula en cada apertura del panel, no queda fijo desde el arranque', () => {
  // Un mismo cliente cuyo estado cambia de desactivado a activo entre dos
  // aperturas: el texto debe cambiar tambien, porque se deriva en vivo de
  // telemetry.getStatus(), no de una constante fijada al cargar la pagina.
  let currentState = 'desactivado';
  const client = {
    create: () => ({
      flushOnHide() {},
      getStatus: () => ({ state: currentState, pending: 0, lastConfirmedAt: null, reason: null }),
      stop() {},
    }),
  };
  const a = app(null, {
    client,
    config: { enabled: true, baseUrl: 'https://telemetria.isla-luma.test' },
  });
  a.nodes.get('family').onclick();
  assert.match(a.nodes.get('modal').html, /no envía datos a un servidor/);
  currentState = 'en linea';
  a.nodes.get('family').onclick();
  assert.match(a.nodes.get('modal').html, /ACTIVADO/);
});
