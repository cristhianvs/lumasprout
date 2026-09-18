(function (root) {
  'use strict';
  // Cliente de envio de telemetria remota para Isla Luma.
  //
  // Diseno: la cola de eventos es el propio state.events del juego mas un
  // cursor (state.enviadoHasta). Este modulo no guarda una segunda cola en
  // ningun otro sitio: solo lee los eventos a traves del adapter y hace
  // avanzar el cursor cuando el servidor confirma la recepcion.
  //
  // El juego nunca debe romperse por la red: toda llamada de red va envuelta
  // en try/catch y ningun fallo aqui detiene el bucle del juego.
  const STATES = Object.freeze({
    DISABLED: 'desactivado',
    CONNECTING: 'conectando',
    ONLINE: 'en linea',
    OFFLINE: 'sin conexion',
    ERROR: 'error',
  });
  const HTTP_UNAUTHORIZED = 401;
  const HTTP_FORBIDDEN = 403;
  const BACKOFF_JITTER_RATIO = 0.2;

  function normalizeCursor(value) {
    return Number.isInteger(value) ? value : -1;
  }

  function estimateBytes(value) {
    try {
      return JSON.stringify(value).length;
    } catch {
      return Infinity;
    }
  }

  // Construye un unico lote a partir del cursor, respetando los limites de
  // cantidad y de tamano. Si quedan mas eventos pendientes de los que caben,
  // el resto se envia en el siguiente tick: asi es como se "parte" un lote
  // que excede los limites, sin bloquear el bucle de envio.
  function buildBatch(events, cursor, maxCount, maxBytes) {
    const batch = [];
    let bytes = 2; // '[' + ']'
    for (let i = cursor + 1; i < events.length && batch.length < maxCount; i++) {
      const event = events[i];
      const size = estimateBytes(event) + 1; // + separador
      if (batch.length > 0 && bytes + size > maxBytes) break;
      batch.push(event);
      bytes += size;
    }
    return batch;
  }

  function createNullClient() {
    return {
      flushOnHide() {},
      getStatus() {
        return { state: STATES.DISABLED, pending: 0, lastConfirmedAt: null };
      },
      stop() {},
    };
  }

  function create(options = {}) {
    const config = options.config || {};
    if (!config.enabled) return createNullClient();

    const adapter = options.adapter;
    if (!adapter || typeof adapter.getEvents !== 'function') {
      throw new Error('LumaTelemetryClient.create requiere un adapter valido');
    }
    const fetchImpl = options.fetch || (typeof fetch !== 'undefined' ? fetch : null);
    const sendBeaconImpl =
      options.sendBeacon ||
      (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function'
        ? navigator.sendBeacon.bind(navigator)
        : null);
    const now = options.now || (() => Date.now());
    const setIntervalImpl = options.setInterval || setInterval;
    const clearIntervalImpl = options.clearInterval || clearInterval;
    const random = options.random || Math.random;
    const onStatusChange =
      typeof options.onStatusChange === 'function' ? options.onStatusChange : () => {};

    const baseUrl = String(config.baseUrl || '').replace(/\/+$/, '');
    const sesionUrl = `${baseUrl}/api/luma/sesion`;
    const eventosUrl = `${baseUrl}/api/luma/eventos`;
    const batchIntervalMs = config.batchIntervalMs || 3000;
    const maxBatchSize = config.maxBatchSize || 200;
    const maxBatchBytes = config.maxBatchBytes || 1000000;
    const minBackoffMs = config.minBackoffMs || 1000;
    const maxBackoffMs = config.maxBackoffMs || 60000;

    let status = STATES.CONNECTING;
    let lastConfirmedAt = null;
    let sending = false;
    let backoffMs = minBackoffMs;
    let nextAttemptAt = 0;

    function setStatus(next) {
      if (status === next) return;
      status = next;
      onStatusChange(status);
    }

    function pendingCount() {
      const events = adapter.getEvents();
      const cursor = normalizeCursor(adapter.getCursor());
      return Math.max(0, events.length - 1 - cursor);
    }

    function scheduleBackoff() {
      backoffMs = Math.min(maxBackoffMs, backoffMs * 2);
      const jitter = backoffMs * BACKOFF_JITTER_RATIO * random();
      nextAttemptAt = now() + backoffMs + jitter;
    }

    function resetBackoff() {
      backoffMs = minBackoffMs;
      nextAttemptAt = 0;
    }

    // Abre sesion una vez por partida. ultimoIndice permite reanudar el
    // cursor si el navegador perdio el suyo (por ejemplo, otro dispositivo
    // ya envio parte de esta misma partida).
    async function ensureSession() {
      if (adapter.getToken()) return true;
      if (!fetchImpl) {
        setStatus(STATES.ERROR);
        return false;
      }
      setStatus(STATES.CONNECTING);
      const ctx = adapter.getContext();
      const response = await fetchImpl(sesionUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          runId: ctx.runId,
          version: ctx.version,
          schemaVersion: ctx.schemaVersion,
          policyVersion: ctx.policyVersion,
          simulation: ctx.simulation,
        }),
      });
      if (!response || !response.ok) {
        setStatus(STATES.OFFLINE);
        scheduleBackoff();
        return false;
      }
      const payload = await response.json();
      if (!payload || typeof payload.token !== 'string' || !payload.token) {
        setStatus(STATES.ERROR);
        scheduleBackoff();
        return false;
      }
      adapter.setToken(payload.token);
      const serverCursor = normalizeCursor(payload.ultimoIndice);
      const localCursor = normalizeCursor(adapter.getCursor());
      if (serverCursor > localCursor) adapter.setCursor(serverCursor);
      adapter.persist();
      return true;
    }

    async function sendPendingBatch() {
      const events = adapter.getEvents();
      const cursor = normalizeCursor(adapter.getCursor());
      const batch = buildBatch(events, cursor, maxBatchSize, maxBatchBytes);
      if (batch.length === 0) return;
      const ctx = adapter.getContext();
      const token = adapter.getToken();
      const response = await fetchImpl(eventosUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Luma-Token': token },
        body: JSON.stringify({ runId: ctx.runId, eventos: batch }),
      });
      if (!response) {
        setStatus(STATES.OFFLINE);
        scheduleBackoff();
        return;
      }
      if (response.status === HTTP_UNAUTHORIZED || response.status === HTTP_FORBIDDEN) {
        // El token dejo de ser valido: se descarta para reabrir sesion en el
        // siguiente tick. El cursor no se toca, nada se da por confirmado.
        adapter.setToken(null);
        adapter.persist();
        setStatus(STATES.ERROR);
        scheduleBackoff();
        return;
      }
      if (!response.ok) {
        setStatus(STATES.OFFLINE);
        scheduleBackoff();
        return;
      }
      const payload = await response.json();
      // El cursor SOLO avanza hasta lo que el servidor confirma, nunca hasta
      // lo que este cliente cree haber enviado.
      const confirmedCursor = normalizeCursor(payload && payload.ultimoIndice);
      const localCursor = normalizeCursor(adapter.getCursor());
      if (confirmedCursor > localCursor) adapter.setCursor(confirmedCursor);
      adapter.persist();
      setStatus(STATES.ONLINE);
      lastConfirmedAt = now();
      resetBackoff();
    }

    async function tick() {
      if (sending) return;
      if (now() < nextAttemptAt) return;
      if (pendingCount() === 0) {
        if (adapter.getToken() && status !== STATES.ONLINE) setStatus(STATES.ONLINE);
        return;
      }
      sending = true;
      try {
        const ready = await ensureSession();
        if (ready) await sendPendingBatch();
      } catch {
        setStatus(STATES.OFFLINE);
        scheduleBackoff();
      } finally {
        sending = false;
      }
    }

    const timer = setIntervalImpl(() => {
      tick().catch(() => {});
    }, batchIntervalMs);

    // Envio best-effort al ocultar la pestana o al descargar la pagina.
    // Diferencia importante frente al envio periodico: sendBeacon no admite
    // cabeceras personalizadas, asi que aqui el token viaja en el cuerpo en
    // lugar de en X-Luma-Token. Ademas, si todavia no hay sesion abierta
    // (no hay token), no se intenta abrir una: requiere leer una respuesta
    // JSON y la pestana puede desaparecer antes de que llegue, asi que ese
    // lote se deja para el siguiente tick en primer plano.
    function flushOnHide() {
      const token = adapter.getToken();
      if (!token) return;
      const events = adapter.getEvents();
      const cursor = normalizeCursor(adapter.getCursor());
      const batch = buildBatch(events, cursor, maxBatchSize, maxBatchBytes);
      if (batch.length === 0) return;
      const ctx = adapter.getContext();
      const body = JSON.stringify({ runId: ctx.runId, eventos: batch, token });
      let sent = false;
      if (sendBeaconImpl) {
        try {
          const blob =
            typeof Blob !== 'undefined' ? new Blob([body], { type: 'application/json' }) : body;
          sent = !!sendBeaconImpl(eventosUrl, blob);
        } catch {
          sent = false;
        }
      }
      if (!sent && fetchImpl) {
        try {
          fetchImpl(eventosUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-Luma-Token': token },
            body,
            keepalive: true,
          }).catch(() => {});
        } catch {
          // El navegador puede rechazar peticiones durante la descarga de la
          // pagina; se ignora y el lote se reintenta cuando vuelva a primer
          // plano (no se toca el cursor, nada se da por confirmado).
        }
      }
    }

    function stop() {
      clearIntervalImpl(timer);
    }

    return {
      flushOnHide,
      getStatus() {
        return { state: status, pending: pendingCount(), lastConfirmedAt };
      },
      stop,
    };
  }

  const api = { create, STATES, buildBatch };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LumaTelemetryClient = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
