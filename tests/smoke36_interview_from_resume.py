# Interview prep: questions made from the resume, STAR notes saved, 2-minute timer, AI feedback that drops invented numbers.
import pathlib, functools, socket, threading, json
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
AI_TEXT = json.dumps({"strengths": ["You name a clear result."], "gaps": ["Say what you did first."],
                      "stronger": "Situation: the team was behind. Task: fix the backlog. Action: I set weekly goals. Result: we cut it by 300%."})
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(INIT)
    calls = []
    def fake_ai(route):
        calls.append(route.request.url)
        route.fulfill(status=200, content_type='application/json', headers={'X-Free-Limit': '20', 'X-Free-Remaining': '19'},
                      body=json.dumps({"candidates": [{"content": {"parts": [{"text": AI_TEXT}]}}]}))
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    ctx.route('https://resumate-ai.gba45684.workers.dev/**', fake_ai)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=interview]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    n = pg.evaluate("document.querySelectorAll('#ivResume .iv-q').length")
    chk('questions are made from the resume', n >= 3, n)
    chk('a question names the resume role', pg.evaluate("document.querySelector('#ivResume .iv-q b').textContent.includes('Walk me through your work')"))
    chk('the feedback button starts disabled (no answer yet)', pg.evaluate("document.querySelector('[data-fb=\"0\"]').disabled"))
    pg.fill('[data-key="r|0"]', 'We had a backlog of forty tickets and it kept growing each week because nobody owned triage.')
    pg.wait_for_timeout(200)
    chk('a short answer keeps the feedback button off', pg.evaluate("document.querySelector('[data-fb=\"0\"]').disabled"))
    long = ' '.join(['I took ownership of the backlog and set a weekly triage routine with the team, then tracked the open count every Monday.'] * 2)
    pg.fill('[data-key="r|0"]', long); pg.wait_for_timeout(200)
    chk('a 20+ word answer enables feedback', not pg.evaluate("document.querySelector('[data-fb=\"0\"]').disabled"))
    pg.reload(); pg.wait_for_timeout(2000)
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=interview]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    chk('the answer is kept on the phone after a restart', pg.evaluate("document.querySelector('[data-key=\"r|0\"]').value").startswith('I took ownership'))
    pg.evaluate("document.querySelector('[data-timer=\"0\"]').click()"); pg.wait_for_timeout(1300)
    chk('the 2-minute timer counts down', '1:5' in pg.evaluate("document.querySelector('[data-timer=\"0\"]').textContent") or '2:00' in pg.evaluate("document.querySelector('[data-timer=\"0\"]').textContent"), pg.evaluate("document.querySelector('[data-timer=\"0\"]').textContent"))
    pg.evaluate("document.querySelector('[data-fb=\"0\"]').click()"); pg.wait_for_timeout(1200)
    out = pg.evaluate("document.getElementById('ivFb0').textContent")
    chk('AI feedback shows what was good and what to improve', 'You name a clear result' in out and 'Say what you did first' in out, out[:120])
    chk('the stronger version with an invented % is dropped', 'stronger version' not in out and '300%' not in out, out[-120:])
    chk('the request went through the app\'s AI proxy', any('resumate-ai' in u for u in calls), calls[:1])
    chk('no page errors', not errs, errs[:3]); ctx.close(); b.close()
print(f"{sum(res)}/{len(res)} passed"); raise SystemExit(0 if all(res) else 1)
