import os, pathlib, json
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
results=[]
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name)
from playwright.sync_api import sync_playwright
PROXY='https://resumate-ai.gba45684.workers.dev/'
def handler(route):
    cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Expose-Headers':'X-Free-Limit, X-Free-Remaining'}
    if route.request.method=='OPTIONS': route.fulfill(status=204, headers=cors); return
    out={"summary":"Product leader who scaled products across three teams.","experience":[],"skills_add":[],"tips":[]}
    route.fulfill(status=200, headers={**cors,'Content-Type':'application/json','X-Free-Limit':'5','X-Free-Remaining':'3'}, body=json.dumps({"candidates":[{"content":{"parts":[{"text":json.dumps(out)}]}}]}))
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':393,'height':852},has_touch=True,is_mobile=True,accept_downloads=True)
    ctx.route(PROXY+'**', handler)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.add_init_script("window.__csp=[];document.addEventListener('securitypolicyviolation',e=>window.__csp.push(e.violatedDirective+' '+e.blockedURI));localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')")
    pg.goto(URL); pg.wait_for_timeout(4800); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    for tab in ['templates','ai','profile','home']:
        pg.evaluate(f"document.querySelector('[data-tab={tab}]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-ai-open=improve]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.getElementById('aiSuggest').click()"); pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('sheet2Close')&&document.querySelector('.ai-back')&&document.querySelector('.ai-back').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-tab=templates]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-open-edit]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('button[data-seg=preview]').click()"); pg.wait_for_timeout(1500)
    with pg.expect_download(timeout=40000) as d: pg.evaluate("document.getElementById('downloadPdfBtn').click()")
    check('PDF export works under the policy', d.value.suggested_filename.endswith('.pdf'))
    check('no policy violations in normal use', pg.evaluate("window.__csp.length")==0)
    if pg.evaluate("window.__csp.length"): print(pg.evaluate("window.__csp"))
    # the policy really blocks things the app never needs
    r=pg.evaluate("fetch('https://evil.example/x').then(()=> 'allowed').catch(()=> 'blocked')"); pg.wait_for_timeout(300)
    check('requests to unknown sites are blocked', r=='blocked' and pg.evaluate("window.__csp.some(x=>x.includes('connect-src'))"))
    check('no page errors', not errs)
    if errs: print(errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed"); raise SystemExit(0 if all(results) else 1)
