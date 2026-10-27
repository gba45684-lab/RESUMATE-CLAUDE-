# Checks Start from a role: six Indian job types, skills added only on tap, and a new resume with the role title.
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
    import json
    def state():
        return json.loads(pg.evaluate("localStorage.getItem('resumate_resumes_v2')") or '{"items":[],"active":""}')
    def cur():
        st = state(); it = next((i for i in st['items'] if i['id'] == st['active']), st['items'][0]); return it['data']
    def skills(): return json.loads(pg.evaluate("localStorage.getItem('resumate_resume_v1')") or '{}').get('skills', '')
    def skills_role(): return cur().get('role', '')
    pg.evaluate("document.querySelector('.tl-tiles [data-tool=roles]').click()"); pg.wait_for_timeout(600)
    chk('six job types are offered', pg.evaluate("document.querySelectorAll('#toolBody [data-id]').length") == 6)
    pg.evaluate("document.querySelector('#toolBody [data-id=sales]').click()"); pg.wait_for_timeout(200)
    chk('choosing Sales shows its title', 'Sales Executive' in pg.evaluate("document.getElementById('toolBody').textContent"))
    before = skills()
    chk('skills are not added until tapped', skills() == before)
    pg.evaluate("document.querySelector('#toolBody [data-skill=\"Lead generation\"]').click()"); pg.wait_for_timeout(200)
    chk('a tapped skill is added to the resume', 'lead generation' in skills().lower(), skills())
    count = len(state()["items"])
    pg.evaluate("document.getElementById('rlGo').click()"); pg.wait_for_timeout(700)
    chk('a new resume is created', len(state()["items"]) == count + 1, count)
    chk('the new resume has the role title', skills_role() == 'Sales Executive', skills_role())
    chk('the new resume is the active one', cur().get('role') == 'Sales Executive')
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
