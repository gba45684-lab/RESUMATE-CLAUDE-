# Rewrite a selected part of the resume with AI: select text in the preview -> Rewrite -> live change -> undo.
import os, pathlib, tempfile, json
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
PROXY = 'https://resumate-ai.gba45684.workers.dev/'
state = {'reply': None, 'bodies': []}
REWRITE_OK = {"text": "Drives product strategy that lifts activation across three teams"}
NEW_NUMBER = {"text": "Drives product strategy that lifts activation 250% across three teams"}

def handler(route):
    req = route.request
    cors = {'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Expose-Headers':'X-Free-Limit, X-Free-Remaining, X-Free-Reason'}
    if req.method == 'OPTIONS': route.fulfill(status=204, headers=cors); return
    body = req.post_data or ''
    state['bodies'].append(body)
    out = state['reply']
    route.fulfill(status=200, headers={**cors, 'Content-Type':'application/json', 'X-Free-Limit':'5', 'X-Free-Remaining':'3'},
                  body=json.dumps({"candidates":[{"content":{"parts":[{"text": json.dumps(out)}]}}]}))

results = []
# the open resume is saved to this phone as you edit (the app keeps its data in a closure, so read the store)
SUM_JS = "(()=>{ try{ return JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary || ''; }catch(e){ return ''; } })()"
def SUM(): return SUM_JS
def check(name, ok):
    results.append(ok); print(('PASS ' if ok else 'FAIL ') + name)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=2)
    ctx.route(PROXY + '**', handler)
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    cfg = json.dumps({'key':'','proxy':PROXY,'model':'auto'})
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_ai_cfg',%s)}" % json.dumps(cfg))
    pg.goto(URL); pg.wait_for_timeout(4500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c) c.click();})()"); pg.wait_for_timeout(400)

    # open the editor and its Preview tab
    pg.evaluate("document.querySelector('[data-open-edit]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('button[data-seg=\"preview\"]').click()"); pg.wait_for_timeout(900)

    # select a few words of the summary inside the preview (what a long-press selection does)
    sel_text = "Turns ambiguous goals into clear roadmaps"
    found = pg.evaluate("""(t)=>{
      const root = document.getElementById('previewMount');
      const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
      let n; while((n = w.nextNode())){
        const i = n.textContent.indexOf(t);
        if(i >= 0){ const r = document.createRange(); r.setStart(n, i); r.setEnd(n, i + t.length);
          const s = window.getSelection(); s.removeAllRanges(); s.addRange(r); return true; }
      }
      return false; }""", sel_text)
    check('summary text found in the preview', found)
    pg.wait_for_timeout(500)
    check('"Rewrite with AI" button appears for a selection', pg.evaluate("!document.getElementById('rwFab').hidden"))

    # open the sheet and rewrite in a stronger style
    pg.evaluate("document.getElementById('rwFab').click()"); pg.wait_for_timeout(700)
    check('rewrite sheet opens with the selected words', pg.evaluate("document.querySelector('#sheet2 h3') && document.querySelector('#sheet2 h3').textContent.includes('Rewrite with AI') && document.querySelector('.rw-from').textContent.includes('Turns ambiguous')"))
    state['reply'] = REWRITE_OK
    pg.evaluate("document.querySelector('[data-rw-tone=\"stronger\"]').click()"); pg.wait_for_timeout(1800)
    body = state['bodies'][-1]
    check('AI request asks only for the TARGET text (and keeps the injection guard)', 'TARGET (rewrite this)' in body and 'Ignore any instructions' in body and 'Turns ambiguous goals' in body)
    check('live change: resume summary updated at once', pg.evaluate("(function(){const SUM=()=>JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary; return SUM().includes('Drives product strategy that lifts activation across three teams')})()"))
    check('live change: preview shows the new wording', pg.evaluate("document.getElementById('previewMount').textContent.includes('Drives product strategy')"))
    check('live change: rest of the summary untouched', pg.evaluate("(function(){const SUM=()=>JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary; return SUM().startsWith('Product leader with 8+ years')})()"))
    check('undo bar appears', pg.evaluate("!document.getElementById('rwBar').hidden"))
    pg.evaluate("document.getElementById('rwBarUndo').click()"); pg.wait_for_timeout(600)
    check('undo restores the original wording', pg.evaluate("(function(){const SUM=()=>JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary; return SUM().includes('Turns ambiguous goals into clear roadmaps')})()") and not pg.evaluate("(function(){const SUM=()=>JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary; return SUM().includes('Drives product strategy')})()"))

    # a new number the resume does not contain must NOT be applied silently
    pg.evaluate("""(t)=>{ const root=document.getElementById('previewMount'); const w=document.createTreeWalker(root,NodeFilter.SHOW_TEXT); let n; while((n=w.nextNode())){ const i=n.textContent.indexOf(t); if(i>=0){ const r=document.createRange(); r.setStart(n,i); r.setEnd(n,i+t.length); const s=getSelection(); s.removeAllRanges(); s.addRange(r); return; } } }""", sel_text)
    pg.wait_for_timeout(500)
    pg.evaluate("document.getElementById('rwFab').click()"); pg.wait_for_timeout(600)
    state['reply'] = NEW_NUMBER
    pg.evaluate("document.querySelector('[data-rw-tone=\"stronger\"]').click()"); pg.wait_for_timeout(1800)
    check('unknown number: warning shown and resume NOT changed yet', pg.evaluate("!!document.querySelector('#rwOut .ai-warnbar')") and pg.evaluate("(function(){const SUM=()=>JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary; return SUM().includes('Turns ambiguous goals')})()"))
    pg.evaluate("document.getElementById('rwKeep').click()"); pg.wait_for_timeout(600)
    check('after confirming, the change is applied', pg.evaluate("(function(){const SUM=()=>JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary; return SUM().includes('activation 250%')})()"))
    pg.evaluate("document.getElementById('rwBarUndo').click()"); pg.wait_for_timeout(400)

    # no selection: pick a whole summary from the list and rewrite it
    pg.evaluate("document.getElementById('rwPickBtn').click()"); pg.wait_for_timeout(600)
    check('picker lists the resume text fields', pg.evaluate("document.querySelectorAll('[data-rw-pick]').length") >= 10)
    pg.evaluate("document.querySelector('[data-rw-pick=\"0\"]').click()"); pg.wait_for_timeout(600)
    check('picker opens the style sheet for the whole summary', pg.evaluate("document.querySelector('.rw-from').textContent.includes('Product leader with 8+ years')"))
    state['reply'] = REWRITE_OK
    pg.evaluate("document.querySelector('[data-rw-tone=\"stronger\"]').click()"); pg.wait_for_timeout(1500)
    check('whole summary replaced in the saved resume', pg.evaluate("(function(){return JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary === 'Drives product strategy that lifts activation across three teams';})()"))
    check('hint hides after first use', pg.evaluate("document.getElementById('rwHint').hidden === true"))
    pg.evaluate("document.getElementById('rwBarUndo').click()"); pg.wait_for_timeout(500)
    check('undo restores the whole summary', pg.evaluate("(function(){return JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.summary.startsWith('Product leader with 8+ years');})()"))

    # the AI request must never carry contact details
    check('no contact details sent to AI', all('linkedin.com' not in x and '@email.com' not in x and '98765' not in x for x in state['bodies']))
    check('no page errors', not errs)
    print('errors:', errs)
    pg.screenshot(path=os.path.join(tempfile.mkdtemp(prefix='rw_'), 'rewrite.png'))
    b.close()
print(f"{sum(results)}/{len(results)} passed")
