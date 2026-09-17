const {test}=require('node:test');
const assert=require('node:assert/strict');
const E=require('../engine.js');
test('fracciones: formato, enteros, ceros y equivalencia exacta',()=>{
 assert.deepEqual(E.parseFraction(' 2 / 4 '),[2,4]);
 assert.deepEqual(E.parseFraction('2'),[2,1]);
 for(const s of ['1/0','x','1.5','-1/2','1/2/3',''])assert.equal(E.parseFraction(s),null);
 assert(E.same([2,4],[1,2]));assert(!E.same([1,4],[1,2]));
});
test('el banco completo genera resultados matemáticos válidos',()=>{
 for(const skill of E.skills)for(let i=0;i<100;i++){
  const t=E.makeTask(skill.id,i);assert(t.answer[1]>0);assert(t.answer[0]>=0);
  if(t.b){const expected=[t.a[0]*t.b[1]+(t.op==='−'?-1:1)*t.b[0]*t.a[1],t.a[1]*t.b[1]];assert(E.same(t.answer,expected));}
  assert.equal(E.classify(t,t.answer),'correct');
 }
});
test('errores frecuentes y representación solicitada',()=>{
 assert.equal(E.classify(E.makeTask('add_same',0),[4,8]),'operates_denominators');
 assert.equal(E.classify(E.makeTask('equivalent',0),[1,4]),'target_denominator');
 assert.equal(E.classify(E.makeTask('equivalent',0),[2,8]),'correct');
 assert.equal(E.classify(E.makeTask('meaning',0),[4,1]),'inverted_fraction');
});
test('una respuesta con ayuda no aumenta ni reduce dominio',()=>{
 const initial={p:.5,n:0,correct:0};
 assert.deepEqual(E.updateKnowledge(initial,true,true),initial);
 assert.deepEqual(E.updateKnowledge(initial,false,true),initial);
 const one=E.updateKnowledge(initial,true,false);assert(!E.mastered(one));
 const three=E.updateKnowledge(E.updateKnowledge(one,true,false),true,false);assert(E.mastered(three));
 assert(E.updateKnowledge(three,false,false).p<three.p);
});
test('el selector respeta prerrequisitos y no fuerza habilidades avanzadas por edad',()=>{
 const k=E.newKnowledge();assert.equal(E.nextSkill(k),'meaning');
 k.meaning={p:.99,n:3,correct:3};
 for(let i=0;i<20;i++){
  const id=E.nextSkill(k),skill=E.skills.find(s=>s.id===id);
  assert(skill.parents.every(p=>E.mastered(k[p])));
  k[id]=E.updateKnowledge(k[id],true,false);
 }
});
test('sin observaciones no hay perfil dominante ni datos familiares inventados',()=>{
 const p=E.inferProfile([],null);assert.equal(p.dominant,null);assert.equal(p.provisional,true);
 assert.deepEqual(p.behavior,p.combined);
});
test('la ayuda automática no se interpreta como preferencia',()=>{
 const events=Array.from({length:20},()=>({type:'support_selected',data:{mode:'audio',voluntary:false}}));
 assert.equal(E.inferProfile(events,null).observations,0);
});
test('triangulación 60/40 solo con vector familiar válido',()=>{
 const events=Array.from({length:8},()=>({type:'support_selected',data:{mode:'visual',voluntary:true}}));
 const parent={estructurado:1,visual:1,auditivo:6,explorador:2};
 const p=E.inferProfile(events,parent);assert.equal(p.provisional,false);
 assert(Math.abs(p.combined.visual-(.6*p.behavior.visual+.4*.1))<1e-12);
 assert.equal(E.inferProfile(events,{visual:1}).provisional,true);
});
test('las pausas y ayudas modifican la duración sugerida, no el conocimiento',()=>{
 const high=E.sessionPolicy([]),low=E.sessionPolicy(Array.from({length:4},()=>({type:'hint_requested'})));
 assert(low.breakAfterMs<high.breakAfterMs);assert.equal(low.blockMs,60000);
});

test('los cuatro perfiles se infieren con evidencia de contextos distintos',()=>{
 for(const profile of E.profiles){
  const events=Array.from({length:8},(_,i)=>({type:'experience_selected',task:`task-${i}`,data:{profile}}));
  const result=E.inferProfile(events,null);
  assert.equal(result.dominant,profile);assert.equal(result.observations,8);
 }
});
test('clics repetidos y evidencia mixta no fuerzan un perfil',()=>{
 const repeated=Array.from({length:30},()=>({type:'experience_selected',task:'same',data:{profile:'visual'}}));
 assert.equal(E.inferProfile(repeated,null).dominant,null);
 assert.equal(E.inferProfile(repeated,null).observations,1);
 const mixed=Array.from({length:20},(_,i)=>({type:'experience_selected',task:`task-${i}`,data:{profile:E.profiles[i%4]}}));
 assert.equal(E.inferProfile(mixed,null).dominant,null);
});
test('evidencia reciente puede cambiar la preferencia y la ayuda automática no tapa la voluntaria',()=>{
 const events=Array.from({length:90},(_,i)=>({type:'experience_selected',task:`task-${i}`,data:{profile:i<10?'visual':'auditivo'}}));
 assert.equal(E.inferProfile(events,null).dominant,'auditivo');
 assert.equal(E.inferProfile([{type:'support_selected',task:'a',data:{mode:'audio',voluntary:false}},{type:'support_selected',task:'a',data:{mode:'audio',voluntary:true}}],null).observations,1);
});
