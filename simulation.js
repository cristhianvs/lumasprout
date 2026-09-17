(function (root) {
  'use strict';
  const E = typeof module !== 'undefined' && module.exports ? require('./engine.js') : root.Luma;
  const R =
    typeof module !== 'undefined' && module.exports ? require('./runtime.js') : root.LumaRuntime;
  const scenarios = [
    ...E.profiles.map((profile) => ({
      id: profile,
      name: `Preferencia ${profile} · avance independiente`,
      profile,
      expectedProfile: profile,
      rounds: 20,
    })),
    {
      id: 'recovery',
      name: 'Dificultad acumulada y recuperación',
      profile: 'visual',
      rounds: 40,
      struggle: true,
    },
    {
      id: 'slow',
      name: 'Lectura lenta con respuestas correctas',
      profile: 'estructurado',
      rounds: 20,
      latency: 70000,
    },
    {
      id: 'interruptions',
      name: 'Interrupciones y regreso a la actividad',
      profile: 'explorador',
      rounds: 20,
      interruptions: true,
    },
    {
      id: 'mixed',
      name: 'Preferencias mixtas · evidencia insuficiente',
      profile: null,
      rounds: 20,
      expectedProfile: null,
    },
    {
      id: 'family',
      name: 'Familia y elecciones observadas en desacuerdo',
      profile: 'visual',
      parent: 'auditivo',
      rounds: 20,
      expectedProfile: null,
    },
    {
      id: 'choice',
      name: 'Elección explícita sobre sugerencia automática',
      profile: 'visual',
      choice: 'explorador',
      rounds: 20,
      expectedProfile: 'visual',
    },
    {
      id: 'assisted',
      name: 'Éxito con ayuda · sin acreditar dominio',
      profile: 'estructurado',
      rounds: 12,
      assisted: true,
    },
    {
      id: 'no_audio',
      name: 'Preferencia auditiva sin audio disponible',
      profile: 'auditivo',
      rounds: 20,
      noAudio: true,
      expectedProfile: 'auditivo',
    },
  ];
  function run(id, options = {}) {
    const scenario = scenarios.find((s) => s.id === id);
    if (!scenario) throw Error('Escenario desconocido');
    const s = {
      version: E.CONFIG.version,
      simulatorVersion: 'legacy-bayesian-1',
      runId: `simulation-${id}`,
      simulation: true,
      simulationConfig: {
        pace: options.pace === 'gentle' ? 'gentle' : 'standard',
        noAudio: !!scenario.noAudio,
      },
      phase: 'play',
      playMs: 0,
      mathMs: 0,
      blockMs: 0,
      events: [],
      knowledge: E.newKnowledge(),
      serial: 0,
      round: 0,
      route: null,
      parent: scenario.parent
        ? { scores: Object.fromEntries(E.profiles.map((p) => [p, p === scenario.parent ? 3 : 0])) }
        : null,
      garden: ['🌿', '🌼', '🌿'],
      sound: false,
      current: null,
      playProgress: { rescued: [0, 1, 2], signals: 3, gardenActions: 1 },
      experienceChoice: scenario.choice || null,
    };
    const frames = [],
      timeline = [];
    function emit(type, data = {}, task = null) {
      s.events.push({
        id: `${s.runId}:${s.events.length}`,
        runId: s.runId,
        session: 'synthetic',
        version: E.CONFIG.version,
        schemaVersion: '1.4',
        policyVersion: 'legacy-bayesian-1',
        simulation: true,
        type,
        at: new Date(Date.UTC(2026, 8, 17) + s.playMs + s.mathMs).toISOString(),
        phase: s.phase,
        scene: s.phase === 'play' ? s.events.length : null,
        playMs: s.playMs,
        mathMs: s.mathMs,
        task,
        data: R.snapshot(data),
      });
    }
    for (let i = 0; i < 8; i++) {
      s.playMs += 15000;
      const profile = scenario.profile || E.profiles[i % 4];
      if (profile === 'estructurado' || profile === 'explorador')
        emit(
          'route_selected',
          { route: profile === 'estructurado' ? 'guided' : 'free' },
          `preference-${i}`,
        );
      else
        emit(
          'support_selected',
          { mode: profile === 'visual' ? 'visual' : 'audio', voluntary: true },
          `preference-${i}`,
        );
    }
    if (scenario.noAudio) emit('audio_unavailable', { source: 'synthetic_device' });
    s.phase = 'math';
    emit('math_started', { knowledgeSource: 'fraction_tasks_only' });
    function capture(label) {
      const profile = E.inferProfile(s.events, s.parent?.scores),
        policy = E.sessionPolicy(s.events, s.simulationConfig);
      const skill = E.skills.every((k) => E.mastered(s.knowledge[k.id]))
        ? null
        : E.nextSkill(s.knowledge);
      timeline.push({
        step: timeline.length,
        label,
        mathMs: s.mathMs,
        profile: profile.dominant,
        experience: s.experienceChoice || profile.dominant || 'estructurado',
        skill,
        policy,
        mastered: E.skills.filter((k) => E.mastered(s.knowledge[k.id])).length,
      });
      frames.push(JSON.parse(JSON.stringify(s)));
    }
    capture('Entrada al taller');
    for (let i = 0; i < scenario.rounds; i++) {
      if (E.skills.every((k) => E.mastered(s.knowledge[k.id]))) {
        s.phase = 'complete';
        s.completionReason = 'mastery';
        emit('learning_path_completed', { skills: E.skills.map((k) => k.id) });
        capture('Recorrido dominado');
        break;
      }
      const skill = E.nextSkill(s.knowledge),
        task = E.makeTask(skill, s.serial++),
        key = `${skill}-${s.serial}`;
      const p = E.sessionPolicy(s.events, s.simulationConfig),
        profile = E.inferProfile(s.events, s.parent?.scores);
      emit(
        'experience_assigned',
        {
          profile: s.experienceChoice || profile.dominant || 'estructurado',
          source: s.experienceChoice ? 'child_choice' : 'observed_preference',
        },
        key,
      );
      emit('task_presented', { skill, policy: p }, key);
      emit('adaptation_decision', { ...p, skill, isClinicalInference: false }, key);
      const latency = scenario.latency || 18000;
      s.mathMs += latency;
      s.blockMs += latency;
      if (scenario.interruptions && i % 4 === 1) {
        emit('idle_started', { thresholdMs: 45000 }, key);
        emit('visibility_hidden', {}, key);
        emit('idle_ended', {}, key);
        emit('visibility_visible', {}, key);
      }
      const wrong = scenario.struggle && i < 3,
        assisted = !!scenario.assisted || p.support === 'concrete';
      const answer = wrong ? [0, 1] : task.answer,
        correct = E.classify(task, answer) === 'correct';
      s.knowledge[skill] = E.updateKnowledge(s.knowledge[skill], correct, assisted);
      emit(
        'attempt',
        { skill, correct, answer, attemptNumber: 1, latencyMs: latency, assisted },
        key,
      );
      emit('knowledge_updated', { skill, assisted, posterior: s.knowledge[skill] }, key);
      if (wrong) {
        emit('hint_requested', { source: 'synthetic' }, key);
        s.mathMs += 1000;
        s.blockMs += 1000;
        emit(
          'attempt',
          {
            skill,
            correct: true,
            answer: task.answer,
            attemptNumber: 2,
            latencyMs: 1000,
            assisted: true,
          },
          key,
        );
      }
      if (s.blockMs >= E.sessionPolicy(s.events, s.simulationConfig).breakAfterMs) {
        emit('break_suggested', { reason: 'adaptive_active_duration' }, key);
        s.blockMs = 0;
        emit('math_resumed');
      }
      capture(
        wrong
          ? 'Error, ayuda y reintento'
          : assisted
            ? 'Respuesta con apoyo'
            : 'Respuesta independiente',
      );
    }
    const inferred = E.inferProfile(s.events, s.parent?.scores);
    const checks = [
      {
        name: 'Registros identificados como simulación',
        pass: s.events.every((e) => e.simulation === true),
      },
      {
        name: 'Prerrequisitos respetados',
        pass: s.events
          .filter((e) => e.type === 'task_presented')
          .every((e) => {
            const idx = s.events.indexOf(e),
              known = E.newKnowledge();
            s.events
              .slice(0, idx)
              .filter((x) => x.type === 'knowledge_updated')
              .forEach((x) => (known[x.data.skill] = x.data.posterior));
            return E.skills
              .find((k) => k.id === e.data.skill)
              .parents.every((k) => E.mastered(known[k]));
          }),
      },
    ];
    if ('expectedProfile' in scenario)
      checks.push({
        name: 'Inferencia prevista',
        pass: inferred.dominant === scenario.expectedProfile,
      });
    if (scenario.assisted)
      checks.push({
        name: 'Ayuda no acredita dominio',
        pass: Object.values(s.knowledge).every((k) => k.n === 0),
      });
    else
      checks.push({
        name: 'Alcanza las seis habilidades',
        pass: E.skills.every((k) => E.mastered(s.knowledge[k.id])),
      });
    if (scenario.struggle)
      checks.push({
        name: 'Apoyo aumenta y luego se retira',
        pass:
          timeline.some((t) => t.policy.support === 'concrete') &&
          timeline.at(-1).policy.support === 'pictorial',
      });
    if (scenario.latency)
      checks.push({
        name: 'Lentitud sola no activa apoyo concreto',
        pass: timeline.every((t) => t.policy.support === 'pictorial'),
      });
    return {
      schema: 'luma-simulation-1',
      simulation: true,
      scenario,
      options: s.simulationConfig,
      state: s,
      timeline,
      frames,
      checks,
    };
  }
  const api = { scenarios, run };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.LumaSimulation = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
