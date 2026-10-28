# Home tiles: one copy of the markup feeds both theme layouts; each theme shows the full set.
# Start from a role: placeholder skills are not ticked by default.
import functools, socket, threading, pathlib
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
WWW = str(pathlib.Path(__file__).resolve().parent.parent / 'www')
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))
s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(SimpleHTTPRequestHandler, directory=WWW); h.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
INIT = "if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}"
VISIBLE = "[...document.querySelectorAll('.tl-tile')].filter(e=> e.offsetParent).length"
with sync_playwright() as p:
    b = p.chromium.launch()
    def open_page(theme=None):
        ctx = b.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True)
        ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
        pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
        pg.add_init_script(INIT)
        if theme: pg.add_init_script(f"localStorage.setItem('resumate_theme','{theme}')")
        pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(2500)
        pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(300)
        return ctx, pg, errs
    ctx, pg, errs = open_page()
    chk('Golden layout shows every Smart tools tile', pg.evaluate(VISIBLE) == 11, pg.evaluate(VISIBLE))
    chk('one template fills both theme slots', pg.evaluate("document.querySelectorAll('[data-tool=roleresume]').length") == 2, pg.evaluate("document.querySelectorAll('[data-tool=roleresume]').length"))
    pg.evaluate("document.querySelector('.tl-tile[data-tool=roleresume]').click()"); pg.wait_for_timeout(500)
    chk('a tile still opens its tool', pg.evaluate("document.getElementById('toolBody').innerHTML.includes('rrJob')"))
    chk('placeholder skills are not ticked by default', pg.evaluate("[...document.querySelectorAll('[data-skill]')].filter(e=>e.getAttribute('aria-pressed')==='true' && e.dataset.skill.includes('[')).length") == 0)
    chk('no page errors', not errs, errs[:3]); ctx.close()
    ctx, pg, errs = open_page('branchdesk')
    chk('Branchdesk layout shows every Smart tools tile', pg.evaluate(VISIBLE) == 11, pg.evaluate(VISIBLE))
    chk('no page errors on Branchdesk', not errs, errs[:3]); ctx.close()
    # first-run tour: starts after the question gate, steps through real controls, can be skipped, never repeats
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_lite','1')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(1500)
    pg.evaluate("document.getElementById('qSkip').click()"); pg.wait_for_timeout(400); pg.evaluate("document.getElementById('qSkip').click()"); pg.wait_for_timeout(2600)
    chk('tour starts after the first-run questions', pg.evaluate("!!document.querySelector('.tour .tour-card')"))
    chk('first tour step names the real Create resume control', pg.evaluate("document.getElementById('tourTitle').textContent")=='Create your resume')
    pg.evaluate("document.querySelector('.tl-tile[data-tool=roleresume]').click()"); pg.wait_for_timeout(400)
    chk('the tour waits while a tool is open', pg.evaluate("document.querySelector('.tour').hidden === true"))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(400)
    chk('the tour returns when the tool closes', pg.evaluate("document.querySelector('.tour').hidden === false"))
    pg.evaluate("document.getElementById('tourNext').click()"); pg.wait_for_timeout(300)
    chk('Next moves to step 2 with a count', pg.evaluate("document.getElementById('tourCount').textContent")=='2 of 4', pg.evaluate("document.getElementById('tourCount').textContent"))
    pg.evaluate("document.getElementById('tourSkip').click()"); pg.wait_for_timeout(500)
    chk('Skip closes the tour', pg.evaluate("!document.querySelector('.tour')"))
    chk('Skip is remembered', pg.evaluate("localStorage.getItem('resumate_tour_done')")=='1')
    pg.reload(); pg.wait_for_timeout(2500)
    chk('the tour does not come back after it was done', pg.evaluate("!document.querySelector('.tour')"))
    chk('no page errors in the tour', not errs, errs[:3]); ctx.close()
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
