# App lock with fingerprint: offered when the phone supports it, tried on open, and the PIN still works when it fails.
import pathlib, functools, socket, threading
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
MOCK = """window.__bio={calls:0, ok: localStorage.getItem('__bioOk') !== '0'}; window.Capacitor={isNativePlatform:()=>true,Plugins:{
  AdMob:{ requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}) },
  BiometricAuthNative:{ checkBiometry:async()=>({isAvailable:true, biometryType:1}),
    internalAuthenticate:async()=>{ window.__bio.calls++; if(!window.__bio.ok) throw new Error('cancelled'); return {}; } },
  Share:{ share:async()=>({}) }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
def tap(pg, digits):
    for d in digits: pg.click(f'[data-k="{d}"]'); pg.wait_for_timeout(60)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=sections]').click()"); pg.wait_for_timeout(800)
    chk('the fingerprint option is offered on a phone that has it', pg.evaluate("!document.getElementById('lkBioWrap').hidden"))
    pg.fill('#lkNew', '1234'); pg.fill('#lkNew2', '1234'); pg.evaluate("document.getElementById('lkOn').click()"); pg.wait_for_timeout(900)
    chk('turning the lock on saves the fingerprint choice', pg.evaluate("JSON.parse(localStorage.getItem('resumate_lock')).bio === true"))
    pg.evaluate("localStorage.setItem('__bioOk','1')")
    pg.reload(); pg.wait_for_timeout(2000)
    chk('a successful fingerprint opens the app without the PIN', pg.evaluate("!document.getElementById('lockScreen')") and pg.evaluate("window.__bio.calls") >= 1)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=sections]').click()"); pg.wait_for_timeout(600)
    pg.fill('#lkCur', '1234'); pg.evaluate("document.getElementById('lkOff').click()"); pg.wait_for_timeout(600)
    pg.fill('#lkNew', '5678'); pg.fill('#lkNew2', '5678'); pg.evaluate("document.getElementById('lkOn').click()"); pg.wait_for_timeout(900)
    pg.evaluate("localStorage.setItem('__bioOk','0')")
    pg.reload(); pg.wait_for_timeout(2000)
    chk('a cancelled fingerprint keeps the PIN screen', pg.evaluate("!!document.getElementById('lockScreen')") and pg.evaluate("window.__bio.calls") >= 1)
    tap(pg, [5, 6, 7, 8]); pg.wait_for_timeout(900)
    chk('the PIN still opens the app after a cancelled fingerprint', pg.evaluate("!document.getElementById('lockScreen')"))
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
