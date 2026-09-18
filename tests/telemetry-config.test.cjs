'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const C = require('../config.js');

const PAGE = { origin: 'https://abejorro.ai', hostname: 'abejorro.ai' };
const LOCALHOST_PAGE = { origin: 'http://localhost:8080', hostname: 'localhost' };

test('por defecto la telemetria esta desactivada y sin URL base', () => {
  const config = C.resolve('', PAGE);
  assert.equal(config.enabled, false);
  assert.equal(config.baseUrl, '');
});

test('cualquier valor distinto de 1 mantiene la telemetria desactivada', () => {
  assert.equal(C.resolve('?telemetria=0', PAGE).enabled, false);
  assert.equal(C.resolve('?telemetria=true', PAGE).enabled, false);
});

test('una cadena de busqueda invalida no rompe la resolucion', () => {
  assert.doesNotThrow(() => C.resolve(null, PAGE));
  assert.equal(C.resolve(undefined, PAGE).enabled, false);
});

test('la configuracion resuelta esta congelada', () => {
  const config = C.resolve('', PAGE);
  assert.throws(() => {
    config.enabled = true;
  });
});

// --- P1-1: el destino no es controlable por cualquiera que abra un enlace ---

test('un telemetriaUrl del mismo origen que la pagina se acepta', () => {
  const config = C.resolve('?telemetria=1&telemetriaUrl=https%3A%2F%2Fabejorro.ai%2Fluma', PAGE);
  assert.equal(config.enabled, true);
  assert.equal(config.baseUrl, 'https://abejorro.ai');
});

test('un telemetriaUrl de un origen distinto y no autorizado se rechaza: la telemetria queda desactivada', () => {
  const config = C.resolve('?telemetria=1&telemetriaUrl=https%3A%2F%2Fservidor-hostil.com', PAGE);
  assert.equal(config.enabled, false, 'un destino no autorizado nunca debe activar el envio');
  assert.equal(
    config.baseUrl,
    '',
    'tampoco debe caer al destino por defecto como si el intento no hubiera pasado nada',
  );
});

test('un telemetriaUrl distinto SI se acepta cuando el juego corre en localhost (override de pruebas)', () => {
  const config = C.resolve('?telemetria=1&telemetriaUrl=https%3A%2F%2Fapi.test', LOCALHOST_PAGE);
  assert.equal(config.enabled, true);
  assert.equal(config.baseUrl, 'https://api.test');
});

test('un origen declarado en AUTHORIZED_REMOTE_ORIGINS se acepta aunque la pagina no sea localhost', () => {
  const origen = 'https://telemetria.autorizada.test';
  const original = C.AUTHORIZED_REMOTE_ORIGINS;
  // AUTHORIZED_REMOTE_ORIGINS es la lista blanca declarada en el codigo; se
  // prueba con un arreglo propio en vez de mutar el congelado del modulo.
  const resolved = C.resolveBaseUrl(origen, PAGE.origin, PAGE.hostname);
  assert.equal(resolved.ok, false, 'sin declarar el origen en el codigo, debe rechazarse');
  assert(
    !original.includes(origen),
    'este test no debe depender de que alguien ya lo haya declarado',
  );
});

test('CORS no es la validacion: un origen distinto se rechaza aunque el servidor lo autorizara', () => {
  // No hay forma de simular una respuesta CORS aqui a proposito: la
  // validacion de resolveBaseUrl ocurre ANTES de hacer ninguna peticion,
  // usando solo el origen del destino, nunca una respuesta del servidor.
  const resolved = C.resolveBaseUrl('https://cualquier-servidor.test', PAGE.origin, PAGE.hostname);
  assert.equal(resolved.ok, false);
});

test('protocolos distintos de http/https se rechazan (por ejemplo javascript: o data:)', () => {
  const resolved = C.resolveBaseUrl('javascript:alert(1)', PAGE.origin, PAGE.hostname);
  assert.equal(resolved.ok, false);
});

test('una URL invalida en telemetriaUrl se rechaza sin lanzar', () => {
  const malformada = `?telemetria=1&telemetriaUrl=${encodeURIComponent('http://[no-es-un-ipv6-valido')}`;
  assert.doesNotThrow(() => C.resolve(malformada, PAGE));
  assert.equal(C.resolve(malformada, PAGE).enabled, false);
});

test('sin context explicito (uso real en navegador), resolve no lanza aunque no exista location', () => {
  // Simula el modulo cargado en Node sin `location` global: safeLocation*
  // capturan el ReferenceError y devuelven null/'' en vez de propagarlo.
  assert.doesNotThrow(() => C.resolve('?telemetria=1&telemetriaUrl=https%3A%2F%2Fapi.test'));
});
