# Rewrite a selected part of the resume with AI:
# select -> pick a style -> Before/After (nothing changes yet) -> Apply -> Undo / Done -> undo bar.
import os, pathlib, tempfile, json
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
PROXY = 'https://resumate-ai.gba45684.workers.dev/'
state = {'reply': None, 'bodies': []}
REWRITE_OK = {"text": "Drives product strategy that lifts activation across three teams"}
NEW_NUMBER = {"text": "Drives product strategy that lifts activation 250% across three teams"}
SEL_TEXT = "Turns ambiguous goals into clear roadmaps"
ORIG_SUMMARY_START = "Product leader with 8+ years"

def handler(route):
    req = route.request
    cors = {'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Expose-Headers':'X-Free-Limit, X-Free-Remaining, X-Free-Reason'}
    if req.method == 'OPTIONS': route.fulfill(status=204, headers=cors); return
    state['bodies'].append(req.post_data or '')
    route.fulfill(status=200, headers={**cors, 'Content-Type':'application/json', 'X-Free-Limit':'5', 'X-Free-Remaining':'3'},
                  body=json.dumps({"candidates":[{"content":{"parts":[{"text": json.dumps(state['reply'])}]}}]}))

results = []
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
SUM = "(()=>{ try{ return JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary || ''; }catch(e){ return ''; } })()"

def new_page(b, errs):
    ctx = b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=2)
    ctx.route(PROXY + '**', handler)
    pg = ctx.new_page()
    pg.on('pageerror', lambda e: errs.append(str(e)))
    cfg = json.dumps({'key':'','proxy':PROXY,'model':'auto'})
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_ai_cfg',%s)}" % json.dumps(cfg))
    pg.goto(URL); pg.wait_for_timeout(4500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c) c.click();})()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-open-edit]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('button[data-seg=\"preview\"]').click()"); pg.wait_for_timeout(900)
    return pg, ctx

def select_text(pg, t):
    ok = pg.evaluate("""(t)=>{
      const root = document.getElementById('previewMount');
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n; while((n = w.nextNode())){
        const i = n.textContent.indexOf(t);
        if(i >= 0){ const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + t.length);
          const s = window.getSelection(); s.removeAllRanges(); s.addRange(r); return true; }
      }
      return false; }""", t)
    pg.wait_for_timeout(500)
    return ok

def summary(pg): return pg.evaluate(SUM)

