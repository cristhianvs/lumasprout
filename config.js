(function (root) {
  'use strict';
  // Configuracion del cliente de telemetria remota. Sin esto, el envio queda
  // desactivado y el juego se comporta exactamente igual que hoy.
  const PARAM_ENABLED = 'telemetria';
  const PARAM_BASE_URL = 'telemetriaUrl';
  const DEFAULTS = Object.freeze({
    enabled: false,
    baseUrl: '',
    batchIntervalMs: 3000,
    maxBatchSize: 200,
    maxBatchBytes: 1000000,
    minBackoffMs: 1000,
    maxBackoffMs: 60000,
    requestTimeoutMs: 12000,
  });
  // Destinos remotos autorizados ademas del propio origen (vacio de fabrica:
  // en produccion solo el origen que sirve el juego puede recibir eventos).
  // Declarar aqui, en el codigo, cualquier servidor de telemetria autorizado
  // antes de desplegar; nunca se acepta un destino nuevo solo porque llegue
  // por la URL.
  const AUTHORIZED_REMOTE_ORIGINS = Object.freeze([]);
  const LOCAL_HOSTNAMES = Object.freeze(['localhost', '127.0.0.1', '::1']);

  function safeLocationOrigin() {
    try {
      return location.origin;
    } catch {
      return null;
    }
  }
  function safeLocationHostname() {
    try {
      return location.hostname;
    } catch {
      return '';
    }
  }
  function isLocalHost(hostname) {
    return LOCAL_HOSTNAMES.includes(hostname);
  }

  // Valida un ?telemetriaUrl= contra una lista blanca. CORS NUNCA se trata
  // como validacion aqui: un servidor receptor hostil simplemente autoriza
  // la peticion, asi que el filtro tiene que vivir en el cliente, antes de
  // enviar nada. Se acepta:
  //   1. El mismo origen que sirve el juego (siempre).
  //   2. Un origen en AUTHORIZED_REMOTE_ORIGINS (declarado en el codigo).
  //   3. Cualquier origen, PERO solo cuando el juego mismo corre en
  //      localhost/127.0.0.1 (override de pruebas locales).
  // Cualquier otro caso se rechaza; el llamador debe entonces dejar la
  // telemetria desactivada, nunca caer al destino por defecto.
  function resolveBaseUrl(rawValue, origin, hostname) {
    if (!rawValue) return { ok: true, value: '' };
    let target;
    try {
      target = new URL(rawValue, origin || undefined);
    } catch {
      return { ok: false, value: '' };
    }
    if (target.protocol !== 'http:' && target.protocol !== 'https:') {
      return { ok: false, value: '' };
    }
    if (origin && target.origin === origin) return { ok: true, value: target.origin };
    if (AUTHORIZED_REMOTE_ORIGINS.includes(target.origin))
      return { ok: true, value: target.origin };
    if (isLocalHost(hostname)) return { ok: true, value: target.origin };
    return { ok: false, value: '' };
  }

  function overridesFromQuery(search, origin, hostname) {
    const overrides = {};
    if (!search) return overrides;
    let params;
    try {
      params = new URLSearchParams(search);
    } catch {
      return overrides;
    }
    const wantsEnabled = params.has(PARAM_ENABLED) && params.get(PARAM_ENABLED) === '1';
    if (params.has(PARAM_BASE_URL)) {
      const resolved = resolveBaseUrl(params.get(PARAM_BASE_URL), origin, hostname);
      if (resolved.ok) {
        overrides.baseUrl = resolved.value;
        if (wantsEnabled) overrides.enabled = true;
      } else {
        // Destino no autorizado: se ignora POR COMPLETO el intento de
        // activar la telemetria por URL. Nunca se envia al destino por
        // defecto como si el intento de redirigirlo no hubiera pasado nada.
        overrides.enabled = false;
      }
    } else if (wantsEnabled) {
      overrides.enabled = true;
    }
    return overrides;
  }

  // `context` es opcional y solo existe para poder probar la resolucion sin
  // un `location` real (Node). En el navegador se usa siempre el origen y
  // host reales de la pagina.
  function resolve(search, context = {}) {
    const origin = 'origin' in context ? context.origin : safeLocationOrigin();
    const hostname = 'hostname' in context ? context.hostname : safeLocationHostname();
    return Object.freeze({ ...DEFAULTS, ...overridesFromQuery(search, origin, hostname) });
  }
  const config = resolve(typeof location !== 'undefined' ? location.search : '');
  const api = { DEFAULTS, resolve, resolveBaseUrl, isLocalHost, AUTHORIZED_REMOTE_ORIGINS, config };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LumaTelemetryConfig = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
