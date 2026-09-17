(function (root) {
  'use strict';
  // Event payloads are JSON records, never live references to application state.
  function snapshot(value) {
    return JSON.parse(JSON.stringify(value));
  }
  function freeze(value) {
    if (value && typeof value === 'object') {
      Object.values(value).forEach(freeze);
      Object.freeze(value);
    }
    return value;
  }
  function createTelemetry({ context, append, now }) {
    return (type, data = {}) => {
      const event = freeze(snapshot({ ...context(), type, at: now(), data }));
      append(event);
      return event;
    };
  }
  // Coalesce synchronous UI/event changes; keep the existing save/export format.
  // Lifecycle boundaries flush explicitly. Failed writes leave the in-memory data intact.
  function createSessionStore({ storage, key, schedule, onError = () => {} }) {
    let pending = null;
    let queued = false;
    function flush() {
      queued = false;
      if (!pending) return true;
      try {
        storage.setItem(key, JSON.stringify(pending()));
        pending = null;
        onError(false);
        return true;
      } catch (error) {
        onError(true, error);
        return false;
      }
    }
    return {
      load(fallback) {
        try {
          return JSON.parse(storage.getItem(key)) || fallback();
        } catch {
          return fallback();
        }
      },
      save(readState) {
        pending = readState;
        if (!queued) {
          queued = true;
          schedule(flush);
        }
      },
      flush,
    };
  }
  const api = { snapshot, createTelemetry, createSessionStore };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LumaRuntime = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
