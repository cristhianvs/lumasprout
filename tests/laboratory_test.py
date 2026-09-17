"""Pruebas del laboratorio con telemetría sintética explícita, no observación infantil."""
import json
import unittest
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'output' / 'simulations'
from browser_config import BASE, BROWSER_CHANNEL

class LaboratoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True, exist_ok=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel=BROWSER_CHANNEL, headless=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000})
        self.page = self.context.new_page()
        self.errors = []
        self.page.on('pageerror', lambda e: self.errors.append(str(e)))
        self.page.goto(BASE + '/admin.html')
        self.original = self.page.evaluate("JSON.stringify(LumaSimulation.run('visual').frames[0])")
        self.page.evaluate("s=>localStorage.setItem('isla-luma-v1',s)", self.original)

    def tearDown(self):
        self.assertEqual(self.page.evaluate("localStorage.getItem('isla-luma-v1')"), self.original)
        self.assertEqual(self.errors, [])
        self.context.close()

    def scenario(self, scenario, step=0):
        self.page.locator('#scenario').select_option(scenario)
        self.page.locator('#run').click()
        self.page.locator('#step').fill(str(step))
        self.page.locator('#step').dispatch_event('input')

    def preview(self):
        self.page.locator('#preview').click()
        frame = self.page.frame_locator('#game')
        expect(frame.locator('.experience-chooser')).to_be_visible()
        return frame

    def simulated(self):
        return self.page.evaluate("JSON.parse(localStorage.getItem('isla-luma-simulation-v1'))")

    def test_01_all_scenarios_render_actual_game(self):
        scenarios = self.page.evaluate('LumaSimulation.scenarios.map(s=>s.id)')
        for scenario in scenarios:
            with self.subTest(scenario=scenario):
                self.scenario(scenario)
                self.preview()
                state = self.simulated()
                inferred = self.page.evaluate('(s)=>Luma.inferProfile(s.events,s.parent?.scores)', state)
                self.assertEqual(state['current']['experience'], state.get('experienceChoice') or inferred['dominant'] or 'estructurado')
                self.assertEqual(state['knowledge']['meaning']['n'], 0)
                self.assertTrue(state['events'][-1]['simulation'])

    def test_02_recovery_scaffold_reload_and_feedback(self):
        index = self.page.evaluate("LumaSimulation.run('recovery').timeline.findIndex(t=>t.policy.support==='concrete')")
        self.scenario('recovery', index)
        frame = self.preview()
        expect(frame.get_by_text('Tu mesa de piezas:', exact=False)).to_be_visible()
        before = self.simulated()
        self.assertTrue(before['current']['assisted'])
        answer = before['current']['task']['answer']
        frame.locator('#answer').fill(f'{answer[0]}/{answer[1]}')
        frame.locator('#answer-form button').click()
        after = self.simulated()
        self.assertEqual(before['knowledge'], after['knowledge'])
        self.page.frames[1].goto(BASE + '/?simulation=1')
        expect(frame.locator('[data-action="next"]')).to_be_visible()
        frame.locator('[data-action="next"]').first.click()
        self.assertTrue(any(e['type']=='adaptation_decision' for e in self.simulated()['events']))
        self.page.screenshot(path=str(OUT / 'laboratory-preview.png'), full_page=True)
        recovered = self.page.evaluate("LumaSimulation.run('recovery').timeline.findIndex((t,i)=>i>5&&t.policy.support==='pictorial')")
        self.scenario('recovery', recovered)
        self.preview()
        self.assertFalse(self.simulated()['current']['assisted'])
        self.assertEqual(self.simulated()['current']['supportMode'], 'visual')

    def test_03_batch_export_import_and_live(self):
        self.page.locator('#suite').click()
        self.assertEqual(self.page.locator('#suite-results .pass').count(), 12)
        self.assertEqual(self.page.locator('#suite-results .fail').count(), 0)
        with self.page.expect_download() as download:
            self.page.locator('#export').click()
        path = OUT / 'laboratory-export.json'
        download.value.save_as(path)
        data = json.loads(path.read_text(encoding='utf8'))
        self.assertEqual(len(data['batch']), 12)
        self.page.locator('#file').set_input_files(str(path))
        expect(self.page.locator('#status')).to_contain_text('Registro importado')
        self.page.locator('#source').select_option('live')
        expect(self.page.locator('#status')).to_contain_text('solo lectura')
        self.page.locator('#file').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':b'{"events":[]}'})
        expect(self.page.locator('#status')).to_contain_text('No se pudo importar')

    def test_04_no_audio_and_explicit_choice(self):
        self.scenario('no_audio')
        frame = self.preview()
        frame.locator('[data-action="rhythm"]').first.click()
        expect(frame.locator('#feedback')).to_contain_text('Puedes jugar sin sonido')
        self.assertTrue(any(e['type']=='audio_fallback' for e in self.simulated()['events']))
        self.scenario('choice')
        frame = self.preview()
        self.assertEqual(self.simulated()['current']['experience'], 'explorador')

    def test_05_mobile_and_dashboard_capture(self):
        self.page.locator('#suite').click()
        self.page.screenshot(path=str(OUT / 'laboratory-desktop.png'), full_page=True)
        self.page.set_viewport_size({'width':360,'height':800})
        self.assertTrue(self.page.evaluate('document.documentElement.scrollWidth <= innerWidth'), self.page.evaluate("Array.from(document.querySelectorAll('*')).filter(e=>e.getBoundingClientRect().right>innerWidth).map(e=>[e.tagName,e.id,e.className,e.getBoundingClientRect().right])"))
        self.page.screenshot(path=str(OUT / 'laboratory-mobile.png'), full_page=True)

if __name__ == '__main__':
    unittest.main(verbosity=2)
