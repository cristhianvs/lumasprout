'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const T = require('../telemetry-client.js');

function makeAdapter() {
  const state = {
    events: [],
    cursor: -1,
    token: null,
    context: {
      runId: 'run-1',
      version: 'v1',
      schemaVersion: '1.4',
      policyVersion: 'p1',
      simulation: false,
    },
    persistCalls: 0,
  };
  return {
    _state: state,
    getContext: () => state.context,
    getEvents: () => state.events,
    getCursor: () => state.cursor,
    setCursor: (value) => {
      state.cursor = value;
    },
    getToken: () => state.token,
    setToken: (value) => {
      state.token = value || null;
    },
    persist: () => {
      state.persistCalls++;
    },
  };
}

// Deja que las cadenas de promesas del cliente (fetch simulado + microtasks
// encadenados) terminen de resolverse antes de comprobar el resultado.
async function flushAsync() {
  await new Promise((resolve) => setTimeout(resolve, 0));
  await new Promise((resolve) => setTimeout(resolve, 0));
}

test('no se envia ni se abre sesion si la telemetria esta desactivada', () => {
  const calls = [];
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' });
  adapter._state.token = 'algun-token';
  let timersCreated = 0;
  const client = T.create({
    config: { enabled: false },
    adapter,
    fetch: async (...args) => {
      calls.push(args);
      return { ok: true, status: 200, json: async () => ({}) };
    },
    sendBeacon: () => {
      calls.push('beacon');
      return true;
    },
    setInterval: () => {
      timersCreated++;
      return 1;
    },
    clearInterval: () => {},
  });
  const status = client.getStatus();
  assert.equal(status.state, 'desactivado');
  assert.equal(status.pending, 0);
  assert.equal(status.lastConfirmedAt, null);
  client.flushOnHide();
  client.stop();
  assert.equal(calls.length, 0);
  assert.equal(timersCreated, 0);
});

test('en modo simulacion el transporte queda inerte: nunca abre sesion ni envia nada', () => {
  const calls = [];
  const adapter = makeAdapter();
  adapter._state.context.simulation = true;
  adapter._state.context.runId = 'simulation-visual';
  // Los eventos de simulacion tienen ids deterministas: correr el mismo
  // escenario dos veces produce exactamente los mismos ids, lo que
  // envenenaria la deduplicacion (runId, id) del servidor.
  adapter._state.events.push({ id: 'simulation-visual:0' }, { id: 'simulation-visual:1' });
  let timersCreated = 0;
  const client = T.create({
    config: { enabled: true, baseUrl: 'https://api.test' },
    adapter,
    fetch: async (...args) => {
      calls.push(args);
      return { ok: true, status: 200, json: async () => ({ token: 'no-deberia-pedirse' }) };
    },
    sendBeacon: () => {
      calls.push('beacon');
      return true;
    },
    setInterval: () => {
      timersCreated++;
      return 1;
    },
    clearInterval: () => {},
  });
  assert.equal(client.getStatus().state, 'desactivado');
  client.flushOnHide();
  assert.equal(calls.length, 0);
  assert.equal(timersCreated, 0);
  assert.equal(adapter.getToken(), null);
});

test('el cursor solo avanza hasta lo que el servidor confirma', async () => {
  let tick;
  const requests = [];
  const fetchMock = async (url, opts) => {
    requests.push({ url, opts });
    if (url.endsWith('/api/luma/sesion')) {
      return { ok: true, status: 200, json: async () => ({ token: 'tok-1', ultimoIndice: -1 }) };
    }
    return {
      ok: true,
      status: 200,
      json: async () => ({ guardados: 2, duplicados: 0, ultimoIndice: 1 }),
    };
  };
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' }, { id: 'e1' });
  T.create({
    config: { enabled: true, baseUrl: 'https://api.test' },
    adapter,
    fetch: fetchMock,
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {},
  });
  tick();
  await flushAsync();
  assert.equal(adapter.getCursor(), 1);
  assert.equal(adapter.getToken(), 'tok-1');
  assert(adapter._state.persistCalls >= 2);
  const eventosCall = requests.find((r) => r.url.endsWith('/api/luma/eventos'));
  assert.equal(eventosCall.opts.headers['X-Luma-Token'], 'tok-1');
  assert.deepEqual(JSON.parse(eventosCall.opts.body).eventos, [{ id: 'e0' }, { id: 'e1' }]);
});

