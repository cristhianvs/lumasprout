'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const E = require('../engine.js');
const R = require('../runtime.js');

test('telemetry retains immutable nested evidence across mutations and export', () => {
  const events = [],
    learning = { passed: ['concrete'], seen: ['a'] };
  const emit = R.createTelemetry({
    context: () => ({ id: String(events.length) }),
    append: (e) => events.push(e),
    now: () => 'fixed-clock',
  });
  const event = emit('decision_evaluated', { learning });
  learning.passed.push('pictorial');
  learning.seen.push('b');
  assert.deepEqual(event.data.learning, { passed: ['concrete'], seen: ['a'] });
  assert.throws(() => event.data.learning.passed.push('transfer'), TypeError);
  assert.deepEqual(JSON.parse(JSON.stringify(events))[0].data.learning.passed, ['concrete']);
});
test('batched persistence retries quota failure without dropping telemetry', () => {
  let writes = 0,
    saved,
    fail = true;
  const callbacks = [],
    errors = [];
  const state = { events: [{ id: 'retained' }] };
  const store = R.createSessionStore({
    key: 'isolated',
    storage: {
      setItem(key, value) {
        writes++;
        if (fail) throw Error('quota');
        saved = value;
      },
      getItem() {
        return saved;
      },
    },
    schedule: (f) => callbacks.push(f),
    onError: (e) => errors.push(e),
  });
  store.save(() => state);
  store.save(() => state);
  assert.equal(callbacks.length, 1);
  callbacks.shift()();
  assert.equal(writes, 1);
  assert.equal(errors.at(-1), true);
  state.events.push({ id: 'new' });
  fail = false;
  assert.equal(store.flush(), true);
  assert.deepEqual(
    store.load(() => null),
    state,
  );
  assert.equal(errors.at(-1), false);
});
test('legacy equivalent transfer exhaustion now selects genuinely new items', () => {
  const knowledge = E.newKnowledge(),
    learning = E.newLearning(knowledge);
  const k = learning.skills.equivalent;
  k.passed = ['concrete', 'pictorial', 'abstract'];
  k.probe = true;
  k.seen = ['recipe', 'garden', 'journey'].map((context, i) =>
    JSON.stringify(['equivalent', [i + 1, 4], null, null, context, 'transfer']),
  );
  const task = E.learningTask('equivalent', 0, learning);
  assert(task.novel);
  assert(!task.bankExhausted);
  E.recordLearning(learning, task, true, false);
  assert(k.passed.includes('transfer'));
});
test('every finite bank exits exhaustion honestly and cannot certify a repeated transfer', () => {
  for (const { id } of E.skills) {
    const learning = E.newLearning(E.newKnowledge()),
      k = learning.skills[id];
    k.passed = ['concrete', 'pictorial', 'abstract'];
    let count = 0,
      task;
    do {
      task = E.learningTask(id, count, learning);
      if (task.bankExhausted) break;
      assert(task.novel);
      E.recordLearning(learning, task, true, true);
      count++;
      assert(count <= task.bankSize);
    } while (!task.bankExhausted);
    assert.equal(count, task.bankSize);
    E.recordLearning(learning, task, true, false);
    assert(!k.passed.includes('transfer'));
  }
});
test('progress distinguishes Bayesian estimate, verified CPA and legacy compatibility', () => {
  const knowledge = E.newKnowledge(),
    learning = E.newLearning(knowledge);
  knowledge.meaning = { p: 0.99, n: 3, correct: 3 };
  let progress = E.progressSummary(knowledge, learning);
  assert.equal(progress.bayesianCount, 1);
  assert.equal(progress.verifiedCount, 0);
  learning.skills.meaning.passed = [...E.stages];
  assert.equal(E.progressSummary(knowledge, learning).verifiedCount, 1);
  progress = E.progressSummary(knowledge);
  assert(progress.legacy);
  assert.equal(progress.verifiedCount, 0);
});
test('signal decision lists exactly its eligible evidence, excluding future and other phases', () => {
  const events = [
    { id: 'future', phase: 'math', mathMs: 200001, type: 'hint_requested' },
    { id: 'expired', phase: 'math', mathMs: 1, type: 'hint_requested' },
    { id: 'play', phase: 'play', playMs: 200000, type: 'hint_requested' },
    { id: 'included', phase: 'math', mathMs: 200000, type: 'hint_requested' },
  ];
  const { metrics } = E.sessionPolicy(events);
  assert.equal(metrics.hints, 1);
  assert.deepEqual(metrics.evidenceIds, ['included']);
});
