# Checks Start from a role: tile placement, the job type preview, skill choices, and the resume it makes.
import pathlib, functools, socket, threading, json
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

    chk('Start from a role is in the Resume group', pg.evaluate("[...document.querySelectorAll('.tl-tiles .tl-group')].find(g=> g.querySelector('.tl-subh').textContent === 'Resume').querySelectorAll('[data-tool=roleresume]').length") == 1)
    before = pg.evaluate("JSON.parse(localStorage.getItem('resumate_resumes_v2')||'{\"items\":[]}').items.length")
    pg.evaluate("document.querySelector('.tl-tiles [data-tool=roleresume]').click()"); pg.wait_for_timeout(600)
    chk('the tool opens', pg.evaluate("document.getElementById('toolTitle').textContent") == 'Start from a role')
    pg.select_option('#rrJob', 'Software and IT'); pg.wait_for_timeout(300)
    chk('the headline is set for IT', 'Software developer' in pg.evaluate("document.getElementById('toolBody').textContent"))
    chk('real skills start selected, placeholders do not', pg.evaluate("[...document.querySelectorAll('[data-skill]')].filter(e=>e.getAttribute('aria-pressed')==='true').map(e=>e.dataset.skill).every(x=>!x.includes('['))") and pg.evaluate("document.querySelectorAll('[data-skill][aria-pressed=true]').length") == 5)
    pg.evaluate("document.querySelector('[data-skill=Git]').click()"); pg.wait_for_timeout(100)
    chk('a skill can be unselected', pg.evaluate("document.querySelector('[data-skill=Git]').getAttribute('aria-pressed')") == 'false')
    pg.evaluate("document.getElementById('rrGo').click()"); pg.wait_for_timeout(900)
    items = pg.evaluate("JSON.parse(localStorage.getItem('resumate_resumes_v2')||'{\"items\":[]}').items")
    chk('a new resume is saved', len(items) == before + 1, len(items))
    active = [i for i in items if i.get('id') == (pg.evaluate("JSON.parse(localStorage.getItem('resumate_resumes_v2')||'{}').active")) ]
    data = active[0]['data'] if active else {}
    chk('the new resume has the IT headline', data.get('role') == 'Software developer', data.get('role'))
    chk('the skill list leaves out the unselected one', 'Git' not in (data.get('skills') or '') and 'Python' in (data.get('skills') or ''), data.get('skills'))
    chk('the new resume is labelled with its job type', active and active[0].get('label') == 'Software and IT', active and active[0].get('label'))
    chk('the section order follows the job type', data.get('extrasOrder', [])[:1] == ['projects'], data.get('extrasOrder'))
    chk('the earlier resumes are kept', len(items) >= before)
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
