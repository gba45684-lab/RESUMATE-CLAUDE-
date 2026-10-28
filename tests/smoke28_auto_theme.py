# Checks the Auto theme: follows the phone's dark setting, switches live, default stays Golden.
import functools, socket, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
import pathlib
WWW = str(pathlib.Path(__file__).resolve().parent.parent / 'www')
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))
s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(SimpleHTTPRequestHandler, directory=WWW); h.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
INIT = "if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}"
with sync_playwright() as p:
    b = p.chromium.launch()
    def page(scheme, stored=None):
        ctx = b.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True, color_scheme=scheme)
        ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script(INIT)
        if stored: pg.add_init_script(f"localStorage.setItem('resumate_theme','{stored}')")
        pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(2500)
        return ctx, pg, errs
    # default (no choice stored) stays Golden even on a dark phone
    ctx, pg, errs = page('dark')
    chk('default stays Golden on a dark phone', pg.evaluate("!document.documentElement.hasAttribute('data-mode') && !document.documentElement.hasAttribute('data-theme')"))
    chk('Auto option exists in the picker', pg.evaluate("!!document.querySelector('#themeSeg [data-th=system]')"))
    pg.evaluate("document.querySelector('#themeSeg [data-th=system]').click()"); pg.wait_for_timeout(600)
    chk('Auto on a dark phone shows Midnight', pg.evaluate("document.documentElement.getAttribute('data-mode')==='dark' && document.documentElement.getAttribute('data-theme')==='branchdesk'"))
    chk('Auto is remembered', pg.evaluate("localStorage.getItem('resumate_theme')")=='system')
    ctx.close()
    ctx, pg, errs = page('light', stored='system')
    chk('Auto on a light phone shows Golden', pg.evaluate("!document.documentElement.hasAttribute('data-mode') && !document.documentElement.hasAttribute('data-theme')"))
    pg.emulate_media(color_scheme='dark'); pg.wait_for_timeout(500)
    chk('Auto switches live when the phone turns dark', pg.evaluate("document.documentElement.getAttribute('data-mode')==='dark'"))
    chk('no page errors', not errs, errs[:3])
    ctx.close(); b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
