# PDF tools: delete pages, extract pages, reorder pages, and black out an area. Each saves a file to the device.
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
from reportlab.pdfgen import canvas
from pypdf import PdfReader
SCR = '/tmp/claude-0/-home-claude/3f08c25f-de67-5997-a6e3-1b4821c2fe7f/scratchpad'
pathlib.Path(SCR).mkdir(parents=True, exist_ok=True)
PDF = f'{SCR}/four_pages.pdf'
c = canvas.Canvas(PDF)
for i in range(1, 5):
    c.drawString(72, 700, f'PAGE {i}'); c.showPage()
c.save()
MOCK = """window.__fs=[]; window.Capacitor={isNativePlatform:()=>true,Plugins:{
  AdMob:{ requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}) },
  Filesystem:{ writeFile:async(o)=>{ window.__fs.push({path:o.path, data:o.data}); return {uri:'file:///x/'+o.path}; } },
  LocalNotifications:{ checkPermissions:async()=>({display:'granted'}), requestPermissions:async()=>({display:'granted'}), createChannel:async()=>({}), registerActionTypes:async()=>({}), schedule:async()=>({}), addListener:async()=>({remove(){}}) },
  Share:{ share:async()=>({}) }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
def pages_of(b64):
    return [pg.extract_text().strip() for pg in PdfReader(io.BytesIO(base64.b64decode(b64))).pages]
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    def open_tool(name):
        pg.evaluate("document.querySelector('.tl-tile[data-tool=pdftools]').click()"); pg.wait_for_timeout(500)
        pg.evaluate(f"[...document.querySelectorAll('.tl-tile[data-tool={name}]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(600)
        pg.set_input_files('#pt-file', PDF); pg.wait_for_timeout(900)
    def run(name, field, value):
        pg.evaluate("window.__fs.length = 0")
        open_tool(name)
        pg.fill(field, value); pg.dispatch_event(field, 'input'); pg.wait_for_timeout(200)
        pg.click('#pt-go'); pg.wait_for_timeout(1800)
        fs = pg.evaluate("window.__fs")
        return (pages_of(fs[-1]['data']) if fs else None), pg.evaluate("document.getElementById('pt-msg').textContent")
    got, msg = run('deletepages', '#dpL', '2, 4')
    chk('delete removes the named pages', got == ['PAGE 1', 'PAGE 3'], (got, msg))
    got, msg = run('extractpages', '#epL', '3-4')
    chk('extract keeps only the named pages', got == ['PAGE 3', 'PAGE 4'], (got, msg))
    got, msg = run('reorderpages', '#roL', '4, 3, 2, 1')
    chk('reorder puts the pages in the new order', got == ['PAGE 4', 'PAGE 3', 'PAGE 2', 'PAGE 1'], (got, msg))
    got, msg = run('reorderpages', '#roL', '1, 2')
    chk('reorder refuses a list that is missing pages', got is None and 'List every page' in msg, (got, msg))
    got, msg = run('deletepages', '#dpL', '1-4')
    chk("delete refuses to remove every page", got is None and "every page" in msg, (got, msg))
    # three saves above used the free daily allowance; start this one with a fresh count
    pg.evaluate("localStorage.setItem('resumate_exports', JSON.stringify({day:new Date().toDateString(), n:0}))")
    open_tool('redactpdf')
    pg.evaluate("window.__fs.length = 0")
    pg.click("#pt-go")
    for _ in range(60):
        if pg.evaluate("window.__fs.length") > 0: break
        pg.wait_for_timeout(1000)
    fs = pg.evaluate("window.__fs")
    chk('black out saves a PDF with every page', fs and len(PdfReader(io.BytesIO(base64.b64decode(fs[-1]['data']))).pages) == 4, fs and len(fs))
    pg.evaluate("document.querySelector('.tl-tile[data-tool=pdftools]').click()"); pg.wait_for_timeout(500)
    chk('the hub shows the four new tiles', pg.evaluate("['deletepages','extractpages','reorderpages','redactpdf'].every(t=>!!document.querySelector('.tl-tile[data-tool='+t+']'))"))
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
