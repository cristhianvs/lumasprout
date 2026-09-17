"""Reproduce the pointer instability without seeding a saved game."""
import json
import time
from playwright.sync_api import sync_playwright
from behavior_matrix import Run,ROOT

with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    run=Run(browser,'visual','interruptions',ROOT/'output/behavior-motion-diagnostic')
    start=time.monotonic()
    diagnostic={}
    try:
        run.execute()
        diagnostic['initial']='passed'
    except Exception as error:
        diagnostic['initial']=str(error)
        button=run.page.get_by_role('button',name='Pintar de azul',exact=True)
        diagnostic['bounds']=[]
        for _ in range(8):
            diagnostic['bounds'].append(button.evaluate('(e)=>({rect:e.getBoundingClientRect().toJSON(),transform:getComputedStyle(e).transform,transition:getComputedStyle(e).transitionDuration,hover:e.matches(":hover"),scrollY,reduce:matchMedia("(prefers-reduced-motion:reduce)").matches})'))
            run.page.clock.run_for(17)
        run.page.mouse.move(0,0)
        try:
            button.click(timeout=2000)
            diagnostic['move_pointer_then_click']='passed'
        except Exception as second:
            diagnostic['move_pointer_then_click']=str(second)
    (run.out/'motion.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf8')
    print(json.dumps(diagnostic),flush=True)
    run.finish('diagnostic',None,time.monotonic()-start)
    browser.close()
