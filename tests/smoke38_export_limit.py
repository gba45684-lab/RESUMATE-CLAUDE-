# Free saves: 3 a day. Over the limit, the person can watch a short ad for one more save, or wait. Paying users have no limit.
import pathlib, functools, socket, threading, json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
HERE = pathlib.Path(__file__).resolve().parent
_s = socket.socket(); _s.bind(('127.0.0.1', 0)); PORT = _s.getsockname()[1]; _s.close()
_h = functools.partial(SimpleHTTPRequestHandler, directory=str(HERE.parent / 'www')); _h.log_message = lambda *a, **k: None
_srv = ThreadingHTTPServer(('127.0.0.1', PORT), _h); threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
res = []
def chk(name, ok, extra=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' — ' + str(extra)))
from playwright.sync_api import sync_playwright
MOCK = """window.__rw=[]; window.__rwMode='ok';
window.Capacitor={isNativePlatform:()=>true,Plugins:{AdMob:{
  requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}),
  prepareInterstitial:async()=>({}), showInterstitial:async()=>({}),
  prepareRewardVideoAd:async()=>{ window.__rw.push('prepare'); return {}; },
  showRewardVideoAd:async()=>{ window.__rw.push('show'); if(window.__rwMode==='ok') return {type:'coins', amount:1}; throw new Error('no ad'); } },
  Filesystem:{ writeFile:async()=>({uri:'file:///cache/x.pdf'}) }, Share:{ share:async()=>({}) }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    def count(): return pg.evaluate("(JSON.parse(localStorage.getItem('resumate_exports')||'{\"n\":0}').n)||0")
    def set_count(n): pg.evaluate(f"localStorage.setItem('resumate_exports', JSON.stringify({{day:new Date().toDateString(), n:{n}}}))")
    def open_letter():
        pg.evaluate("(()=>{const t=document.getElementById('toolPage'); if(t&&!t.hidden) document.getElementById('toolBack').click();})()"); pg.wait_for_timeout(450)
        pg.evaluate("document.querySelector('[data-tab=home]').click()"); pg.wait_for_timeout(500)
        pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=letter]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    def save_pdf(): pg.evaluate("document.getElementById('clPdf').click()"); pg.wait_for_timeout(1500)
    gate = lambda: pg.evaluate("!!document.querySelector('.ex-gate')")
    open_letter()
    save_pdf(); chk('a save within the free limit works', count() == 1, count())
    set_count(3)
    save_pdf(); chk('over the limit, the ask appears', gate())
    pg.evaluate("document.querySelector('[data-ex=no]').click()"); pg.wait_for_timeout(300)
    chk('"Not now" closes the ask and saves nothing', (not gate()) and count() == 3, (gate(), count()))
    chk('"Not now" does not show an ad', pg.evaluate("window.__rw") == [], pg.evaluate("window.__rw"))
    save_pdf(); pg.evaluate("document.querySelector('[data-ex=yes]').click()"); pg.wait_for_timeout(1500)
    chk('watching the ad shows it', pg.evaluate("window.__rw") == ['prepare', 'show'], pg.evaluate("window.__rw"))
    chk('after the ad, the save goes through', count() == 4, count())
    pg.evaluate("window.__rwMode='fail'"); set_count(3)
    save_pdf(); pg.evaluate("document.querySelector('[data-ex=yes]').click()"); pg.wait_for_timeout(1500)
    chk('if the ad does not finish, nothing is saved', count() == 3, count())
    pg.evaluate("window.__rwMode='ok'")
    pg.evaluate("window.__billing = { upgraded: () => true, buy: async()=>'cancel', restore: async()=>'none' }")
    set_count(9); save_pdf()
    chk('paying users are never asked', not gate() and count() == 10, (gate(), count()))
    chk('no page errors', not errs, errs[:3]); ctx.close(); b.close()
print(f"{sum(res)}/{len(res)} passed"); raise SystemExit(0 if all(res) else 1)
