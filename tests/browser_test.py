"""Pruebas de navegador real. Ejecutar: python tests/browser_test.py

Requiere Playwright para Python y Google Chrome. Contextos aislados: no se usa
el perfil personal. El reloj de Playwright acelera el tiempo, no las reglas.
"""
import json
import re
import unittest
from datetime import datetime, timezone, timedelta
from fractions import Fraction
from pathlib import Path

from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'output' / 'playwright'
BASE = 'http://127.0.0.1:4173'


class BrowserTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ARTIFACTS.mkdir(parents=True, exist_ok=True)
        cls.pw = sync_playwright().start()
        cls.browser = cls.pw.chromium.launch(channel='chrome', headless=True)
        print(f'\nChrome real: {cls.browser.version}', flush=True)

    @classmethod
    def tearDownClass(cls):
        cls.browser.close()
        cls.pw.stop()

    def setUp(self):
        self.context = self.browser.new_context(viewport={'width': 1440, 'height': 1000}, reduced_motion='reduce')
        self.context.tracing.start(screenshots=True, snapshots=True, sources=True)
        self.page = self.context.new_page()
        self.page.set_default_timeout(4000)
        self.errors = []
        self.requests = []
        self.page.on('pageerror', lambda error: self.errors.append(str(error)))
        self.page.on('request', lambda request: self.requests.append(request.url))
        start = datetime(2026, 9, 16, 12, tzinfo=timezone.utc)
        self.page.clock.install(time=start)
        self.page.clock.pause_at(start + timedelta(seconds=1))
        self.page.goto(BASE)

    def tearDown(self):
        self.page.screenshot(path=str(ARTIFACTS / (self._testMethodName + '.png')), full_page=True)
        self.context.tracing.stop(path=str(ARTIFACTS / (self._testMethodName + '.zip')))
        self.context.close()
        self.assertEqual(self.errors, [], 'Errores JavaScript del navegador')
        self.assertTrue(all(url.startswith(BASE) or url.startswith('blob:') for url in self.requests), self.requests)

    def state(self):
        return self.page.evaluate("JSON.parse(localStorage.getItem('isla-luma-v1'))")

    def start(self):
        self.page.get_by_role('button', name='Explorar con Luma').click()

    def advance(self, milliseconds, active=True):
        remaining = milliseconds
        while remaining:
            chunk = min(10000, remaining)
            if active:
                # Una acción normal del teclado renueva la actividad sin responder retos.
                self.page.keyboard.press('Shift')
            self.page.clock.run_for(chunk)
            remaining -= chunk

    def go_math(self):
        self.start()
        self.advance(300000)
        self.page.get_by_role('button', name='Entrar al taller').click()
        expect(self.page.get_by_role('heading', name='Partes de un entero')).to_be_visible()

    def screenshot(self, name):
        self.page.screenshot(path=str(ARTIFACTS / name), full_page=True)

    def test_01_complete_adventure_and_telemetry(self):
        self.screenshot('desktop-home.png')
        self.start()
        self.page.get_by_role('button', name='Quiero explorar', exact=True).click()
        self.page.get_by_role('button', name='Invernadero', exact=False).click()
        expect(self.page.locator('#feedback')).to_contain_text('refugio')
        self.page.get_by_role('button', name='Guíame, Luma', exact=True).click()
        self.advance(60000)
        expect(self.page.get_by_role('heading', name='El refugio de las hojas')).to_be_visible()
        self.page.get_by_role('button', name='Elegir criatura flor', exact=True).click()
        for _ in range(3):
            self.page.get_by_role('button', name='Refugio luna', exact=True).click()
        self.assertTrue(any(e['type']=='adaptation' and e['data']['rule']=='three_failures' for e in self.state()['events']))
        self.page.get_by_role('button', name='Refugio flor', exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('Encontró su refugio')
        self.screenshot('desktop-refugio.png')
        self.advance(90000)
        expect(self.page.get_by_role('heading', name='Una señal entre las nubes')).to_be_visible()
        self.page.get_by_role('button', name='Añadir luna', exact=True).click()
        self.page.get_by_role('button', name='Deshacer', exact=True).click()
        for name in ['flor','rombo','luna']:
            self.page.get_by_role('button', name=f'Añadir {name}', exact=True).click()
        self.page.get_by_role('button', name='Enviar señal', exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('La señal llegó')
        self.screenshot('desktop-signal.png')
        self.advance(90000)
        self.page.get_by_role('button', name='Cambiar planta del centro', exact=True).click()
        self.page.get_by_role('button', name='Cambiar ambiente', exact=True).click()
        self.advance(59000)
        self.assertEqual(self.state()['phase'], 'play')
        self.advance(1000)
        expect(self.page.get_by_role('button', name='Entrar al taller')).to_be_visible()
        state = self.state()
        self.assertEqual(state['playMs'], 300000)
        self.assertTrue(all(k['n']==0 and k['p']==0.5 for k in state['knowledge'].values()))
        for event in ['route_selected','navigation','post_error_action','attempt','strategy_changed','creative_change','playtest_completed']:
            self.assertTrue(any(e['type']==event for e in state['events']), event)
        (ARTIFACTS / 'sample-telemetry.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')

    def test_02_pauses_reload_and_family_export(self):
        self.start()
        self.advance(10000)
        self.page.get_by_role('button', name='Pausar', exact=True).click()
        before = self.state()['playMs']
        self.advance(60000, active=False)
        self.assertEqual(self.state()['playMs'], before)
        self.page.keyboard.press('Escape')
        expect(self.page.locator('#modal')).not_to_be_visible()
        self.advance(45000, active=False)
        expect(self.page.get_by_role('heading', name='La isla puede esperar.')).to_be_visible()
        self.page.get_by_role('button', name='Seguir explorando', exact=True).click()
        self.page.get_by_role('button', name='Familias', exact=True).click()
        self.page.get_by_text('Observaciones de la familia', exact=True).click()
        self.page.get_by_role('button', name='Guardar observaciones', exact=True).click()
        expect(self.page.locator('#parent-status')).to_contain_text('necesitamos las tres respuestas')
        self.page.locator('[name=channel]').select_option('visual')
        self.page.locator('[name=interest]').select_option('explorador')
        self.page.locator('[name=response]').select_option('help')
        self.page.get_by_role('button', name='Guardar observaciones', exact=True).click()
        self.page.get_by_text('Registro y adaptación', exact=True).click()
        with self.page.expect_download() as info:
            self.page.get_by_role('button', name='Exportar registro completo (JSON)', exact=True).click()
        export = info.value
        exported = json.loads(Path(export.path()).read_text(encoding='utf-8'))
        self.assertFalse(exported['profile']['provisional'])
        self.assertEqual(exported['parent']['response'], 'help')
        self.page.get_by_role('button', name='Volver a la isla', exact=True).click()
        before = self.state()['playMs']
        self.page.reload()
        self.assertEqual(self.state()['playMs'], before)
        self.assertEqual(self.state()['parent']['channel'], 'visual')

    def test_03_math_prerequisites_all_operations(self):
        self.go_math()
        visited = set()
        for _ in range(24):
            visited.add(self.page.locator('h2').inner_text())
            if self.page.locator('.task-facts').count():
                n,d=map(int,re.findall(r'\d+',self.page.locator('.task-facts').inner_text()))
                answer=f'{n}/{d}'
            elif self.page.locator('.equation .fraction').count() == 0:
                label = self.page.locator('.scene .bar').first.get_attribute('aria-label')
                n,d = map(int,re.findall(r'\d+',label))
                answer = f'{n}/{d}'
            elif self.page.locator('.equation').inner_text().find('?\n8') >= 0:
                parts = self.page.locator('.equation .fraction').first.locator('span').all_inner_texts()
                n,d = map(int,parts)
                answer = f'{n*8//d}/8'
            else:
                parts = self.page.locator('.equation .fraction').all_inner_texts()
                a,b = [Fraction(*map(int,part.split())) for part in parts]
                value = a-b if '−' in self.page.locator('.equation').inner_text() else a+b
                answer = f'{value.numerator}/{value.denominator}'
            self.page.get_by_role('textbox', name='Tu respuesta').fill(answer)
            self.page.get_by_role('button', name='Probar', exact=True).click()
            expect(self.page.locator('#feedback')).to_contain_text('La energía llegó')
            self.page.get_by_role('button', name='Siguiente descubrimiento').click()
        self.assertEqual(len(visited), 6)
        self.assertTrue(all(k['n']>=3 and k['p']>=.85 for k in self.state()['knowledge'].values()))
        self.screenshot('desktop-math.png')

    def test_04_draft_and_workspace_survive_help_and_reload(self):
        self.go_math()
        self.page.get_by_role('textbox', name='Tu respuesta').fill('1/4')
        self.page.get_by_role('button', name='Probar con Luma').click()
        expect(self.page.get_by_role('textbox', name='Tu respuesta')).to_have_value('1/4')
        piece = self.page.locator('[data-action=piece]').first
        piece.click()
        self.page.get_by_role('button', name='Dame una pista', exact=True).click()
        self.page.get_by_role('button', name='Probar con Luma').click()
        expect(piece).to_have_attribute('aria-pressed','true')
        self.page.reload()
        expect(self.page.get_by_role('textbox', name='Tu respuesta')).to_have_value('1/4')
        expect(piece).to_have_attribute('aria-pressed','true')
        self.page.get_by_role('button', name='Probar', exact=True).click()
        self.assertEqual(self.state()['knowledge']['meaning']['n'],0)

    def test_05_keyboard_focus_survives_scene_interactions(self):
        self.start()
        self.advance(60000)
        creature = self.page.get_by_role('button', name='Elegir criatura flor', exact=True)
        creature.focus()
        self.page.keyboard.press('Enter')
        expect(creature).to_be_focused()
        self.page.keyboard.press('Tab')
        self.assertNotEqual(self.page.evaluate('document.activeElement.tagName'),'BODY')

    def test_06_mobile_layout(self):
        self.page.set_viewport_size({'width':390,'height':844})
        self.screenshot('mobile-home.png')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
        self.start()
        for duration,name in [(60000,'mobile-refugio.png'),(90000,'mobile-signal.png'),(90000,'mobile-garden.png'),(60000,'mobile-bridge.png')]:
            self.advance(duration)
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)
            self.screenshot(name)
        self.page.get_by_role('button', name='Entrar al taller').click()
        self.page.get_by_role('button', name='Probar con Luma').click()
        self.screenshot('mobile-math.png')
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),390)

    def test_07_audio_unavailable_fallback(self):
        self.start()
        # Solo esta prueba simula una capacidad que el navegador puede no ofrecer.
        self.page.evaluate("Object.defineProperty(window, 'speechSynthesis', {value: undefined, configurable: true})")
        self.page.get_by_role('button', name='Escuchar', exact=False).click()
        expect(self.page.locator('#feedback')).to_contain_text('escrita')
        self.assertTrue(any(e['type']=='support_unavailable' for e in self.state()['events']))

    def test_08_construct_answer_without_typing(self):
        self.go_math()
        self.page.get_by_role('button', name='Probar con Luma').click()
        self.page.locator('[data-action=piece]').first.click()
        self.page.get_by_role('button', name='Responder con mis piezas', exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('La energía llegó')
        state = self.state()
        self.assertEqual(state['knowledge']['meaning']['n'],0)
        attempt = [e for e in state['events'] if e['type']=='attempt'][-1]
        self.assertEqual(attempt['data']['cpaPhase'],'concrete')
        self.assertEqual(attempt['data']['attemptNumber'],1)
        self.assertTrue(attempt['data']['assisted'])
        self.screenshot('constructed-answer.png')

    def test_09_support_duration_excludes_pause(self):
        self.start()
        self.page.get_by_role('button', name='Ver una pista', exact=False).click()
        self.advance(5000)
        self.page.get_by_role('button', name='Pausar', exact=True).click()
        self.advance(60000,active=False)
        self.page.get_by_role('button', name='Seguir explorando', exact=True).click()
        self.advance(5000)
        self.page.get_by_role('button', name='Probar con Luma').click()
        observations = [e for e in self.state()['events'] if e['type']=='support_exposure']
        self.assertEqual(sum(e['data']['activeMs'] for e in observations),10000)

    def test_10_narrow_screen_and_touch_controls(self):
        self.page.set_viewport_size({'width':320,'height':740})
        self.start()
        self.advance(60000)
        expect(self.page.locator('.mission-instruction')).to_be_in_viewport()
        for target in ['creature','shelter']:
            for button in self.page.locator(f'[data-action={target}]').all():
                box=button.bounding_box()
                self.assertGreaterEqual(box['width'],44)
                self.assertGreaterEqual(box['height'],44)
        self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'),320)
        self.screenshot('narrow-320.png')

    def test_11_explored_map_can_advance_without_shortening_playtest(self):
        self.start()
        for place in ['Invernadero','Estación','Jardín']:
            self.page.get_by_role('button',name=place,exact=True).click()
        self.page.get_by_role('button',name='Ir al invernadero').click()
        expect(self.page.get_by_role('heading',name='El refugio de las hojas')).to_be_visible()
        self.advance(299000)
        self.assertEqual(self.state()['phase'],'play')
        self.advance(1000)
        self.assertEqual(self.state()['playMs'],300000)
        self.assertEqual(self.state()['phase'],'bridge')

    def test_12_correct_answers_finish_missions_without_waiting(self):
        """Regresión del bucle reportado: solo clics, sin adelantar el reloj."""
        self.start()
        for name in ['Invernadero','Estación','Jardín']:
            self.page.get_by_role('button',name=name,exact=True).click()
        self.page.get_by_role('button',name='Ir al invernadero').click()
        for name in ['flor','luna','rombo']:
            expect(self.page.locator('.creature-target')).to_contain_text(name)
            self.page.get_by_role('button',name=f'Elegir criatura {name}',exact=True).click()
            self.page.get_by_role('button',name=f'Refugio {name}',exact=True).click()
            if name=='luna':
                self.page.reload()
                self.assertEqual(self.state()['playProgress']['rescued'],[0,1])
        expect(self.page.get_by_role('heading',name='¡Todas las criaturas están a salvo!')).to_be_visible()
        expect(self.page.locator('[data-action=shelter]')).to_have_count(0)
        self.screenshot('refuge-completed.png')
        self.page.get_by_role('button',name='Ir a la estación').click()
        for pattern in [['flor','rombo','luna'],['luna','flor','rombo'],['rombo','luna','flor']]:
            for name in pattern:
                self.page.get_by_role('button',name=f'Añadir {name}',exact=True).click()
            self.page.get_by_role('button',name='Enviar señal',exact=True).click()
        expect(self.page.get_by_role('heading',name='¡La antena ya está conectada!')).to_be_visible()
        expect(self.page.locator('[data-action=signal]')).to_have_count(0)
        self.page.reload()
        self.page.get_by_role('button',name='Ir al jardín').click()
        self.page.get_by_role('button',name='Cambiar planta del centro',exact=True).click()
        self.page.get_by_role('button',name='Terminar mi jardín y continuar').click()
        self.assertEqual(self.state()['phase'],'bridge')
        self.assertEqual(self.state()['playProgress']['signals'],3)
        self.assertLess(self.state()['playMs'],300000)
        completion=[e for e in self.state()['events'] if e['type']=='playtest_completed']
        self.assertEqual(len(completion),1)
        self.assertEqual(completion[0]['data']['reason'],'child_finished_objectives')
        self.page.get_by_role('button',name='Entrar al taller').click()
        self.page.get_by_role('textbox',name='Tu respuesta').fill('1/4')
        self.page.get_by_role('button',name='Probar',exact=True).click()
        expect(self.page.get_by_role('button',name='Siguiente descubrimiento')).to_be_visible()

    def test_13_legacy_repeated_correct_answers_migrate(self):
        self.start()
        self.advance(60000)
        # Fixture de la versión anterior: aciertos repetidos, sin contadores de misión.
        legacy=self.state()
        del legacy['playProgress']
        for i in range(6):
            legacy['events'].append({'type':'attempt','data':{'activity':'shelter','correct':True,'choice':i%3}})
        legacy['round']=6
        # Instalar antes del código de la app; pagehide guarda legítimamente la sesión saliente.
        self.page.add_init_script("localStorage.setItem('isla-luma-v1',"+json.dumps(json.dumps(legacy))+");")
        self.page.reload()
        expect(self.page.get_by_role('button',name='Ir a la estación')).to_be_visible()
        expect(self.page.locator('[data-action=shelter]')).to_have_count(0)
        self.assertEqual(self.state()['playProgress']['rescued'],[0,1,2])

    def test_14_entire_mvp_real_clock_errors_help_and_finish(self):
        """Partida completa mediante la interfaz, sin reloj virtual ni estado inyectado."""
        self.context.tracing.stop()
        self.context.close()
        self.context=self.browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
        self.context.tracing.start(screenshots=True,snapshots=True,sources=True)
        self.page=self.context.new_page()
        self.page.set_default_timeout(4000)
        self.page.on('pageerror',lambda error:self.errors.append(str(error)))
        self.page.on('request',lambda request:self.requests.append(request.url))
        self.page.goto(BASE)
        self.start()
        self.page.get_by_role('button',name='Guíame, Luma',exact=True).click()
        for name in ['Invernadero','Estación','Jardín']:
            self.page.get_by_role('button',name=name,exact=True).click()
        self.page.get_by_role('button',name='Ir al invernadero').click()
        self.page.get_by_role('button',name='Elegir criatura flor',exact=True).click()
        self.page.get_by_role('button',name='Refugio luna',exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('distinta')
        self.page.get_by_role('button',name='Probar con Luma').click()
        self.page.get_by_role('button',name='Refugio flor',exact=True).click()
        for name in ['luna','rombo']:
            self.page.get_by_role('button',name=f'Elegir criatura {name}',exact=True).click()
            self.page.get_by_role('button',name=f'Refugio {name}',exact=True).click()
        self.page.get_by_role('button',name='Ir a la estación').click()
        self.page.get_by_role('button',name='Enviar señal',exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('todavía')
        for _ in range(3):
            self.page.get_by_role('button',name='Añadir flor',exact=True).click()
        self.page.get_by_role('button',name='Enviar señal',exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('diferente')
        for _ in range(3):
            pattern=self.page.locator('.steps').get_attribute('aria-label').removeprefix('Señal: ').split(', ')
            for name in pattern:
                self.page.get_by_role('button',name=f'Añadir {name}',exact=True).click()
            self.page.get_by_role('button',name='Enviar señal',exact=True).click()
        self.page.get_by_role('button',name='Ir al jardín').click()
        self.page.get_by_role('button',name='Cambiar planta del centro',exact=True).click()
        self.page.get_by_role('button',name='Cambiar ambiente',exact=True).click()
        self.page.get_by_role('button',name='Una idea de Luma',exact=True).click()
        self.page.get_by_role('button',name='Terminar mi jardín y continuar').click()
        self.page.get_by_role('button',name='Entrar al taller').click()
        self.page.get_by_role('textbox',name='Tu respuesta').fill('1/0')
        self.page.get_by_role('button',name='Probar',exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('mayor que cero')
        self.page.get_by_role('textbox',name='Tu respuesta').fill('1/3')
        self.page.get_by_role('button',name='Probar',exact=True).click()
        expect(self.page.locator('#feedback')).to_contain_text('Todavía no coincide')
        self.page.get_by_role('button',name='Probar con Luma').click()
        self.page.locator('[data-action=piece]').first.click()
        self.page.get_by_role('button',name='Responder con mis piezas',exact=True).click()
        self.page.get_by_role('button',name='Pausar',exact=True).click()
        expect(self.page.locator('#modal')).to_be_visible()
        self.page.get_by_role('button',name='Seguir explorando',exact=True).click()
        self.page.reload()
        self.page.get_by_role('button',name='Siguiente descubrimiento').click()
        self.page.get_by_role('button',name='Quiero descansar',exact=True).click()
        self.page.get_by_role('button',name='Volver al taller',exact=True).click()
        visited=set()
        for _ in range(40):
            if self.page.get_by_role('heading',name='¡El taller está encendido!').count():
                break
            visited.add(self.page.locator('h2').inner_text())
            if self.page.locator('.task-facts').count():
                n,d=map(int,re.findall(r'\d+',self.page.locator('.task-facts').inner_text()))
                answer=f'{n}/{d}'
            elif self.page.locator('.equation .fraction').count()==0:
                label=self.page.locator('.scene .bar').first.get_attribute('aria-label')
                n,d=map(int,re.findall(r'\d+',label))
                answer=f'{n}/{d}'
            elif self.page.get_by_text('Escribe tu respuesta con denominador 8.',exact=True).count():
                n,d=map(int,self.page.locator('.equation .fraction').first.locator('span').all_inner_texts())
                answer=f'{n*8//d}/8'
            else:
                a,b=[Fraction(*map(int,part.split())) for part in self.page.locator('.equation .fraction').all_inner_texts()]
                value=a-b if '−' in self.page.locator('.equation').inner_text() else a+b
                answer=f'{value.numerator}/{value.denominator}'
            self.page.get_by_role('textbox',name='Tu respuesta').fill(answer)
            self.page.get_by_role('button',name='Probar',exact=True).click()
            expect(self.page.locator('#feedback')).to_contain_text('La energía llegó')
            self.page.get_by_role('button',name='Siguiente descubrimiento').click()
        self.assertEqual(len(visited),6)
        expect(self.page.get_by_role('heading',name='¡El taller está encendido!')).to_be_visible()
        expect(self.page.get_by_role('textbox',name='Tu respuesta')).to_have_count(0)
        self.page.reload()
        expect(self.page.get_by_role('heading',name='¡El taller está encendido!')).to_be_visible()
        self.screenshot('full-game-completed.png')
        self.page.get_by_role('button',name='Familias',exact=True).click()
        self.page.get_by_text('Observaciones de la familia',exact=True).click()
        for field,value in [('channel','visual'),('interest','estructurado'),('response','help')]:
            self.page.locator(f'[name={field}]').select_option(value)
        self.page.get_by_role('button',name='Guardar observaciones',exact=True).click()
        self.page.get_by_text('Registro y adaptación',exact=True).click()
        with self.page.expect_download() as info:
            self.page.get_by_role('button',name='Exportar registro completo (JSON)',exact=True).click()
        exported=json.loads(Path(info.value.path()).read_text(encoding='utf-8'))
        self.assertEqual(exported['completionReason'],'mastery')
        self.assertTrue(all(k['p']>=.85 for k in exported['knowledge'].values()))
        events=exported['events']
        self.assertEqual(len(events),len({e['id'] for e in events}))
        self.assertEqual(len([e for e in events if e['type']=='learning_path_completed']),1)
        self.assertFalse(exported['profile']['provisional'])
        (ARTIFACTS/'full-game-telemetry.json').write_text(json.dumps(exported,ensure_ascii=False,indent=2),encoding='utf-8')
        self.page.get_by_role('button',name='Volver a la isla',exact=True).click()


if __name__ == '__main__':
    unittest.main(verbosity=2)
