(function (root) {
  'use strict';
  const CONFIG = Object.freeze({
    version: '2026-09-prototype-1',
    playMs: 300000,
    idleMs: 45000,
    failures: 3,
    mastery: 0.85,
    minEvidence: 3,
  });
  // Prototype parameters, centralized for review; values are not empirically calibrated.
  const POLICY = Object.freeze({
    version: 'cpa-2',
    knowledge: Object.freeze({
      prior: 0.5,
      knownCorrect: 0.9,
      unknownCorrect: 0.15,
      transition: 0.08,
      floor: 0.01,
      ceiling: 0.99,
    }),
    preference: Object.freeze({
      history: 80,
      prior: 1,
      behaviorWeight: 0.6,
      familyWeight: 0.4,
      minimum: 5,
      gap: 0.06,
      creativeWeight: 0.2,
    }),
    signals: Object.freeze({
      windowMs: 120000,
      history: 20,
      elevated: 4,
      observe: 2,
      participation: 3,
    }),
    support: Object.freeze({ windowMs: 60000, hints: 3, latencySamples: 5, variation: 1 }),
    pace: Object.freeze({
      standardBlockMs: 90000,
      gentleBlockMs: 60000,
      standardBreakMs: 480000,
      gentleBreakMs: 240000,
      readingGraceMs: 120000,
    }),
    content: Object.freeze({
      denominators: Object.freeze([2, 3, 4, 6, 8, 12, 16, 18, 24]),
      sourceDenominators: Object.freeze([4, 6, 8]),
      contexts: Object.freeze(['recipe', 'garden', 'journey']),
      operationSeeds: 96,
    }),
  });
  const profiles = ['estructurado', 'visual', 'auditivo', 'explorador'];
  const experiences = {
    estructurado: {
      name: 'Laboratorio de pasos',
      verb: 'Resolver por pasos',
      goal: 'Revisa el entero, elige el tamaño de las partes y construye tu respuesta.',
    },
    visual: {
      name: 'Estudio de mosaicos',
      verb: 'Pintar mosaicos',
      goal: 'Pinta la cantidad que responde al reto. Cada tablero completo vale un entero.',
    },
    auditivo: {
      name: 'Estación de ritmos',
      verb: 'Crear ritmos',
      goal: 'Marca los pulsos que responden al reto. Cada compás completo vale un entero. También puedes jugar sin sonido.',
    },
    explorador: {
      name: 'Ruta de energía',
      verb: 'Llevar energía',
      goal: 'Carga las piezas que necesita la expedición. Cada batería completa vale un entero.',
    },
  };
  const skills = [
    { id: 'meaning', name: 'Partes de un entero', parents: [] },
    { id: 'equivalent', name: 'Fracciones equivalentes', parents: ['meaning'] },
    { id: 'add_same', name: 'Sumar partes del mismo tamaño', parents: ['meaning'] },
    { id: 'sub_same', name: 'Restar partes del mismo tamaño', parents: ['meaning'] },
    {
      id: 'add_diff',
      name: 'Sumar con distintos denominadores',
      parents: ['equivalent', 'add_same'],
    },
    {
      id: 'sub_diff',
      name: 'Restar con distintos denominadores',
      parents: ['equivalent', 'sub_same'],
    },
  ];
  function gcd(a, b) {
    while (b) [a, b] = [b, a % b];
    return Math.abs(a);
  }
  function same(a, b) {
    return a[0] * b[1] === b[0] * a[1];
  }
  function parseFraction(value) {
    const m = String(value)
      .trim()
      .match(/^(\d{1,4})(?:\s*\/\s*(\d{1,4}))?$/);
    if (!m || Number(m[2] || 1) === 0) return null;
    return [Number(m[1]), Number(m[2] || 1)];
  }
  function newKnowledge() {
    return Object.fromEntries(
      skills.map((s) => [s.id, { p: POLICY.knowledge.prior, n: 0, correct: 0 }]),
    );
  }
  function updateKnowledge(previous, correct, assisted) {
    if (assisted) return { ...previous }; // El éxito con pistas no demuestra dominio independiente.
    const likelihoodKnown = correct
        ? POLICY.knowledge.knownCorrect
        : 1 - POLICY.knowledge.knownCorrect,
      likelihoodUnknown = correct
        ? POLICY.knowledge.unknownCorrect
        : 1 - POLICY.knowledge.unknownCorrect;
    const p =
      (previous.p * likelihoodKnown) /
      (previous.p * likelihoodKnown + (1 - previous.p) * likelihoodUnknown);
    // Pequeña transición de aprendizaje después del intento; parámetros pendientes de calibración.
    return {
      p: Math.min(
        POLICY.knowledge.ceiling,
        Math.max(POLICY.knowledge.floor, p + (1 - p) * POLICY.knowledge.transition),
      ),
      n: previous.n + 1,
      correct: previous.correct + Number(correct),
    };
  }
  const mastered = (k) => k.n >= CONFIG.minEvidence && k.p >= CONFIG.mastery;
  function nextSkill(knowledge) {
    const ready = skills.filter(
      (s) => !mastered(knowledge[s.id]) && s.parents.every((id) => mastered(knowledge[id])),
    );
    if (!ready.length)
      return skills.reduce((a, b) => (knowledge[a.id].p < knowledge[b.id].p ? a : b)).id;
    return ready.sort((a, b) => {
      const score = (s) => {
        const k = knowledge[s.id];
        return (
          (1 - k.p) * 2 +
          (k.n === 0 ? 0.5 : 0) +
          skills.filter((x) => x.parents.includes(s.id)).length * 0.1
        );
      };
      return score(b) - score(a);
    })[0].id;
  }
  function inferProfile(events, parent) {
    const score = Object.fromEntries(profiles.map((p) => [p, POLICY.preference.prior]));
    let observations = 0;
    // Una observación por contexto evita que pulsar repetidamente una ayuda
    // convierta una preferencia provisional en una etiqueta permanente.
    const seen = new Set();
    const recent = events
      .filter((e) =>
        ['support_selected', 'route_selected', 'creative_change', 'experience_selected'].includes(
          e.type,
        ),
      )
      .slice(-POLICY.preference.history);
    for (const e of recent) {
      if (e.type === 'support_selected' && !e.data.voluntary) continue;
      const context = e.task || `${e.phase || 'play'}:${e.scene ?? e.data.context ?? 'unknown'}`;
      const key = `${context}:${e.type}:${e.data.mode || e.data.route || e.data.profile || ''}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (e.type === 'experience_selected' && profiles.includes(e.data.profile)) {
        score[e.data.profile] += 1;
        observations++;
      }
      if (e.type === 'support_selected' && e.data.voluntary) {
        const p = { visual: 'visual', audio: 'auditivo', hands: 'explorador' }[e.data.mode];
        if (p) {
          score[p] += 1;
          observations++;
        }
      }
      if (e.type === 'route_selected') {
        score[e.data.route === 'guided' ? 'estructurado' : 'explorador'] += 1;
        observations++;
      }
      if (e.type === 'creative_change') {
        score.visual += POLICY.preference.creativeWeight;
        observations++;
      }
    }
    const total = Object.values(score).reduce((a, b) => a + b, 0);
    const behavior = Object.fromEntries(profiles.map((p) => [p, score[p] / total]));
    const validParent =
      parent &&
      profiles.every((p) => Number.isFinite(parent[p]) && parent[p] >= 0) &&
      profiles.reduce((n, p) => n + parent[p], 0) > 0;
    const pt = validParent ? profiles.reduce((n, p) => n + parent[p], 0) : 1;
    const combined = Object.fromEntries(
      profiles.map((p) => [
        p,
        validParent
          ? POLICY.preference.behaviorWeight * behavior[p] +
            (POLICY.preference.familyWeight * parent[p]) / pt
          : behavior[p],
      ]),
    );
    const ranked = [...profiles].sort((a, b) => combined[b] - combined[a]);
    const sufficient =
      observations >= POLICY.preference.minimum &&
      combined[ranked[0]] - combined[ranked[1]] >= POLICY.preference.gap;
    return {
      behavior,
      combined,
      dominant: sufficient ? ranked[0] : null,
      secondary: sufficient ? ranked[1] : null,
      observations,
      provisional: !validParent,
      confidence: sufficient ? 'exploratoria' : 'evidencia insuficiente',
    };
  }
  function signals(events) {
    const last = events.at(-1),
      phase = last?.phase;
    const clock = phase === 'play' ? 'playMs' : 'mathMs',
      now = last?.[clock];
    const recent = events
      .filter(
        (e) =>
          (!phase || e.phase === phase) &&
          (!Number.isFinite(now) ||
            !Number.isFinite(e[clock]) ||
            (now - e[clock] >= 0 && now - e[clock] <= POLICY.signals.windowMs)),
      )
      .filter((e) => ['attempt', 'hint_requested', 'idle_started', 'idle_ended'].includes(e.type))
      .slice(-POLICY.signals.history);
    const attempts = recent.filter((e) => e.type === 'attempt'),
      errors = attempts.filter((e) => e.data?.correct === false).length;
    const hints = recent.filter((e) => e.type === 'hint_requested').length,
      idle = recent.filter((e) => e.type === 'idle_started').length;
    const latencies = attempts
      .map((e) => e.data?.latencyMs)
      .filter((n) => Number.isFinite(n) && n >= 0)
      .sort((a, b) => a - b);
    const load = errors + hints;
    return {
      windowMs: POLICY.signals.windowMs,
      evidenceIds: recent.map((event) => event.id).filter(Boolean),
      attempts: attempts.length,
      errors,
      hints,
      idle,
      accuracy: attempts.length ? (attempts.length - errors) / attempts.length : null,
      medianLatencyMs: latencies.length ? latencies[Math.floor(latencies.length / 2)] : null,
      supportNeed:
        load >= POLICY.signals.elevated
          ? 'elevada'
          : load >= POLICY.signals.observe
            ? 'en observación'
            : 'sin señal suficiente',
      engagement: idle
        ? 'interrupción observada'
        : attempts.length >= POLICY.signals.participation
          ? 'participación observada'
          : 'evidencia insuficiente',
      anxiety: 'no inferible',
      isClinicalInference: false,
    };
  }
  function sessionPolicy(events, options = {}) {
    const metrics = signals(events),
      gentle = options.pace === 'gentle',
      elevated = metrics.supportNeed === 'elevada';
    return {
      blockMs: elevated || gentle ? POLICY.pace.gentleBlockMs : POLICY.pace.standardBlockMs,
      breakAfterMs: elevated || gentle ? POLICY.pace.gentleBreakMs : POLICY.pace.standardBreakMs,
      support: elevated ? 'concrete' : 'pictorial',
      reason: elevated
        ? 'recent_errors_and_help'
        : gentle
          ? 'simulation_gentle_pace'
          : 'standard_pace',
      metrics,
    };
  }
  function makeTask(id, serial) {
    const ds = POLICY.content.sourceDenominators,
      d = ds[serial % ds.length];
    if (id === 'meaning') {
      const n = 1 + (serial % (d - 1));
      return {
        id,
        kind: 'meaning',
        a: [n, d],
        answer: [n, d],
        prompt: '¿Qué fracción del panel está iluminada?',
        hint: 'El denominador cuenta todas las partes iguales; el numerador, las iluminadas.',
      };
    }
    if (id === 'equivalent') {
      const n = 1 + (serial % 3);
      return {
        id,
        kind: 'equivalent',
        a: [n, 4],
        answer: [n * 2, 8],
        targetDen: 8,
        prompt: 'Escribe una fracción equivalente usando octavos.',
        hint: 'Divide cada cuarto en dos partes iguales. El tamaño iluminado no cambia.',
      };
    }
    const subtract = id.startsWith('sub'),
      diff = id.endsWith('diff');
    const a = diff ? [3, 4] : [d - 1, d],
      b = diff ? [1, serial % 2 ? 2 : 8] : [1 + (serial % 2), d];
    const den = a[1] * b[1],
      num = a[0] * b[1] + (subtract ? -1 : 1) * b[0] * a[1],
      g = gcd(num, den);
    return {
      id,
      kind: 'operation',
      a,
      b,
      op: subtract ? '−' : '+',
      answer: [num / g, den / g],
      prompt: subtract
        ? 'Retira la energía indicada. ¿Cuánta queda?'
        : 'Une la energía de ambos paneles. ¿Cuánta hay en total?',
      hint: diff
        ? 'Las piezas deben tener el mismo tamaño. Busca un denominador común antes de unirlas o retirarlas.'
        : 'Los denominadores iguales indican piezas del mismo tamaño. Opera los numeradores y conserva el denominador.',
    };
  }
  function classify(task, answer) {
    if (!answer) return 'invalid_format';
    if (task.targetDen && answer[1] !== task.targetDen && same(answer, task.answer))
      return 'target_denominator';
    if (same(answer, task.answer)) return 'correct';
    if (
      task.b &&
      answer[0] === task.a[0] + (task.op === '−' ? -task.b[0] : task.b[0]) &&
      answer[1] === task.a[1] + task.b[1]
    )
      return 'operates_denominators';
    if (task.b && task.a[1] !== task.b[1] && answer[1] === task.a[1]) return 'no_common_unit';
    if (answer[0] === task.answer[1] && answer[1] === task.answer[0]) return 'inverted_fraction';
    return 'other';
  }
  // La evidencia anterior se conserva, pero no se inventa evidencia CPA retrospectiva.
  const stages = ['concrete', 'pictorial', 'abstract', 'transfer'];
  function newLearning(knowledge) {
    return {
      version: 1,
      skills: Object.fromEntries(
        skills.map((s) => [
          s.id,
          { passed: [], seen: [], probe: false, legacyMastered: mastered(knowledge[s.id]) },
        ]),
      ),
    };
  }
  function learningComplete(id, knowledge, learning) {
    const k = learning?.skills[id];
    return (
      mastered(knowledge[id]) &&
      (!k || k.legacyMastered || stages.every((s) => k.passed.includes(s)))
    );
  }
  function progressSummary(knowledge, learning) {
    const rows = skills.map(({ id }) => {
      const evidence = learning?.skills[id];
      return {
        id,
        bayesian: mastered(knowledge[id]),
        legacy: !evidence || !!evidence.legacyMastered,
        stages: [...(evidence?.passed || [])],
        transfer: !!evidence?.passed.includes('transfer'),
        complete: learningComplete(id, knowledge, learning),
      };
    });
    return {
      skills: rows,
      total: rows.length,
      bayesianCount: rows.filter((s) => s.bayesian).length,
      verifiedCount: rows.filter((s) => s.complete && !s.legacy).length,
      complete: rows.every((s) => s.complete),
      legacy: rows.some((s) => s.legacy),
    };
  }
  function nextLearningSkill(knowledge, learning) {
    return (
      skills.find(
        (s) =>
          !learningComplete(s.id, knowledge, learning) &&
          s.parents.every((p) => learningComplete(p, knowledge, learning)),
      )?.id || nextSkill(knowledge)
    );
  }
  function taskFingerprint(task, context, stage) {
    const parts = [task.id, task.a, task.b || null, task.op || null, context, stage];
    // Preserve fingerprints of the original quarters/eighths bank.
    if (task.targetDen && task.targetDen !== 8) parts.push(task.targetDen);
    return JSON.stringify(parts);
  }
  function taskVariants(id) {
    const candidates = [];
    if (id === 'equivalent') {
      for (const denominator of POLICY.content.sourceDenominators) {
        for (let numerator = 1; numerator < denominator; numerator++) {
          for (const factor of [2, 3]) {
            candidates.push({
              ...makeTask(id, 0),
              a: [numerator, denominator],
              answer: [numerator * factor, denominator * factor],
              targetDen: denominator * factor,
              prompt: `Escribe una fracción equivalente con denominador ${denominator * factor}.`,
              hint: `Divide cada parte en ${factor} partes iguales. La cantidad no cambia.`,
            });
          }
        }
      }
    } else {
      for (let seed = 0; seed < POLICY.content.operationSeeds; seed++) {
        const task = makeTask(id, seed);
        if (task.b) {
          const denominators = POLICY.content.sourceDenominators;
          const d = denominators[seed % denominators.length];
          task.a = id.endsWith('diff') ? [2 + (seed % 2), 4] : [2 + (seed % (d - 2)), d];
          task.b = id.endsWith('diff') ? [1, seed % 2 ? 2 : 8] : [1, d];
          const denominator = task.a[1] * task.b[1];
          const numerator =
            task.a[0] * task.b[1] + (task.op === '−' ? -1 : 1) * task.b[0] * task.a[1];
          const divisor = gcd(numerator, denominator);
          task.answer = [numerator / divisor, denominator / divisor];
        }
        candidates.push(task);
      }
    }
    return [
      ...new Map(candidates.map((t) => [JSON.stringify([t.a, t.b, t.targetDen]), t])).values(),
    ];
  }
  const banks = new Map();
  function learningTask(id, serial, learning) {
    const k = learning.skills[id];
    const stage = stages.find((s) => !k.passed.includes(s)) || 'transfer';
    if (!banks.has(id)) banks.set(id, taskVariants(id));
    const candidates = banks.get(id).flatMap((t) =>
      (stage === 'transfer' ? POLICY.content.contexts : ['energy']).map((context) => ({
        ...t,
        context,
        variantId: taskFingerprint(t, context, stage),
      })),
    );
    const preferred = serial % candidates.length;
    const ordered = [...candidates.slice(preferred), ...candidates.slice(0, preferred)];
    const seen = new Set(k.seen);
    const unseen = ordered.find((t) => !seen.has(t.variantId));
    const t = { ...(unseen || ordered[0]) };
    if (stage === 'transfer') {
      const object = { recipe: 'una receta', garden: 'el riego del jardín', journey: 'una ruta' }[
        t.context
      ];
      t.prompt =
        t.kind === 'meaning'
          ? `Para ${object}, se usan ${t.a[0]} de ${t.a[1]} partes iguales de un entero. ¿Qué fracción se usa?`
          : t.kind === 'equivalent'
            ? `Para ${object}, expresa ${t.a[0]}/${t.a[1]} de un entero con denominador ${t.targetDen}.`
            : `Para ${object}, hay ${t.a[0]}/${t.a[1]} de un entero y ${t.op === '−' ? 'se retiran' : 'se agregan'} ${t.b[0]}/${t.b[1]} del mismo entero. ¿Qué fracción ${t.op === '−' ? 'queda' : 'hay en total'}?`;
    }
    return {
      ...t,
      stage,
      itemVersion: 'fractions-3',
      novel: !seen.has(t.variantId),
      independentProbe: k.probe,
      bankSize: candidates.length,
      bankExhausted: stage === 'transfer' && !unseen && !k.passed.includes('transfer'),
    };
  }
  function recordLearning(learning, task, correct, assisted) {
    const k = learning.skills[task.id];
    if (!task.stage) return;
    const novel = !k.seen.includes(task.variantId);
    if (novel) k.seen.push(task.variantId);
    if (correct && !assisted && (novel || task.stage !== 'transfer')) {
      if (!k.passed.includes(task.stage)) k.passed.push(task.stage);
      k.probe = false;
    } else k.probe = true;
  }
  const api = {
    CONFIG,
    POLICY,
    progressSummary,
    profiles,
    experiences,
    skills,
    gcd,
    same,
    parseFraction,
    newKnowledge,
    updateKnowledge,
    mastered,
    nextSkill,
    inferProfile,
    signals,
    sessionPolicy,
    makeTask,
    classify,
    stages,
    newLearning,
    learningComplete,
    nextLearningSkill,
    learningTask,
    recordLearning,
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Luma = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
