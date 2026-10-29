# Job match saves a version for the job; the job tracker keeps a posting link; two new role starts.
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
CNT = "(JSON.parse(localStorage.getItem('resumate_resumes_v2')||'{\"items\":[]}').items||[]).length"
AD = ("Acme Corp is looking for a Product Manager to lead our analytics roadmap. You will work with engineering and design, "
      "own discovery and delivery, write clear requirements, track metrics, and communicate with stakeholders. Experience with "
      "SQL, dashboards, customer research and agile delivery is valued. Position: Product Manager. Location: Noida. ") * 2
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(INIT)
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    def open_tool(k):
        pg.evaluate("(()=>{const t=document.getElementById('toolPage'); if(t&&!t.hidden) document.getElementById('toolBack').click();})()"); pg.wait_for_timeout(450)
        pg.evaluate("document.querySelector('[data-tab=home]').click()"); pg.wait_for_timeout(500)
        pg.evaluate(f"[...document.querySelectorAll('.tl-tile[data-tool={k}]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    # 1) Job match -> save a version for this job
    open_tool('job')
    pg.fill('#jdText', AD); pg.evaluate("document.getElementById('jdGo').click()"); pg.wait_for_timeout(500)
    chk('the company is guessed from the ad', pg.evaluate("document.getElementById('jdVCo').value") == 'Acme Corp', pg.evaluate("document.getElementById('jdVCo').value"))
    chk('the job title is guessed from the ad', pg.evaluate("document.getElementById('jdVRole').value") == 'Product Manager', pg.evaluate("document.getElementById('jdVRole').value"))
    n = pg.evaluate(CNT)
    pg.evaluate("document.getElementById('jdVersion').click()"); pg.wait_for_timeout(700)
    label = pg.evaluate("(JSON.parse(localStorage.getItem('resumate_resumes_v2')).items||[]).map(i=>i.label)")
    chk('Save as a version adds one resume', pg.evaluate(CNT) == n + 1, (n, pg.evaluate(CNT)))
    chk('the new version is named for the job', 'Product Manager · Acme Corp' in label, label)
    # 2) job tracker keeps the posting link
    open_tool('jobtracker')
    pg.fill('#jtRole', 'Product Manager'); pg.fill('#jtCo', 'Acme Corp'); pg.fill('#jtLink', 'javascript:alert(1)')
    pg.evaluate("document.getElementById('jtAdd').click()"); pg.wait_for_timeout(400)
    chk('a link that is not https is refused', pg.evaluate("(JSON.parse(localStorage.getItem('resumate_jobs_v1')||'[]')).length") == 0 and 'https' in pg.evaluate("document.getElementById('jtMsg').textContent"))
    pg.fill('#jtLink', 'https://careers.acme.example/job/42')
    pg.evaluate("document.getElementById('jtAdd').click()"); pg.wait_for_timeout(500)
    saved = pg.evaluate("(JSON.parse(localStorage.getItem('resumate_jobs_v1')||'[]'))[0]")
    chk('a valid link is saved with the application', saved and saved.get('link') == 'https://careers.acme.example/job/42', saved)
    chk('the row shows Open posting', pg.evaluate("!!document.querySelector('.jt-open')"))
    # 3) two new role starts appear and fill in without leaving placeholders
    open_tool('roleresume')
    opts = pg.evaluate("[...document.querySelectorAll('#rrJob option')].map(o=>o.value)")
    chk('Government / PSU and Career switch are offered', 'Government / PSU job' in opts and 'Career switch' in opts, opts)
    pg.select_option('#rrJob', 'Government / PSU job'); pg.wait_for_timeout(300)
    chk('the government start lists its skills', pg.evaluate("document.querySelectorAll('[data-skill]').length") >= 3)
    chk('no page errors', not errs, errs[:3]); ctx.close(); b.close()
print(f"{sum(res)}/{len(res)} passed"); raise SystemExit(0 if all(res) else 1)