test('una vez confirmado un lote, un reintento no lo vuelve a enviar', async () => {
  let tick;
  let eventosCalls = 0;
  const fetchMock = async (url) => {
    if (url.endsWith('/api/luma/sesion')) {
      return { ok: true, status: 200, json: async () => ({ token: 'tok-1', ultimoIndice: -1 }) };
    }
    eventosCalls++;
    return {
      ok: true,
      status: 200,
      json: async () => ({ guardados: 2, duplicados: 0, ultimoIndice: 1 }),
    };
  };
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' }, { id: 'e1' });
  T.create({
    config: { enabled: true, baseUrl: '' },
    adapter,
    fetch: fetchMock,
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {},
  });
  tick();
  await flushAsync();
  assert.equal(eventosCalls, 1);
  tick();
  await flushAsync();
  assert.equal(eventosCalls, 1, 'sin eventos nuevos pendientes, no debe reenviar nada');
});

test('un reintento tras fallo de red reenvia el mismo lote, sin duplicar ni perder eventos', async () => {
  let tick;
  let attempt = 0;
  const sentBatches = [];
  const fetchMock = async (url, opts) => {
    if (url.endsWith('/api/luma/sesion')) {
      return { ok: true, status: 200, json: async () => ({ token: 'tok-1', ultimoIndice: -1 }) };
    }
    attempt++;
    if (attempt === 1) throw new Error('network down');
    const body = JSON.parse(opts.body);
    sentBatches.push(body.eventos.map((e) => e.id));
    return {
      ok: true,
      status: 200,
      json: async () => ({
        guardados: body.eventos.length,
        duplicados: 0,
        ultimoIndice: body.eventos.length - 1,
      }),
    };
  };
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' }, { id: 'e1' });
  const client = T.create({
    config: { enabled: true, baseUrl: '', minBackoffMs: 1, maxBackoffMs: 2 },
    adapter,
    fetch: fetchMock,
    now: () => Date.now(),
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {},
  });
  tick();
  await flushAsync();
  assert.equal(adapter.getCursor(), -1, 'el fallo de red no debe confirmar nada');
  assert.equal(client.getStatus().state, 'sin conexion');
  await new Promise((resolve) => setTimeout(resolve, 5));
  tick();
  await flushAsync();
  assert.equal(adapter.getCursor(), 1);
  assert.deepEqual(sentBatches, [['e0', 'e1']]);
});

test('si el servidor confirma mas eventos de los que existen localmente, no se adopta el cursor', async () => {
  // Simula dos pestanas sobre la misma partida: el servidor ya tiene mas
  // eventos confirmados (de la otra pestana) de los que esta pestana ve en
  // su propio arreglo state.events.
  let tick;
  let eventosCalls = 0;
  const fetchMock = async (url) => {
    if (url.endsWith('/api/luma/sesion')) {
      return { ok: true, status: 200, json: async () => ({ token: 'tok-1', ultimoIndice: 5 }) };
    }
    eventosCalls++;
    return {
      ok: true,
      status: 200,
      json: async () => ({ guardados: 0, duplicados: 0, ultimoIndice: 5 }),
    };
  };
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' }, { id: 'e1' });
  const client = T.create({
    config: { enabled: true, baseUrl: '', minBackoffMs: 1 },
    adapter,
    fetch: fetchMock,
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {},
  });
  tick();
  await flushAsync();
  assert.equal(adapter.getCursor(), -1, 'no se adopta un cursor mayor a los eventos locales');
  assert.equal(eventosCalls, 0, 'no se intenta enviar un lote mientras hay divergencia');
  const status = client.getStatus();
  assert.equal(status.state, 'error');
  assert.equal(status.reason, T.REASONS.POSIBLE_MULTIPLES_PESTANAS);
});

test('un cursor guardado que ya supera los eventos locales no envia nada y se reporta error', async () => {
  let tick;
  let fetchCalls = 0;
  const adapter = makeAdapter();
  adapter._state.token = 'tok-previo';
  adapter._state.cursor = 5;
  adapter._state.events.push({ id: 'e0' }, { id: 'e1' });
  const client = T.create({
    config: { enabled: true, baseUrl: '', minBackoffMs: 1 },
    adapter,
    fetch: async () => {
      fetchCalls++;
      throw new Error('no deberia llamarse mientras hay divergencia');
    },
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {},
  });
  tick();
  await flushAsync();
  assert.equal(fetchCalls, 0);
  assert.equal(adapter.getCursor(), 5, 'no se toca ni se resetea el cursor existente');
  assert.deepEqual(adapter.getEvents(), [{ id: 'e0' }, { id: 'e1' }], 'no se borra ningun evento');
  const status = client.getStatus();
  assert.equal(status.state, 'error');
  assert.equal(status.reason, T.REASONS.POSIBLE_MULTIPLES_PESTANAS);
});

