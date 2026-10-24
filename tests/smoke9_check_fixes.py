import os, pathlib, json
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
results=[]
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name)
from playwright.sync_api import sync_playwright
PROXY='https://resumate-ai.gba45684.workers.dev/'
mode={'m':'ok'}
def handler(route):
    req=route.request
    cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Expose-Headers':'X-Free-Limit, X-Free-Remaining, X-Free-Reason'}
    if req.method=='OPTIONS': route.fulfill(status=204, headers=cors); return
    if mode['m']=='limit':
        route.fulfill(status=429, headers={**cors,'Content-Type':'application/json','X-Free-Limit':'5','X-Free-Remaining':'0','X-Free-Reason':'limit'}, body=json.dumps({"error":{"message":"used"}})); return
    out={"bullets":["Managed the weekly release plan for the checkout team","Coordinated design and engineering to ship features on schedule"]}
    route.fulfill(status=200, headers={**cors,'Content-Type':'application/json','X-Free-Limit':'5','X-Free-Remaining':'3'}, body=json.dumps({"candidates":[{"content":{"parts":[{"text":json.dumps(out)}]}}]}))
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True)
    ctx.route(PROXY+'**', handler)
    pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    cfg=json.dumps({'key':'','proxy':PROXY,'model':'auto'})
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_ai_cfg',%s)}"%json.dumps(cfg))
    pg.goto(URL); pg.wait_for_timeout(4800); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    def one_bullet():
        pg.evaluate("document.querySelector('[data-open-edit]').click()"); pg.wait_for_timeout(400)
        pg.evaluate("document.querySelector('button[data-seg=content]').click()")
        for _ in range(8):
            if pg.evaluate("(document.querySelector('#stepLabel')||{textContent:''}).textContent").find('Experience')>=0: break
            pg.evaluate("document.getElementById('stepNext')&&document.getElementById('stepNext').click()"); pg.wait_for_timeout(150)
        pg.evaluate("""()=>{const blk=document.querySelectorAll('#segContent .entry-block')[0];
          const rows=[...blk.querySelectorAll('[data-remove-bullet]')];}""")
        for _ in range(12):
            n=pg.evaluate("document.querySelectorAll('#segContent .entry-block')[0].querySelectorAll('[data-remove-bullet]').length")
            if n<=1: break
            pg.evaluate("document.querySelectorAll('#segContent .entry-block')[0].querySelector('[data-remove-bullet]').click()"); pg.wait_for_timeout(120)
        pg.evaluate("document.querySelector('[data-close-edit]').click()"); pg.wait_for_timeout(400)
        return pg.evaluate("document.querySelectorAll('#segContent .entry-block')[0].querySelectorAll('.bullet-input').length")
    check('setup: role has one bullet', one_bullet()==1)
    pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('[data-ai-open=check]').click()"); pg.wait_for_timeout(900)
    check('Run again is clickable with a real tap', True) if pg.locator('#aiHealthBtn').is_visible() else check('Run again visible', False)
    pg.locator('#aiHealthBtn').click(timeout=3000); pg.wait_for_timeout(300)
    check('Run again shows feedback', 'Checked again' in pg.inner_text('#toast'))
    fix=pg.locator('[data-ai-fix=fill]')
    check('failing bullets check has a Fix this button', fix.count()==1)
    fix.click(timeout=3000); pg.wait_for_timeout(2500)
    bl=pg.evaluate("[...document.querySelectorAll('#segContent .entry-block')[0].querySelectorAll('.bullet-input')].map(t=>t.value)")
    check('AI filled the missing bullet(s)', len(bl)>=2 and all(x.strip() for x in bl))
    check('first bullet kept', len(bl)>0 and bl[0].strip()!='' )
    check('editor is open on the bullets', pg.evaluate("document.querySelectorAll('#segContent .bullet-input').length")>=2)
    check('no empty bullet left', pg.evaluate("[...document.querySelectorAll('#segContent .bullet-input')].every(t=>t.value.trim())"))
    # limit: bullets stay, options offered
    check('setup again: one bullet', one_bullet()==1)
    mode['m']='limit'
    pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-ai-open=check]').click()"); pg.wait_for_timeout(700)
    pg.locator('[data-ai-fix=fill]').click(timeout=3000); pg.wait_for_timeout(2500)
    check('limit: no empty bullet remains', pg.evaluate("[...document.querySelectorAll('#segContent .bullet-input')].every(t=>t.value.trim())"))
    check('limit: offers key and upgrade', 'Add my own key' in pg.inner_text('#sheet2') and 'Upgrade' in pg.inner_text('#sheet2'))
    check('no page errors', not errs)
    if errs: print(errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed"); raise SystemExit(0 if all(results) else 1)
