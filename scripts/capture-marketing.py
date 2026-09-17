"""Capture real UI actions in an isolated browser; publish no gameplay exports."""
from pathlib import Path
import io,json
from PIL import Image
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/media';OUT.mkdir(parents=True,exist_ok=True)
frames=[]
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':1100,'height':760},reduced_motion='reduce')
    page=context.new_page();page.goto('http://127.0.0.1:4173/?simulation=1')
    def snap(name=None):
        page.mouse.move(0,0);page.wait_for_timeout(180)
        data=page.screenshot()
        if name:(OUT/name).write_bytes(data)
        frames.append(Image.open(io.BytesIO(data)).convert('RGB').resize((960,663)))
    snap('island.png')
    page.get_by_role('button',name='Explorar con Luma').click();snap()
    page.get_by_role('button',name='Guíame, Luma',exact=True).click()
    for name in ['Invernadero','Estación','Jardín']:page.get_by_role('button',name=name,exact=True).click();snap()
    page.get_by_role('button',name='Ir al invernadero').click();snap()
    for name in ['flor','luna','rombo']:
        page.get_by_role('button',name=f'Elegir criatura {name}',exact=True).click();snap()
        page.get_by_role('button',name=f'Refugio {name}',exact=True).click();snap()
    page.get_by_role('button',name='Ir a la estación').click();snap()
    for _ in range(3):
        for name in page.locator('.steps').get_attribute('aria-label').removeprefix('Señal: ').split(', '):page.get_by_role('button',name=f'Añadir {name}',exact=True).click()
        page.get_by_role('button',name='Enviar señal',exact=True).click()
    page.get_by_role('button',name='Ir al jardín').click();snap()
    page.get_by_role('button',name='Cambiar planta del centro',exact=True).click();snap()
    page.get_by_role('button',name='Terminar mi jardín y continuar').click()
    page.get_by_role('button',name='Entrar al taller').click()
    page.locator('.experience-chooser summary').click();page.locator('[data-action=experience][data-profile=visual]').click();snap('workshop.png')
    page.locator('[data-action=experience_cell][data-index="0"]').click();snap()
    page.locator('[data-action=experience_submit]').click();snap()
    page.locator('[data-action=next]').click();page.locator('[data-action=dont_know]').click();snap()
    # GIFs are edited sequences of authentic screenshots, not invented product states.
    palette=[f.quantize(colors=128,method=Image.Quantize.MEDIANCUT) for f in frames]
    palette[0].save(OUT/'gameplay.gif',save_all=True,append_images=palette[1:],duration=1100,loop=0,optimize=True)
    dashboard=context.new_page();dashboard.goto('http://127.0.0.1:4173/admin.html')
    dashboard.locator('#scenario').select_option('recovery');dashboard.locator('#run').click()
    dashboard.locator('#metrics').scroll_into_view_if_needed();dashboard.screenshot(path=str(OUT/'dashboard.png'))
    dframes=[]
    for index in [0,2,4,6,8,10]:
        maximum=int(dashboard.locator('#step').get_attribute('max'));value=min(maximum,index)
        dashboard.locator('#step').fill(str(value));dashboard.locator('#metrics').scroll_into_view_if_needed()
        data=dashboard.screenshot();dframes.append(Image.open(io.BytesIO(data)).convert('RGB').resize((960,663)).quantize(colors=128))
    dframes[0].save(OUT/'feedback-loop.gif',save_all=True,append_images=dframes[1:],duration=1500,loop=0,optimize=True)
    browser.close()
print(json.dumps({p.name:p.stat().st_size for p in OUT.iterdir()}))
