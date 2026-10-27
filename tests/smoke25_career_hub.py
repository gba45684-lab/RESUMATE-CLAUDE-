# Checks the career hub: Career group placement, Job match explanation, Interview prep, Messages, and the resume name on job applications.
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
JD = ('We are hiring a product analyst to work with our growth team. You will build dashboards in SQL and Python, run A/B tests, '
      'and present findings to stakeholders. Experience with Figma, Amplitude and user research is a plus. Strong communication is required.')

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)
    open_tool = lambda t: (pg.evaluate(f"document.querySelector('.tl-tiles [data-tool={t}]').click()"), pg.wait_for_timeout(600))
    close = lambda: (pg.evaluate("document.getElementById('toolBack').click()"), pg.wait_for_timeout(500))

    order = pg.evaluate("[...document.querySelectorAll('.tl-tiles .tl-subh')].map(e=>e.textContent)")
    chk('Career group sits right after Resume', order[:2] == ['Resume', 'Career'], order)
    career = pg.evaluate("[...document.querySelectorAll('.tl-tiles .tl-group')].find(g=> g.querySelector('.tl-subh').textContent === 'Career').querySelectorAll('[data-tool]')")
    tools = pg.evaluate("[...document.querySelectorAll('.tl-tiles .tl-group')].find(g=> g.querySelector('.tl-subh').textContent === 'Career').querySelectorAll('[data-tool]').length")
    chk('Career has five tools', tools == 5, tools)
    chk('Resume no longer holds job match or cover letter', pg.evaluate("![...document.querySelectorAll('.tl-tiles .tl-group')].find(g=> g.querySelector('.tl-subh').textContent === 'Resume').querySelectorAll('[data-tool=job],[data-tool=letter],[data-tool=jobtracker]').length"))

    open_tool('job')
    pg.fill('#jdText', JD); pg.evaluate("document.getElementById('jdGo').click()"); pg.wait_for_timeout(400)
    chk('job match explains how the score works', 'How this score works' in pg.evaluate("document.getElementById('jdOut').textContent") and 'not a promise' in pg.evaluate("document.getElementById('jdOut').textContent"))
    close()

    open_tool('interview')
    chk('interview prep opens with six questions', pg.evaluate("document.querySelectorAll('.iv-q').length") == 6)
    pg.select_option('#ivFam', 'Sales'); pg.wait_for_timeout(400)
    chk('switching job type changes the questions', 'customers' in pg.evaluate("document.querySelector('.iv-q b').textContent"), pg.evaluate("document.querySelector('.iv-q b').textContent"))
    pg.evaluate("document.querySelector('[data-starter]') && document.querySelector('[data-starter]').click()"); pg.wait_for_timeout(200)
    filled = pg.evaluate("document.querySelector('.iv-q textarea').value")
    chk('"Start from my experience" fills the answer from the resume', len(filled) > 20 and ' at ' in filled, filled[:80])
    chk('word count appears under the answer', pg.evaluate("document.querySelector('.iv-count').textContent").strip() != '')
    pg.reload(); pg.wait_for_timeout(4000)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(300)
    open_tool('interview')
    chk('answers and job type are kept after a reload', pg.evaluate("document.getElementById('ivFam').value") == 'Sales' and len(pg.evaluate("document.querySelector('.iv-q textarea').value")) > 20)
    close()

    open_tool('messages')
    chk('messages has a recruiter reply by default', 'Thank you for reaching out' in pg.evaluate("document.getElementById('msOut').value"))
    pg.evaluate("document.querySelector('[data-type=linkedin]').click()"); pg.wait_for_timeout(300)
    chk('LinkedIn summary uses the resume role and skills', 'Figma' in pg.evaluate("document.getElementById('msOut').value") or '|' in pg.evaluate("document.getElementById('msOut').value"))
    pg.evaluate("document.querySelector('[data-type=followup]').click()"); pg.wait_for_timeout(300)
    chk('follow-up email has a subject line', pg.evaluate("document.getElementById('msOut').value").startswith('Subject:'))
    pg.evaluate("document.getElementById('msCopy').click()"); pg.wait_for_timeout(300)
    chk('copy gives feedback', pg.evaluate("document.getElementById('toastMsg').textContent").strip() != '')
    close()

    open_tool('jobtracker')
    pg.fill('#jtRole', 'Analyst'); pg.fill('#jtCo', 'Acme')
    pg.evaluate("document.getElementById('jtAdd').click()"); pg.wait_for_timeout(300)
    chk('job application records the resume it used', 'Resume:' in pg.evaluate("document.querySelector('.jt-row').textContent"), pg.evaluate("document.querySelector('.jt-row').textContent")[:120])
    close()
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
