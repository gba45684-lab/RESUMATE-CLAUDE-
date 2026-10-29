# First run: the upgrade paywall waits for the tour. One interstitial per launch after a finished export, not in the first 3 minutes.
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
MOCK = """window.__ad=[];
window.Capacitor={isNativePlatform:()=>true,Plugins:{AdMob:{
  requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}),
  prepareInterstitial:async(o)=>{ window.__ad.push('prepare'); return {}; }, showInterstitial:async()=>{ window.__ad.push('show'); return {}; } },
  Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1')}catch(e){}"   # a fresh install: the intro runs
with sync_playwright() as p:
    b = p.chromium.launch()
    # A) first run: the paywall waits for the tour
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.clock.install() if hasattr(pg, 'clock') else None
    pg.goto(URL); pg.wait_for_timeout(3500)
    pg.evaluate("document.getElementById('wsSkip').click()"); pg.wait_for_timeout(800)
    pg.evaluate("document.getElementById('qSkip').click()"); pg.wait_for_timeout(500); pg.evaluate("document.getElementById('qSkip').click()"); pg.wait_for_timeout(1800)
    chk('the paywall is not on top while the tour is running', pg.evaluate("document.getElementById('paywall').hidden"), pg.evaluate("document.getElementById('paywall').hidden"))
    chk('the tour is on screen', pg.evaluate("!!document.querySelector('.tour-card') && getComputedStyle(document.querySelector('.tour')).display !== 'none'"))
    pg.evaluate("localStorage.setItem('resumate_tour_done','1')"); pg.wait_for_timeout(1200)
    chk('the paywall shows once the tour is finished', not pg.evaluate("document.getElementById('paywall').hidden"))
    pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    # B) export: interstitial only after the first 3 minutes, once per launch
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=pdftools]')].find(x=>x.offsetParent)?.click()"); pg.wait_for_timeout(500)
    pg.evaluate("window.__ads.afterExport()"); pg.wait_for_timeout(300)
    chk('no interstitial in the first 3 minutes', pg.evaluate("window.__ad") == [], pg.evaluate("window.__ad"))
    pg.evaluate("window.__ads.afterExport()"); pg.wait_for_timeout(300)
    chk('still none on an immediate second try', pg.evaluate("window.__ad") == [], pg.evaluate("window.__ad"))
    chk('no page errors', not errs, errs[:3]); ctx.close()
    # C) after 3 minutes: one interstitial, then no more this launch
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}")
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs2 = []; pg.on('pageerror', lambda e: errs2.append(str(e)[:120])); pg.clock.install(); pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.clock.fast_forward(200000); pg.wait_for_timeout(300)
    pg.evaluate("window.__ads.afterExport()"); pg.wait_for_timeout(400)
    chk('after 3 minutes, an export shows one interstitial', pg.evaluate("window.__ad") == ['prepare', 'show'], pg.evaluate("window.__ad"))
    pg.evaluate("window.__ads.afterExport()"); pg.wait_for_timeout(300)
    chk('a second export in the same launch shows no more', pg.evaluate("window.__ad") == ['prepare', 'show'], pg.evaluate("window.__ad"))
    chk('no page errors (late run)', not errs2, errs2[:3]); ctx.close(); b.close()
print(f"{sum(res)}/{len(res)} passed"); raise SystemExit(0 if all(res) else 1)
