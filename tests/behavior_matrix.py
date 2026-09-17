"""End-to-end behavior matrix. UI actions only; telemetry is read, never seeded.

The virtual clock models active reading and pauses; it is not human observation.
Answers are computed from visible panels using Python fractions (profiles_test).
"""
import sys
import argparse
import hashlib
import json
import time
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
from profiles_test import ProfileTests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from validate import source_hash
from browser_config import BASE, BROWSER_CHANNEL
PROFILES = ['estructurado', 'visual', 'auditivo', 'explorador']
BEHAVIORS = ['baseline', 'recovery', 'slow', 'interruptions', 'assisted', 'no_audio', 'mixed', 'family', 'override']
PARENTS = {'meaning': [], 'equivalent': ['meaning'], 'add_same': ['meaning'], 'sub_same': ['meaning'], 'add_diff': ['equivalent', 'add_same'], 'sub_diff': ['equivalent', 'sub_same']}

def mastered(k):
    return k['n'] >= 3 and k['p'] >= .85

class Run:
    choose = ProfileTests.choose
    construct = ProfileTests.construct
    answer_from_screen = ProfileTests.answer_from_screen

    def __init__(self, browser, profile, behavior, out):
        self.source_hash = source_hash()
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.profile, self.behavior = profile, behavior
        self.out = out / f'{profile}-{behavior}'
        self.out.mkdir(parents=True, exist_ok=True)
        self.context = browser.new_context(viewport={'width': 1366, 'height': 1000}, reduced_motion='reduce')
        if behavior == 'no_audio':
            # Device capability only; no state, telemetry, answers or policies injected.
            self.context.add_init_script("Object.defineProperty(window,'speechSynthesis',{value:undefined});window.AudioContext=undefined;window.webkitAudioContext=undefined;")
        self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        self.page = self.context.new_page()
        self.page.set_default_timeout(6000)
        self.errors, self.requests, self.checkpoints, self.checks = [], [], [], []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.on('request', lambda r: self.requests.append(r.url))
        start = datetime(2026, 9, 17, 12, tzinfo=timezone.utc)
        self.page.clock.install(time=start)
        self.page.clock.pause_at(start + timedelta(seconds=1))
        self.page.goto(BASE + '/?simulation=1')
        self.check('fresh_real_storage_untouched', self.page.evaluate("localStorage.getItem('isla-luma-v1')") is None)
        self.check('fresh_start', self.state()['phase'] == 'welcome')

    def state(self):
        return self.page.evaluate("JSON.parse(localStorage.getItem('isla-luma-simulation-v1'))")

    def check(self, name, condition, detail=None):
        self.checks.append({'name': name, 'pass': bool(condition), 'detail': detail})
        if not condition:
            raise AssertionError(f'{name}: {detail}')

    def advance(self, ms, active=True):
        while ms:
            step = min(ms, 10000)
            if active:
                self.page.keyboard.press('Shift')
            self.page.clock.run_for(step)
            ms -= step

    def snapshot(self, label):
        s = self.state()
        c = s.get('current') or {}
        self.checkpoints.append({'label': label, 'eventCount': len(s['events']), 'phase': s['phase'], 'mathMs': s['mathMs'], 'blockMs': s['blockMs'], 'knowledge': s['knowledge'], 'current': {k:c.get(k) for k in ['key','experience','assisted','firstAttempt','supportMode','solved']}, 'lastDecision': next((e for e in reversed(s['events']) if e['type']=='adaptation_decision'), None)})
        return s

    def pregame(self):
        self.page.get_by_role('button', name='Explorar con Luma').click()
        for name in ['Invernadero', 'Estación', 'Jardín']:
            self.advance(1500)
            self.page.get_by_role('button', name=name, exact=True).click()
        self.page.get_by_role('button', name='Ir al invernadero').click()
        if self.behavior == 'recovery':
            for _ in range(3):
                self.page.get_by_role('button', name='Elegir criatura flor', exact=True).click()
                self.page.get_by_role('button', name='Refugio luna', exact=True).click()
                self.advance(2000)
            self.check('pregame_errors_do_not_teach_math', all(k['n']==0 for k in self.state()['knowledge'].values()))
        for name in ['flor', 'luna', 'rombo']:
            self.advance(2000)
            self.page.get_by_role('button', name=f'Elegir criatura {name}', exact=True).click()
            self.page.get_by_role('button', name=f'Refugio {name}', exact=True).click()
        self.page.get_by_role('button', name='Ir a la estación').click()
        for _ in range(3):
            for name in self.page.locator('.steps').get_attribute('aria-label').removeprefix('Señal: ').split(', '):
                self.page.get_by_role('button', name=f'Añadir {name}', exact=True).click()
            self.advance(2500)
            self.page.get_by_role('button', name='Enviar señal', exact=True).click()
        self.page.get_by_role('button', name='Ir al jardín').click()
        self.page.get_by_role('button', name='Cambiar planta del centro', exact=True).click()
        self.page.get_by_role('button', name='Terminar mi jardín y continuar').click()
        self.check('pregame_objectives_complete', self.state()['playProgress']['signals']==3 and len(self.state()['playProgress']['rescued'])==3)
        self.check('no_math_inference_from_pregame', all(k['n']==0 for k in self.state()['knowledge'].values()))
        self.page.get_by_role('button', name='Entrar al taller').click()
        if self.behavior == 'family':
            self.page.get_by_role('button', name='Familias', exact=True).click()
            self.page.get_by_text('Observaciones de la familia', exact=True).click()
            other = PROFILES[(PROFILES.index(self.profile)+1)%4]
            for name, value in [('channel',other),('interest',other),('response','help')]:
                self.page.locator(f'[name={name}]').select_option(value)
            self.page.get_by_role('button', name='Guardar observaciones', exact=True).click()
            self.page.get_by_role('button', name='Volver a la isla', exact=True).click()
            self.check('family_saved_through_form', self.state()['parent']['scores'][other]==5)
        self.snapshot('math_entry')

    def auto(self):
        self.page.locator('.experience-chooser summary').click()
        self.page.locator('[data-action=experience_auto]').click()

    def answer(self, correct=True):
        n,d = self.answer_from_screen() if correct else (0,4)
        profile = self.page.locator('.experience-intro').get_attribute('data-profile')
        # Move away from controls before a rerender; keep native clicks and checks.
        # A stationary pointer plus a frozen clock can retain a hover transform.
        self.page.mouse.move(0,0)
        self.construct(profile,n,d)
        before = self.state()
        ProfileTests.submit_constructed(self)
        after = self.state()
        attempt = [e for e in after['events'] if e['type']=='attempt'][-1]
        self.check('answer_outcome_matches_visible_math', attempt['data']['correct']==correct)
        skill = attempt['data']['skill']
        first = before['current']['firstAttempt']
        assisted = before['current']['assisted']
        if first:
            self.check('active_latency_survives_reload',attempt['data']['latencyMs']>=self.expected_latency-500,attempt['data']['latencyMs'])
        self.check('attempt_assistance_correct', attempt['data']['assisted']==(assisted or not first))
        for key, previous in before['knowledge'].items():
            expected = dict(previous)
            if key==skill and first and not assisted:
                likelihood_known, likelihood_unknown = (.9,.15) if correct else (.1,.85)
                p=previous['p']*likelihood_known/(previous['p']*likelihood_known+(1-previous['p'])*likelihood_unknown)
                expected={'p':min(.99,max(.01,p+(1-p)*.08)), 'n':previous['n']+1, 'correct':previous['correct']+int(correct)}
            actual=after['knowledge'][key]
            self.check('independent_knowledge_update', actual['n']==expected['n'] and actual['correct']==expected['correct'] and abs(actual['p']-expected['p'])<1e-10, key)
        self.snapshot('answer_correct' if correct else 'answer_error')

    def interruption(self):
        before=self.state()
        self.advance(60000, active=False)
        expect(self.page.locator('#resume')).to_be_visible()
        paused=self.state()
        self.advance(90000, active=False)
        self.check('idle_pause_excludes_wait', self.state()['mathMs']==paused['mathMs'])
        self.check('idle_does_not_penalize_knowledge', self.state()['knowledge']==before['knowledge'])
        self.page.locator('#resume').click()
        self.snapshot('idle_resumed')

    def audit(self, state):
        known={k:{'p':.5,'n':0,'correct':0} for k in PARENTS}
        for e in state['events']:
            if e['type']=='task_presented':
                self.check('all_prerequisites_respected', all(mastered(known[k]) for k in PARENTS[e['data']['skill']]))
            if e['type']=='knowledge_updated':
                known[e['data']['skill']]=e['data']['posterior']
            if e['type']=='adaptation_decision':
                index=state['events'].index(e)
                recent=[x for x in state['events'][:index] if x['phase']==e['phase'] and 0<=e['mathMs']-x['mathMs']<=120000 and x['type'] in ['attempt','hint_requested','idle_started','idle_ended']][-20:]
                load=sum(x['type']=='hint_requested' or x['type']=='attempt' and x['data']['correct'] is False for x in recent)
                self.check('policy_matches_recent_raw_telemetry',e['data']['support']==('concrete' if load>=4 else 'pictorial'))
                self.check('break_policy_matches_raw_telemetry',e['data']['breakAfterMs']==(240000 if load>=4 else 480000))
        self.check('knowledge_matches_telemetry',known==state['knowledge'])
        self.check('unique_event_ids',len(state['events'])==len({e['id'] for e in state['events']}))
        self.check('only_local_requests',all(url.startswith(BASE) or url.startswith('blob:') for url in self.requests))
        self.check('no_js_errors',not self.errors,self.errors)
        self.check('all_events_marked_simulation',all(e.get('simulation') for e in state['events']))
        self.check('real_storage_still_untouched',self.page.evaluate("localStorage.getItem('isla-luma-v1')") is None)
        decisions=[e['data'] for e in state['events'] if e['type']=='adaptation_decision']
        self.check('no_clinical_anxiety_inference',all(d['metrics']['anxiety']=='no inferible' and d['isClinicalInference'] is False for d in decisions))
        if self.behavior=='recovery':
            self.check('support_escalates_and_recovers',any(d['support']=='concrete' for d in decisions) and decisions[-1]['support']=='pictorial')
        if self.behavior=='slow':
            self.check('slow_is_not_concrete_support',all(d['support']=='pictorial' for d in decisions))
            self.check('slow_gets_duration_breaks',any(e['type']=='break_suggested' for e in state['events']))
        if self.behavior=='interruptions':
            self.check('idle_recorded_and_resumed',sum(e['type']=='idle_started' for e in state['events'])>=2 and sum(e['type']=='idle_ended' for e in state['events'])>=2)
        if self.behavior=='no_audio':
            self.check('audio_unavailability_recorded',any(e['type']=='support_unavailable' for e in state['events']))

    def execute(self):
        self.pregame()
        for i in range(65):
            state=self.state()
            if state['phase']=='complete':
                if state.get('completionReason')=='mastery' or self.behavior=='assisted':
                    break
                known=state['knowledge']
                self.advance(120000, active=False)
                self.page.get_by_role('button',name='Volver al taller',exact=True).click()
                self.check('break_preserves_knowledge',self.state()['knowledge']==known)
            if self.behavior=='mixed' and i<8:
                self.choose(PROFILES[(i+PROFILES.index(self.profile))%4])
            elif self.behavior!='mixed' and i<5:
                self.choose(self.profile)
            if i==(8 if self.behavior=='mixed' else 5):
                self.auto()
                self.snapshot('automatic_preference')
                active=self.state()['current']['experience']
                self.check('automatic_assignment_from_observed_choices',active==('estructurado' if self.behavior=='mixed' else self.profile),active)
            if self.behavior=='override' and i==7:
                before=self.state()
                other=PROFILES[(PROFILES.index(self.profile)+1)%4]
                self.choose(other)
                self.check('override_keeps_task_and_knowledge',self.state()['current']['key']==before['current']['key'] and self.state()['knowledge']==before['knowledge'])
            if self.behavior=='interruptions' and i in [2,7]:
                self.interruption()
            duration=70000 if self.behavior=='slow' else 20000 if self.behavior=='assisted' else 15000
            self.expected_latency=duration
            self.advance(duration)
            if i==6:
                before=self.state()
                self.page.get_by_role('button',name='Pausar',exact=True).click()
                paused_time=self.state()['mathMs']
                self.advance(60000,active=False)
                self.check('manual_pause_excludes_wait',self.state()['mathMs']==paused_time)
                self.page.locator('#resume').click()
                self.page.reload()
                self.check('reload_preserves_task',self.state()['current']['key']==before['current']['key'])
                self.check('reload_preserves_knowledge',self.state()['knowledge']==before['knowledge'])
            if self.behavior=='no_audio' and i==0:
                self.page.locator('[data-action=support][data-mode=audio]').click()
                expect(self.page.locator('#feedback')).to_contain_text('pista escrita')
                self.check('written_fallback_is_assistance',self.state()['current']['assisted'])
                if self.profile=='auditivo':
                    self.page.locator('[data-action=rhythm][data-source=a]').click()
                    expect(self.page.locator('#feedback')).to_contain_text('sin sonido')
            if self.behavior=='recovery' and i<3:
                self.answer(correct=False)
                self.page.get_by_role('button',name='Dame una pista',exact=True).click()
                self.advance(2000)
            if self.behavior=='assisted':
                self.page.get_by_role('button',name='Dame una pista',exact=True).click()
            self.answer()
            expect(self.page.locator('[data-action=next]')).to_be_visible()
            self.page.locator('[data-action=next]').click()
            self.snapshot('next_boundary')
        final=self.state()
        self.check('explicit_terminal_state',final['phase']=='complete')
        if self.behavior=='assisted':
            self.check('assisted_only_no_mastery',all(k['n']==0 for k in final['knowledge'].values()))
            self.check('assisted_gets_adaptive_break',final.get('completionReason')=='break' and any(e['type']=='break_suggested' for e in final['events']))
        else:
            self.check('all_six_skills_mastered',all(mastered(k) for k in final['knowledge'].values()))
            self.check('mastery_closure',final.get('completionReason')=='mastery')
            self.check('all_24_pedagogy_stages',all(set(k['passed'])=={'concrete','pictorial','abstract','transfer'} for k in final['learning']['skills'].values()))
        event_by_id={e['id']:e for e in final['events']}
        outcomes=[e for e in final['events'] if e['type']=='decision_evaluated']
        for outcome in outcomes:
            decision=event_by_id.get(outcome['data']['decisionId'])
            self.check('outcome_linked_to_its_decision',decision is not None and decision['task']==outcome['task'])
            self.check('decision_evidence_exists_and_precedes',all(key in event_by_id and event_by_id[key]['mathMs']<=decision['mathMs'] for key in decision['data']['evidenceIds']))
        self.check('each_solved_task_has_one_outcome',len(outcomes)==len({e['task'] for e in outcomes}))
        self.audit(final)
        self.page.screenshot(path=str(self.out/'final.png'),full_page=True)
        # Export through the real Families UI, then verify against the state read.
        self.page.get_by_role('button',name='Familias',exact=True).click()
        self.page.get_by_text('Registro y adaptación',exact=True).click()
        with self.page.expect_download() as download:
            self.page.get_by_role('button',name='Exportar registro completo (JSON)',exact=True).click()
        download.value.save_as(self.out/'export.json')
        exported=json.loads((self.out/'export.json').read_text(encoding='utf8'))
        self.check('ui_export_matches_knowledge',exported['knowledge']==final['knowledge'])
        self.page.get_by_role('button',name='Volver a la isla',exact=True).click()
        # Monitor the same generated record through import without altering the game.
        dashboard=self.context.new_page()
        dashboard.goto(BASE+'/admin.html')
        dashboard.locator('#file').set_input_files(str(self.out/'export.json'))
        expect(dashboard.locator('#status')).to_contain_text('Registro importado')
        expect(dashboard.locator('#metrics')).to_contain_text('0 / 6' if self.behavior=='assisted' else '6 / 6')
        if self.behavior in ['recovery','slow','assisted']:
            dashboard.screenshot(path=str(self.out/'dashboard.png'),full_page=True)
        dashboard.close()
        self.check('dashboard_reads_real_ui_export',True)

    def finish(self,status,error,wall_seconds):
        state=self.state()
        (self.out/'telemetry.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf8')
        (self.out/'checkpoints.json').write_text(json.dumps(self.checkpoints,ensure_ascii=False,indent=2),encoding='utf8')
        self.page.screenshot(path=str(self.out/'last-screen.png'),full_page=True)
        self.context.tracing.stop(path=str(self.out/'trace.zip'))
        summary={'sourceHash':self.source_hash,'startedAt':self.started_at,'finishedAt':datetime.now(timezone.utc).isoformat(),'sourceUnchanged':self.source_hash==source_hash(),'profile':self.profile,'behavior':self.behavior,'status':status,'error':error,'wallSeconds':round(wall_seconds,2),'clock':'virtual; UI events only; no seeded state','browser':self.context.browser.version,'phase':state['phase'],'completionReason':state.get('completionReason'),'events':len(state['events']),'mathActiveSeconds':round(state['mathMs']/1000,2),'mastered':sum(mastered(k) for k in state['knowledge'].values()),'attempts':sum(e['type']=='attempt' and e['phase']=='math' for e in state['events']),'errors':sum(e['type']=='attempt' and e['phase']=='math' and not e['data']['correct'] for e in state['events']),'hints':sum(e['type']=='hint_requested' for e in state['events']),'breaks':sum(e['type']=='break_suggested' for e in state['events']),'idle':sum(e['type']=='idle_started' for e in state['events']),'checks':self.checks,'artifacts':str(self.out.relative_to(ROOT)),'telemetrySha256':hashlib.sha256((self.out/'telemetry.json').read_bytes()).hexdigest()}
        (self.out/'result.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
        self.context.close()
        return summary

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--profile',choices=PROFILES,required=True)
    parser.add_argument('--behaviors',nargs='+',choices=BEHAVIORS,default=BEHAVIORS)
    parser.add_argument('--output',default='output/behavior-matrix')
    args=parser.parse_args()
    out=ROOT/args.output
    out.mkdir(parents=True,exist_ok=True)
    results=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel=BROWSER_CHANNEL,headless=True)
        for behavior in args.behaviors:
            start=time.monotonic()
            run=Run(browser,args.profile,behavior,out)
            status,error='passed',None
            try:
                run.execute()
            except Exception:
                status,error='failed',traceback.format_exc()
            result=run.finish(status,error,time.monotonic()-start)
            results.append(result)
            print(json.dumps({k:result[k] for k in ['profile','behavior','status','error','wallSeconds','mastered']},ensure_ascii=False),flush=True)
        browser.close()
    (out/f'{args.profile}-summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
    raise SystemExit(1 if any(r['status']=='failed' for r in results) else 0)

if __name__=='__main__':
    main()
