# Checks OCR for scanned resumes: a PDF with no text layer and a photo of a resume are read on the phone.
import os, pathlib, tempfile, threading, functools, socket
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_ocr_') + '/'
from PIL import Image, ImageDraw, ImageFont
from reportlab.pdfgen import canvas
from playwright.sync_api import sync_playwright
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))

FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf'
LINES = ['Krapal Singh', 'Senior Product Manager', 'krapal.test@example.com', 'Summary', 'Product manager with eight years of experience.', 'Skills', 'Python, SQL, Figma']
# the resume as a picture, with no text layer
img = Image.new('RGB', (1240, 1754), 'white'); d = ImageDraw.Draw(img); f = ImageFont.truetype(FONT, 34)
for i, ln in enumerate(LINES): d.text((90, 90 + i * 64), ln, font=f, fill='black')
img.save(TMP + 'scan.png')
scan_pdf = TMP + 'scan.pdf'; c = canvas.Canvas(scan_pdf, pagesize=(595, 842)); c.drawImage(TMP + 'scan.png', 0, 0, width=595, height=842); c.save()
photo = TMP + 'photo.jpg'; img.convert('RGB').save(photo, 'JPEG', quality=90)

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port
port = free_port()
handler = functools.partial(SimpleHTTPRequestHandler, directory=WWW); handler.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

def wait_done(pg, limit=240):
    import time
    t0 = time.time()
    while time.time() - t0 < limit:
        done = pg.evaluate("(()=>!!document.getElementById('imp-name') || /Couldn|couldn|didn/.test((document.getElementById('impMsg')||{}).textContent||''))()")
        if done: return
        pg.wait_for_timeout(1000)

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-tool=importpdf]').click()"); pg.wait_for_timeout(600)
    chk('picker accepts PDFs and photos', 'image/*' in pg.evaluate("document.getElementById('impFile').accept"))

    val = lambda k: pg.evaluate(f"(document.getElementById('imp-{k}')||{{}}).value || ''")
    pg.set_input_files('#impFile', scan_pdf)
    wait_done(pg)
    chk('scanned PDF: name is read by OCR', 'Krapal' in val('name') and 'Singh' in val('name'), val('name'))
    chk('scanned PDF: email is read by OCR', 'krapal' in val('email').lower() and '@' in val('email'), val('email'))
    chk('scanned PDF: the review says it came from OCR', 'Read from a scan with OCR' in pg.evaluate("document.getElementById('toolBody').innerText"))

    pg.evaluate("document.getElementById('impBack').click()"); pg.wait_for_timeout(400)
    pg.set_input_files('#impFile', photo)
    wait_done(pg)
    chk('photo: name is read by OCR', 'Krapal' in val('name'), val('name'))
    chk('photo: skills are read by OCR', 'Python' in val('skills') or 'Figma' in val('skills'), val('skills'))

    chk('OCR engine is not left running', pg.evaluate("typeof ocrJob === 'undefined' || ocrJob === null") is True)
    chk('no script errors', not errs, errs)
    b.close()
srv.shutdown()
print(f"\n{sum(ok for _, ok in res)}/{len(res)} passed")
