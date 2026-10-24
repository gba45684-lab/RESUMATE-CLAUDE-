import os, pathlib, json
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
results=[]
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name)
from playwright.sync_api import sync_playwright
PROXY='https://resumate-ai.gba45684.workers.dev/'
calls={'n':0}
def handler(route):
    calls['n']+=1; route.abort()
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True)
    ctx.route(PROXY+'**', handler)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')")
    pg.goto(URL); pg.wait_for_timeout(4800); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    # paywall copy is consistent and shows the free number
    txt=pg.evaluate("document.getElementById('paywall').textContent")
    check('upgrade sheet states the free AI runs', 'Free: 5 AI runs a day' in txt)
    check('upgrade sheet no longer promises unlimited AI', 'unlimited AI' not in txt)
    # offline: the AI says so at once and sends nothing
    ctx.set_offline(True); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('[data-ai-open=improve]').click()"); pg.wait_for_timeout(700)
    before=calls['n']
    pg.evaluate("document.getElementById('aiSuggest').click()"); pg.wait_for_timeout(900)
    check('offline: the app says it cannot reach the AI', "reach the AI" in pg.inner_text('#aiStatus') or 'offline' in pg.inner_text('#aiStatus').lower())
    check('offline: no request was sent', calls['n']==before)
    ctx.set_offline(False)
    # one-page help sheet
    pg.evaluate("document.getElementById('sheet2Close') && (document.querySelector('#sheet2.show') && document.querySelector('.ai-back') && document.querySelector('.ai-back').click())"); pg.wait_for_timeout(500)
    pg.evaluate("const f=document.getElementById('pvFit'); f.hidden=false; f.dataset.over='1.2'; f.click()"); pg.wait_for_timeout(600)
    sh=pg.inner_text('#sheet2').lower()
    check('one-page sheet opens with the overflow and the longest bullets', 'fit to one page' in sh and '20%' in sh)
    check('one-page sheet has edit buttons', pg.locator('#sheet2 [data-fit-edit]').count()>=1)
    pg.locator('#sheet2 [data-fit-edit]').first.click(timeout=3000); pg.wait_for_timeout(900)
    check('Edit goes to the Experience step', 'Experience' in pg.inner_text('#stepLabel'))
    check('no page errors', not errs)
    if errs: print(errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed"); raise SystemExit(0 if all(results) else 1)
