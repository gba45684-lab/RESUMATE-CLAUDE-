# App lock: a PIN is asked for when the app opens. Wrong PINs are refused; the right one opens the app and can be turned off.
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
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
def tap(pg, digits):
    for d in digits: pg.click(f'[data-k="{d}"]'); pg.wait_for_timeout(60)
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=sections]').click()"); pg.wait_for_timeout(600)
    pg.fill('#lkNew', '1234'); pg.fill('#lkNew2', '1299'); pg.click('#lkOn'); pg.wait_for_timeout(600)
    chk('mismatched PINs are refused', 'do not match' in pg.evaluate("document.getElementById('lkMsg').textContent") and pg.evaluate("!localStorage.getItem('resumate_lock')"))
    pg.fill('#lkNew', '1234'); pg.fill('#lkNew2', '1234'); pg.click('#lkOn'); pg.wait_for_timeout(900)
    chk('a PIN is stored hashed, not as typed', pg.evaluate("(()=>{const v=localStorage.getItem('resumate_lock')||''; return v.length>0 && v.indexOf('1234')<0;})()"))
    pg.reload(); pg.wait_for_timeout(2000)
    chk('the app asks for the PIN on open', pg.evaluate("!!document.getElementById('lockScreen')"))
    tap(pg, [1, 2, 3, 9])
    pg.wait_for_timeout(500)
    chk('a wrong PIN is refused', pg.evaluate("document.getElementById('lockMsg').textContent").startswith('Wrong'))
    tap(pg, [1, 2, 3, 4]); pg.wait_for_timeout(900)
    chk('the right PIN opens the app', pg.evaluate("!document.getElementById('lockScreen')"))
    pg.evaluate("document.querySelector('.tl-tile[data-tool=sections]').click()"); pg.wait_for_timeout(600)
    pg.fill('#lkCur', '0000'); pg.evaluate("document.getElementById('lkOff').click()"); pg.wait_for_timeout(400)
    chk('turning the lock off needs the current PIN', pg.evaluate("!!localStorage.getItem('resumate_lock')"))
    pg.fill('#lkCur', '1234'); pg.evaluate("document.getElementById('lkOff').click()"); pg.wait_for_timeout(600)
    chk('the right PIN turns the lock off', pg.evaluate("!localStorage.getItem('resumate_lock')"))
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
