"""Render original, code-authored brand layouts; no external image assets."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import base64
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'assets/media'
logo=(ROOT/'assets/brand/logo.svg').read_text(encoding='utf8')
shot=base64.b64encode((OUT/'island.png').read_bytes()).decode()
html='''<!doctype html><html><meta charset="utf-8"><style>
*{box-sizing:border-box}body{margin:0;background:#133e33;color:#f7f6e9;font-family:Arial,sans-serif;width:1200px;height:560px;overflow:hidden}.grid{position:absolute;inset:0;background-image:linear-gradient(#ffffff05 1px,transparent 1px),linear-gradient(90deg,#ffffff05 1px,transparent 1px);background-size:40px 40px}.copy{position:absolute;top:65px;left:65px;z-index:2}.mark{display:flex;align-items:center;gap:16px;font-size:15px;letter-spacing:2px}.mark svg{width:60px;height:60px;border:1px solid #71956c66;border-radius:18px}h1{font-size:80px;letter-spacing:-4px;margin:30px 0 16px;font-weight:600}.tag{font-size:28px;line-height:1.35;color:#d5efb7;margin:0}.small{margin-top:38px;font-size:13px;letter-spacing:1.5px;color:#c4d9cd}.shot{position:absolute;left:734px;top:95px;width:590px;transform:rotate(-7deg);border:8px solid #739273;border-radius:22px;box-shadow:0 20px 70px #0005;z-index:1}.circle{position:absolute;width:480px;height:480px;border-radius:50%;background:#2b5942;right:-50px;top:30px}.pill{position:absolute;right:45px;bottom:45px;background:#f0b99c;color:#173e34;padding:14px 22px;border-radius:100px;font-size:14px;font-weight:bold;z-index:3}.line{position:absolute;bottom:0;height:9px;width:100%;background:linear-gradient(90deg,#d5efb7 0 50%,#f0b99c 50% 80%,#e9bd69 80%)}
</style><body><div class="grid"></div><div class="circle"></div><div class="copy"><div class="mark">LOGO <span>PLAY. OBSERVE. ADAPT.</span></div><h1>LumaSprout</h1><p class="tag">Every next step<br>has a reason.</p><p class="small">AN OPEN-SOURCE LEARNING ADVENTURE</p></div><img class="shot" src="data:image/png;base64,SHOT"><div class="pill">Come build the next discovery ↗</div><div class="line"></div></body></html>'''.replace('LOGO',logo).replace('SHOT',shot)
with sync_playwright() as pw:
    browser=pw.chromium.launch(channel='chrome',headless=True)
    page=browser.new_page(viewport={'width':1200,'height':560},device_scale_factor=1)
    page.set_content(html);page.screenshot(path=str(OUT/'hero.png'))
    page.set_viewport_size({'width':1200,'height':630});page.add_style_tag(content='body{height:630px}.copy{top:85px}.shot{top:120px}.pill{bottom:60px}')
    page.screenshot(path=str(OUT/'social-card.png'));browser.close()
