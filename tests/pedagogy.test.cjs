const {test}=require('node:test'),assert=require('node:assert/strict'),E=require('../engine.js');
test('CPA, transferencia y prerrequisitos requieren evidencia independiente; repetir con ayuda no certifica',()=>{
 const knowledge=E.newKnowledge(),learning=E.newLearning(knowledge);let serial=0;
 for(const skill of E.skills){
  for(const stage of E.stages){
   assert.equal(E.nextLearningSkill(knowledge,learning),skill.id);
   const t=E.learningTask(skill.id,serial++,learning);assert.equal(t.stage,stage);
   E.recordLearning(learning,t,true,true);assert(!learning.skills[skill.id].passed.includes(stage));
   let probe=E.learningTask(skill.id,serial++,learning);assert(probe.independentProbe);
   knowledge[skill.id]=E.updateKnowledge(knowledge[skill.id],true,false);E.recordLearning(learning,probe,true,false);
  }
  assert(E.learningComplete(skill.id,knowledge,learning));
 }
});
test('migración conserva dominio anterior y no inventa CPA ni borra conocimiento',()=>{
 const knowledge=E.newKnowledge();knowledge.meaning={p:.98,n:8,correct:7};const before=JSON.stringify(knowledge),learning=E.newLearning(knowledge);
 assert(E.learningComplete('meaning',knowledge,learning));assert.deepEqual(learning.skills.meaning.passed,[]);assert.equal(JSON.stringify(knowledge),before);
});
test('banco ampliado: resultados exactos y no negativos en las seis habilidades y cuatro etapas',()=>{
 for(const skill of E.skills)for(const stage of E.stages)for(let serial=0;serial<96;serial++){
  const l=E.newLearning(E.newKnowledge());l.skills[skill.id].passed=E.stages.slice(0,E.stages.indexOf(stage));
  const t=E.learningTask(skill.id,serial,l);assert(t.answer[0]>=0&&t.answer[1]>0);assert.equal(E.classify(t,t.answer),'correct');
  if(t.b)assert.equal(t.answer[0]*t.a[1]*t.b[1],t.answer[1]*(t.a[0]*t.b[1]+(t.op==='−'?-1:1)*t.b[0]*t.a[1]));
  assert.equal(t.stage,stage);if(stage==='transfer')assert.notEqual(t.context,'energy');
 }
});
