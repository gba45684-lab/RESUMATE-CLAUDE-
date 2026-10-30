# PDF: Extract images saves each picture in the PDF as a JPG, skips tiny icons, and says so when there are none.
import pathlib, functools, socket, threading, base64, io
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
from PIL import Image
from reportlab.pdfgen import canvas
SCR = '/tmp/claude-0/-home-claude/3f08c25f-de67-5997-a6e3-1b4821c2fe7f/scratchpad'
pathlib.Path(SCR).mkdir(parents=True, exist_ok=True)
big = f'{SCR}/pic_big.png'; Image.new('RGB', (200, 150), (200, 30, 30)).save(big)
mid = f'{SCR}/pic_mid.png'; Image.new('RGB', (120, 90), (30, 30, 200)).save(mid)
tiny = f'{SCR}/pic_tiny.png'; Image.new('RGB', (20, 20), (0, 200, 0)).save(tiny)
PDF = f'{SCR}/with_pictures.pdf'
c = canvas.Canvas(PDF)
c.drawString(72, 780, 'Page one'); c.drawImage(big, 72, 500, 200, 150); c.drawImage(tiny, 300, 500, 20, 20); c.drawImage(mid, 72, 300, 120, 90); c.showPage()
c.drawString(72, 780, 'Page two has only text'); c.showPage(); c.save()
TEXT = f'{SCR}/text_only.pdf'
c = canvas.Canvas(TEXT); c.drawString(72, 780, 'No pictures here'); c.showPage(); c.save()
MOCK = """window.__fs=[]; window.Capacitor={isNativePlatform:()=>true,Plugins:{
  AdMob:{ requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}) },
  Filesystem:{ writeFile:async(o)=>{ window.__fs.push({path:o.path, data:o.data}); return {uri:'file:///x/'+o.path}; } },
  LocalNotifications:{ checkPermissions:async()=>({display:'granted'}), requestPermissions:async()=>({display:'granted'}), createChannel:async()=>({}), registerActionTypes:async()=>({}), schedule:async()=>({}), addListener:async()=>({remove(){}}) },
  Share:{ share:async()=>({}) }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    def run_on(path):
        pg.evaluate("window.__fs.length = 0; localStorage.setItem('resumate_exports', JSON.stringify({day:new Date().toDateString(), n:0}))")
        pg.evaluate("document.querySelector('.tl-tile[data-tool=pdftools]').click()"); pg.wait_for_timeout(500)
        pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=extractimgs]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(600)
        pg.set_input_files('#pt-file', path); pg.wait_for_timeout(900)
        pg.evaluate("document.getElementById('pt-go').click()")
        for _ in range(60):
            msg = pg.evaluate("document.getElementById('pt-msg').textContent")
            if msg and not msg.startswith('Saved ') and 'Looking' not in msg and 'Page ' not in msg: break
            pg.wait_for_timeout(500)
        return pg.evaluate("window.__fs"), pg.evaluate("document.getElementById('pt-msg').textContent")
    fs, msg = run_on(PDF)
    chk('two pictures are saved (icon skipped)', len(fs) == 2, (len(fs), msg))
    sizes = sorted(Image.open(io.BytesIO(base64.b64decode(f['data']))).size for f in fs) if fs else []
    chk('the saved pictures keep their size', sizes == [(120, 90), (200, 150)], sizes)
    chk('the pictures are saved as JPG', all(base64.b64decode(f['data'])[:2] == b'\xff\xd8' for f in fs) if fs else False)
    fs, msg = run_on(TEXT)
    chk('a PDF with no pictures says so', len(fs) == 0 and 'No pictures' in msg, (len(fs), msg))
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
