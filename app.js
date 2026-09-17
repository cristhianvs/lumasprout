/* Isla Luma: sin servicios externos. Datos y progreso permanecen en este navegador. */
'use strict';
const E=window.Luma, $=s=>document.querySelector(s), SIMULATION=new URLSearchParams(location.search).get('simulation')==='1', KEY=SIMULATION?'isla-luma-simulation-v1':'isla-luma-v1';
const adaptationPolicy=()=>E.sessionPolicy(state.events,SIMULATION?state.simulationConfig||{}:{});
const fresh=()=>({version:E.CONFIG.version,simulation:SIMULATION,runId:crypto.randomUUID(),phase:'welcome',playMs:0,mathMs:0,blockMs:0,events:[],knowledge:E.newKnowledge(),serial:0,round:0,route:null,parent:null,garden:['🌿','🌼','🌿'],sound:false,current:null});
let state;
try{state=JSON.parse(localStorage.getItem(KEY))||fresh();if(state.version!==E.CONFIG.version)state=fresh();}catch{state=fresh();}
state.learning??=E.newLearning(state.knowledge);
state.microBlock??={startedAt:state.mathMs,tasks:[]};
let readingUntil=0;
// Recupera también los aciertos de partidas anteriores a la progresión por objetivos.
state.playProgress??={rescued:[...new Set(state.events.filter(e=>e.type==='attempt'&&e.data.activity==='shelter'&&e.data.correct).map(e=>e.data.choice))],signals:Math.min(3,state.events.filter(e=>e.type==='attempt'&&e.data.activity==='signal'&&e.data.correct).length),gardenActions:0};
let session=crypto.randomUUID(),paused=false,hidden=document.hidden,lastTick=performance.now(),lastInput=performance.now(),idle=false,sceneIndex=-1,selection=null,sequence=[],taskOpened=0,lastError=null,moves=0,moveDistance=0,point=null,storageError=false;
let supportMode='visual',failures=0,assisted=false,firstAttempt=true,solved=false,sandboxColor=0,interactionType='unknown',attemptNumber=0,exposure=null;
let rhythmContext=null;
const scenes=[{at:0,name:'Un lugar por descubrir',tag:'EL DESPERTAR',label:'Explora la isla',text:'Soy Luma. La tormenta dejó nuestra isla un poco dormida. ¿Me acompañas a despertarla?'},{at:60000,name:'El refugio de las hojas',tag:'EL INVERNADERO',label:'Encuentra un refugio',text:'Cada criatura tiene un refugio con su misma señal. Elige una criatura y después toca su refugio.'},{at:150000,name:'Una señal entre las nubes',tag:'LA ESTACIÓN',label:'Reconecta la señal',text:'Las señales de la antena se desordenaron. Toca los símbolos siguiendo el camino que aparece arriba.'},{at:240000,name:'Tu rincón de la isla',tag:'EL JARDÍN',label:'Crea a tu manera',text:'La isla vuelve a respirar. Ahora haz tuyo este rincón: cambia las plantas, descubre sonidos o sigue explorando.'}];
const shapes=['<path d="M16 10C6-4-4 9 7 16C-4 23 6 36 16 23C26 36 36 23 25 16C36 9 26-4 16 10Z"/><circle cx="16" cy="16" r="4" fill="#fff8de"/>','<path d="M24 3A14 14 0 1 0 24 29A15 15 0 0 1 24 3Z"/>','<path d="M16 2L29 16L16 30L3 16Z"/>'];
const icons=shapes.map(s=>`<svg class="glyph" viewBox="0 0 32 32" aria-hidden="true" focusable="false">${s}</svg>`), words=['flor','luna','rombo'];
function creature(j){return `<svg class="creature-art" viewBox="0 0 100 100" aria-hidden="true" focusable="false"><path d="M49 23Q24 23 26 7Q44 4 50 20Q55 0 76 9Q72 24 52 24" fill="#507a56"/><path d="M18 76Q9 29 50 23Q91 29 82 76Q74 95 50 91Q25 94 18 76Z" fill="#eed691" stroke="#8b784b" stroke-width="2"/><circle cx="33" cy="44" r="3" fill="#263e39"/><circle cx="67" cy="44" r="3" fill="#263e39"/><path d="M45 49Q50 54 55 49" fill="none" stroke="#263e39" stroke-width="2"/><g transform="translate(36 58) scale(.85)" fill="#356e56">${shapes[j]}</g></svg>`;}
function shelter(j){return `<svg class="shelter-art" viewBox="0 0 100 100" aria-hidden="true" focusable="false"><path d="M16 44L50 15L84 44V89H16Z" fill="#fff8de" stroke="#47745b" stroke-width="3"/><path d="M8 45L50 9L92 45" fill="none" stroke="#47745b" stroke-width="7" stroke-linecap="round"/><g transform="translate(34 49)" fill="#356e56">${shapes[j]}</g></svg>`;}
const esc=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function save(){if(state.phase==='math'&&state.current){Object.assign(state.current,{assisted,firstAttempt,solved,failures,supportMode,attemptNumber,taskOpened});}try{localStorage.setItem(KEY,JSON.stringify(state));storageError=false;}catch{storageError=true;}}
function log(type,data={}){state.events.push({id:`${session}:${state.events.length}`,session,runId:state.runId,version:E.CONFIG.version,schemaVersion:'1.3',policyVersion:'cpa-1',simulation:SIMULATION,experience:state.phase==='math'?(state.current?.experience||null):null,type,at:new Date().toISOString(),playMs:Math.round(state.playMs),mathMs:Math.round(state.mathMs),phase:state.phase,scene:state.phase==='play'?sceneIndex:null,task:state.current?.key||null,data});save();return state.events.at(-1);}
function announce(text){$('#live').textContent=text;}
function message(text){const box=$('#feedback');if(box)box.textContent=text;const inline=$('#feedback-inline');if(inline)inline.textContent=text;announce(text);}
function rememberFocus(){const d=document.activeElement?.dataset;return d?.action?`[data-action="${d.action}"]${d.index!==undefined?`[data-index="${d.index}"]`:''}${d.mode?`[data-mode="${d.mode}"]`:''}${d.place?`[data-place="${d.place}"]`:''}`:null;}
function restoreFocus(selector){if(selector)$(selector)?.focus?.({preventScroll:true});}
function active(){return ['play','math'].includes(state.phase)&&!paused&&!hidden;}
function elapsed(){return state.phase==='play'?state.playMs:state.mathMs;}
function markTask(){taskOpened=elapsed();lastError=null;failures=0;selection=null;sequence=[];assisted=false;attemptNumber=0;}
function flushExposure(reason){if(!exposure)return;const now=exposure.phase==='play'?state.playMs:state.mathMs;log('support_exposure',{mode:exposure.mode,voluntary:exposure.voluntary,activeMs:Math.max(0,Math.round(now-exposure.start)),reason,sourcePhase:exposure.phase,sourceTask:exposure.task,sourceScene:exposure.scene});exposure.start=now;}
function respondToSupportSignals(){
 const recent=state.events.filter(e=>e.phase===state.phase && elapsed()-(state.phase==='play'?e.playMs:e.mathMs)<=60000);
 const hints=recent.filter(e=>e.type==='hint_requested').length;
 const samples=recent.filter(e=>e.type==='attempt').slice(-5).map(e=>e.data.latencyMs);
 const average=samples.reduce((a,b)=>a+b,0)/(samples.length||1);
 const variation=average?Math.sqrt(samples.reduce((a,b)=>a+(b-average)**2,0)/samples.length)/average:0;
 const reason=hints>=3?'repeated_help_requests':samples.length>=5&&variation>1?'variable_response_latency':null;
 if(reason&&!recent.some(e=>e.type==='adaptation'&&e.data.rule===reason)){
  log('adaptation',{rule:reason,action:'offer_concrete_support',isClinicalInference:false});
  chooseSupport('hands',false);
 }
}
function interaction(event){if(!active())return;lastInput=performance.now();interactionType=event.pointerType|| (event.type==='keydown'?'keyboard':interactionType);if(idle){idle=false;log('idle_ended');}if(lastError!==null){log('post_error_action',{action:event.target.closest('[data-action]')?.dataset.action||event.type,latencyMs:Math.round(elapsed()-lastError)});lastError=null;}}
document.addEventListener('pointerdown',interaction,true);document.addEventListener('keydown',interaction,true);
document.addEventListener('pointermove',e=>{if(!active())return;moves++;if(point)moveDistance+=Math.hypot(e.clientX-point.x,e.clientY-point.y);point={x:e.clientX,y:e.clientY};});
function flushMotion(){if(moves){log('interaction_summary',{moveEvents:moves,distancePx:Math.round(moveDistance),input:interactionType});moves=0;moveDistance=0;point=null;}}
function world(){return `<svg class="world" viewBox="0 0 600 520" role="img" aria-label="Una isla verde entre nubes, con un invernadero, una antena y un jardín"><defs><linearGradient id="sky" x2="0" y2="1"><stop stop-color="#d7e5d8"/><stop offset="1" stop-color="#ecedce"/></linearGradient><linearGradient id="land" x2="0" y2="1"><stop stop-color="#b0c780"/><stop offset="1" stop-color="#6d965d"/></linearGradient></defs><rect x="20" y="15" width="560" height="485" rx="180" fill="url(#sky)"/><circle cx="448" cy="112" r="40" fill="#f5e7a8"/><g fill="#f7f8e9" opacity=".85"><ellipse cx="115" cy="120" rx="67" ry="17"/><ellipse cx="141" cy="104" rx="36" ry="28"/><ellipse cx="470" cy="361" rx="79" ry="21"/><ellipse cx="435" cy="343" rx="30" ry="26"/></g><path d="M92 338Q276 290 505 335L404 429 280 474 168 420Z" fill="#8c8f64"/><path d="M92 338L179 397 280 474 248 376Z" fill="#6f8059"/><path d="M280 474L363 381 505 335 404 429Z" fill="#a5a175"/><ellipse cx="298" cy="324" rx="211" ry="88" fill="url(#land)"/><path d="M158 333Q320 255 431 333" fill="none" stroke="#e4dcae" stroke-width="21" stroke-linecap="round"/><path d="M274 320Q262 350 326 379" fill="none" stroke="#e4dcae" stroke-width="17"/><g stroke="#43715c" stroke-width="5" stroke-linejoin="round"><path d="M179 302V219L241 167 303 219V302Z" fill="#d5e2b5"/><path d="M179 219H303M241 168V302M179 256H303" fill="none"/><path d="M164 224L241 158 316 224" fill="none" stroke="#315b49" stroke-width="9"/><path d="M213 303V265H269V303" fill="#a3c98c"/></g><g fill="#38664d"><path d="M136 295L123 296V236H136Z"/><ellipse cx="130" cy="226" rx="31" ry="44"/><path d="M465 315H454V267H465Z"/><ellipse cx="460" cy="249" rx="28" ry="36"/></g><g transform="translate(370 207)"><path d="M-4 90L8 7 27 90" stroke="#6b7965" stroke-width="7" fill="none"/><path d="M-6 7Q30 36 43-12Z" fill="#e9e4c4" stroke="#798b70" stroke-width="4"/><path d="M27 5L42-16" stroke="#5d755e" stroke-width="4"/><circle cx="44" cy="-18" r="6" fill="#d68559"/><path d="M50-35Q76-30 76-6M54-47Q93-41 93-4" fill="none" stroke="#91aa80" stroke-width="3"/></g><g transform="translate(306 334)"><ellipse cx="0" cy="27" rx="25" ry="8" fill="#71905a" opacity=".4"/><path d="M-22 12Q-26-23 0-27Q28-24 22 12Z" fill="#f0d994"/><circle cx="-8" cy="-5" r="3" fill="#345744"/><circle cx="8" cy="-5" r="3" fill="#345744"/><path d="M-5 7Q0 12 5 7" fill="none" stroke="#345744" stroke-width="2"/><path d="M0-25Q-12-42-24-31Q-12-22 0-25Q12-46 25-37Q17-23 0-25" fill="#507f53"/></g><g fill="#e6af81"><circle cx="183" cy="341" r="7"/><circle cx="410" cy="349" r="6"/><circle cx="394" cy="362" r="8"/></g><g fill="#f4edc4"><circle cx="147" cy="325" r="4"/><circle cx="351" cy="303" r="5"/><circle cx="228" cy="349" r="4"/></g><path d="M66 215l8-8 8 8M474 165l7-7 7 7" fill="none" stroke="#698570" stroke-width="3"/></svg>`;}
function fraction(a){return `<span class="fraction"><span>${a[0]}</span><span>${a[1]}</span></span>`;}
function supports(){const order=Number.parseInt(state.runId.slice(0,2),16)%3;const modes=[['visual','◉','Ver una pista'],['audio','♫','Escuchar'],['hands','✋','Probar con Luma']];return `<div class="support-row" aria-label="Elige una ayuda">${[...modes.slice(order),...modes.slice(0,order)].map(([m,i,t])=>`<button data-action="support" data-mode="${m}" aria-pressed="${supportMode===m}">${i} ${t}</button>`).join('')}</div>`;}
function buddy(){return `<div class="buddy"><span class="buddy-face" aria-hidden="true">•ᴗ•</span><div><b>Luma</b><small>Tu compañera de aventuras</small></div></div>`;}
function render(){
  $('#pause').hidden=!['play','math'].includes(state.phase);$('#sound').textContent=state.sound?'Sonido encendido':'Sonido apagado';$('#sound').setAttribute('aria-pressed',String(state.sound));
  if(state.phase==='welcome')renderWelcome();else if(state.phase==='play')renderPlay();else if(state.phase==='bridge')renderBridge();else if(state.phase==='math')renderMath();else renderComplete();
}
function renderWelcome(){
 $('#app').innerHTML=`<section class="hero"><div class="hero-copy"><div class="eyebrow"><span class="dot"></span> UNA AVENTURA A TU MANERA</div><h1>Despierta<br><em>Isla Luma.</em></h1><p>La tormenta apagó la isla. Ayuda a Luma a encontrar refugios, conectar la antena y crear un jardín.</p><button class="primary" data-action="start">Explorar con Luma <span aria-hidden="true">↗</span></button><p class="tiny">Empieza jugando unos cinco minutos. Sin calificaciones.</p></div><div class="art">${world()}<span class="caption">✦ Tu próxima aventura está aquí</span></div></section><section class="feature-strip"><div class="feature"><span class="feature-icon">⌁</span><div><b>Tu propio camino</b><p>Explora, escucha o prueba con tus manos.</p></div></div><div class="feature"><span class="feature-icon">❀</span><div><b>Siempre puedes volver a intentar</b><p>Luma te acompaña cuando lo necesitas.</p></div></div><div class="feature"><span class="feature-icon">☀</span><div><b>Cada descubrimiento cuenta</b><p>Después, despierta el taller de fracciones.</p></div></div></section>`;
}
function renderPlay(){
 const focus=rememberFocus();
 const i=Math.max(state.playStage||0,scenes.reduce((n,s,j)=>state.playMs>=(j===1?(state.refugeAt??s.at):s.at)?j:n,0));if(i!==sceneIndex){flushExposure('scene_change');exposure=null;if(sceneIndex>=0)log('scene_left',{scene:sceneIndex,reason:'active_time_or_child_choice'});sceneIndex=i;markTask();supportMode='visual';log('scene_entered',{scene:i,availableModes:['visual','audio','hands'],positionCounterbalance:Number.parseInt(state.runId.slice(0,2),16)%3});}
 const s=scenes[i];
 let scene='';
 if(i===0)scene=`${world()}<div class="island-places">${[['greenhouse','Invernadero'],['station','Estación'],['garden','Jardín']].map(([id,name])=>`<button class="place ${(state.visits||[]).includes(id)?'visited':''}" data-action="place" data-place="${id}">${name}${(state.visits||[]).includes(id)?' ✓':''}</button>`).join('')}</div>`;
 if(i===1){const target=refugeTarget();scene=`<div class="target creature-target" aria-label="Criatura con señal de ${words[target]}">${creature(target)}<small>Busca a esta criatura: <strong>${words[target]}</strong></small></div><p class="scene-label">${selection===null?'ELIGE LA CRIATURA DE ARRIBA':'CRIATURA ELEGIDA: '+words[selection].toUpperCase()}</p><div class="choice-grid">${icons.map((x,j)=>`<button class="object ${selection===j?'selected':''}" data-action="creature" data-index="${j}" aria-pressed="${selection===j}" aria-label="Elegir criatura ${words[j]}">${creature(j)}<small>${words[j]}</small></button>`).join('')}</div><p class="scene-label">AHORA TOCA EL REFUGIO CON LA MISMA SEÑAL</p><div class="choice-grid">${[2,0,1].map(j=>`<button class="object" data-action="shelter" data-index="${j}" aria-label="Refugio ${words[j]}">${shelter(j)}<small>${words[j]}</small></button>`).join('')}</div>`;}
 if(i===2){const pattern=antenna();scene=`<div class="scene-label">COPIA ESTE CAMINO, DE IZQUIERDA A DERECHA</div><div class="steps" aria-label="Señal: ${pattern.map(j=>words[j]).join(', ')}">${pattern.map(j=>icons[j]).join(' <span aria-hidden="true">→</span> ')}</div><div class="target" aria-label="Tu señal"><div class="signal-slots">${pattern.map((_,k)=>`<span class="signal-slot">${sequence[k]!==undefined?icons[sequence[k]]:'<span aria-hidden="true">·</span>'}</span>`).join('')}</div><small>${sequence.length===3?'Tu camino está listo. Toca «Enviar señal».':'Toca los símbolos de abajo para completar tu camino.'}</small></div><div class="choice-grid">${[1,2,0].map(j=>`<button class="object" data-action="signal" data-index="${j}" aria-label="Añadir ${words[j]}"><span class="symbol">${icons[j]}</span><small>${words[j]}</small></button>`).join('')}</div><div class="actions"><button data-action="undo" ${sequence.length===0?'disabled':''}>Deshacer</button><button class="primary" data-action="send">Enviar señal</button></div>`;}
 if(i===3)scene=`<div class="garden" style="filter:hue-rotate(${sandboxColor}deg)">${state.garden.map((x,j)=>`<button class="object" data-action="plant" data-index="${j}" aria-label="Cambiar planta del ${['lado izquierdo','centro','lado derecho'][j]}"><span class="symbol">${x}</span></button>`).join('')}</div><div class="route-actions"><button data-action="color">Cambiar ambiente</button><button data-action="garden_sound">Escuchar el jardín</button><button data-action="garden_guide">Una idea de Luma</button></div>`;
 const complete=(i===1&&state.playProgress.rescued.length>=3)||(i===2&&state.playProgress.signals>=3);
 if(complete)scene=`<div class="scene-complete"><div class="completion-art">${i===1?creature(0)+creature(1)+creature(2):icons.join('')}</div><p class="eyebrow">MISIÓN COMPLETADA</p><h3>${i===1?'¡Todas las criaturas están a salvo!':'¡La antena ya está conectada!'}</h3><p>${i===1?'Cada una encontró su refugio. Sigamos con una misión diferente.':'Las señales llegaron. Ahora puedes crear tu jardín.'}</p><button class="primary" data-action="next_scene">${i===1?'Ir a la estación →':'Ir al jardín →'}</button></div>`;
 if(i===1&&!complete)scene=`<div class="mission-progress" aria-label="Criaturas rescatadas">${words.map((word,j)=>`<span class="${state.playProgress.rescued.includes(j)?'done':''}">${word}${state.playProgress.rescued.includes(j)?' ✓':''}</span>`).join('')}</div>`+scene;
 if(i===2&&!complete)scene=`<p class="mission-progress">${['Conecta el invernadero','Conecta el taller','Conecta el jardín'][state.playProgress.signals]}</p>`+scene;
 if(i===3)scene+=`<div class="actions"><button class="primary" data-action="finish_play">Terminar mi jardín y continuar →</button></div>`;
 const instruction=complete?'Tu misión está lista. Pulsa el botón para seguir.':['Toca los lugares de la isla para conocerlos. Después visitaremos el invernadero.','Cada criatura necesita un refugio. Las que ya ayudaste quedan marcadas y no se repiten.','Conecta los lugares de la isla copiando cada camino. Después envía la señal.','Crea tu jardín y, cuando esté como te gusta, pulsa «Terminar mi jardín y continuar».'][i];
 $('#app').innerHTML=`<div class="game-top"><div><p class="eyebrow">ISLA LUMA / ${s.tag}</p><h2>${s.name}</h2></div><span class="chapter">${['Conoce la isla','Ayuda a las criaturas','Conecta la antena','Crea tu jardín'][i]}</span></div><p class="mission-instruction">${instruction}</p><div id="feedback-inline" class="mobile-feedback" aria-live="polite"></div><div class="game-layout"><section class="scene" aria-label="${s.label}">${scene}</section><aside class="side">${buddy()}<h3>${s.label}</h3><p>${s.text}</p>${i===0?`<div class="route-actions"><button data-action="route" data-route="guided" ${state.route==='guided'?'class="secondary"':''}>Guíame, Luma</button><button data-action="route" data-route="free" ${state.route==='free'?'class="secondary"':''}>Quiero explorar</button></div>`:''}${supports()}<div id="feedback" class="message" role="status">${i===0?'Aquí no hay prisa. Puedes visitar cualquier rincón.':i===3?'No hay una respuesta correcta. Este lugar es tuyo.':'Puedes probar de nuevo todas las veces que quieras.'}</div><button class="quiet" data-action="hint">Dame una pista</button></aside></div>`;
 if(complete){$('.side').innerHTML=`${buddy()}<h3>Misión completada</h3><p>Lo lograste. Esta misión ya está guardada y no necesitas repetirla.</p><div id="feedback" class="message" role="status">${i===1?'Continúa hacia la estación.':'Continúa hacia el jardín.'}</div>`;$('[data-action="next_scene"]')?.focus?.({preventScroll:true});}
 else restoreFocus(focus);
 if(i===0&&(state.visits||[]).length===3){const go=document.createElement('button');go.className='primary';go.dataset.action='enter_refuge';go.textContent='Ir al invernadero →';$('.side').append?.(go);}
}
function refugeTarget(){return [0,1,2].find(j=>!state.playProgress.rescued.includes(j))??0;}
function antenna(){return [[0,2,1],[1,0,2],[2,1,0]][Math.min(2,state.playProgress.signals)];}
function finishPlay(reason){flushMotion();flushExposure('playtest_completed');exposure=null;log('playtest_completed',{durationMs:state.playMs,reason,completedObjectives:{...state.playProgress}});state.phase='bridge';state.current=null;render();}
function audio(text){
 if((SIMULATION&&state.simulationConfig?.noAudio)||typeof window.speechSynthesis?.speak!=='function'){log('support_unavailable',{mode:'audio',reason:'unsupported'});message(text+' Puedes seguir la pista escrita.');return false;}
 state.sound=true;$('#sound').textContent='Sonido encendido';$('#sound').setAttribute('aria-pressed','true');speechSynthesis.cancel();const utterance=new SpeechSynthesisUtterance(text);utterance.lang='es-MX';utterance.rate=.9;utterance.onend=()=>log('audio_completed');utterance.onerror=e=>{log('support_unavailable',{mode:'audio',reason:e.error});message('El audio no pudo reproducirse. La misma pista está disponible por escrito.');};speechSynthesis.speak(utterance);log('audio_started',{language:'es-MX'});return true;
}
function hintText(){if(state.phase==='math')return state.current.task.hint;if(sceneIndex===0)return state.route==='guided'?'Visita primero el invernadero. Después puedes conocer la estación y el jardín.':'Toca uno de los lugares de la isla para descubrir qué hay allí.';if(sceneIndex===1)return `Elige la criatura con ${words[refugeTarget()]} y después el refugio con esa misma señal.`;if(sceneIndex===2)return `Sigue este camino: ${antenna().map(j=>words[j]).join(', ')}.`;return 'Toca las plantas para cambiarlas. Prueba un ambiente distinto y escucha cómo suena el jardín.';}
function chooseSupport(mode,voluntary=true){
 const text=hintText(),requestedMode=mode,unavailable=mode==='audio'&&!audio(text);
 if(unavailable)mode='visual';
 flushExposure('channel_switch');exposure={mode,voluntary,phase:state.phase,start:elapsed(),task:state.current?.key||null,scene:sceneIndex};
 supportMode=mode;assisted=true;log('support_selected',{mode,requestedMode,voluntary:voluntary&&!unavailable,previousFailures:failures,reason:unavailable?'audio_unavailable':undefined});
 if(state.phase==='math'){assisted=true;log('scaffold_shown',{representation:mode==='hands'?'concrete':mode==='audio'?'audio':'pictorial',reason:voluntary?'student_choice':'adaptive'});renderMath();}
 if(mode==='hands'&&state.phase==='play'){
  if(sceneIndex===1){selection=refugeTarget();renderPlay();}
  if(sceneIndex===2){sequence=[antenna()[0]];renderPlay();}
 }
 message(unavailable?text+' Puedes seguir la pista escrita.':mode==='hands'?'Empecemos juntos. '+text:text);
 document.querySelectorAll('[data-action="support"]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.mode===mode)));
}
function recordAttempt(correct,data={}){
 attemptNumber++;log('attempt',{correct,attemptNumber,latencyMs:Math.round(elapsed()-taskOpened),input:interactionType,representation:supportMode,decisionId:state.current?.decisionId||null,itemVersion:state.current?.task?.itemVersion||'legacy',variantId:state.current?.task?.variantId||null,cpaPhase:state.phase==='math'?(assisted?(supportMode==='hands'?'concrete':'pictorial'):(state.current?.task?.stage||'pictorial')):'not_applicable',plannedStage:state.current?.task?.stage||null,assisted,...data});
 taskOpened=elapsed();
 if(correct){failures=0;lastError=null;}else{failures++;lastError=elapsed();if(failures>=E.CONFIG.failures){log('adaptation',{rule:'three_failures',action:'offer_concrete_support',isClinicalInference:false});chooseSupport('hands',false);}}
 respondToSupportSignals();
}
function renderBridge(){
 const profile=E.inferProfile(state.events,state.parent?.scores);state.profile=profile;save();
 $('#app').innerHTML=`<section class="center"><div class="art" style="max-width:300px;margin:auto">${world()}</div><p class="eyebrow">LA ISLA YA TE CONOCE UN POCO</p><h2>Ahora, encendamos<br>el taller.</h2><p>Vamos a jugar con piezas de energía. Empezaremos con algo pequeño y encontraremos juntos tu siguiente reto.</p><div class="actions"><button class="primary" data-action="math_start">Entrar al taller ↗</button><button data-action="rest">Descansar un momento</button></div></section>`;
}
function startTask(){
 flushExposure('task_change');exposure=null;
 const id=E.nextLearningSkill(state.knowledge,state.learning);state.current={key:`${id}-${state.serial}`,task:E.learningTask(id,state.serial,state.learning)};state.serial++;markTask();firstAttempt=true;solved=false;assisted=false;
 const profile=E.inferProfile(state.events,state.parent?.scores);state.profile=profile;supportMode='visual';
 const previous=state.lastExperience;state.current.experience=state.experienceChoice||profile.dominant||'estructurado';state.lastExperience=state.current.experience;
 log('experience_assigned',{profile:state.current.experience,previous,source:state.experienceChoice?'child_choice':profile.dominant?'observed_preference':'insufficient_evidence_default',inference:profile,isClinicalInference:false});
 log('task_presented',{item:state.current.task,skill:id,selection:'prerequisites_and_stage_coverage',prior:state.knowledge[id],experience:state.current.experience,representation:supportMode,policy:adaptationPolicy()});save();
 const decision=adaptationPolicy(),t=state.current.task;const evidenceIds=state.events.filter(e=>e.phase==='math'&&state.mathMs-e.mathMs<=120000&&['attempt','hint_requested','idle_started','idle_ended'].includes(e.type)).slice(-20).map(e=>e.id);
 state.current.decisionId=log('adaptation_decision',{...decision,experience:state.current.experience,skill:id,stage:t.stage,independentProbe:t.independentProbe,effectiveSupport:t.independentProbe?'independent_opportunity':decision.support,evidenceIds,parentResponse:state.parent?.response||null,parentResponseUse:'context_only_unvalidated',appliesAt:'task_boundary',isClinicalInference:false}).id;
 log('experience_options_offered',{options:E.profiles,selected:state.current.experience});save();
 if(decision.support==='concrete'&&!state.current.task.independentProbe){supportMode='hands';assisted=true;log('scaffold_shown',{representation:'concrete',reason:decision.reason});}
}
function closeLearningBlock(){const b=state.microBlock;b.tasks.push(state.current.key);const duration=state.mathMs-b.startedAt,policy=adaptationPolicy();if(duration>=policy.blockMs){log('learning_block_completed',{tasks:[...b.tasks],activeMs:duration,targetMs:policy.blockMs,reason:'duration_at_task_boundary'});state.microBlock={startedAt:state.mathMs,tasks:[]};state.blockNotice=true;}}
function bar(a,cls=''){return `<div class="bar" aria-label="${a[0]} de ${a[1]} partes iluminadas">${Array.from({length:a[1]},(_,i)=>`<span class="piece ${i<a[0]?'filled '+cls:''}"></span>`).join('')}</div>`;}
function renderMath(){
 const focus=rememberFocus();
 if(!state.current)startTask();const t=state.current.task,skill=E.skills.find(s=>s.id===t.id);const policy=adaptationPolicy();
 let graphics=`<p class="bar-caption">${t.b?'Panel inicial':'Un entero dividido en partes iguales'}</p>`+bar(t.a);if(t.b)graphics+=`<div class="bar-caption">${t.op==='−'?'Energía que se retira':'Energía que se agrega'}</div>${bar(t.b,'b')}`;
 if(['abstract','transfer'].includes(t.stage)&&!assisted)graphics=t.kind==='meaning'?`<p class="task-facts">Partes usadas: ${t.a[0]}. Partes iguales del entero: ${t.a[1]}.</p>`:'';
 if(t.kind==='equivalent'&&(!['abstract','transfer'].includes(t.stage)||assisted))graphics+=`<p class="bar-caption">El mismo entero, dividido en octavos</p>${bar([0,8])}`;
 if(supportMode==='hands'){
 const denominator=t.b?t.a[1]*t.b[1]/E.gcd(t.a[1],t.b[1]):(t.targetDen||t.a[1]);const rows=t.b&&t.op==='+'&&t.answer[0]>t.answer[1]?2:1;
 state.current.workspaceDen=denominator;state.current.workspaceSize=denominator*rows;
 graphics+=`<p class="bar-caption">Tu mesa de piezas: toca para iluminar o apagar. Cada fila es un entero.</p>${Array.from({length:rows},(_,r)=>`<div class="bar">${Array.from({length:denominator},(_,j)=>{const index=r*denominator+j,on=!!state.current.pieces?.[index];return `<button class="piece ${on?'filled':''}" data-action="piece" data-index="${index}" aria-label="Pieza ${index+1}: una de ${denominator} partes iguales" aria-pressed="${on}"></button>`;}).join('')}</div>`).join('')}<div class="construction-answer"><p id="piece-count" class="bar-caption">${pieceCount()} partes iluminadas de tamaño 1/${denominator}.</p><button data-action="use_pieces" ${solved?'disabled':''}>Responder con mis piezas</button></div>`;
 }
 $('#app').innerHTML=`<div class="game-top"><div><p class="eyebrow">ISLA LUMA / EL TALLER DE ENERGÍA</p><h2>${skill.name}</h2></div><span class="chapter">A tu ritmo, con Luma</span></div><div class="game-layout"><section class="scene"><p>${t.prompt}</p><div class="equation ${t.kind==='meaning'?'empty-equation':''}">${t.kind==='meaning'?'':fraction(t.a)}${t.b?`<span>${t.op}</span>${fraction(t.b)}<span>= ?</span>`:t.kind==='equivalent'?'<span>=</span>'+fraction(['?',8]):''}</div>${graphics}<form id="answer-form" class="math-form"><label for="answer">${t.targetDen?'Escribe tu respuesta con denominador 8.':'Escribe una fracción, por ejemplo 1/4, o un entero.'}</label><input id="answer" name="answer" aria-label="Tu respuesta" inputmode="text" autocomplete="off" maxlength="12" required ${solved?'disabled':''}><button class="primary" type="submit" ${solved?'disabled':''}>Probar</button></form></section><aside class="side">${buddy()}<p>Estas piezas mantienen despierta la isla. Cada barra completa representa un entero. Puedes pedir ayuda cuando quieras.</p>${supports()}<div id="feedback" class="message" role="status">${solved?'¡Encontraste la energía que necesitábamos!':assisted?t.hint:'Prueba tu idea. Si algo no sale, lo vemos juntos.'}</div><button data-action="hint">Dame una pista</button>${!solved?'<button data-action="dont_know">Todavía no sé</button>':''}${solved?'<button class="primary" data-action="next">Siguiente descubrimiento →</button>':''}<button class="quiet" data-action="rest">Quiero descansar</button></aside></div>`;
 if(policy.support==='concrete'&&failures>=3&&supportMode!=='hands')chooseSupport('hands',false);
 $('#answer').value=state.current.draft||'';
 $('#answer').addEventListener('input',()=>{state.current.draft=$('#answer').value;save();});
 $('#answer-form').addEventListener('submit',submitMath);
 mountExperience();
 if(state.blockNotice&&$('.scene')){ $('.scene').insertAdjacentHTML('afterbegin','<p role="status">Terminaste una parte del camino. Puedes seguir o elegir «Quiero descansar».</p>');state.blockNotice=false;}
 restoreFocus(focus);
}
function submitMath(e){
 e.preventDefault();if(solved)return;const t=state.current.task,answer=E.parseFraction($('#answer').value),kind=E.classify(t,answer);
 if(kind==='invalid_format'){log('input_validation',{reason:kind});message('Escribe algo como 1/4. El número de abajo debe ser mayor que cero.');return;}
 const correct=kind==='correct';const wasAssisted=assisted||!firstAttempt;
 // Capturar antes de mostrar cualquier andamiaje provocado por este intento.
 if(firstAttempt){state.knowledge[t.id]=E.updateKnowledge(state.knowledge[t.id],correct,assisted);firstAttempt=false;log('knowledge_updated',{skill:t.id,assisted,posterior:state.knowledge[t.id]});}
 recordAttempt(correct,{skill:t.id,answer,errorPattern:correct?null:kind,assisted:wasAssisted});
 if(correct){E.recordLearning(state.learning,t,true,wasAssisted);log('decision_evaluated',{decisionId:state.current.decisionId||null,skill:t.id,stage:t.stage||'legacy',variantId:t.variantId||null,independent:!wasAssisted,attempts:attemptNumber,posterior:state.knowledge[t.id],learning:state.learning.skills[t.id],outcome:'solved'});solved=true;state.current.solved=true;const p=state.current.experience||'estructurado';state.rewards??={};state.rewards[p]=(state.rewards[p]||0)+1;log('experience_reward',{profile:p,total:state.rewards[p],independent:!wasAssisted});renderMath();message('¡Sí! La energía llegó al taller. Puedes continuar cuando quieras.');}
 else {E.recordLearning(state.learning,t,false,wasAssisted);log('decision_response',{decisionId:state.current.decisionId||null,skill:t.id,errorPattern:kind,independent:!wasAssisted});assisted=true;message(({operates_denominators:'El denominador indica el tamaño de las piezas. No necesitamos sumar esos tamaños.',no_common_unit:'Estas piezas tienen tamaños diferentes. Podemos dividirlas para que sean del mismo tamaño.',inverted_fraction:'Revisa el orden: arriba van las partes que tomas y abajo las partes iguales del entero.',target_denominator:'Representa la misma cantidad. Ahora escríbela usando octavos.'})[kind]||'Todavía no coincide. Mira las piezas o pide una pista para probar otra idea.');}
 state.current.assisted=assisted;state.current.firstAttempt=firstAttempt;save();
}
// Estas modalidades son medios de respuesta, no pistas: no revelan el resultado
// ni el denominador común. Las ayudas explícitas conservan la marca assisted.
function mountExperience(){
 const scene=$('.scene');if(!scene)return;
 const c=state.current,p=c.experience||state.experienceChoice||'estructurado';c.experience=p;
 const info=E.experiences[p];c.boards??={};const board=c.boards[p]??={den:4,cells:[],numerator:0,step:0};
 const count=board.cells.length,reward=state.rewards?.[p]||0;
 const nouns={visual:['Tablero','Pintar casilla'],auditivo:['Compás','Marcar pulso'],explorador:['Batería','Cargar pieza']};
 const chooser=`<details class="experience-chooser"><summary>Cambiar mi forma de jugar</summary><p>Puedes probar todas. Tu avance se conserva.</p><div class="experience-options">${E.profiles.map(k=>`<button data-action="experience" data-profile="${k}" aria-pressed="${p===k}">${E.experiences[k].verb}</button>`).join('')}<button data-action="experience_auto">Dejar que Luma sugiera</button></div></details>`;
 const denominator=`<label for="experience-den">Partes iguales en cada entero</label><select id="experience-den" ${solved?'disabled':''}>${[2,3,4,6,8,12,16,24].map(n=>`<option value="${n}" ${board.den===n?'selected':''}>${n} partes</option>`).join('')}</select>`;
 let activity;
 if(p==='estructurado'){
  activity=`<ol class="step-plan"><li>Observa los paneles y la operación.</li><li>Elige cuántas partes iguales tendrá tu entero.</li><li>Indica cuántas partes quedan en tu respuesta.</li></ol><button data-action="plan_step" ${solved?'disabled':''}>${board.step<3?`Marcar paso ${board.step+1} revisado`:'Volver a revisar los pasos'}</button><p role="status">${board.step} de 3 pasos revisados. Puedes responder cuando estés listo.</p>${denominator}<label for="experience-num">Partes de tu respuesta (numerador)</label><input id="experience-num" type="number" min="0" max="48" step="1" value="${board.numerator}" ${solved?'disabled':''}>`;
 }else{
  activity=`${denominator}<p class="tiny">Cambiar el tamaño vacía tu construcción. Usa el segundo entero si necesitas más de uno.</p>${[0,1].map(r=>`<fieldset class="response-board"><legend>${nouns[p][0]} ${r+1}: un entero</legend><div class="response-cells ${p}" style="--parts:${board.den}">${Array.from({length:board.den},(_,j)=>{const i=r*board.den+j,on=board.cells.includes(i);return `<button data-action="experience_cell" data-index="${i}" aria-label="${nouns[p][1]} ${i+1}" aria-pressed="${on}" class="response-cell ${on?'on':''}" ${solved?'disabled':''}>${on?(p==='auditivo'?'♪':p==='explorador'?'⚡':'●'):'·'}</button>`;}).join('')}</div></fieldset>`).join('')}<p id="experience-count" role="status">${count} partes elegidas: ${count}/${board.den}.</p>`;
  if(p==='auditivo')activity+=`<div class="actions"><button data-action="rhythm" data-source="a">Escuchar panel inicial</button>${c.task.b?'<button data-action="rhythm" data-source="b">Escuchar segundo panel</button>':''}<button data-action="rhythm" data-source="response">Escuchar mi ritmo</button></div><p class="tiny">Cada pulso dura lo mismo dentro de un compás. Los pulsos elegidos suenan más agudos; los demás, más graves. Los paneles y las notas también lo muestran.</p>`;
 }
 const prizes={estructurado:'planos resueltos',visual:'teselas ganadas',auditivo:'notas recuperadas',explorador:'entregas realizadas'};
 const progress=`<div class="experience-reward" aria-label="${reward} ${prizes[p]}"><b>${reward} ${prizes[p]}</b><div class="reward-art" aria-hidden="true">${Array.from({length:Math.min(reward,24)},(_,i)=>`<span class="reward-${p}">${p==='auditivo'?'♪':p==='explorador'?'⚑':p==='estructurado'?'✓':'◆'}</span>`).join('')}</div></div>`;
 scene.insertAdjacentHTML('afterbegin',`<section class="experience-intro" data-profile="${p}"><p class="eyebrow">${info.name}</p><p>${info.goal}</p>${chooser}${progress}</section>`);
 if(['pictorial','abstract','transfer'].includes(c.task.stage)&&!assisted){save();return;}
 $('#answer-form').insertAdjacentHTML('beforebegin',`<section id="experience-workspace" class="experience-workspace ${p}" aria-label="${info.name}"><h3>Construye tu respuesta</h3>${activity}<button class="primary" data-action="experience_submit" ${solved?'disabled':''}>${p==='estructurado'?'Comprobar mi plan':p==='visual'?'Enviar mi mosaico':p==='auditivo'?'Enviar mi ritmo':'Entregar energía'}</button><p class="tiny">También puedes escribir tu respuesta abajo. No necesitas usar ambas formas.</p></section>`);
 $('#experience-den').addEventListener('change',e=>{board.den=Number(e.target.value);board.cells=[];log('experience_action',{profile:p,action:'partition_changed',denominator:board.den});renderMath();$('#experience-den').focus();});
 $('#experience-num')?.addEventListener('input',e=>{board.numerator=e.target.value;log('experience_action',{profile:p,action:'numerator_changed',value:board.numerator});});
 if(p==='visual'){
  $('#experience-den').insertAdjacentHTML('afterend',`<div class="actions paint-palette" aria-label="Colores del mosaico">${[['terracota','#9b5038'],['azul','#365f8b'],['verde','#296952']].map(([name,color])=>`<button data-action="paint_color" data-color="${color}" aria-pressed="${(board.color||'#9b5038')===color}" ${solved?'disabled':''}>Pintar de ${name}</button>`).join('')}</div>`);
  document.querySelectorAll('[data-action="experience_cell"].on').forEach(el=>{el.style.background=board.colors?.[el.dataset.index]||'#9b5038';});
 }
 if(p==='explorador')$('#experience-den').insertAdjacentHTML('afterend',`<p>Prepara tu cargamento: añade o devuelve piezas antes de hacer la entrega.</p><div class="actions"><button data-action="cargo_add" ${solved||count>=board.den*2?'disabled':''}>Cargar una pieza</button><button data-action="cargo_remove" ${solved||!count?'disabled':''}>Devolver una pieza</button></div>`);
 // En móvil, el resultado y la salida deben quedar junto a la acción de responder.
 const submit=$('[data-action="experience_submit"]');
 const next=$('[data-action="next"]');if(next)submit.insertAdjacentElement('afterend',next);
 submit.insertAdjacentHTML('afterend',`<p id="feedback-inline" class="response-feedback" role="status">${esc($('#feedback').textContent)}</p>`);
 save();
}
function stopRhythm(){if(rhythmContext){rhythmContext.close().catch(()=>{});rhythmContext=null;}}
async function playRhythm(source){
 stopRhythm();const c=state.current,b=c.boards.auditivo;
 const pair=source==='response'?[b.cells.length,b.den]:c.task[source];if(!pair)return;
 const Audio=SIMULATION&&state.simulationConfig?.noAudio?null:window.AudioContext||window.webkitAudioContext;
 if(!Audio){log('audio_fallback',{feature:'rhythm',reason:'unavailable'});message('Puedes jugar sin sonido: mira las partes iluminadas y marca tus pulsos.');return;}
 try{
  const ctx=new Audio();rhythmContext=ctx;await ctx.resume();
  if(rhythmContext!==ctx)return;
  state.sound=true;$('#sound').textContent='Sonido encendido';$('#sound').setAttribute('aria-pressed','true');
  const den=pair[1],length=source==='response'?den*2:den,duration=2/den;
  for(let i=0;i<length;i++){
   const on=source==='response'?b.cells.includes(i):i<pair[0];
   const osc=ctx.createOscillator(),gain=ctx.createGain(),at=ctx.currentTime+.05+i*duration;
   osc.frequency.value=on?660:220;gain.gain.setValueAtTime(.0001,at);gain.gain.exponentialRampToValueAtTime(.12,at+.01);gain.gain.exponentialRampToValueAtTime(.0001,at+Math.min(.15,duration*.8));osc.connect(gain);gain.connect(ctx.destination);osc.start(at);osc.stop(at+duration);
  }
  log('rhythm_played',{source,numerator:pair[0],denominator:den,assistance:false});message('Escucha y compara con las partes del panel. Puedes volver a escuchar.');
 }catch{stopRhythm();log('audio_fallback',{feature:'rhythm',reason:'playback_failed'});message('El sonido no está disponible. Puedes seguir con los paneles y los pulsos visibles.');}
}
function experienceAction(b){
 if(state.phase!=='math')return false;const a=b.dataset.action,c=state.current;
 if(!['experience','experience_auto','experience_cell','experience_submit','plan_step','rhythm','paint_color','cargo_add','cargo_remove'].includes(a))return false;
 const p=c.experience,board=c.boards[p];
 if(a==='experience'||a==='experience_auto'){
  stopRhythm();const automatic=a==='experience_auto';state.experienceChoice=automatic?null:b.dataset.profile;
  const inference=E.inferProfile(state.events,state.parent?.scores);c.experience=state.experienceChoice||inference.dominant||'estructurado';
  log(automatic?'experience_auto_requested':'experience_selected',{profile:c.experience,previous:p,voluntary:true,keepsKnowledge:true});renderMath();message(`Ahora jugamos en ${E.experiences[c.experience].name}. Tu avance sigue aquí.`);return true;
 }
 if(a==='rhythm'){playRhythm(b.dataset.source);return true;}
 if(solved)return true;
 if(a==='paint_color'){board.color=b.dataset.color;log('experience_action',{profile:p,action:'brush_changed',color:board.color});renderMath();}
 if(a==='cargo_add'||a==='cargo_remove'){
  if(a==='cargo_add'){const next=Array.from({length:board.den*2},(_,i)=>i).find(i=>!board.cells.includes(i));if(next!==undefined)board.cells.push(next);}else board.cells.pop();
  log('experience_action',{profile:p,action:a,loaded:board.cells.length,denominator:board.den});renderMath();
 }
 if(a==='plan_step'){board.step=(board.step+1)%4;log('experience_action',{profile:p,action:'plan_step',step:board.step});renderMath();}
 if(a==='experience_cell'){
  const i=Number(b.dataset.index);board.cells=board.cells.includes(i)?board.cells.filter(x=>x!==i):[...board.cells,i];
  if(p==='visual'){board.colors??={};board.colors[i]=board.color||'#9b5038';}
  log('experience_action',{profile:p,action:p==='visual'?'paint':p==='auditivo'?'sequence_pulse':'load_cargo',index:i,selected:board.cells.includes(i),denominator:board.den});renderMath();
 }
 if(a==='experience_submit'){
  const n=p==='estructurado'?String(board.numerator):String(board.cells.length);
  state.current.draft=`${n}/${board.den}`;$('#answer').value=state.current.draft;
  log('experience_answer',{profile:p,numerator:n,denominator:board.den,assisted});submitMath({preventDefault(){}});
 }
 save();return true;
}
function pieceCount(){return Object.entries(state.current?.pieces||{}).filter(([index,on])=>on&&Number(index)>=0&&Number(index)<state.current.workspaceSize).length;}
function renderComplete(){
 const finished=state.completionReason==='mastery';
 $('#app').innerHTML=`<section class="center"><p class="eyebrow">${finished?'AVENTURA COMPLETADA':'UN NUEVO DESCUBRIMIENTO'}</p><h2>${finished?'¡El taller está encendido!':'La isla guarda<br>tu camino.'}</h2><p>${finished?'Completaste las habilidades de esta aventura. Tu progreso quedó guardado. Puedes terminar aquí o volver a practicar cuando quieras.':'Podemos seguir explorando cuando tengas ganas.'}</p><div class="progress-list">${E.skills.map(s=>`<div class="skill"><span>${s.name}</span><span class="pill">${E.mastered(state.knowledge[s.id])?'Con más autonomía':state.knowledge[s.id].n?'En exploración':'Por descubrir'}</span></div>`).join('')}</div><div class="actions"><button class="primary" data-action="continue_math">${finished?'Practicar otra vez':'Volver al taller'}</button></div></section>`;
}
function openPause(reason='student'){
 stopRhythm();
 if(paused)return;flushMotion();flushExposure('pause');paused=true;log('pause_started',{reason});
 $('#modal').innerHTML=`<h2>La isla puede esperar.</h2><p>${reason==='idle'?'¿Seguimos? Puedes pedir una pista o tomarte un descanso.':'Estira las manos, mira a tu alrededor y vuelve cuando quieras.'}</p><div class="actions"><button class="primary" id="resume">Seguir explorando</button><button id="pause-help">Volver con una pista</button>${reason==='idle'?'<button id="reading">Sigo leyendo</button>':''}</div>`;$('#modal').showModal();$('#resume').onclick=()=>closePause(false);$('#pause-help').onclick=()=>closePause(true);if($('#reading'))$('#reading').onclick=()=>{closePause(false);readingUntil=performance.now()+120000;log('reading_confirmed',{source:'child_self_report',graceMs:120000,interpretation:'not_verified_engagement'});};
}
function closePause(help){$('#modal').close();paused=false;if(idle)log('idle_ended');idle=false;lastInput=lastTick=performance.now();log('pause_ended',{help});if(help)chooseSupport('hands',false);}
function family(){
 stopRhythm();
 const wasPaused=paused;flushExposure('family_panel');paused=true;log('family_opened');const profile=E.inferProfile(state.events,state.parent?.scores);
 $('#modal').innerHTML=`<h2>Un vistazo a su aventura</h2><p>Este prototipo guarda en este navegador las elecciones de ayuda, intentos, tiempos activos y avances. No solicita nombre, cámara ni micrófono y no envía datos a un servidor.</p><p class="tiny">Un perfil por navegador. Las preferencias son provisionales y no son diagnósticos. ${storageError?'No se pudo guardar: exporta los datos antes de cerrar.':'El progreso se guarda en este equipo.'}</p><details><summary>Observaciones de la familia</summary><p class="tiny">Se completa una vez, por un adulto. Es un instrumento de prototipo pendiente de validación. El niño puede jugar sin esperar estas respuestas.</p><form id="parent-form"><label>¿Qué instrucciones suele elegir?<select name="channel"><option value="">Aún no lo sé</option><option value="visual">Dibujos o demostraciones visuales</option><option value="auditivo">Explicaciones habladas</option><option value="explorador">Probar con objetos</option><option value="estructurado">Pasos ordenados</option></select></label><label>¿Qué actividad busca por iniciativa propia?<select name="interest"><option value="">Aún no lo sé</option><option value="estructurado">Construcción con instrucciones o acertijos</option><option value="visual">Dibujo y creación libre</option><option value="auditivo">Música y juegos sonoros</option><option value="explorador">Aventuras, movimiento o deportes</option></select></label><label>Cuando algo se complica, suele…<select name="response"><option value="">Aún no lo sé</option><option value="retry">Volver a intentar</option><option value="help">Pedir ayuda</option><option value="pause">Parar o alejarse de la actividad</option><option value="varies">Depende del momento</option></select></label><button type="submit">Guardar observaciones</button><p id="parent-status" role="status"></p></form></details><details><summary>Registro y adaptación</summary><p class="tiny">${state.events.length} eventos · ${Math.floor(state.playMs/1000)} segundos activos de juego previo. Sin observación familiar completa, no se aplica la ponderación 60/40.</p><pre>${esc(JSON.stringify({profile,activeExperience:state.current?.experience||state.lastExperience,childChoice:state.experienceChoice||null,rewards:state.rewards||{},policy:adaptationPolicy(),knowledge:state.knowledge},null,2))}</pre><button id="export">Exportar registro completo (JSON)</button></details><div class="actions"><button class="primary" id="close-family">Volver a la isla</button></div>`;
 $('#modal').showModal();if(state.parent){for(const key of ['channel','interest','response'])$('#parent-form').elements[key].value=state.parent[key]||'';}
 $('#close-family').onclick=()=>{$('#modal').close();paused=wasPaused;lastTick=lastInput=performance.now();log('family_closed');};
 $('#parent-form').onsubmit=e=>{e.preventDefault();const data=Object.fromEntries(new FormData(e.target));if(!data.channel||!data.interest||!data.response){$('#parent-status').textContent='Puedes dejarlo pendiente. Para combinar ambas observaciones, necesitamos las tres respuestas.';return;}const scores=Object.fromEntries(E.profiles.map(p=>[p,1]));scores[data.channel]+=2;scores[data.interest]+=2;state.parent={...data,scores};log('parent_observation_saved',{...data,instrumentVersion:'prototype-1',validated:false});$('#parent-status').textContent='Observaciones guardadas. Se combinarán con lo que observe el juego.';};
 $('#export').onclick=()=>{log('export_requested');const payload={...state,profile:E.inferProfile(state.events,state.parent?.scores),exportedAt:new Date().toISOString()};const url=URL.createObjectURL(new Blob([JSON.stringify(payload,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='isla-luma-registro.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);};
}
$('#modal').addEventListener('cancel',e=>{e.preventDefault();const close=$('#close-family')||$('#resume');close?.click();});
$('#family').onclick=family;$('#pause').onclick=()=>openPause();$('#sound').onclick=()=>{state.sound=!state.sound;if(!state.sound){window.speechSynthesis?.cancel?.();stopRhythm();}log('sound_changed',{enabled:state.sound});$('#sound').textContent=state.sound?'Sonido encendido':'Sonido apagado';$('#sound').setAttribute('aria-pressed',String(state.sound));};
$('#app').addEventListener('click',e=>{
 const b=e.target.closest('[data-action]');if(!b||b.disabled||paused)return;const a=b.dataset.action,j=Number(b.dataset.index);
 if(experienceAction(b))return;
 if(a==='start'){state.phase='play';lastInput=lastTick=performance.now();log('playtest_started',{durationMs:E.CONFIG.playMs,gradeRange:'5-6',country:'MX',audioAvailable:'speechSynthesis'in window,reducedMotion:matchMedia('(prefers-reduced-motion: reduce)').matches});render();}
 if(a==='route'){state.route=b.dataset.route;log('route_selected',{route:state.route});renderPlay();message(hintText());}
 if(a==='place'){state.visits??=[];const from=state.lastPlace||'map';state.lastPlace=b.dataset.place;if(!state.visits.includes(b.dataset.place))state.visits.push(b.dataset.place);log('navigation',{from,destination:b.dataset.place,route:state.route||'unselected',latencyMs:Math.round(elapsed()-taskOpened)});renderPlay();message(state.visits.length===3?'Ya conoces la isla. Cuando quieras, podemos ir al invernadero.':{greenhouse:'Aquí ayudaremos a las criaturas a encontrar su refugio. Toca otro lugar para conocerlo.',station:'La antena lleva mensajes por toda la isla. Pronto arreglaremos su señal.',garden:'Aquí podrás inventar un jardín que se parezca a ti.'}[b.dataset.place]);}
 if(a==='enter_refuge'){state.refugeAt=state.playMs;log('scene_advance_requested',{destination:'greenhouse',reason:'map_explored'});renderPlay();}
 if(a==='support')chooseSupport(b.dataset.mode);
 if(a==='dont_know'&&!solved){log('uncertainty_reported',{skill:state.current.task.id,interpretation:'self_report_not_error'});state.learning.skills[state.current.task.id].probe=true;chooseSupport('hands',false);return;}
 if(a==='hint'){log('hint_requested',{afterError:failures>0,latencyMs:Math.round(elapsed()-taskOpened)});chooseSupport('visual',false);respondToSupportSignals();}
 if(a==='creature'){selection=j;log('object_selected',{object:words[j]});renderPlay();message('Ahora toca el refugio con la misma señal.');}
 if(a==='next_scene'){state.playStage=Math.min(3,sceneIndex+1);log('scene_advance_requested',{destination:state.playStage,reason:'objectives_completed'});renderPlay();$('h2')?.focus?.();}
 if(a==='finish_play'&&sceneIndex===3)finishPlay('child_finished_objectives');
 if(a==='shelter'&&sceneIndex===1&&state.playProgress.rescued.length<3){
  if(selection===null){message('Primero elige la criatura que quieres acompañar.');return;}
  const ok=selection===refugeTarget()&&j===selection;recordAttempt(ok,{domain:'non_math',activity:'shelter',choice:j,selected:selection,errorPattern:ok?null:'symbol_mismatch'});
  if(ok){state.playProgress.rescued.push(j);state.round++;markTask();renderPlay();message(state.playProgress.rescued.length>=3?'¡Todas están a salvo! Pulsa «Ir a la estación» para continuar.':'¡Encontró su refugio! Su señal quedó marcada. Ayudemos a la siguiente.');}else message('Esa señal es distinta. Mira la criatura de arriba y prueba de nuevo.');
 }
 if(a==='signal'){if(sequence.length<3){sequence.push(j);log('sequence_action',{symbol:words[j],position:sequence.length});renderPlay();}else message('Puedes enviar la señal o deshacer para cambiarla.');}
 if(a==='undo'){sequence.pop();log('strategy_changed',{action:'undo'});renderPlay();}
 if(a==='send'&&sceneIndex===2&&state.playProgress.signals<3){
  if(sequence.length<3){message('El camino todavía tiene un espacio. Puedes completar la señal o pedir una pista.');return;}
  const ok=antenna().every((x,k)=>x===sequence[k]);recordAttempt(ok,{domain:'non_math',activity:'signal',choice:[...sequence],errorPattern:ok?null:'sequence_mismatch'});
  if(ok){state.playProgress.signals++;state.round++;markTask();renderPlay();message(state.playProgress.signals>=3?'¡La señal llegó a todos los lugares! Pulsa «Ir al jardín».':'¡La señal llegó! Ese lugar ya está conectado. Vamos al siguiente.');}else{sequence=failures>=E.CONFIG.failures?[antenna()[0]]:[];renderPlay();message('La antena necesita un camino diferente. Sigue las señales de arriba.');}
 }
 if(a==='plant'){const variants=['🌿','🌼','🌻','🌷'];state.garden[j]=variants[(variants.indexOf(state.garden[j])+1)%variants.length];state.playProgress.gardenActions++;log('creative_change',{slot:j,plant:state.garden[j]});renderPlay();}
 if(a==='color'){sandboxColor=(sandboxColor+30)%90;state.playProgress.gardenActions++;log('creative_change',{environment:sandboxColor});renderPlay();}
 if(a==='garden_sound'){if(audio('El viento canta entre las hojas. Las flores despiertan y la isla vuelve a brillar.'))log('support_selected',{mode:'audio',voluntary:true});}
 if(a==='garden_guide'){log('route_selected',{route:'guided',context:'garden'});message('Puedes poner tu flor favorita en el centro y probar otras plantas a sus lados.');}
 if(a==='math_start'){state.phase='math';state.blockMs=0;state.current=null;lastInput=lastTick=performance.now();log('math_started',{knowledgeSource:'fraction_tasks_only'});render();}
 if(a==='piece'){b.classList.toggle('filled');const filled=b.classList.contains('filled');b.setAttribute('aria-pressed',String(filled));state.current.pieces??={};state.current.pieces[j]=filled;log('manipulation',{tool:'fraction_bar',piece:j,filled});$('#piece-count').textContent=`${pieceCount()} partes iluminadas de tamaño 1/${state.current.workspaceDen}.`;}
 if(a==='use_pieces'&&!solved){assisted=true;state.current.draft=`${pieceCount()}/${state.current.workspaceDen}`;$('#answer').value=state.current.draft;log('constructed_answer',{tool:'fraction_bar',numerator:pieceCount(),denominator:state.current.workspaceDen});submitMath({preventDefault(){}});}
 if(a==='next'){stopRhythm();closeLearningBlock();state.current=null;const p=adaptationPolicy();if(E.skills.every(s=>E.learningComplete(s.id,state.knowledge,state.learning))){flushExposure('learning_path_completed');exposure=null;state.phase='complete';state.completionReason='mastery';log('learning_path_completed',{skills:E.skills.map(s=>s.id)});}else if(state.blockMs>=p.breakAfterMs){state.phase='complete';state.completionReason='break';state.blockMs=0;log('break_suggested',{policy:p,reason:'adaptive_active_duration'});}render();}
 if(a==='rest'){stopRhythm();if(state.phase==='math'){flushExposure('voluntary_break');exposure=null;state.phase='complete';state.completionReason='break';log('voluntary_break');render();}else openPause();}
 if(a==='continue_math'){state.phase='math';state.blockMs=0;lastInput=lastTick=performance.now();log('math_resumed');render();}
 save();
});
document.addEventListener('visibilitychange',()=>{hidden=document.hidden;if(hidden)stopRhythm();flushMotion();flushExposure('visibility_change');log(hidden?'visibility_hidden':'visibility_visible',{reason:'tab_visibility_not_assumed_abandonment'});lastTick=performance.now();if(!hidden)lastInput=performance.now();});
window.addEventListener('pagehide',()=>{flushMotion();flushExposure('pagehide');log('session_interrupted',{reason:'pagehide',completion:state.phase,notAssumedFailure:true});});
setInterval(()=>{
 const now=performance.now(),dt=Math.min(1500,now-lastTick);lastTick=now;if(!active())return;
 if(now-lastInput>=E.CONFIG.idleMs&&now>=readingUntil){if(!idle){idle=true;log('idle_started',{thresholdMs:E.CONFIG.idleMs});openPause('idle');}return;}
 if(state.phase==='play'){
  state.playMs=Math.min(E.CONFIG.playMs,state.playMs+dt);
  if(state.playMs>=E.CONFIG.playMs)finishPlay('active_time_limit');
  else if(scenes.some((s,i)=>state.playMs>=s.at&&i>sceneIndex))renderPlay();
 }else{state.mathMs+=dt;state.blockMs+=dt;}
},250);
setInterval(()=>{if(active()){flushMotion();log('heartbeat',{active:true});}save();},5000);
if(state.phase==='math'&&state.current){solved=!!state.current.solved;assisted=!!state.current.assisted;firstAttempt=state.current.firstAttempt!==false;failures=state.current.failures||0;attemptNumber=state.current.attemptNumber||0;supportMode=state.current.supportMode||'visual';
 // Compatibilidad: partidas antiguas recuperan el inicio desde su propio registro.
 const origin=state.current.taskOpened??state.events.findLast(e=>e.task===state.current.key&&['attempt','task_presented'].includes(e.type))?.mathMs??state.mathMs;
 taskOpened=Number.isFinite(origin)?Math.max(0,Math.min(state.mathMs,origin)):state.mathMs;
}
if(SIMULATION){const banner=document.createElement('p');banner.textContent='SIMULACIÓN TÉCNICA · partida de prueba separada';banner.style.cssText='text-align:center;background:#f5e7a8;padding:12px;margin:0';document.body.prepend(banner);document.querySelector('.brand').href='?simulation=1';}
log('session_started',{resumed:state.phase!=='welcome',simulation:SIMULATION,viewport:{width:innerWidth,height:innerHeight},audioAvailable:'speechSynthesis'in window});render();
