# Sample or my own content: switch any time from the Content and Preview tabs; nothing is lost; undo works; saved on the phone.
import pathlib
import functools, socket, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
HERE = pathlib.Path(__file__).resolve().parent
# served over http (not file://) so a page reload keeps its saved data, as it does on the phone
_s = socket.socket(); _s.bind(('127.0.0.1', 0)); PORT = _s.getsockname()[1]; _s.close()
_h = functools.partial(SimpleHTTPRequestHandler, directory=str(HERE.parent / 'www')); _h.log_message = lambda *a, **k: None
_srv = ThreadingHTTPServer(('127.0.0.1', PORT), _h); threading.Thread(target=_srv.serve_forever, daemon=True).start()
URL = f'http://127.0.0.1:{PORT}/index.html'
res = []
def chk(name, ok, extra=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' — ' + str(extra)))
from playwright.sync_api import sync_playwright
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    name = lambda: pg.evaluate("(document.querySelector('#segContent input[data-key=name]')||{}).value")
    on = lambda: pg.evaluate("(()=>{const e=[...document.querySelectorAll('[data-content-switch]')].find(x=>x.offsetParent); const o=e&&e.querySelector('.pagesize-chip.on'); return o?o.dataset.cs:null})()")
    def cs(kind):
        pg.evaluate(f"[...document.querySelectorAll('[data-content-switch] [data-cs={kind}]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(500)
    # a blank resume that the user fills in
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=resumes]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    pg.evaluate("document.getElementById('rsNewBlank').click()"); pg.wait_for_timeout(1200)
    chk('the switch is on the Content tab', pg.evaluate("[...document.querySelectorAll('[data-content-switch] [data-cs=sample]')].some(x=>x.offsetParent)"))
    chk('a new blank resume shows My content as selected', on() == 'own', on())
    pg.fill('#segContent input[data-key=name]', 'Priya Sharma'); pg.wait_for_timeout(500)
    # sample
    cs('sample')
    chk('Sample fills the resume with the full sample', name() == 'Alex Morgan', name())
    chk('Sample is shown as selected', on() == 'sample', on())
    # my content comes back
    cs('own')
    chk('My content brings the user\'s own text back', name() == 'Priya Sharma', name())
    chk('My content is shown as selected', on() == 'own', on())
    # undo and undo again
    cs('sample'); cs('undo')
    chk('Undo goes back to the user\'s content', name() == 'Priya Sharma', name())
    cs('undo')
    chk('Undo again goes forward to the sample', name() == 'Alex Morgan', name())
    # it is saved: reload keeps both versions
    pg.reload(); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('[data-tab=create], [data-tab=edit], .bd-resume') && 0")
    saved = pg.evaluate("(()=>{const rs=JSON.parse(localStorage.getItem('resumate_resumes_v2')||'{}'); const it=(rs.items||[]).find(i=>i.id===rs.active); return it? {own: it.own && it.own.name, undo: !!it.undo, now: it.data && it.data.name, active: rs.active, ids: (rs.items||[]).map(i=>i.id)} : {active: rs.active, ids: (rs.items||[]).map(i=>i.id)}})()")
    chk('the sample, the user\'s own content and undo are saved on the phone', saved and saved['own'] == 'Priya Sharma' and saved['undo'] and saved['now'] == 'Alex Morgan', saved)
    pg.evaluate("document.querySelector('[data-content-switch] [data-cs=own]').click()"); pg.wait_for_timeout(600)
    back = pg.evaluate("(()=>{const rs=JSON.parse(localStorage.getItem('resumate_resumes_v2')||'{}'); const it=(rs.items||[]).find(i=>i.id===rs.active); return it && it.data && it.data.name})()")
    chk('after a restart, My content brings the user\'s own resume back', back == 'Priya Sharma', back)
    # the Preview tab has it too
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=resumes]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('.bd-resume, [data-open-edit]') && 0")
    pg.evaluate("document.querySelector('[data-seg=preview]') && document.querySelector('[data-seg=preview]').click()"); pg.wait_for_timeout(400)
    chk('the switch is also in the Preview tab', pg.evaluate("[...document.querySelectorAll('#segPreview [data-content-switch] [data-cs]')].length === 3"))
    chk('no page errors', not errs, errs[:3]); ctx.close(); b.close()
print(f"{sum(res)}/{len(res)} passed"); raise SystemExit(0 if all(res) else 1)
