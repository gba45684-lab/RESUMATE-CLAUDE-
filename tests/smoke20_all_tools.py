# Checks the All tools screen: the button opens it, search filters, a row opens its tool.
import pathlib, functools, socket, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port
port = free_port()
handler = functools.partial(SimpleHTTPRequestHandler, directory=WWW); handler.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    chk('All tools button is on Home', pg.evaluate("!!document.querySelector('.tl-allbtn[data-tool=alltools]')"))
    pg.evaluate("document.querySelector('[data-tool=alltools]').click()"); pg.wait_for_timeout(600)
    rows = lambda: pg.evaluate("document.querySelectorAll('.at-row').length")
    chk('list shows all 16 tools', rows() == 16, rows())
    pg.fill('#atSearch', 'pdf'); pg.wait_for_timeout(200)
    n = rows()
    chk('search "pdf" narrows to PDF tools', 6 <= n < 16, n)
    names = pg.evaluate("[...document.querySelectorAll('.at-row b')].map(b=>b.textContent)")
    chk('every match mentions PDF', all('pdf' in x.lower() for x in names), names)
    pg.fill('#atSearch', 'zzzz'); pg.wait_for_timeout(200)
    chk('no match shows a helpful message', 'No tool matches' in pg.evaluate("document.getElementById('atList').textContent") and rows() == 0)
    pg.fill('#atSearch', 'rotate'); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('.at-row').click()"); pg.wait_for_timeout(700)
    chk('tapping a row opens that tool', pg.evaluate("!!document.getElementById('pt-file') && document.getElementById('toolTitle').textContent === 'Rotate PDF'"), pg.evaluate("document.getElementById('toolTitle').textContent"))
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
