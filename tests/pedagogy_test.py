"""Recorridos de UI: sin inyectar conocimiento, respuestas ni telemetría."""
import json
import unittest
import browser_test as base
import profiles_test as profiles
from playwright.sync_api import expect

class PedagogyTests(unittest.TestCase):
    setUpClass=classmethod(base.BrowserTests.setUpClass.__func__)
    tearDownClass=classmethod(base.BrowserTests.tearDownClass.__func__)
    setUp=base.BrowserTests.setUp
    tearDown=base.BrowserTests.tearDown
    state=base.BrowserTests.state
    start=base.BrowserTests.start
    advance=base.BrowserTests.advance
    pregame=profiles.ProfileTests.pregame
    answer_from_screen=profiles.ProfileTests.answer_from_screen

    def solve(self):
        n,d=self.answer_from_screen()
        self.page.locator('#answer').fill(f'{n}/{d}')
        self.page.locator('#answer-form button').click()
        expect(self.page.locator('[data-action=next]')).to_be_visible()

    def test_01_unknown_probe_reload_and_linked_evidence(self):
        self.pregame()
        before=self.state()['knowledge']
        self.page.locator('[data-action=dont_know]').click()
        self.assertEqual(before,self.state()['knowledge'])
        self.solve()
        self.assertEqual(self.state()['learning']['skills']['meaning']['passed'],[])
        self.page.locator('[data-action=next]').click()
        self.assertTrue(self.state()['current']['task']['independentProbe'])
        self.assertFalse(self.state()['current']['assisted'])
        for stage in ['concrete','pictorial','abstract','transfer']:
            self.assertEqual(self.state()['current']['task']['stage'],stage)
            self.assertEqual(self.page.locator('#experience-workspace').count(),int(stage=='concrete'))
            if stage in ['abstract','transfer']:
                self.assertEqual(self.page.locator('.scene .bar').count(),0)
            self.page.reload()
            self.solve()
            state=self.state()
            outcome=[e for e in state['events'] if e['type']=='decision_evaluated'][-1]
            decision=next(e for e in state['events'] if e['id']==outcome['data']['decisionId'])
            self.assertEqual(outcome['task'],decision['task'])
            self.assertTrue(outcome['data']['independent'])
            for evidence in decision['data']['evidenceIds']:
                self.assertTrue(any(e['id']==evidence and e['mathMs']<=decision['mathMs'] for e in state['events']))
            self.page.locator('[data-action=next]').click()
        self.assertNotEqual(self.state()['current']['task']['id'],'meaning')
        outcomes=[e for e in self.state()['events'] if e['type']=='decision_evaluated']
        self.assertEqual(outcomes[1]['data']['learning']['passed'],['concrete'])
        folder=base.ROOT/'output'/'pedagogy-specific';folder.mkdir(exist_ok=True,parents=True)
        exported=folder/'ui-progression.json';exported.write_text(json.dumps(self.state(),ensure_ascii=False,indent=2),encoding='utf8')
        dashboard=self.context.new_page();dashboard.goto(base.BASE+'/admin.html')
        dashboard.locator('#file').set_input_files(str(exported))
        expect(dashboard.locator('#decision')).to_contain_text('transfer')
        expect(dashboard.locator('#decision')).to_contain_text('resuelto sin ayuda')
        dashboard.screenshot(path=str(folder/'dashboard.png'),full_page=True)
        dashboard.close()

    def test_02_reading_self_report_expires_without_error(self):
        self.pregame()
        self.advance(46000,active=False)
        self.page.locator('#reading').click()
        before=self.state()['knowledge']
        self.advance(70000,active=False)
        expect(self.page.locator('#modal')).not_to_be_visible()
        self.assertEqual(before,self.state()['knowledge'])
        self.advance(51000,active=False)
        expect(self.page.locator('#modal')).to_be_visible()
        self.assertEqual(len([e for e in self.state()['events'] if e['type']=='reading_confirmed']),1)

    def test_03_microblock_waits_for_response_and_closes_once(self):
        self.pregame()
        key=self.state()['current']['key']
        self.advance(95000)
        self.assertEqual(self.state()['current']['key'],key)
        self.assertFalse(any(e['type']=='learning_block_completed' for e in self.state()['events']))
        self.solve();self.page.locator('[data-action=next]').click()
        blocks=[e for e in self.state()['events'] if e['type']=='learning_block_completed']
        self.assertEqual(len(blocks),1);self.assertEqual(blocks[0]['data']['tasks'],[key])
        self.assertGreaterEqual(blocks[0]['data']['activeMs'],90000)
        expect(self.page.get_by_text('Terminaste una parte del camino.',exact=False)).to_be_visible()
        self.page.reload();self.solve();self.page.locator('[data-action=next]').click()
        self.assertEqual(len([e for e in self.state()['events'] if e['type']=='learning_block_completed']),1)

    def test_04_equivalence_uses_visible_target_denominator(self):
        self.pregame()
        for _ in range(4):
            self.solve();self.page.locator('[data-action=next]').click()
        targets=set()
        for _ in range(4):
            task=self.state()['current']['task']
            self.assertEqual(task['id'],'equivalent')
            target=task['targetDen'];targets.add(target)
            expect(self.page.locator('#answer-form label')).to_contain_text(f'denominador {target}')
            expect(self.page.locator('.equation .fraction').last).to_contain_text(str(target))
            self.solve();self.page.locator('[data-action=next]').click()
        self.assertTrue(any(target!=8 for target in targets))

    def test_05_exhausted_bank_preserves_progress_and_requests_review(self):
        # Focused migration fixture, distinct from the UI-only behavior matrix.
        self.pregame()
        self.page.goto(base.BASE+'/admin.html')
        self.page.evaluate("""() => {
          const key='isla-luma-v1', s=JSON.parse(localStorage.getItem(key));
          const k=s.learning.skills.meaning;k.passed=['concrete','pictorial','abstract'];
          let task;
          do { task=Luma.learningTask('meaning',s.serial++,s.learning);
            if (!task.bankExhausted) Luma.recordLearning(s.learning,task,true,true);
          } while (!task.bankExhausted);
          s.current=null;localStorage.setItem(key,JSON.stringify(s));
        }""")
        before=self.state()['knowledge']
        self.page.goto(base.BASE)
        expect(self.page.get_by_text('Has explorado todos estos retos.',exact=True)).to_be_visible()
        state=self.state()
        self.assertEqual(state['knowledge'],before)
        self.assertEqual(state['completionReason'],'bank_exhausted')
        self.assertNotIn('transfer',state['learning']['skills']['meaning']['passed'])
        self.assertEqual(sum(e['type']=='item_bank_exhausted' for e in state['events']),1)
        self.page.reload()
        self.assertEqual(sum(e['type']=='item_bank_exhausted' for e in self.state()['events']),1)

if __name__=='__main__':unittest.main(verbosity=2)
