# Target size: image Compress and Shrink PDF can aim for a file size (in KB) and step quality down until the file fits.
import pathlib, functools, socket, threading, random, base64, io
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
# a busy picture, so a JPEG at high quality is clearly bigger than 40 KB
# a photo-like picture: smooth gradient with light grain (noise alone cannot be compressed to a small size)
random.seed(1)
im = Image.new('RGB', (1200, 900))
im.putdata([(min(255, x // 5 + random.randint(0, 12)), min(255, y // 4 + random.randint(0, 12)), 120) for y in range(900) for x in range(1200)])
IMG = '/tmp/claude-0/-home-claude/3f08c25f-de67-5997-a6e3-1b4821c2fe7f/scratchpad/noise.png'
pathlib.Path(IMG).parent.mkdir(parents=True, exist_ok=True); im.save(IMG)
MOCK = """window.__fs=[]; window.Capacitor={isNativePlatform:()=>true,Plugins:{
  AdMob:{ requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}) },
  Filesystem:{ writeFile:async(o)=>{ window.__fs.push({path:o.path, dir:o.directory, bytes: Math.round(o.data.length*0.75)}); return {uri:'file:///x/'+o.path}; } },
  LocalNotifications:{ checkPermissions:async()=>({display:'granted'}), requestPermissions:async()=>({display:'granted'}), createChannel:async()=>({}), registerActionTypes:async()=>({}), schedule:async()=>({}), addListener:async()=>({remove(){}}) },
  Share:{ share:async()=>({}) }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=imagetools]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=compress]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(600)
    pg.set_input_files('#cmpFile', IMG); pg.wait_for_timeout(1500)
    chk('the image compress screen has a target size box', pg.locator('#cmpTarget').count() == 1)
    pg.fill('#cmpTarget', '40'); pg.dispatch_event('#cmpTarget', 'change'); pg.wait_for_timeout(600)
    pg.click('#cmpSave'); pg.wait_for_timeout(2500)
    fs = pg.evaluate("window.__fs")
    got = fs[-1]['bytes'] if fs else None
    chk('compress saves a file under the 40 KB target', got is not None and got <= 40 * 1024, fs)
    msg = pg.evaluate("document.getElementById('cmpMsg') && document.getElementById('cmpMsg').textContent")
    chk('the message reports the quality used', 'quality' in (msg or '') or 'lowest quality' in (msg or ''), msg)
    pg.evaluate("window.__fs.length = 0")
    chk('no page errors on the compress screen', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
