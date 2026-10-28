# Image tools (rotate, flip, crop, resize, black and white, change format) and the swap bars
# that flip between PDF to pictures and Pictures to PDF on the same screen.
import functools, socket, threading, pathlib, tempfile, io
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from PIL import Image
from playwright.sync_api import sync_playwright
WWW = str(pathlib.Path(__file__).resolve().parent.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_img_') + '/'
pic = TMP + 'wide.jpg'; Image.new('RGB', (300, 200), (200, 40, 40)).save(pic, 'JPEG')
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))
s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(SimpleHTTPRequestHandler, directory=WWW); h.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
INIT = "if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}"
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(INIT)
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(2500)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(300)
    chk('Image tools tile is on Home', pg.evaluate("!!document.querySelector('.tl-tile[data-tool=imagetools]')"))
    pg.evaluate("document.querySelector('.tl-tile[data-tool=imagetools]').click()"); pg.wait_for_timeout(500)
    chk('Image tools hub shows its picture tools on screen', pg.evaluate("['rotateimg','flipimg','cropimg','resizeimg','grayimg','convertimg'].every(k=> { const e = document.querySelector('#toolBody [data-tool='+k+']'); return !!e && e.offsetParent !== null; })"))
    pg.evaluate("document.querySelector('#toolBody [data-tool=rotateimg]').click()"); pg.wait_for_timeout(400)
    pg.set_input_files('#it-file', pic); pg.wait_for_timeout(400)
    with pg.expect_download(timeout=60000) as dl:
        pg.evaluate("document.getElementById('it-go').click()")
    saved = TMP + 'rot.jpg'; dl.value.save_as(saved)
    chk('rotate 90 turns a 300x200 picture into 200x300', Image.open(saved).size == (200, 300), Image.open(saved).size)
    # swap bar: Pictures to PDF is reached on the same screen from PDF to pictures
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=pdftools]').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('#toolBody [data-tool=pdf2jpg]').click()"); pg.wait_for_timeout(400)
    chk('PDF to pictures shows the swap bar', pg.evaluate("!!document.querySelector('#toolBody .swap-bar')"))
    pg.evaluate("document.querySelector('[data-swap=imgpdf]').click()"); pg.wait_for_timeout(400)
    chk('the swap bar switches to Images to PDF', pg.evaluate("document.getElementById('toolTitle').textContent") == 'Images to PDF')
    chk('Images to PDF also shows the swap bar', pg.evaluate("document.querySelector('[data-swap=pdf2jpg]') !== null && document.querySelector('[data-swap=imgpdf]').getAttribute('aria-checked')==='true'"))
    pg.evaluate("document.querySelector('[data-swap=pdf2jpg]').click()"); pg.wait_for_timeout(400)
    chk('and back again', pg.evaluate("document.getElementById('toolTitle').textContent") == 'PDF to JPG')
    # resize to 50% and black and white on real files
    def run_tool(key, pick_js=None):
        pg.evaluate("document.getElementById('toolBack') && document.getElementById('toolBack').click()"); pg.wait_for_timeout(300)
        pg.evaluate("document.querySelector('.tl-tile[data-tool=imagetools]').click()"); pg.wait_for_timeout(400)
        pg.evaluate(f"document.querySelector('#toolBody [data-tool={key}]').click()"); pg.wait_for_timeout(400)
        pg.set_input_files('#it-file', pic); pg.wait_for_timeout(300)
        if pick_js: pg.evaluate(pick_js); pg.wait_for_timeout(200)
        with pg.expect_download(timeout=60000) as d:
            pg.evaluate("document.getElementById('it-go').click()")
        out = TMP + key + '.' + d.value.suggested_filename.rsplit('.',1)[-1]; d.value.save_as(out); return out
    half = run_tool('resizeimg', "document.querySelector('[data-opt=scale][data-val=\"0.5\"]').click()")
    chk('resize to 50% gives 150x100', Image.open(half).size == (150, 100), Image.open(half).size)
    bw = run_tool('grayimg')
    px = Image.open(bw).convert('RGB').getpixel((50, 50))
    chk('black and white has no colour', abs(px[0]-px[1]) < 4 and abs(px[1]-px[2]) < 4, px)
    png = run_tool('convertimg', "document.querySelector('[data-opt=fmt][data-val=\"image/png\"]').click()")
    chk('change format saves a PNG', Image.open(png).format == 'PNG', Image.open(png).format)
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
