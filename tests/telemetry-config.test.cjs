'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const C = require('../config.js');

test('por defecto la telemetria esta desactivada y sin URL base', () => {
  const config = C.resolve('');
  assert.equal(config.enabled, false);
  assert.equal(config.baseUrl, '');
});

test('el parametro de URL telemetria=1 activa el envio solo para pruebas', () => {
  const config = C.resolve('?telemetria=1&telemetriaUrl=https%3A%2F%2Fapi.test');
  assert.equal(config.enabled, true);
  assert.equal(config.baseUrl, 'https://api.test');
});

test('cualquier valor distinto de 1 mantiene la telemetria desactivada', () => {
  assert.equal(C.resolve('?telemetria=0').enabled, false);
  assert.equal(C.resolve('?telemetria=true').enabled, false);
});

test('una cadena de busqueda invalida no rompe la resolucion', () => {
  assert.doesNotThrow(() => C.resolve(null));
  assert.equal(C.resolve(undefined).enabled, false);
});

test('la configuracion resuelta esta congelada', () => {
  const config = C.resolve('');
  assert.throws(() => {
    config.enabled = true;
  });
});
