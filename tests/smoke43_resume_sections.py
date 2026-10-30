# Resume: hide sections and contact details, date-gap checker, and paste-text import (no AI).
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
MOCK = """window.Capacitor={isNativePlatform:()=>false,Plugins:{}};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=sections]').click()"); pg.wait_for_timeout(600)
    chk('the sections tool opens from Home', pg.evaluate("!!document.querySelector('[data-sec=summary]')"))
    pg.evaluate("document.querySelector('[data-sec=summary]').click()"); pg.wait_for_timeout(500)
    chk('hiding a section is saved with the resume', 'summary' in json.loads(pg.evaluate("localStorage.getItem('resumate_resume_v1')") or '{}').get('hiddenSections', []), pg.evaluate("localStorage.getItem('resumate_resume_v1')")[:200] if pg.evaluate("localStorage.getItem('resumate_resume_v1')") else 'nothing saved')
    chk('the preview data leaves the hidden summary out', pg.evaluate("window.__resume.viewData(window.__resume.data()).summary === ''"))
    chk('other sections are kept', pg.evaluate("window.__resume.viewData(window.__resume.data()).experience.length > 0"))
    pg.evaluate("document.querySelector('[data-sec=summary]').click()"); pg.wait_for_timeout(500)
    chk('showing it again brings it back', pg.evaluate("window.__resume.viewData(window.__resume.data()).summary.length > 0"))
    pg.evaluate("document.getElementById('pvHideContact').click()"); pg.wait_for_timeout(500)
    chk('hiding contact details blanks the email and phone in the output', pg.evaluate("(()=>{const v=window.__resume.viewData(window.__resume.data()); return v.email==='' && v.phone==='' && v.linkedin==='';})()"))
    chk('the saved details themselves are not deleted', pg.evaluate("window.__resume.data().email.length > 0"))
    gaps = pg.evaluate("window.__resume.dateGaps([{title:'A',dates:'2010 — 2012'},{title:'B',dates:'2015 — 2016'}])")
    chk('a gap of two years is found', len(gaps) == 1 and gaps[0]['months'] == 24, gaps)
    chk('no gap when the next job starts the month after', pg.evaluate("window.__resume.dateGaps([{title:'A',dates:'Jan 2018 — Dec 2019'},{title:'B',dates:'Jan 2020 — Present'}]).length") == 0)
    chk('months-only gaps under six months are ignored', pg.evaluate("window.__resume.dateGaps([{title:'A',dates:'2018 — 2019'},{title:'B',dates:'2020 — 2021'}]).length") == 0)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=score]').click()"); pg.wait_for_timeout(600)
    chk('the score screen shows the date-gap section', pg.evaluate("[...document.querySelectorAll('.tl-h')].some(h=>h.textContent.trim()==='Date gaps')"))
    pg.evaluate("document.querySelector('.tl-tile[data-tool=importpdf]').click()"); pg.wait_for_timeout(600)
    pg.fill('#impPaste', 'Priya Sharma\nProduct Designer\npriya.sharma@example.com\n+91 99999 00000\nExperience\nDesigner at Acme 2019 — 2023')
    pg.click('#impPasteGo'); pg.wait_for_timeout(500)
    email = pg.evaluate("(document.getElementById('imp-email')||{}).value || ''")
    chk('pasted text fills the email field', email == 'priya.sharma@example.com', email)
    chk('pasted text fills the name field', pg.evaluate("(document.getElementById('imp-name')||{}).value || ''").startswith('Priya'))
    pg.click('#impBack'); pg.wait_for_timeout(400)
    pg.fill('#impPaste', 'short'); pg.click('#impPasteGo'); pg.wait_for_timeout(300)
    chk('too little pasted text is refused', 'Paste at least a few lines' in pg.evaluate("document.getElementById('impMsg').textContent"))
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