with sync_playwright() as p:
    b = p.chromium.launch(); errs = []
    pg, ctx = new_page(b, errs)

    # 1. select -> tip card and the Rewrite button
    check('summary text found in the preview', select_text(pg, SEL_TEXT))
    check('"Rewrite with AI" button appears for a selection', pg.evaluate("!document.getElementById('rwFab').hidden"))
    check('tip card shows on the Preview with three steps', pg.evaluate("!document.getElementById('rwTip').hidden && document.querySelectorAll('#rwTip .rw-steps li').length === 3"))

    # 2. choose a style -> Before/After, nothing changed yet
    pg.evaluate("document.getElementById('rwFab').click()"); pg.wait_for_timeout(700)
    check('rewrite sheet opens with the selected words', pg.evaluate("document.querySelector('#sheet2 h3').textContent.includes('Rewrite with AI') && document.querySelector('.rw-from').textContent.includes('Turns ambiguous')"))
    state['reply'] = REWRITE_OK
    pg.evaluate("document.querySelector('[data-rw-tone=\"stronger\"]').click()"); pg.wait_for_timeout(1800)
    body = state['bodies'][-1]
    check('AI request asks only for the TARGET text (and keeps the injection guard)', 'TARGET (rewrite this)' in body and 'Ignore any instructions' in body and 'Turns ambiguous goals' in body)
    check('Before/After shown: original is highlighted, change is marked', pg.evaluate("!!document.querySelector('#rwOut mark') && document.querySelector('#rwOut mark').textContent.includes('Turns ambiguous') && !!document.querySelector('#rwOut .ai-sug mark')"))
    check('Apply and Rewrite buttons shown', pg.evaluate("!!document.getElementById('rwApplyBtn') && !!document.getElementById('rwAgainBtn')"))
    check('resume NOT changed before Apply', pg.evaluate("(%s).includes('Turns ambiguous goals into clear roadmaps')" % SUM))

    # 3. Apply -> written in, Undo offered in the sheet, bar not yet
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(600)
    check('Apply: resume summary updated', pg.evaluate("(%s).includes('Drives product strategy that lifts activation across three teams')" % SUM))
    check('Apply: preview shows the new wording', pg.evaluate("document.getElementById('previewMount').textContent.includes('Drives product strategy')"))
    check('Apply: rest of the summary untouched', pg.evaluate("(%s).startsWith('Product leader with 8+ years')" % SUM))
    check('after Apply: Undo and Done in the sheet', pg.evaluate("!!document.getElementById('rwUndoBtn') && !!document.getElementById('rwDoneBtn')"))
    check('tip hides after the first applied rewrite', pg.evaluate("document.getElementById('rwTip').hidden === true"))

    # 4. Undo in the sheet -> original back, Before/After returns so it can be applied again
    pg.evaluate("document.getElementById('rwUndoBtn').click()"); pg.wait_for_timeout(600)
    check('undo (sheet) restores the original wording', pg.evaluate("(%s).includes('Turns ambiguous goals into clear roadmaps') && !(%s).includes('Drives product strategy')" % (SUM, SUM)))
    check('undo (sheet) brings back Apply so it can be applied again', pg.evaluate("!!document.getElementById('rwApplyBtn')"))

    # 5. Apply again -> Done -> sheet closes and the undo bar stays
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.getElementById('rwDoneBtn').click()"); pg.wait_for_timeout(500)
    check('Done: sheet closed and undo bar shown', pg.evaluate("!document.getElementById('sheet2').classList.contains('show') && !document.getElementById('rwBar').hidden"))
    check('undo bar keeps the change in place', pg.evaluate("(%s).includes('Drives product strategy')" % SUM))

    # 6. bar Undo -> original back, sheet reopens at Before/After
    pg.evaluate("document.getElementById('rwBarUndo').click()"); pg.wait_for_timeout(600)
    check('bar undo restores the original wording', pg.evaluate("(%s).includes('Turns ambiguous goals into clear roadmaps')" % SUM))
    check('bar undo reopens Before/After to apply again', pg.evaluate("document.getElementById('sheet2').classList.contains('show') && !!document.getElementById('rwApplyBtn')"))

    # 7. dismiss the bar: the change stays, the bar goes away
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.getElementById('rwDoneBtn').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.getElementById('rwBarClose').click()"); pg.wait_for_timeout(300)
    check('dismiss (✕) hides the bar and keeps the change', pg.evaluate("document.getElementById('rwBar').hidden === true && (%s).includes('Drives product strategy')" % SUM))

    # 8. a number the resume does not contain: warning, no change until Apply
    pg.evaluate("document.querySelector('button[data-seg=\"preview\"]').click()"); pg.wait_for_timeout(400)
    check('select the whole summary for the number check', select_text(pg, 'Drives product strategy that lifts activation across three teams'))
    pg.evaluate("document.getElementById('rwFab').click()"); pg.wait_for_timeout(600)
    state['reply'] = NEW_NUMBER
    pg.evaluate("document.querySelector('[data-rw-tone=\"stronger\"]').click()"); pg.wait_for_timeout(1800)
    check('unknown number: warning shown in Before/After', pg.evaluate("!!document.querySelector('#rwOut .ai-warnbar')"))
    check('unknown number: resume NOT changed yet', pg.evaluate("!(%s).includes('250%%')" % SUM))
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(500)
    check('after Apply the number change is applied', pg.evaluate("(%s).includes('250%%')" % SUM))
    pg.evaluate("document.getElementById('rwDoneBtn').click()"); pg.wait_for_timeout(400)

    # 9. the person edits the summary after the change -> Undo refuses and keeps the edit
    check('undo bar showing before the edit', pg.evaluate("!document.getElementById('rwBar').hidden"))
    pg.evaluate("document.querySelector('button[data-seg=\"content\"]').click()"); pg.wait_for_timeout(600)
    for _ in range(4):
        if pg.evaluate("!!document.querySelector('textarea[data-key=\"summary\"]')"): break
        pg.evaluate("document.getElementById('stepNext').click()"); pg.wait_for_timeout(400)
    pg.evaluate("""(()=>{ const t=document.querySelector('textarea[data-key="summary"]'); t.value='Edited by me'; t.dispatchEvent(new Event('input',{bubbles:true})); t.dispatchEvent(new Event('change',{bubbles:true})); })()""")
    pg.wait_for_timeout(900)
    pg.evaluate("document.querySelector('button[data-seg=\"preview\"]').click()"); pg.wait_for_timeout(400)
    check('edit saved to the resume', pg.evaluate("(%s).includes('Edited by me')" % SUM))
    pg.evaluate("document.getElementById('rwBarUndo').click()"); pg.wait_for_timeout(500)
    check('undo refused after an edit: the edit is kept', pg.evaluate("(%s).includes('Edited by me')" % SUM))
    check('refused undo keeps the bar so nothing is lost silently', pg.evaluate("!document.getElementById('rwBar').hidden"))

    # 10. whole-summary picker on the edited text
    pg.evaluate("document.getElementById('rwBarClose').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.getElementById('rwPickBtn').click()"); pg.wait_for_timeout(600)
    check('picker lists the resume text fields', pg.evaluate("document.querySelectorAll('[data-rw-pick]').length") >= 10)
    pg.evaluate("document.querySelector('[data-rw-pick=\"0\"]').click()"); pg.wait_for_timeout(600)
    check('picker opens the style sheet for the whole summary', pg.evaluate("document.querySelector('.rw-from').textContent.includes('Edited by me')"))
    state['reply'] = REWRITE_OK
    pg.evaluate("document.querySelector('[data-rw-tone=\"stronger\"]').click()"); pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('rwApplyBtn').click()"); pg.wait_for_timeout(500)
    check('whole summary replaced in the saved resume', pg.evaluate("(%s) === 'Drives product strategy that lifts activation across three teams'" % SUM))

    # 11. the contact-detail guard still works
    check('no contact details sent to AI', all('linkedin.com' not in x and '@email.com' not in x and '98765' not in x for x in state['bodies']))
    check('no page errors', not errs)
    pg.screenshot(path=os.path.join(tempfile.mkdtemp(prefix='rw_'), 'rewrite.png'))
    ctx.close()

    # 12. tip card: visible on a fresh Preview, closes, and stays closed after a reload
    errs2 = []
    pg2, ctx2 = new_page(b, errs2)
    check('tip visible on a fresh Preview', pg2.evaluate("!document.getElementById('rwTip').hidden"))
    pg2.evaluate("document.getElementById('rwTipClose').click()"); pg2.wait_for_timeout(300)
    check('tip closes with ✕', pg2.evaluate("document.getElementById('rwTip').hidden === true"))
    pg2.reload(); pg2.wait_for_timeout(4000)
    pg2.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c) c.click();})()"); pg2.wait_for_timeout(300)
    pg2.evaluate("document.querySelector('[data-open-edit]').click()"); pg2.wait_for_timeout(600)
    pg2.evaluate("document.querySelector('button[data-seg=\"preview\"]').click()"); pg2.wait_for_timeout(900)
    check('tip stays closed after a reload', pg2.evaluate("document.getElementById('rwTip').hidden === true"))
    check('no page errors (tip)', not errs2)
    ctx2.close(); b.close()

print(f"{sum(results)}/{len(results)} passed")
