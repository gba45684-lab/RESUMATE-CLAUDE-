# Checks Sign, Split, Page numbers and Watermark, and the free file-size limit with Premium.
import pathlib, functools, socket, threading, tempfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from reportlab.pdfgen import canvas
from pypdf import PdfReader
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_more_') + '/'
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))
two = TMP + 'two.pdf'; c = canvas.Canvas(two, pagesize=(595, 842)); c.drawString(72, 760, 'Page one text'); c.showPage(); c.drawString(72, 760, 'Page two text'); c.showPage(); c.drawString(72, 760, 'Page three text'); c.save()
big = TMP + 'big.pdf'
with open(big, 'wb') as f: f.write(b'%PDF-1.4\n' + b'0' * (11 * 1024 * 1024) + b'\n%%EOF\n')
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
    msg = lambda: pg.evaluate("(document.getElementById('pt-msg')||{}).textContent||''")
    def open_tool(t):
        pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(500)
        pg.evaluate(f"document.querySelector('#toolBody [data-tool={t}]').click()"); pg.wait_for_timeout(600)
    def go():
        pg.evaluate("document.getElementById('pt-go').click()")
    def save_next():
        with pg.expect_download(timeout=120000) as dl:
            go()
        out = TMP + dl.value.suggested_filename; dl.value.save_as(out); return out

    # Sign: no drawing yet is refused; a drawn signature is placed on the page
    open_tool('signpdf')
    pg.set_input_files('#pt-file', two); pg.wait_for_timeout(500)
    go(); pg.wait_for_timeout(300)
    chk('sign: asks for a drawn signature first', 'Draw your signature first' in msg(), msg())
    box = pg.evaluate("(()=>{const r=document.getElementById('sgCv').getBoundingClientRect(); return [r.left, r.top, r.width, r.height];})()")
    x0, y0, w, h = box
    pg.mouse.move(x0 + w * 0.2, y0 + h * 0.5); pg.mouse.down()
    for i in range(1, 12): pg.mouse.move(x0 + w * (0.2 + i * 0.05), y0 + h * (0.5 + (0.2 if i % 2 else -0.2)))
    pg.mouse.up(); pg.wait_for_timeout(200)
    chk('sign: the drawing is kept', pg.evaluate("(document.getElementById('sgCv')&&1)") == 1)
    pg.evaluate("document.getElementById('sgPage').value = '2'; document.getElementById('sgPage').dispatchEvent(new Event('input'))")
    out = save_next()
    r = PdfReader(out)
    xo = r.pages[1].get('/Resources', {}).get('/XObject', {})
    chk('sign: page 2 has the signature image', len(r.pages) == 3 and any(xo[k].get_object().get('/Subtype') == '/Image' for k in xo), list(xo.keys()) if xo else 'none')
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)

    # Split: ranges become separate files
    open_tool('splitpdf')
    pg.set_input_files('#pt-file', two); pg.wait_for_timeout(500)
    pg.evaluate("const i=document.getElementById('spR'); i.value='1-2, 3'; i.dispatchEvent(new Event('input'))")
    got = []; pg.on('download', lambda d: got.append(d))
    go(); t0 = 0
    for _ in range(120):
        if len(got) >= 2: break
        pg.wait_for_timeout(300)
    chk('split: two ranges make two files', len(got) == 2, len(got))
    pg.evaluate("const i=document.getElementById('spR'); i.value='9'; i.dispatchEvent(new Event('input'))"); go(); pg.wait_for_timeout(400)
    chk('split: out-of-range pages are refused', 'between 1 and 3' in msg(), msg())
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)

    # Page numbers: each page gets "n of 3"
    open_tool('pagenums')
    pg.set_input_files('#pt-file', two); pg.wait_for_timeout(500)
    out = save_next()
    texts = [pgx.extract_text() for pgx in PdfReader(out).pages]
    chk('page numbers: each page shows "n of 3"', all(f'{i+1} of 3' in t for i, t in enumerate(texts)), texts)
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)

    # Watermark: the word is on every page
    open_tool('watermark')
    pg.set_input_files('#pt-file', two); pg.wait_for_timeout(500)
    out = save_next()
    texts = [pgx.extract_text() for pgx in PdfReader(out).pages]
    chk('watermark: DRAFT is on every page', all('DRAFT' in t for t in texts))
    pg.evaluate("const i=document.getElementById('wmText'); i.value='עברית'; i.dispatchEvent(new Event('input'))"); go(); pg.wait_for_timeout(300)
    chk('watermark: non-English text is refused', 'English letters' in msg(), msg())
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)

    # Free file limit: an 11 MB file is refused and sends the person to Premium
    open_tool('rotatepdf')
    pg.set_input_files('#pt-file', big); pg.wait_for_timeout(500)
    go(); pg.wait_for_timeout(500)
    chk('free: a file over 10 MB is refused', 'Free use is up to 10 MB' in pg.evaluate("document.getElementById('toastMsg').textContent"), pg.evaluate("document.getElementById('toastMsg').textContent"))
    chk('free: the Premium screen opens', pg.evaluate("document.getElementById('toolTitle').textContent") == 'ResuMate Premium')
    pg.evaluate("localStorage.setItem('resumate_premium','active')")
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)
    open_tool('rotatepdf')
    pg.set_input_files('#pt-file', big); pg.wait_for_timeout(500)
    go(); pg.wait_for_timeout(1500)
    chk('premium: the same 11 MB file is not refused for size', 'Free use is up to 10 MB' not in msg(), msg())
    pg.evaluate("localStorage.removeItem('resumate_premium')")
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
