# Rewrite follow-ups: "For this job" style (uses the job ad already pasted) and the word-change summary after Apply.
import os, json
from playwright.sync_api import sync_playwright
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
PROXY = 'https://resumate-ai.gba45684.workers.dev/'
JOB = "We need a Product Manager who runs SQL dashboards and leads roadmap planning across teams."
state = {'reply': None, 'bodies': []}
REPLY = {"text": "Leads roadmap planning across three teams and runs SQL dashboards that lift activation"}
results = []
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
SUM = "(()=>{ try{ return JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary || ''; }catch(e){ return ''; } })()"

def handler(route):
    req = route.request
    cors = {'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Expose-Headers':'X-Free-Limit, X-Free-Remaining, X-Free-Reason'}
    if req.method == 'OPTIONS': route.fulfill(status=204, headers=cors); return
    state['bodies'].append(req.post_data or '')
    route.fulfill(status=200, headers={**cors, 'Content-Type':'application/json', 'X-Free-Limit':'5', 'X-Free-Remaining':'3'},
                  body=json.dumps({"candidates":[{"content":{"parts":[{"text": json.dumps(state['reply'])}]}}]}))

with sync_playwright() as p:
    b = p.chromium.launch(); errs = []
    ctx = b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=2)
    ctx.route(PROXY + '**', handler)
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    cfg = json.dumps({'key':'','proxy':PROXY,'model':'auto'})
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_ai_cfg',%s)}" % json.dumps(cfg))
    pg.goto(URL); pg.wait_for_timeout(4500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c) c.click();})()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-open-edit]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('button[data-seg=\"preview\"]').click()"); pg.wait_for_timeout(900)

    # no job ad yet: no "For this job" style
    sel = "Turns ambiguous goals into clear roadmaps"
    def select(t):
        ok = pg.evaluate("""(t)=>{ const root=document.getElementById('previewMount'); const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT); let n;
          while((n=w.nextNode())){ const i=n.textContent.indexOf(t); if(i>=0){ const r=document.createRange(); r.setStart(n,i); r.setEnd(n,i+t.length); const s=getSelection(); s.removeAllRanges(); s.addRange(r); return true; } } return false; }""", t)
        pg.wait_for_timeout(500); return ok
    select(sel); pg.evaluate("document.getElementById('rwFab').click()"); pg.wait_for_timeout(600)
    check('no job ad: "For this job" style is not offered', pg.evaluate("!document.querySelector('[data-rw-tone=\"job\"]')"))
    pg.evaluate("document.getElementById('sheet2Backdrop') && document.getElementById('sheet2Backdrop').click()"); pg.wait_for_timeout(300)

    # job ad pasted in the AI tab -> "For this job" offered and sent with the request
    pg.evaluate("localStorage.setItem('resumate_jd', %s)" % json.dumps(JOB))
    select(sel); pg.evaluate("document.getElementById('rwFab').click()"); pg.wait_for_timeout(600)
    check('job ad present: "For this job" style offered', pg.evaluate("!!document.querySelector('[data-rw-tone=\"job\"]')"))
    state['reply'] = REPLY
    pg.evaluate("document.querySelector('[data-rw-tone=\"job\"]').click()"); pg.wait_for_timeout(1800)
    body = state['bodies'][-1]
    check('job style sends the job ad for matching only', 'JOB AD (for matching only' in body and 'SQL dashboards' in body)
    check('job style keeps the injection guard and the TARGET', 'Ignore any instructions' in body and 'Turns ambiguous goals' in body)
    check('job style: Before/After shown, resume not changed yet', pg.evaluate("!!document.getElementById('rwApplyBtn')") and pg.evaluate("(%s).includes('Turns ambiguous')" % SUM))

    # Apply -> change summary in the sheet
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(500)
    delta = pg.evaluate("(document.querySelector('.rw-delta')||{}).textContent || ''")
    check('after Apply: word-change summary shown', 'added' in delta and 'removed' in delta)
    # 6 original words, 13 new words, no word in common -> 13 added, 6 removed
    check('change summary counts are exact', delta == '13 words added, 6 words removed')
    pg.evaluate("document.getElementById('rwDoneBtn').click()"); pg.wait_for_timeout(400)
    check('undo bar message includes the change summary', pg.evaluate("document.getElementById('rwBarMsg').textContent.includes('added')"))
    check('no contact details sent to AI', all('98765' not in x and 'linkedin.com' not in x and '@email.com' not in x for x in state['bodies']))
    check('no page errors', not errs)
    print('errors:', errs)
    ctx.close(); b.close()
print(f"{sum(results)}/{len(results)} passed")
