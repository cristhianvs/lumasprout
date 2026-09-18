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
  });
  function overridesFromQuery(search) {
    const overrides = {};
    if (!search) return overrides;
    let params;
    try {
      params = new URLSearchParams(search);
    } catch {
      return overrides;
    }
    if (params.has(PARAM_ENABLED)) overrides.enabled = params.get(PARAM_ENABLED) === '1';
    if (params.has(PARAM_BASE_URL)) overrides.baseUrl = params.get(PARAM_BASE_URL);
    return overrides;
  }
  function resolve(search) {
    return Object.freeze({ ...DEFAULTS, ...overridesFromQuery(search) });
  }
  const config = resolve(typeof location !== 'undefined' ? location.search : '');
  const api = { DEFAULTS, resolve, config };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LumaTelemetryConfig = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
