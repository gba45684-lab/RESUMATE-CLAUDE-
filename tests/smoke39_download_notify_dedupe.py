# Download saves the file to the device and posts a notification with Open and Share. Image tools no longer repeat PDF tools.
import pathlib, functools, socket, threading
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
MOCK = """window.__fs=[]; window.__ln={types:[],scheduled:[],listeners:{}}; window.__share=[];
window.Capacitor={isNativePlatform:()=>true,Plugins:{
  AdMob:{ requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}) },
  Filesystem:{ writeFile:async(o)=>{ window.__fs.push({path:o.path, dir:o.directory}); return {uri:'file:///storage/emulated/0/Android/data/app/files/Documents/'+o.path}; } },
  LocalNotifications:{ checkPermissions:async()=>({display:'granted'}), requestPermissions:async()=>({display:'granted'}),
    createChannel:async()=>({}), registerActionTypes:async(o)=>{ window.__ln.types.push(o); },
    schedule:async(o)=>{ window.__ln.scheduled.push(o); }, addListener:async(n,cb)=>{ window.__ln.listeners[n]=cb; return {remove(){}}; } },
  Share:{ share:async(o)=>{ window.__share.push(o); return {}; } }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=letter]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    pg.evaluate("document.getElementById('clPdf').click()"); pg.wait_for_timeout(1800)
    fs = pg.evaluate("window.__fs"); sch = pg.evaluate("window.__ln.scheduled")
    chk('the file is saved to the device (Documents folder)', fs and fs[0]['dir'] == 'DOCUMENTS' and fs[0]['path'].startswith('ResuMate/') and fs[0]['path'].endswith('.pdf'), fs)
    chk('the Open and Share actions are registered', pg.evaluate("window.__ln.types.length") == 1 and [a['id'] for a in pg.evaluate("window.__ln.types")[0]['types'][0]['actions']] == ['open', 'share'])
    n = sch[0]['notifications'][0] if sch else {}
    chk('a notification is posted with those actions', n.get('actionTypeId') == 'resumate_saved_file' and n.get('extra', {}).get('path', '').startswith('file://'), n)
    chk('no share sheet opens first', pg.evaluate("window.__share") == [], pg.evaluate("window.__share"))
    pg.evaluate("window.__ln.listeners['localNotificationActionPerformed']({actionId:'open', notification:{title:'Saved', extra:{path:'file:///x/a.pdf'}}})"); pg.wait_for_timeout(400)
    chk('Open from the notification opens the file', pg.evaluate("window.__share.length") == 1 and pg.evaluate("window.__share[0].files[0]") == 'file:///x/a.pdf', pg.evaluate("window.__share"))
    pg.evaluate("window.__ln.listeners['localNotificationActionPerformed']({actionId:'share', notification:{title:'Saved', extra:{path:'file:///x/a.pdf'}}})"); pg.wait_for_timeout(400)
    chk('Share from the notification shares the file', pg.evaluate("window.__share.length") == 2, pg.evaluate("window.__share.length"))
    # duplicates: each tool appears in one hub only
    pg.evaluate("(()=>{const t=document.getElementById('toolPage'); if(t&&!t.hidden) document.getElementById('toolBack').click();})()"); pg.wait_for_timeout(450)
    pg.evaluate("document.querySelector('[data-tab=home]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=imagetools]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    dup = pg.evaluate("['imgpdf','pdf2jpg'].filter(k=>document.querySelector('#toolBody [data-tool='+k+']'))")
    chk('the Image tools hub has no PDF duplicates', dup == [], dup)
    chk('the Image tools hub still has Passport photo', pg.evaluate("!!document.querySelector('#toolBody [data-tool=idphoto]')"))
    pg.evaluate("(()=>{const t=document.getElementById('toolBack'); if(t) t.click();})()"); pg.wait_for_timeout(450)
    pg.evaluate("[...document.querySelectorAll('.tl-tile[data-tool=pdftools]')].find(x=>x.offsetParent).click()"); pg.wait_for_timeout(700)
    chk('the PDF tools hub keeps Images to PDF and PDF to JPG', pg.evaluate("['imgpdf','pdf2jpg'].every(k=>!!document.querySelector('#toolBody [data-tool='+k+']'))"))
    chk('no page errors', not errs, errs[:3]); ctx.close(); b.close()
print(f"{sum(res)}/{len(res)} passed"); raise SystemExit(0 if all(res) else 1)
