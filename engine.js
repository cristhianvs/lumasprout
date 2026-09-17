(function (root) {
  'use strict';
  const CONFIG = Object.freeze({version:'2026-09-prototype-1', playMs:300000, idleMs:45000, failures:3, mastery:.85, minEvidence:3});
  const profiles = ['estructurado','visual','auditivo','explorador'];
  const experiences = {
    estructurado:{name:'Laboratorio de pasos', verb:'Resolver por pasos', goal:'Revisa el entero, elige el tamaño de las partes y construye tu respuesta.'},
    visual:{name:'Estudio de mosaicos', verb:'Pintar mosaicos', goal:'Pinta la cantidad que responde al reto. Cada tablero completo vale un entero.'},
    auditivo:{name:'Estación de ritmos', verb:'Crear ritmos', goal:'Marca los pulsos que responden al reto. Cada compás completo vale un entero. También puedes jugar sin sonido.'},
    explorador:{name:'Ruta de energía', verb:'Llevar energía', goal:'Carga las piezas que necesita la expedición. Cada batería completa vale un entero.'}
  };
  const skills = [
    {id:'meaning', name:'Partes de un entero', parents:[]},
    {id:'equivalent', name:'Fracciones equivalentes', parents:['meaning']},
    {id:'add_same', name:'Sumar partes del mismo tamaño', parents:['meaning']},
    {id:'sub_same', name:'Restar partes del mismo tamaño', parents:['meaning']},
    {id:'add_diff', name:'Sumar con distintos denominadores', parents:['equivalent','add_same']},
    {id:'sub_diff', name:'Restar con distintos denominadores', parents:['equivalent','sub_same']}
  ];
  function gcd(a,b) { while(b) [a,b]=[b,a%b]; return Math.abs(a); }
  function same(a,b) { return a[0]*b[1]===b[0]*a[1]; }
  function parseFraction(value) {
    const m = String(value).trim().match(/^(\d{1,4})(?:\s*\/\s*(\d{1,4}))?$/);
    if (!m || Number(m[2] || 1)===0) return null;
    return [Number(m[1]),Number(m[2] || 1)];
  }
  function newKnowledge() { return Object.fromEntries(skills.map(s=>[s.id,{p:.5,n:0,correct:0}])); }
  function updateKnowledge(previous, correct, assisted) {
    if (assisted) return {...previous}; // El éxito con pistas no demuestra dominio independiente.
    const likelihoodKnown=correct?.9:.1, likelihoodUnknown=correct?.15:.85;
    const p = previous.p*likelihoodKnown / (previous.p*likelihoodKnown+(1-previous.p)*likelihoodUnknown);
    // Pequeña transición de aprendizaje después del intento; parámetros pendientes de calibración.
    return {p:Math.min(.99,Math.max(.01,p+(1-p)*.08)),n:previous.n+1,correct:previous.correct+Number(correct)};
  }
  const mastered = k => k.n>=CONFIG.minEvidence && k.p>=CONFIG.mastery;
  function nextSkill(knowledge) {
    const ready = skills.filter(s=>!mastered(knowledge[s.id]) && s.parents.every(id=>mastered(knowledge[id])));
    if (!ready.length) return skills.reduce((a,b)=>knowledge[a.id].p<knowledge[b.id].p?a:b).id;
    return ready.sort((a,b)=>{
      const score = s => {const k=knowledge[s.id]; return (1-k.p)*2 + (k.n===0?.5:0) + skills.filter(x=>x.parents.includes(s.id)).length*.1;};
      return score(b)-score(a);
    })[0].id;
  }
  function inferProfile(events, parent) {
    const score=Object.fromEntries(profiles.map(p=>[p,1]));
    let observations=0;
    // Una observación por contexto evita que pulsar repetidamente una ayuda
    // convierta una preferencia provisional en una etiqueta permanente.
    const seen=new Set();
    const recent=events.filter(e=>['support_selected','route_selected','creative_change','experience_selected'].includes(e.type)).slice(-80);
    for (const e of recent) {
      if(e.type==='support_selected'&&!e.data.voluntary)continue;
      const context=e.task||`${e.phase||'play'}:${e.scene??e.data.context??'unknown'}`;
      const key=`${context}:${e.type}:${e.data.mode||e.data.route||e.data.profile||''}`;
      if(seen.has(key))continue;seen.add(key);
      if(e.type==='experience_selected'&&profiles.includes(e.data.profile)){score[e.data.profile]+=1;observations++;}
      if(e.type==='support_selected' && e.data.voluntary) {
        const p={visual:'visual',audio:'auditivo',hands:'explorador'}[e.data.mode];
        if(p) {score[p]+=1; observations++;}
      }
      if(e.type==='route_selected') {score[e.data.route==='guided'?'estructurado':'explorador']+=1; observations++;}
      if(e.type==='creative_change') {score.visual+=.2; observations++;}
    }
    const total=Object.values(score).reduce((a,b)=>a+b,0);
    const behavior=Object.fromEntries(profiles.map(p=>[p,score[p]/total]));
    const validParent=parent && profiles.every(p=>Number.isFinite(parent[p]) && parent[p]>=0) && profiles.reduce((n,p)=>n+parent[p],0)>0;
    const pt=validParent?profiles.reduce((n,p)=>n+parent[p],0):1;
    const combined=Object.fromEntries(profiles.map(p=>[p,validParent?.6*behavior[p]+.4*parent[p]/pt:behavior[p]]));
    const ranked=[...profiles].sort((a,b)=>combined[b]-combined[a]);
    const sufficient=observations>=5 && combined[ranked[0]]-combined[ranked[1]]>=.06;
    return {behavior,combined,dominant:sufficient?ranked[0]:null,secondary:sufficient?ranked[1]:null,observations,provisional:!validParent,confidence:sufficient?'exploratoria':'evidencia insuficiente'};
  }
  function signals(events) {
    const last=events.at(-1), phase=last?.phase;
    const clock=phase==='play'?'playMs':'mathMs', now=last?.[clock];
    const recent=events.filter(e=>(!phase||e.phase===phase)&&(!Number.isFinite(now)||!Number.isFinite(e[clock])||now-e[clock]>=0&&now-e[clock]<=120000))
      .filter(e=>['attempt','hint_requested','idle_started','idle_ended'].includes(e.type)).slice(-20);
    const attempts=recent.filter(e=>e.type==='attempt'), errors=attempts.filter(e=>e.data?.correct===false).length;
    const hints=recent.filter(e=>e.type==='hint_requested').length, idle=recent.filter(e=>e.type==='idle_started').length;
    const latencies=attempts.map(e=>e.data?.latencyMs).filter(n=>Number.isFinite(n)&&n>=0).sort((a,b)=>a-b);
    const load=errors+hints;
    return {windowMs:120000,attempts:attempts.length,errors,hints,idle,accuracy:attempts.length?(attempts.length-errors)/attempts.length:null,
      medianLatencyMs:latencies.length?latencies[Math.floor(latencies.length/2)]:null,
      supportNeed:load>=4?'elevada':load>=2?'en observación':'sin señal suficiente',
      engagement:idle?'interrupción observada':attempts.length>=3?'participación observada':'evidencia insuficiente',
      anxiety:'no inferible',isClinicalInference:false};
  }
  function sessionPolicy(events, options={}) {
    const metrics=signals(events), gentle=options.pace==='gentle', elevated=metrics.supportNeed==='elevada';
    return {blockMs:elevated||gentle?60000:90000,breakAfterMs:elevated||gentle?240000:480000,support:elevated?'concrete':'pictorial',
      reason:elevated?'recent_errors_and_help':gentle?'simulation_gentle_pace':'standard_pace',metrics};
  }
  function makeTask(id, serial) {
    const ds=[4,6,8], d=ds[serial%ds.length];
    if(id==='meaning') {const n=1+serial%(d-1); return {id,kind:'meaning',a:[n,d],answer:[n,d],prompt:'¿Qué fracción del panel está iluminada?',hint:'El denominador cuenta todas las partes iguales; el numerador, las iluminadas.'};}
    if(id==='equivalent') {const n=1+serial%3; return {id,kind:'equivalent',a:[n,4],answer:[n*2,8],targetDen:8,prompt:'Escribe una fracción equivalente usando octavos.',hint:'Divide cada cuarto en dos partes iguales. El tamaño iluminado no cambia.'};}
    const subtract=id.startsWith('sub'), diff=id.endsWith('diff');
    const a=diff?[3,4]:[d-1,d], b=diff?[1,serial%2?2:8]:[1+serial%2,d];
    const den=a[1]*b[1], num=a[0]*b[1]+(subtract?-1:1)*b[0]*a[1], g=gcd(num,den);
    return {id,kind:'operation',a,b,op:subtract?'−':'+',answer:[num/g,den/g],prompt:subtract?'Retira la energía indicada. ¿Cuánta queda?':'Une la energía de ambos paneles. ¿Cuánta hay en total?',hint:diff?'Las piezas deben tener el mismo tamaño. Busca un denominador común antes de unirlas o retirarlas.':'Los denominadores iguales indican piezas del mismo tamaño. Opera los numeradores y conserva el denominador.'};
  }
  function classify(task, answer) {
    if(!answer) return 'invalid_format';
    if(task.targetDen && answer[1]!==task.targetDen && same(answer,task.answer)) return 'target_denominator';
    if(same(answer,task.answer)) return 'correct';
    if(task.b && answer[0]===task.a[0]+(task.op==='−'?-task.b[0]:task.b[0]) && answer[1]===task.a[1]+task.b[1]) return 'operates_denominators';
    if(task.b && task.a[1]!==task.b[1] && answer[1]===task.a[1]) return 'no_common_unit';
    if(answer[0]===task.answer[1] && answer[1]===task.answer[0]) return 'inverted_fraction';
    return 'other';
  }
  // La evidencia anterior se conserva, pero no se inventa evidencia CPA retrospectiva.
  const stages=['concrete','pictorial','abstract','transfer'];
  function newLearning(knowledge){return {version:1,skills:Object.fromEntries(skills.map(s=>[s.id,{passed:[],seen:[],probe:false,legacyMastered:mastered(knowledge[s.id])}]))};}
  function learningComplete(id,knowledge,learning){const k=learning?.skills[id];return mastered(knowledge[id])&&(!k||k.legacyMastered||stages.every(s=>k.passed.includes(s)));}
  function nextLearningSkill(knowledge,learning){return skills.find(s=>!learningComplete(s.id,knowledge,learning)&&s.parents.every(p=>learningComplete(p,knowledge,learning)))?.id||nextSkill(knowledge);}
  function learningTask(id,serial,learning){
    const k=learning.skills[id],stage=stages.find(s=>!k.passed.includes(s))||'transfer';
    const t=makeTask(id,serial);
    // Amplía operandos dentro de unidades representables por las cuatro modalidades.
    if(t.b){const d=[4,6,8][serial%3];t.a=id.endsWith('diff')?[2+serial%2,4]:[2+serial%(d-2),d];t.b=id.endsWith('diff')?[1,serial%2?2:8]:[1,d];const den=t.a[1]*t.b[1],n=t.a[0]*t.b[1]+(t.op==='−'?-1:1)*t.b[0]*t.a[1],g=gcd(n,den);t.answer=[n/g,den/g];}
    const context=stage==='transfer'?['recipe','garden','journey'][serial%3]:'energy';
    if(stage==='transfer'){
      const object={recipe:'una receta',garden:'el riego del jardín',journey:'una ruta'}[context];
      t.prompt=t.kind==='meaning'?`Para ${object}, se usan ${t.a[0]} de ${t.a[1]} partes iguales de un entero. ¿Qué fracción se usa?`:t.kind==='equivalent'?`Para ${object}, expresa ${t.a[0]}/${t.a[1]} de un entero usando octavos.`:`Para ${object}, hay ${t.a[0]}/${t.a[1]} de un entero y ${t.op==='−'?'se retiran':'se agregan'} ${t.b[0]}/${t.b[1]} del mismo entero. ¿Qué fracción ${t.op==='−'?'queda':'hay en total'}?`;
    }
    const fingerprint=JSON.stringify([id,t.a,t.b||null,t.op||null,context,stage]);
    return {...t,stage,context,itemVersion:'fractions-2',variantId:fingerprint,novel:!k.seen.includes(fingerprint),independentProbe:k.probe};
  }
  function recordLearning(learning,task,correct,assisted){
    const k=learning.skills[task.id];if(!task.stage)return;
    if(!k.seen.includes(task.variantId))k.seen.push(task.variantId);
    if(correct&&!assisted&&(task.novel||task.stage!=='transfer')){if(!k.passed.includes(task.stage))k.passed.push(task.stage);k.probe=false;}
    else k.probe=true;
  }
  const api={CONFIG,profiles,experiences,skills,gcd,same,parseFraction,newKnowledge,updateKnowledge,mastered,nextSkill,inferProfile,signals,sessionPolicy,makeTask,classify,stages,newLearning,learningComplete,nextLearningSkill,learningTask,recordLearning};
  if(typeof module!=='undefined'&&module.exports) module.exports=api; else root.Luma=api;
})(typeof globalThis!=='undefined'?globalThis:this);
