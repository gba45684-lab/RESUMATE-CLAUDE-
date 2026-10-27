# Checks the PDF tools card: Home keeps only the card for PDF work, and the card lists every PDF tool, each of which opens.
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
PDF_TOOLS = ['imgpdf', 'mergepdf', 'rotatepdf', 'croppdf', 'shrinkpdf', 'signpdf', 'splitpdf', 'pagenums', 'watermark', 'pdf2jpg', 'pdf2txt', 'protectpdf', 'unlockpdf']

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    chk('PDF tools card is on Home, in Documents', pg.evaluate("!!document.querySelector('.tl-tiles [data-tool=pdftools]') && document.querySelector('[data-tool=pdftools] b').textContent === 'PDF tools'"))
    chk('Home has no other PDF tiles', pg.evaluate("%s.every(t=> !document.querySelector('.tl-tiles [data-tool=\"'+t+'\"]'))" % repr(PDF_TOOLS)))
    chk('Import PDF resume is in the Resume group', pg.evaluate("!!document.querySelector('.tl-group [data-tool=importpdf]') && [...document.querySelectorAll('.tl-group')].some(g=> g.querySelector('[data-tool=importpdf]') && g.querySelector('.tl-subh').textContent === 'Resume')"))
    chk('Smart tools has no Edit PDF, Convert or Security groups', pg.evaluate("![...document.querySelectorAll('.tl-tiles .tl-subh')].some(e=> ['Edit PDF','Convert','Security'].includes(e.textContent))"))

    pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(600)
    chk('card opens the PDF tools screen', pg.evaluate("document.getElementById('toolTitle').textContent") == 'PDF tools')
    chk('screen lists all 13 PDF tools', pg.evaluate("document.querySelectorAll('#toolBody .tl-tile').length") == 13)
    chk('screen has the four groups', pg.evaluate("[...document.querySelectorAll('#toolBody .tl-subh')].map(e=>e.textContent).join(',')") == 'Documents,Edit PDF,Convert,Security')
    chk('screen has ResuMate Premium', pg.evaluate("!!document.querySelector('#toolBody [data-tool=premium]')"))
    pg.evaluate("document.querySelector('#toolBody [data-tool=rotatepdf]').click()"); pg.wait_for_timeout(600)
    chk('tapping a tile opens that tool', pg.evaluate("document.getElementById('toolTitle').textContent") == 'Rotate PDF', pg.evaluate("document.getElementById('toolTitle').textContent"))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('#toolBody [data-tool=premium]').click()"); pg.wait_for_timeout(600)
    chk('Premium opens from the card', pg.evaluate("document.getElementById('toolTitle').textContent") == 'ResuMate Premium')
    pg.evaluate("document.querySelector('[data-plan=yearly]').click()"); pg.wait_for_timeout(200)
    chk('buying says nothing is charged while purchases are off', 'Nothing has been charged' in pg.evaluate("document.getElementById('premMsg').textContent"))
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
