"""Check the assembled public site, its media, and nested game/lab links."""
from pathlib import Path
import os,json
from playwright.sync_api import sync_playwright,expect
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/marketing';OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get('LUMA_SITE_URL','http://127.0.0.1:4180/')
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    context=browser.new_context(viewport={'width':1440,'height':1000},reduced_motion='reduce')
    page=context.new_page();errors=[];bad=[]
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.on('response',lambda r:bad.append(r.url) if r.status>=400 and r.url.startswith(BASE) else None)
    page.goto(BASE);expect(page.get_by_role('heading',level=1)).to_contain_text('Every next step')
    page.locator('.demo-section').scroll_into_view_if_needed()
    page.wait_for_function('Array.from(document.images).every(i=>i.complete&&i.naturalWidth>0)')
    for width in [1440,390,320]:
        page.set_viewport_size({'width':width,'height':1000});page.evaluate('scrollTo(0,0)')
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        page.screenshot(path=str(OUT/f'landing-{width}.png'),full_page=True)
    page.set_viewport_size({'width':1280,'height':900})
    page.get_by_role('link',name='Explore the island').click()
    expect(page.get_by_role('button',name='Explorar con Luma')).to_be_visible()
    assert '/play/?simulation=1' in page.url
    page.goto(BASE+'play/admin.html');expect(page.locator('#status')).to_contain_text('verificaciones')
    page.locator('#preview').click()
    expect(page.frame_locator('#game').get_by_role('button',name='Probar',exact=True)).to_be_visible()
    assert page.locator('#game').get_attribute('src')=='./?simulation=1'
    assert not errors,errors
    assert not bad,bad
    browser.close()
for name in ['gameplay.gif','feedback-loop.gif']:
    im=Image.open(ROOT/'assets/media'/name);assert im.n_frames>1;assert (ROOT/'assets/media'/name).stat().st_size<2000000
result={'base':BASE,'widths':[1440,390,320],'checks':['landing images load','no horizontal overflow','game simulation link','nested lab preview','no JavaScript errors','no local HTTP errors','two animated GIFs under 2 MB each'],'status':'passed'}
(OUT/'result.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
