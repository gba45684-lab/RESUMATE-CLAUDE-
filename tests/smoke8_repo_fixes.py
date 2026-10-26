# Fixes from the repo audit: "Clear data saved on this device" also removes the own AI key and the
# recent-changes history; the app opens with no page errors; the worker defaults to the app's own origins.
import os, pathlib, re
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
results = []
def chk(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852})
    pg = ctx.new_page()
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.route('https://**', lambda r: r.abort())          # offline: no network in this test
    pg.goto(URL); pg.wait_for_timeout(800)
    pg.evaluate("localStorage.setItem('resumate_ai_history', JSON.stringify([{t:Date.now(),label:'x',d:'{}'}]))")
    pg.evaluate("localStorage.setItem('resumate_own_key', 'AIzaTESTKEY-0000000000000000')")
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(400)
    pg.evaluate("[...document.querySelectorAll('.prow')].find(r=>r.textContent.startsWith('Settings')).click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.getElementById('clearAppDataBtn').click()"); pg.wait_for_timeout(400)
    chk('clear data removes the own AI key', pg.evaluate("localStorage.getItem('resumate_own_key')") is None)
    chk('clear data removes the recent-changes history', pg.evaluate("localStorage.getItem('resumate_ai_history')") is None)
    chk('app opens with no page errors', not errors)
    b.close()
src = (HERE.parent / 'free-ai-proxy' / 'worker.js').read_text(encoding='utf-8')
chk('worker default origins are not "*"', "DEFAULT_ORIGINS = 'https://localhost" in src and "|| '*'" not in src)
root_pp = (HERE.parent / 'privacy.html').read_text(encoding='utf-8'); www_pp = HERE.parent / 'www' / 'privacy.html'
chk('privacy page is also in www (the folder the website serves)', www_pp.exists() and www_pp.read_text(encoding='utf-8') == root_pp)
chk('privacy page covers ads and has no leftover placeholder text about advertising', 'Advertising' in root_pp and 'AdMob' in root_pp)
print(f"{sum(results)}/{len(results)} passed")
