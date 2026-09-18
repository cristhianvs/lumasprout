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
  // Motivos expuestos en getStatus().reason cuando state es 'error'. No son
  // texto para el jugador: son para quien lea el estado de conexion.
  const REASONS = Object.freeze({
    SIN_FETCH: 'no hay una implementacion de fetch disponible',
    SESION_INVALIDA: 'la respuesta del servidor al abrir sesion no trae un token valido',
    TOKEN_RECHAZADO: 'el servidor rechazo el token de esta partida',
    FALLO_RED: 'fallo de red al intentar enviar telemetria',
    // Limitacion conocida: runtime.js guarda el estado COMPLETO en cada save,
    // asi que dos pestanas sobre la misma partida se pisan entre si. Si el
    // servidor confirma (o el estado cargado ya trae) mas eventos de los que
    // existen localmente, es la senal de ese conflicto. No se intenta
    // resolver: no se reenvia ni se borra nada, solo se deja de enviar hasta
    // que el arreglo local vuelva a alcanzar (o supere) lo que el servidor
    // ya tiene, momento en el que el envio se reanuda solo.
    POSIBLE_MULTIPLES_PESTANAS:
      'el servidor (o el estado guardado) confirma mas eventos de los que existen localmente; posible partida abierta en otra pestana',
  });

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

  function createNullClient(reason = null) {
    return {
      flushOnHide() {},
      getStatus() {
        return { state: STATES.DISABLED, pending: 0, lastConfirmedAt: null, reason };
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
    // El laboratorio de simulacion genera eventos con ids DETERMINISTAS
    // (mismo runId + mismo indice en cada corrida del mismo escenario, ver
    // simulation.js). Enviarlos envenenaria la deduplicacion del servidor y
    // mezclaria datos sinteticos con los de una partida real. El transporte
    // se corta al arrancar: nunca abre sesion ni envia nada en modo
    // simulacion, sin importar la configuracion.
    if (adapter.getContext().simulation) {
      return createNullClient(
        'modo simulacion: los eventos son deterministas y no se envian nunca',
      );
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
    let statusReason = null;
    let lastConfirmedAt = null;
    let sending = false;
    let backoffMs = minBackoffMs;
    let nextAttemptAt = 0;

    function setStatus(next, reason = null) {
      status = next;
      statusReason = reason;
      onStatusChange(status, reason);
    }

    function pendingCount() {
      const events = adapter.getEvents();
      const cursor = normalizeCursor(adapter.getCursor());
      return Math.max(0, events.length - 1 - cursor);
    }

    // Unico punto que mueve state.enviadoHasta. Nunca lo retrocede (ignora
    // candidatos menores o iguales al cursor actual) y nunca lo adelanta mas
    // alla de los eventos que existen localmente: si el candidato (del
    // servidor, o el que ya venia guardado) supera lo que hay en memoria,
    // se reporta como divergencia en vez de adoptarlo. Adoptarlo a ciegas
    // marcaria como "ya enviados" eventos locales que en realidad todavia
    // no coinciden con lo que el servidor tiene bajo esos indices.
    function tryAdvanceCursor(candidate) {
      const events = adapter.getEvents();
      const localCursor = normalizeCursor(adapter.getCursor());
      const value = normalizeCursor(candidate);
      if (value <= localCursor) return { advanced: false, diverged: false };
      if (value > events.length - 1) return { advanced: false, diverged: true };
      adapter.setCursor(value);
      return { advanced: true, diverged: false };
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
        setStatus(STATES.ERROR, REASONS.SIN_FETCH);
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
        setStatus(STATES.ERROR, REASONS.SESION_INVALIDA);
        scheduleBackoff();
        return false;
      }
      adapter.setToken(payload.token);
      const advance = tryAdvanceCursor(payload.ultimoIndice);
      adapter.persist();
      if (advance.diverged) {
        setStatus(STATES.ERROR, REASONS.POSIBLE_MULTIPLES_PESTANAS);
        scheduleBackoff();
        return false;
      }
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
        setStatus(STATES.ERROR, REASONS.TOKEN_RECHAZADO);
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
      const advance = tryAdvanceCursor(payload && payload.ultimoIndice);
      adapter.persist();
      if (advance.diverged) {
        setStatus(STATES.ERROR, REASONS.POSIBLE_MULTIPLES_PESTANAS);
        scheduleBackoff();
        return;
      }
      setStatus(STATES.ONLINE);
      lastConfirmedAt = now();
      resetBackoff();
    }

    async function tick() {
      if (sending) return;
      if (now() < nextAttemptAt) return;
      // El cursor cargado (de un save anterior de esta misma pestana, o del
      // disco al arrancar) nunca deberia superar los eventos que existen en
      // memoria. Si lo hace, es la misma senal de "otra pestana sobrescribio
      // esta partida": no se envia nada hasta que los eventos locales
      // vuelvan a alcanzarlo.
      if (normalizeCursor(adapter.getCursor()) > adapter.getEvents().length - 1) {
        setStatus(STATES.ERROR, REASONS.POSIBLE_MULTIPLES_PESTANAS);
        scheduleBackoff();
        return;
      }
      if (pendingCount() === 0) {
        if (adapter.getToken() && status !== STATES.ONLINE) setStatus(STATES.ONLINE);
        return;
      }
      sending = true;
      try {
        const ready = await ensureSession();
        if (ready) await sendPendingBatch();
      } catch {
        setStatus(STATES.OFFLINE, REASONS.FALLO_RED);
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
      // Si el cursor ya supera los eventos locales (posible conflicto entre
      // pestanas, ver REASONS.POSIBLE_MULTIPLES_PESTANAS), buildBatch no
      // encuentra nada desde cursor + 1 y devuelve un lote vacio: no hace
      // falta un chequeo aparte aqui, el siguiente `if` ya corta el envio.
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
        return { state: status, pending: pendingCount(), lastConfirmedAt, reason: statusReason };
      },
      stop,
    };
  }

  const api = { create, STATES, REASONS, buildBatch };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LumaTelemetryClient = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
