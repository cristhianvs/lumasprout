const { test } = require('node:test');
const assert = require('node:assert/strict');
const E = require('../engine');
const S = require('../simulation');
for (const scenario of S.scenarios)
  test(`simulación reproducible: ${scenario.id}`, () => {
    for (const pace of ['standard', 'gentle']) {
      const r = S.run(scenario.id, { pace });
      for (const check of r.checks) assert(check.pass, check.name);
      assert.deepEqual(r, S.run(scenario.id, { pace }));
      if (scenario.choice) assert(r.timeline.every((t) => t.experience === scenario.choice));
    }
  });
test('la política recupera el ritmo y separa juego previo de matemáticas', () => {
  const errors = Array.from({ length: 4 }, () => ({
    type: 'attempt',
    phase: 'math',
    mathMs: 0,
    data: { correct: false },
  }));
  assert.equal(E.sessionPolicy(errors).support, 'concrete');
  assert.equal(
    E.sessionPolicy([...errors, { type: 'heartbeat', phase: 'math', mathMs: 120001, data: {} }])
      .support,
    'pictorial',
  );
  assert.equal(
    E.sessionPolicy([...errors, { type: 'heartbeat', phase: 'play', playMs: 1, data: {} }]).support,
    'pictorial',
  );
});
test('interrupción y latencia no se convierten en ansiedad ni fracaso', () => {
  const events = [
    { type: 'idle_started', data: {} },
    ...Array.from({ length: 5 }, () => ({
      type: 'attempt',
      data: { correct: true, latencyMs: 90000 },
    })),
  ];
  const p = E.sessionPolicy(events);
  assert.equal(p.support, 'pictorial');
  assert.equal(p.metrics.anxiety, 'no inferible');
  assert.equal(p.metrics.engagement, 'interrupción observada');
});