test('la divergencia se recupera sola cuando los eventos locales vuelven a alcanzar al servidor', async () => {
  let tick;
  const fetchMock = async (url, opts) => {
    if (url.endsWith('/api/luma/sesion')) {
      return { ok: true, status: 200, json: async () => ({ token: 'tok-1', ultimoIndice: 5 }) };
    }
    const body = JSON.parse(opts.body);
    return {
      ok: true,
      status: 200,
      json: async () => ({
        guardados: body.eventos.length,
        duplicados: 0,
        ultimoIndice: body.eventos.length - 1,
      }),
    };
  };
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' }, { id: 'e1' });
  const client = T.create({
    config: { enabled: true, baseUrl: '', minBackoffMs: 1, maxBackoffMs: 2 },
    adapter,
    fetch: fetchMock,
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {},
  });
  tick();
  await flushAsync();
  assert.equal(client.getStatus().state, 'error');
  assert.equal(adapter.getCursor(), -1);
  // Los eventos locales crecen (el nino sigue jugando en esta pestana) hasta
  // alcanzar lo que el servidor ya tenia.
  for (let i = adapter.getEvents().length; i <= 5; i++) adapter._state.events.push({ id: `e${i}` });
  await new Promise((resolve) => setTimeout(resolve, 5));
  tick();
  await flushAsync();
  assert.equal(client.getStatus().state, 'en linea');
  assert.equal(adapter.getCursor(), 5);
});

test('un fallo de red no lanza excepciones ni bloquea el bucle del cliente', async () => {
  let tick;
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' });
  const client = T.create({
    config: { enabled: true, baseUrl: '', minBackoffMs: 1 },
    adapter,
    fetch: async () => {
      throw new Error('caido');
    },
    setInterval: (fn) => {
      tick = fn;
      return 1;
    },
    clearInterval: () => {},
  });
  await assert.doesNotReject(async () => {
    tick();
    await flushAsync();
  });
  assert.equal(client.getStatus().state, 'sin conexion');
  assert.equal(adapter.getCursor(), -1);
});

test('el envio al ocultar la pestana usa sendBeacon con el token en el cuerpo', async () => {
  const beaconCalls = [];
  const adapter = makeAdapter();
  adapter._state.token = 'tok-oculto';
  adapter._state.events.push({ id: 'e0' }, { id: 'e1' });
  const client = T.create({
    config: { enabled: true, baseUrl: 'https://api.test' },
    adapter,
    fetch: async () => ({ ok: true, status: 200, json: async () => ({}) }),
    sendBeacon: (url, blob) => {
      beaconCalls.push({ url, blob });
      return true;
    },
    setInterval: () => 1,
    clearInterval: () => {},
  });
  client.flushOnHide();
  assert.equal(beaconCalls.length, 1);
  assert.equal(beaconCalls[0].url, 'https://api.test/api/luma/eventos');
  const raw =
    typeof beaconCalls[0].blob === 'string'
      ? beaconCalls[0].blob
      : await beaconCalls[0].blob.text();
  const body = JSON.parse(raw);
  assert.equal(body.token, 'tok-oculto');
  assert.deepEqual(body.eventos, [{ id: 'e0' }, { id: 'e1' }]);
  // sendBeacon no confirma nada: el cursor se queda igual hasta que el
  // servidor lo confirme en un envio normal.
  assert.equal(adapter.getCursor(), -1);
});

test('sin token todavia no hay sesion sincrona posible: ocultar la pestana no intenta nada', () => {
  const calls = [];
  const adapter = makeAdapter();
  adapter._state.events.push({ id: 'e0' });
  const client = T.create({
    config: { enabled: true, baseUrl: '' },
    adapter,
    fetch: async (...args) => {
      calls.push(args);
      return { ok: true, status: 200, json: async () => ({}) };
    },
    sendBeacon: () => {
      calls.push('beacon');
      return true;
    },
    setInterval: () => 1,
    clearInterval: () => {},
  });
  client.flushOnHide();
  assert.equal(calls.length, 0);
});

test('buildBatch respeta el maximo de eventos y el maximo de bytes por lote', () => {
  const events = Array.from({ length: 500 }, (_, i) => ({ id: `e${i}`, data: 'x'.repeat(10) }));
  const byCount = T.buildBatch(events, -1, 10, 1000000);
  assert.equal(byCount.length, 10);
  assert.equal(byCount[0].id, 'e0');
  const byBytes = T.buildBatch(events, -1, 500, 50);
  assert(byBytes.length >= 1);
  assert(JSON.stringify(byBytes).length <= 60);
  const fromCursor = T.buildBatch(events, 4, 10, 1000000);
  assert.equal(fromCursor[0].id, 'e5');
});

test('el cliente nunca toca localStorage directamente: solo lee y escribe a traves del adapter', () => {
  const source = fs.readFileSync(path.join(__dirname, '..', 'telemetry-client.js'), 'utf8');
  assert.equal(/localStorage/.test(source), false);
  const configSource = fs.readFileSync(path.join(__dirname, '..', 'config.js'), 'utf8');
  assert.equal(/localStorage/.test(configSource), false);
});
