# "New blank resume" and "Create resume from this" must always do something visible:
# one tap makes exactly one resume, a dropped click still works, and a failure shows a message.
import pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = HERE.parent.joinpath('www', 'index.html').as_uri()
res = []
def chk(name, ok, extra=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' — ' + str(extra)))
from playwright.sync_api import sync_playwright
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
CNT = "(JSON.parse(localStorage.getItem('resumate_resumes_v2')||'{\"items\":[]}').items||[]).length"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.add_init_script(INIT)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    def home():
        pg.evaluate("(()=>{const t=document.getElementById('toolPage'); if(t&&!t.hidden) document.getElementById('toolBack').click();})()"); pg.wait_for_timeout(450)
        pg.evaluate("document.querySelector('[data-tab=home]').click()"); pg.wait_for_timeout(500)
    def open_tool(key):
        home(); pg.evaluate(f"[...document.querySelectorAll('.tl-tile[data-tool={key}]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    def center(sel):
        return pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}'); e.scrollIntoView({{block:'center'}}); const r=e.getBoundingClientRect(); return {{x:r.left+r.width/2,y:r.top+r.height/2}}}})()")
    def pointer_only(sel):   # a finger lifted on the button but the browser never sent the click
        pg.evaluate(f"(()=>{{const e=document.querySelector('{sel}'); const o={{pointerType:'touch',bubbles:true}}; e.dispatchEvent(new PointerEvent('pointerdown',o)); e.dispatchEvent(new PointerEvent('pointerup',o));}})()")
    # 1) a real touch tap makes exactly one resume
    open_tool('roleresume'); n = pg.evaluate(CNT); c = center('#rrGo'); pg.touchscreen.tap(c['x'], c['y']); pg.wait_for_timeout(1200)
    chk('one tap on Create resume from this makes exactly one resume', pg.evaluate(CNT) == n + 1, (n, pg.evaluate(CNT)))
    # 2) the click is dropped: the pointer-up alone still creates it
    open_tool('roleresume'); n = pg.evaluate(CNT); pointer_only('#rrGo'); pg.wait_for_timeout(1000)
    chk('Create resume from this works when the click is dropped', pg.evaluate(CNT) == n + 1, (n, pg.evaluate(CNT)))
    # 3) same for New blank resume, and a mouse click does not double up
    open_tool('resumes'); n = pg.evaluate(CNT); pointer_only('#rsNewBlank'); pg.wait_for_timeout(1000)
    chk('New blank resume works when the click is dropped', pg.evaluate(CNT) == n + 1, (n, pg.evaluate(CNT)))
    open_tool('resumes'); n = pg.evaluate(CNT); pg.evaluate("document.getElementById('rsNewBlank').click()"); pg.wait_for_timeout(1000)
    chk('a normal click makes exactly one resume (no double)', pg.evaluate(CNT) == n + 1, (n, pg.evaluate(CNT)))
    # 4) a failure inside the action is shown and kept, not silent
    open_tool('roleresume'); n = pg.evaluate(CNT)
    pg.evaluate("(()=>{ const o = JSON.stringify; JSON.stringify = function(...a){ JSON.stringify = o; throw new Error('boom'); }; document.getElementById('rrGo').click(); JSON.stringify = o; })()"); pg.wait_for_timeout(500)
    toast = pg.evaluate("(()=>{const t=document.querySelector('.toast, #toast'); return t ? t.textContent : ''})()")
    chk('a failure shows a message', "didn't work" in toast and 'boom' in toast, toast)
    chk('the failure is kept for Copy diagnostics', 'Create resume from this' in pg.evaluate("localStorage.getItem('resumate_errors')||''"))
    chk('the failed tap added no resume', pg.evaluate(CNT) == n, (n, pg.evaluate(CNT)))
    chk('no page errors', not errs, errs[:3]); ctx.close(); b.close()
print(f"{sum(res)}/{len(res)} passed"); raise SystemExit(0 if all(res) else 1)
