# The first-run tour waits for the app lock: it shows only after the PIN is entered. Monthly premium price is ₹99.
import pathlib, functools, socket, threading, hashlib
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
SALT = 'salt42'
HASH = hashlib.sha256(f'{SALT}:1234'.encode()).hexdigest()
LOCK = "{\"salt\":\"%s\",\"hash\":\"%s\",\"len\":4,\"bio\":false}" % (SALT, HASH)
INIT = ("try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');"
        "localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_pending','1');"
        "localStorage.setItem('resumate_lock', '%s')}catch(e){}" % LOCK)
def tap(pg, digits):
    for d in digits: pg.click(f'[data-k="{d}"]'); pg.wait_for_timeout(60)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(4000)
    chk('the PIN screen is up first', pg.evaluate("!!document.getElementById('lockScreen')"))
    chk('the tour does not show under the PIN screen', pg.evaluate("!document.querySelector('.tour')"))
    tap(pg, [1, 2, 3, 4]); pg.wait_for_timeout(500)
    chk('unlocking removes the PIN screen', pg.evaluate("!document.getElementById('lockScreen')"))
    pg.wait_for_function("!!document.querySelector('.tour')", timeout=12000)
    chk('the tour shows after the app is unlocked', pg.evaluate("!!document.querySelector('.tour')"))
    chk('the monthly price on the paywall is ₹99', pg.evaluate("document.getElementById('pwPrice').textContent.trim()") == '₹99')
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
