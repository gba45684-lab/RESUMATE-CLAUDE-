# First-run tour: every step keeps its card and buttons fully on screen, on short and tall phones.
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
INIT = ("try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');"
        "localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_pending','1');}catch(e){}")
SIZES = [('short', 360, 640), ('usual', 393, 852), ('tall', 412, 915)]
with sync_playwright() as p:
    b = p.chromium.launch()
    for label, w, h in SIZES:
        ctx = b.new_context(viewport={'width': w, 'height': h}, has_touch=True, is_mobile=True); ctx.add_init_script(INIT)
        ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
        pg.goto(URL); pg.wait_for_timeout(2500)
        pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
        pg.wait_for_selector('.tour', timeout=12000)
        for step in range(1, 5):
            pg.wait_for_timeout(500)
            box = pg.evaluate("(()=>{const c=document.querySelector('.tour-card'), n=document.getElementById('tourNext'); if(!c||!n) return null; const a=c.getBoundingClientRect(), b=n.getBoundingClientRect(); return {top:a.top, bottom:a.bottom, btnBottom:b.bottom, btnTop:b.top, vh:innerHeight};})()")
            ok = box is not None and box['top'] >= 0 and box['bottom'] <= box['vh'] and box['btnTop'] >= 0 and box['btnBottom'] <= box['vh']
            chk(f'{label} {w}x{h}: step {step} card and Next are on screen', ok, box)
            if step < 4:
                pg.evaluate("document.getElementById('tourNext').click()")
            else:
                pg.evaluate("document.getElementById('tourNext').click()")
        pg.wait_for_timeout(600)
        chk(f'{label}: the tour ends and the dimmed overlay is removed', pg.evaluate("!document.querySelector('.tour')"))
        chk(f'{label}: no page errors', not errs, errs)
        ctx.close()
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
