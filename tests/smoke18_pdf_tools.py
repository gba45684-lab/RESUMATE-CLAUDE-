# Checks the Edit PDF and Convert tools on the phone: rotate, crop, shrink, PDF to JPG, PDF to text.
import pathlib, tempfile, threading, functools, socket, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_pdftools_') + '/'
try:
    import pypdf
except ImportError:
    pypdf = None
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))

# two text pages, and one picture-only page (a scan)
text_pdf = TMP + 'text.pdf'
c = canvas.Canvas(text_pdf, pagesize=(595, 842))
c.drawString(72, 760, 'Krapal Singh resume page one'); c.showPage()
c.drawString(72, 760, 'Second page with more words'); c.save()
img = Image.new('RGB', (1240, 1754), 'white'); ImageDraw.Draw(img).text((90, 90), 'Scanned only', fill='black'); img.save(TMP + 'scan.png')
scan_pdf = TMP + 'scan.pdf'; c = canvas.Canvas(scan_pdf, pagesize=(595, 842)); c.drawImage(TMP + 'scan.png', 0, 0, width=595, height=842); c.save()

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port
port = free_port()
handler = functools.partial(SimpleHTTPRequestHandler, directory=WWW); handler.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

def wait_msg(pg, limit=120):
    t0 = time.time()
    while time.time() - t0 < limit:
        m = pg.evaluate("(document.getElementById('pt-msg')||{}).textContent||''")
        if m and 'Working' not in m and not m.startswith('Page '): return m
        pg.wait_for_timeout(500)
    return 'TIMEOUT'

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    tools = ['rotatepdf', 'croppdf', 'shrinkpdf', 'pdf2jpg', 'pdf2txt']
    chk('PDF tools card is on Home', pg.evaluate("!!document.querySelector('[data-tool=pdftools]')"))
    pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(500)
    chk('PDF tools card lists Edit PDF and Convert', pg.evaluate("[...document.querySelectorAll('#toolBody .tl-subh')].map(e=>e.textContent).includes('Edit PDF') && [...document.querySelectorAll('#toolBody .tl-subh')].map(e=>e.textContent).includes('Convert')"))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)

    def open_tool(t):
        pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(500)
        pg.evaluate(f"document.querySelector('#toolBody [data-tool={t}]').click()"); pg.wait_for_timeout(600)
    def close_tool():
        pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)
    def run_and_save(name=None):
        with pg.expect_download(timeout=120000) as dl:
            pg.evaluate("document.getElementById('pt-go').click()")
        d = dl.value; out = TMP + d.suggested_filename; d.save_as(out); return out

    # Rotate: default is right 90°
    open_tool('rotatepdf')
    pg.set_input_files('#pt-file', text_pdf); pg.wait_for_timeout(500)
    out = run_and_save()
    chk('rotate: a PDF is saved', out.endswith('.pdf') and open(out, 'rb').read(4) == b'%PDF')
    if pypdf and out.endswith('.pdf'):
        r = pypdf.PdfReader(out)
        chk('rotate: every page turned 90 degrees', all(pgx.get('/Rotate', 0) % 360 == 90 for pgx in r.pages), [pgx.get('/Rotate') for pgx in r.pages])
    close_tool()

    # Crop: trim 10% from each edge
    open_tool('croppdf')
    pg.set_input_files('#pt-file', text_pdf); pg.wait_for_timeout(500)
    pg.evaluate("const r=document.getElementById('pt-pct'); r.value='10'; r.dispatchEvent(new Event('input'))")
    out = run_and_save()
    if pypdf:
        r = pypdf.PdfReader(out); w = float(r.pages[0].mediabox.width)
        chk('crop: width reduced by 20% (10% each side)', abs(w - 595 * 0.8) < 1, w)
    else:
        chk('crop: file saved', out.endswith('.pdf'))
    close_tool()

    # Shrink: balanced, keeps both pages
    open_tool('shrinkpdf')
    pg.set_input_files('#pt-file', text_pdf); pg.wait_for_timeout(500)
    out = run_and_save()
    chk('shrink: valid PDF saved', open(out, 'rb').read(4) == b'%PDF')
    if pypdf:
        chk('shrink: both pages kept', len(pypdf.PdfReader(out).pages) == 2)
    close_tool()

    # PDF to JPG: one file per page
    open_tool('pdf2jpg')
    pg.set_input_files('#pt-file', text_pdf); pg.wait_for_timeout(500)
    got = []
    pg.on('download', lambda d: got.append(d))
    pg.evaluate("document.getElementById('pt-go').click()")
    t0 = time.time()
    while len(got) < 2 and time.time() - t0 < 120: pg.wait_for_timeout(300)
    files = []
    for d in got:
        o = TMP + d.suggested_filename; d.save_as(o); files.append(o)
    chk('pdf to JPG: two pictures for two pages', len(files) == 2, [f.split('/')[-1] for f in files])
    chk('pdf to JPG: files are JPEG', all(open(f, 'rb').read(2) == b'\xff\xd8' for f in files))
    chk('pdf to JPG: message says two pictures', 'Saved 2 pictures' in pg.evaluate("document.getElementById('pt-msg').textContent"))
    close_tool()

    # PDF to text: text layer gives a file, scan gives a helpful message
    open_tool('pdf2txt')
    pg.set_input_files('#pt-file', text_pdf); pg.wait_for_timeout(500)
    out = run_and_save()
    txt = open(out, encoding='utf-8').read()
    chk('pdf to text: words are saved', 'Krapal Singh' in txt and 'Second page' in txt, txt[:80])
    close_tool()
    open_tool('pdf2txt')
    pg.set_input_files('#pt-file', scan_pdf); pg.wait_for_timeout(500)
    pg.evaluate("document.getElementById('pt-go').click()"); pg.wait_for_timeout(2500)
    chk('pdf to text: scan gets the OCR hint', 'Import PDF' in pg.evaluate("document.getElementById('pt-msg').textContent"))
    close_tool()

    chk('no page errors', not errs, errs[:3])
    b.close()

srv.shutdown()
ok = sum(1 for _, v in res if v)
print(f'\n{ok}/{len(res)} passed')
