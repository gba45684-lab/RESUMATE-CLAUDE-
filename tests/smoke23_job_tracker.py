# Checks the Job tracker: add, due follow-ups, status changes, saved across reloads, two-tap delete.
import pathlib, functools, socket, threading, datetime
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
today = datetime.date.today()
yday = (today - datetime.timedelta(days=1)).isoformat(); later = (today + datetime.timedelta(days=7)).isoformat()

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    def open_tool():
        pg.evaluate("document.querySelector('.tl-tiles [data-tool=jobtracker]').click()"); pg.wait_for_timeout(500)
    def fill(id_, v):
        pg.evaluate(f"(()=>{{const e=document.getElementById('{id_}'); e.value={v!r}; e.dispatchEvent(new Event('input'));}})()")
    def add(role, co, follow=''):
        fill('jtRole', role); fill('jtCo', co); fill('jtFollow', follow)
        pg.evaluate("document.getElementById('jtAdd').click()"); pg.wait_for_timeout(300)
    rows = lambda: pg.evaluate("document.querySelectorAll('.jt-row').length")

    chk('Job tracker tile is on Home', pg.evaluate("!!document.querySelector('.tl-tiles [data-tool=jobtracker]')"))
    open_tool()
    chk('screen opens', pg.evaluate("document.getElementById('toolTitle').textContent") == 'Job tracker')
    add('', '')
    chk('empty entry is refused', 'Add a role or a company' in pg.evaluate("document.getElementById('jtMsg').textContent"))
    add('Analyst', 'Acme', yday)
    chk('an application is added', rows() == 1)
    chk('a past follow-up shows the due mark', pg.evaluate("!!document.querySelector('.jt-row.due .jt-due')"))
    add('Developer', 'Beta', later)
    chk('two applications listed', rows() == 2)
    chk('future follow-up is not marked due', pg.evaluate("document.querySelectorAll('.jt-row.due').length") == 1)
    pg.evaluate("document.querySelector('.jt-row [data-st=offer]').click()"); pg.wait_for_timeout(300)
    chk('status changes to offer', pg.evaluate("document.querySelector('.jt-row [data-st=offer]').getAttribute('aria-pressed')") in ('true',))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)
    pg.reload(); pg.wait_for_timeout(4000)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(300)
    open_tool()
    chk('applications are kept after a reload', rows() == 2, rows())
    chk('the offer status is kept after a reload', pg.evaluate("[...document.querySelectorAll('[data-st=offer][aria-pressed=true]')].length") == 1)
    pg.evaluate("document.querySelector('.jt-row [data-act=del]').click()"); pg.wait_for_timeout(200)
    chk('first delete tap only asks to confirm', rows() == 2)
    pg.evaluate("document.querySelector('.jt-row [data-act=del]').click()"); pg.wait_for_timeout(300)
    chk('second tap deletes it', rows() == 1, rows())
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
