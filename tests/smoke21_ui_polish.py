# Checks the editor "Saved" hint and the clearer busy messages on the PDF tools.
import pathlib, functools, socket, threading
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from reportlab.pdfgen import canvas
import tempfile
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_ui_') + '/'
pdf = TMP + 'a.pdf'; c = canvas.Canvas(pdf); c.drawString(72, 760, 'Krapal'); c.save()
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
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    # Saved hint: editing a field in the editor shows "Saved on this phone"
    pg.evaluate("document.querySelector('[data-open-edit]').click()"); pg.wait_for_timeout(900)
    chk('editor shows the Saved hint element', pg.evaluate("!!document.getElementById('saveHint')"))
    pg.evaluate("""(()=>{ const i=[...document.querySelectorAll('input[type=text], input:not([type])')].find(e=> e.offsetParent && !e.closest('#toolPage') && !e.closest('#paywall')); if(i){ i.value = (i.value||'') + 'x'; i.dispatchEvent(new Event('input', {bubbles:true})); } })()""")
    pg.wait_for_timeout(200)
    chk('an edit shows "Saved on this phone"', pg.evaluate("(()=>{const e=document.getElementById('saveHint'); return e.classList.contains('on') && /Saved on this phone/.test(e.textContent);})()"), pg.evaluate("document.getElementById('saveHint').className"))
    pg.wait_for_timeout(1800)
    chk('the hint fades out again after a moment', pg.evaluate("!document.getElementById('saveHint').classList.contains('on')"))
    pg.evaluate("document.getElementById('toolBack') && document.getElementById('toolBack').click()")
    pg.evaluate("document.querySelector('.rfs') && 0"); pg.keyboard.press('Escape'); pg.wait_for_timeout(400)

    # Busy message: Protect says it is encrypting straight away
    pg.evaluate("document.querySelector('[data-tool=protectpdf]').click()"); pg.wait_for_timeout(600)
    pg.set_input_files('#pt-file', pdf); pg.wait_for_timeout(400)
    pg.evaluate("(()=>{for(const id of ['pt-pw','pt-pw2']){const e=document.getElementById(id); e.value='secret123'; e.dispatchEvent(new Event('input'));}})()")
    with pg.expect_download(timeout=120000):
        pg.evaluate("document.getElementById('pt-go').click()")
        chk('protect shows an encrypting message', 'Encrypting' in pg.evaluate("document.getElementById('pt-msg').textContent"), pg.evaluate("document.getElementById('pt-msg').textContent"))
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
