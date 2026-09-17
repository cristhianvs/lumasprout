"""Cuatro recorridos completos por la interfaz de Chrome; sin inyectar perfiles ni respuestas."""
import json
import re
import unittest
from fractions import Fraction
import browser_test as base
from browser_test import ARTIFACTS
from playwright.sync_api import expect

class ProfileTests(unittest.TestCase):
    setUpClass = classmethod(base.BrowserTests.setUpClass.__func__)
    tearDownClass = classmethod(base.BrowserTests.tearDownClass.__func__)
    setUp = base.BrowserTests.setUp
    tearDown = base.BrowserTests.tearDown
    state = base.BrowserTests.state
    start = base.BrowserTests.start
    screenshot = base.BrowserTests.screenshot

    def pregame(self):
        self.start()
        self.page.get_by_role('button',name='Guíame, Luma',exact=True).click()
        for name in ['Invernadero','Estación','Jardín']:
            self.page.get_by_role('button',name=name,exact=True).click()
        self.page.get_by_role('button',name='Ir al invernadero').click()
        for name in ['flor','luna','rombo']:
            self.page.get_by_role('button',name=f'Elegir criatura {name}',exact=True).click()
            self.page.get_by_role('button',name=f'Refugio {name}',exact=True).click()
        self.page.get_by_role('button',name='Ir a la estación').click()
        for _ in range(3):
            for name in self.page.locator('.steps').get_attribute('aria-label').removeprefix('Señal: ').split(', '):
                self.page.get_by_role('button',name=f'Añadir {name}',exact=True).click()
            self.page.get_by_role('button',name='Enviar señal',exact=True).click()
        self.page.get_by_role('button',name='Ir al jardín').click()
        self.page.get_by_role('button',name='Cambiar planta del centro',exact=True).click()
        self.page.get_by_role('button',name='Terminar mi jardín y continuar').click()
        self.page.get_by_role('button',name='Entrar al taller').click()

    def choose(self, profile):
        self.page.locator('.experience-chooser summary').click()
        self.page.locator(f'[data-action=experience][data-profile={profile}]').click()
        expect(self.page.locator('.experience-intro')).to_have_attribute('data-profile',profile)

    def answer_from_screen(self):
        if self.page.locator('.task-facts').count():
            return tuple(map(int,re.findall(r'\d+',self.page.locator('.task-facts').inner_text())))
        if self.page.locator('.equation .fraction').count()==0:
            n,d=map(int,re.findall(r'\d+',self.page.locator('.scene .bar').first.get_attribute('aria-label')))
            return n,d
        if self.page.locator('#answer-form label').inner_text().startswith('Escribe tu respuesta con denominador'):
            n,d=map(int,self.page.locator('.equation .fraction').first.locator('span').all_inner_texts())
            target=int(re.search(r'\d+',self.page.locator('#answer-form label').inner_text()).group())
            return n*target//d,target
        a,b=[Fraction(*map(int,part.split())) for part in self.page.locator('.equation .fraction').all_inner_texts()]
        value=a-b if '−' in self.page.locator('.equation').inner_text() else a+b
        return (value.numerator,value.denominator) if value.denominator>1 else (value.numerator*4,4)

    def construct(self,profile,n,d):
        if not self.page.locator('#experience-den').count():
            self.page.locator('#answer').fill(f'{n}/{d}')
            return
        self.page.locator('#experience-den').select_option(str(d))
        if profile=='estructurado':
            self.page.locator('#experience-num').fill(str(n))
            self.page.locator('[data-action=plan_step]').click()
        elif profile=='explorador':
            while self.page.locator('[data-action=cargo_remove]').is_enabled():
                self.page.locator('[data-action=cargo_remove]').click()
            for _ in range(n):
                self.page.locator('[data-action=cargo_add]').click()
        else:
            if profile=='visual':
                self.page.get_by_role('button',name='Pintar de azul',exact=True).click()
            for cell in self.page.locator('[data-action=experience_cell][aria-pressed=true]').all():
                cell.click()
            for i in range(n):
                self.page.locator(f'[data-action=experience_cell][data-index="{i}"]').click()

    def submit_constructed(self):
        if self.page.locator('[data-action=experience_submit]').count():
            self.page.locator('[data-action=experience_submit]').click()
        else:
            self.page.locator('#answer-form button').click()

    def run_profile(self,profile):
        self.pregame()
        self.choose(profile)
        self.assertEqual(self.state()['knowledge']['meaning']['n'],0)
        # Niño que se equivoca y solicita ayuda: la corrección no acredita dominio.
        self.construct(profile,0,4)
        self.submit_constructed()
        expect(self.page.locator('#feedback')).to_contain_text('Todavía')
        self.page.get_by_role('button',name='Dame una pista',exact=True).click()
        n,d=self.answer_from_screen()
        self.construct(profile,n,d)
        board=self.state()['current']['boards'][profile]
        self.page.reload()
        self.assertEqual(self.state()['current']['boards'][profile],board)
        if profile=='auditivo':
            self.page.locator('[data-action=rhythm][data-source=a]').click()
            expect(self.page.locator('#feedback')).to_contain_text('Escucha')
            self.page.locator('[data-action=rhythm][data-source=response]').click()
            self.page.get_by_role('button',name='Sonido encendido',exact=True).click()
        self.page.get_by_role('button',name='Pausar',exact=True).click()
        self.page.get_by_role('button',name='Seguir explorando',exact=True).click()
        self.submit_constructed()
        self.assertEqual(self.state()['knowledge']['meaning']['correct'],0)
        self.page.locator('[data-action=next]').click()
        visited=set()
        for i in range(35):
            if self.state()['phase']=='complete': break
            self.assertEqual(self.state()['current']['experience'],profile)
            visited.add(self.state()['current']['task']['id'])
            n,d=self.answer_from_screen()
            self.construct(profile,n,d)
            if i==2:
                self.screenshot(f'profile-{profile}-desktop.png')
                self.page.set_viewport_size({'width':320,'height':800})
                self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth<=innerWidth'))
                sizes=self.page.locator('#experience-workspace button').evaluate_all('(nodes)=>nodes.map(n=>n.getBoundingClientRect().height)')
                self.assertTrue(all(x>=44 for x in sizes))
                self.screenshot(f'profile-{profile}-mobile.png')
                self.page.set_viewport_size({'width':1440,'height':1000})
            self.submit_constructed()
            expect(self.page.locator('[data-action=next]')).to_be_visible()
            self.page.locator('[data-action=next]').click()
        expect(self.page.get_by_role('heading',name='¡El taller está encendido!')).to_be_visible()
        self.assertEqual(len(visited),6)
        state=self.state()
        self.assertTrue(all(k['p']>=.85 and k['n']>=3 for k in state['knowledge'].values()))
        self.assertTrue(all(e['experience']==profile for e in state['events'] if e['type']=='experience_answer'))
        self.assertEqual(state['rewards'][profile],len([e for e in state['events'] if e['type']=='experience_reward']))
        self.page.reload()
        self.assertEqual(self.state()['completionReason'],'mastery')
        (ARTIFACTS/f'profile-{profile}-telemetry.json').write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')

    def test_01_structured(self): self.run_profile('estructurado')
    def test_02_visual(self): self.run_profile('visual')
    def test_03_auditory(self): self.run_profile('auditivo')
    def test_04_explorer(self): self.run_profile('explorador')

    def test_05_switch_modes_without_reset_or_reward_farming(self):
        self.pregame()
        initial=self.state()['current']['key']
        self.choose('visual')
        self.construct('visual',1,4)
        self.choose('explorador')
        self.construct('explorador',2,8)
        self.choose('visual')
        self.assertEqual(self.state()['current']['boards']['visual']['cells'],[0])
        self.assertEqual(self.state()['current']['key'],initial)
        self.assertEqual(self.state()['knowledge']['meaning']['n'],0)
        self.submit_constructed()
        self.choose('auditivo')
        expect(self.page.locator('[data-action=experience_submit]')).to_be_disabled()
        self.assertEqual(sum(self.state()['rewards'].values()),1)
        self.page.locator('[data-action=next]').click()
        self.page.locator('.experience-chooser summary').click()
        self.page.locator('[data-action=experience_auto]').click()
        self.assertIsNone(self.state()['experienceChoice'])
        self.assertEqual(self.state()['knowledge']['meaning']['n'],1)

    def test_06_audio_unavailable_keyboard_response(self):
        self.pregame()
        self.choose('auditivo')
        self.page.evaluate('window.AudioContext=undefined;window.webkitAudioContext=undefined')
        self.page.locator('[data-action=rhythm][data-source=a]').click()
        expect(self.page.locator('#feedback')).to_contain_text('sin sonido')
        cell=self.page.locator('[data-action=experience_cell]').first
        cell.focus()
        self.page.keyboard.press('Space')
        expect(self.page.locator('[data-action=experience_cell]').first).to_be_focused()
        self.submit_constructed()
        self.assertEqual(self.state()['knowledge']['meaning']['correct'],1)

    def test_07_observed_preference_drives_automatic_assignment(self):
        self.pregame()
        for _ in range(5):
            self.choose('auditivo')
            n,d=self.answer_from_screen()
            self.construct('auditivo',n,d)
            self.submit_constructed()
            self.page.locator('[data-action=next]').click()
        self.page.locator('.experience-chooser summary').click()
        self.page.locator('[data-action=experience_auto]').click()
        self.assertEqual(self.state()['current']['experience'],'auditivo')
        n,d=self.answer_from_screen()
        self.construct('auditivo',n,d)
        self.submit_constructed()
        self.page.locator('[data-action=next]').click()
        event=[e for e in self.state()['events'] if e['type']=='experience_assigned'][-1]
        self.assertEqual(event['data']['source'],'observed_preference')
        self.assertEqual(event['data']['profile'],'auditivo')

if __name__=='__main__': unittest.main(verbosity=2)
