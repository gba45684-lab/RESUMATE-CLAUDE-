# Image tools: black out or blur, date or text stamp, brightness and contrast, combine pictures.
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
from PIL import Image, ImageStat
SCR = '/tmp/claude-0/-home-claude/3f08c25f-de67-5997-a6e3-1b4821c2fe7f/scratchpad'
pathlib.Path(SCR).mkdir(parents=True, exist_ok=True)
WHITE = f'{SCR}/white400.png'; Image.new('RGB', (400, 200), (255, 255, 255)).save(WHITE)
GREY = f'{SCR}/grey400.png'; Image.new('RGB', (400, 200), (60, 60, 60)).save(GREY)
A = f'{SCR}/left100.png'; Image.new('RGB', (100, 50), (200, 0, 0)).save(A)
B = f'{SCR}/right100.png'; Image.new('RGB', (100, 50), (0, 0, 200)).save(B)
MOCK = """window.__fs=[]; window.Capacitor={isNativePlatform:()=>true,Plugins:{
  AdMob:{ requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}) },
  Filesystem:{ writeFile:async(o)=>{ window.__fs.push({path:o.path, data:o.data}); return {uri:'file:///x/'+o.path}; } },
  LocalNotifications:{ checkPermissions:async()=>({display:'granted'}), requestPermissions:async()=>({display:'granted'}), createChannel:async()=>({}), registerActionTypes:async()=>({}), schedule:async()=>({}), addListener:async()=>({remove(){}}) },
  Share:{ share:async()=>({}) }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
def last_image(pg):
    fs = pg.evaluate("window.__fs")
    return Image.open(io.BytesIO(base64.b64decode(fs[-1]['data']))).convert('RGB') if fs else None
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    def open_tool(name):
        pg.evaluate("window.__fs.length = 0; localStorage.setItem('resumate_exports', JSON.stringify({day:new Date().toDateString(), n:0}))")
        pg.evaluate("document.querySelector('.tl-tile[data-tool=imagetools]').click()"); pg.wait_for_timeout(500)
        pg.evaluate(f"[...document.querySelectorAll('.tl-tile[data-tool={name}]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(600)
    def wait_save():
        for _ in range(40):
            if pg.evaluate("window.__fs.length") > 0: return True
            pg.wait_for_timeout(500)
        return False
    # 1. black box
    open_tool('redactimg'); pg.set_input_files('#it-file', WHITE); pg.wait_for_timeout(900)
    pg.fill('[data-rk=x]', '0'); pg.dispatch_event('[data-rk=x]', 'input')
    pg.fill('[data-rk=y]', '0'); pg.dispatch_event('[data-rk=y]', 'input')
    pg.fill('[data-rk=w]', '50'); pg.dispatch_event('[data-rk=w]', 'input')
    pg.fill('[data-rk=h]', '50'); pg.dispatch_event('[data-rk=h]', 'input')
    pg.click('#it-go'); saved = wait_save()
    im = last_image(pg) if saved else None
    chk('black box covers the chosen corner', im and im.getpixel((20, 20))[0] < 30 and im.getpixel((350, 150))[0] > 240, im and (im.getpixel((20, 20)), im.getpixel((350, 150))))
    # 2. blur
    open_tool('redactimg'); pg.set_input_files('#it-file', GREY); pg.wait_for_timeout(900)
    pg.click('[data-opt=mode][data-val=blur]'); pg.wait_for_timeout(300)
    pg.fill('[data-rk=w]', '100'); pg.dispatch_event('[data-rk=w]', 'input')
    pg.click('#it-go'); saved = wait_save()
    chk('blur saves a picture of the same size', saved and last_image(pg).size == (400, 200), saved)
    # 3. stamp with the date (default)
    open_tool('stampimg'); pg.set_input_files('#it-file', GREY); pg.wait_for_timeout(900)
    pg.click('#it-go'); saved = wait_save()
    im = last_image(pg) if saved else None
    corner = im.crop((250, 150, 400, 200)) if im else None
    bright = max(corner.getdata(), key=lambda px: sum(px)) if corner else None
    chk('date stamp puts white text in the corner', bright is not None and min(bright) > 230, bright)
    # 4. empty text stamp is refused
    open_tool('stampimg'); pg.set_input_files('#it-file', GREY); pg.wait_for_timeout(900)
    pg.click('[data-opt=kind][data-val=text]'); pg.wait_for_timeout(300)
    pg.click('#it-go'); pg.wait_for_timeout(800)
    chk('text stamp asks for text when it is empty', 'Type the text' in pg.evaluate("document.getElementById('it-msg').textContent"))
    # 5. brightness up
    open_tool('adjustimg'); pg.set_input_files('#it-file', GREY); pg.wait_for_timeout(900)
    pg.evaluate("(()=>{const r=document.getElementById('adj_bright'); r.value=40; r.dispatchEvent(new Event('input'));})()")
    pg.click('#it-go'); saved = wait_save()
    im = last_image(pg) if saved else None
    chk('brightness up makes the picture lighter', im and ImageStat.Stat(im).mean[0] > 60 + 30, im and ImageStat.Stat(im).mean)
    # 6. combine side by side and stacked
    open_tool('combineimg'); pg.set_input_files('#cbFile', [A, B]); pg.wait_for_timeout(900)
    pg.click('#cbGo'); saved = wait_save()
    im = last_image(pg) if saved else None
    chk('side by side is twice as wide', im and im.size == (200, 50), im and im.size)
    pg.evaluate("window.__fs.length = 0; localStorage.setItem('resumate_exports', JSON.stringify({day:new Date().toDateString(), n:0}))")
    pg.click('[data-opt=dir][data-val=col]'); pg.wait_for_timeout(300)
    pg.click('#cbGo'); saved = wait_save()
    im = last_image(pg) if saved else None
    chk('stacked is twice as tall', im and im.size == (100, 100), im and im.size)
    chk('the combined picture keeps both colours', im and im.getpixel((50, 10))[0] > 150 and im.getpixel((50, 90))[2] > 150, im and (im.getpixel((50, 10)), im.getpixel((50, 90))))
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
