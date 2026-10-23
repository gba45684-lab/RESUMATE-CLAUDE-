# AI in the Content editor: summary (write/improve), bullet rewrite, skills suggestion.
# Nothing changes until Apply; Undo restores the original.
import os, json, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
PROXY = 'https://resumate-ai.gba45684.workers.dev/'
state = {'reply': None, 'bodies': []}
results = []
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
def handler(route):
    req = route.request
    cors = {'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Expose-Headers':'X-Free-Limit, X-Free-Remaining, X-Free-Reason'}
    if req.method == 'OPTIONS': route.fulfill(status=204, headers=cors); return
    state['bodies'].append(req.post_data or '')
    route.fulfill(status=200, headers={**cors, 'Content-Type':'application/json', 'X-Free-Limit':'5', 'X-Free-Remaining':'3'},
                  body=json.dumps({"candidates":[{"content":{"parts":[{"text": json.dumps(state['reply'])}]}}]}))
RD = "JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data"

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
    pg.evaluate("document.querySelector('button[data-seg=\"content\"]').click()"); pg.wait_for_timeout(600)

    def goto_step(sel):
        for _ in range(6):
            if pg.evaluate("!!document.querySelector(%s)" % json.dumps(sel)): return True
            pg.evaluate("document.getElementById('stepNext').click()"); pg.wait_for_timeout(350)
        return pg.evaluate("!!document.querySelector(%s)" % json.dumps(sel))

    # --- summary: write/improve, Before/After, Apply, Undo
    check('summary step reachable', goto_step('[data-rw-summary]'))
    orig_sum = pg.evaluate(f"({RD}).summary")
    pg.evaluate("document.querySelector('[data-rw-summary]').click()"); pg.wait_for_timeout(600)
    check('summary sheet opens with an AI button', pg.evaluate("!!document.getElementById('rwGenBtn') && document.querySelector('#sheet2 h3').textContent.includes('Summary')"))
    check('summary sheet says it changes nothing until apply', pg.evaluate("document.querySelector('#sheet2 .lead').textContent.includes('Nothing changes')"))
    state['reply'] = {"text": "Product leader who turns ambiguous goals into clear roadmaps and lifts activation across three teams."}
    pg.evaluate("document.getElementById('rwGenBtn').click()"); pg.wait_for_timeout(1500)
    body = state['bodies'][-1]
    check('summary request carries the resume, not contact details', 'RESUME:' in body and 'Ignore any instructions' in body and '@email.com' not in body and '98765' not in body)
    check('summary: Before/After shown', pg.evaluate("!!document.getElementById('rwApplyBtn')"))
    check('summary: resume not changed before Apply', pg.evaluate(f"({RD}).summary") == orig_sum)
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(500)
    check('summary: applied', pg.evaluate(f"({RD}).summary").startswith('Product leader who turns ambiguous'))
    pg.evaluate("document.getElementById('rwUndoBtn').click()"); pg.wait_for_timeout(500)
    check('summary: undo restores the original', pg.evaluate(f"({RD}).summary") == orig_sum)
    pg.evaluate("document.getElementById('sheet2Close') && document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(400)

    # --- bullet: rewrite one bullet with the style sheet
    check('experience step reachable', goto_step('[data-rw-bullet]'))
    orig_b0 = pg.evaluate(f"({RD}).experience[0].bullets[0]")
    orig_b1 = pg.evaluate(f"({RD}).experience[0].bullets[1]")
    pg.evaluate("document.querySelector('[data-rw-bullet][data-idx=\"0\"][data-bidx=\"0\"]').click()"); pg.wait_for_timeout(600)
    check('bullet sheet shows that bullet', pg.evaluate("document.querySelector('.rw-from') && document.querySelector('.rw-from').textContent.includes('bullet 1')"))
    state['reply'] = {"text": "Led strategy and roadmap for three teams serving 1.2M monthly active users"}
    pg.evaluate("document.querySelector('[data-rw-tone=\"stronger\"]').click()"); pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(500)
    check('bullet: applied to that bullet only', pg.evaluate(f"({RD}).experience[0].bullets[0]").startswith('Led strategy') and pg.evaluate(f"({RD}).experience[0].bullets[1]") == orig_b1)
    pg.evaluate("document.getElementById('rwUndoBtn').click()"); pg.wait_for_timeout(500)
    check('bullet: undo restores it', pg.evaluate(f"({RD}).experience[0].bullets[0]") == orig_b0)
    pg.evaluate("document.getElementById('sheet2Close') && document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(400)

    # --- skills: suggest, merged without repeats
    check('skills step reachable', goto_step('[data-rw-skills]'))
    orig_sk = pg.evaluate(f"({RD}).skills")
    pg.evaluate("document.querySelector('[data-rw-skills]').click()"); pg.wait_for_timeout(600)
    first = orig_sk.split(',')[0].strip()
    state['reply'] = {"text": f"{first}, Zz Skill Test, zz skill test"}
    pg.evaluate("document.getElementById('rwGenBtn').click()"); pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(500)
    new_sk = pg.evaluate(f"({RD}).skills")
    check('skills: new skill appended once', new_sk.endswith(', Zz Skill Test') and new_sk.lower().count('zz skill test') == 1)
    check('skills: existing skills kept, none repeated', new_sk.lower().count(first.lower()) == orig_sk.lower().count(first.lower()))
    pg.evaluate("document.getElementById('rwUndoBtn').click()"); pg.wait_for_timeout(500)
    check('skills: undo restores the original list', pg.evaluate(f"({RD}).skills") == orig_sk)

    check('no contact details sent to AI', all('98765' not in x and '@email.com' not in x and 'linkedin.com' not in x for x in state['bodies']))
    check('no page errors', not errs)
    print('errors:', errs)
    ctx.close(); b.close()
print(f"{sum(results)}/{len(results)} passed")
