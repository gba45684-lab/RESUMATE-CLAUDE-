# Job tracker: follow-up reminders (local notifications), your numbers, and saved message templates.
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
from datetime import date, timedelta
FUTURE = (date.today() + timedelta(days=3)).isoformat()
MOCK = """window.__ln={scheduled:[],cancelled:[],channels:[]}; window.Capacitor={isNativePlatform:()=>true,Plugins:{
  AdMob:{ requestConsentInfo:async()=>({status:'NOT_REQUIRED'}), initialize:async()=>({}), showBanner:async()=>({}), hideBanner:async()=>({}), resumeBanner:async()=>({}) },
  LocalNotifications:{ checkPermissions:async()=>({display:'granted'}), requestPermissions:async()=>({display:'granted'}),
    createChannel:async(o)=>{ window.__ln.channels.push(o); }, schedule:async(o)=>{ window.__ln.scheduled.push(...o.notifications); },
    cancel:async(o)=>{ window.__ln.cancelled.push(...o.notifications); }, registerActionTypes:async()=>({}), addListener:async()=>({remove(){}}) },
  Share:{ share:async()=>({}) }, Browser:{open:async()=>({})} }};"""
INIT = "try{localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}catch(e){}"
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True); ctx.add_init_script(MOCK + INIT)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{PORT}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c&&c.offsetParent) c.click();})()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=jobtracker]').click()"); pg.wait_for_timeout(600)
    pg.fill('#jtRole', 'Product Manager'); pg.fill('#jtCo', 'Acme'); pg.fill('#jtFollow', FUTURE)
    pg.click('#jtAdd'); pg.wait_for_timeout(900)
    sch = pg.evaluate("window.__ln.scheduled")
    chk('a follow-up reminder is scheduled for the follow-up date', len(sch) == 1 and sch[0]['title'].startswith('Follow up'), sch)
    y, m, d, hh = pg.evaluate("(()=>{const d=window.__ln.scheduled[0].schedule.at; return [d.getFullYear(), d.getMonth()+1, d.getDate(), d.getHours()];})()")
    chk('the reminder is set for 10:00 on that day', f'{y:04d}-{m:02d}-{d:02d}' == FUTURE and hh == 10, (y, m, d, hh))
    pg.fill('#jtRole', 'Analyst'); pg.fill('#jtCo', 'Beta'); pg.fill('#jtFollow', FUTURE); pg.click('#jtAdd'); pg.wait_for_timeout(900)
    chk('a second application adds a second reminder', len(pg.evaluate("window.__ln.scheduled")) == 2)
    chk('your numbers count the applications', 'Applications' in pg.evaluate("document.querySelector('.jt-stats') ? document.querySelector('.jt-stats').textContent : ''") and pg.evaluate("document.querySelector('.jt-stats b').textContent") == '2')
    pg.evaluate("document.querySelector('.jt-row [data-st=offer]').click()"); pg.wait_for_timeout(900)
    chk('an application that gets an offer loses its reminder', len(pg.evaluate("window.__ln.cancelled")) == 1 and len(pg.evaluate("window.__ln.scheduled")) == 2)
    chk('the default message templates are shown', pg.evaluate("document.querySelectorAll('.jt-tpl').length") == 3)
    pg.fill('#tplName', 'Ask for feedback'); pg.fill('#tplText', 'Dear [Name], could you share any feedback on my interview? Thank you.')
    pg.click('#tplAdd'); pg.wait_for_timeout(700)
    chk('a new template is saved', pg.evaluate("document.querySelectorAll('.jt-tpl').length") == 4)
    pg.reload(); pg.wait_for_timeout(2000)
    stored = pg.evaluate("localStorage.getItem('resumate_msg_templates') || ''")
    chk('the new template survives a reload', 'Ask for feedback' in stored)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=jobtracker]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('[data-tpl-del]').click()"); pg.wait_for_timeout(600)
    chk('a template can be deleted', pg.evaluate("document.querySelectorAll('.jt-tpl').length") == 3)
    chk('no page errors', not errs, errs)
    b.close()
print(f'{sum(res)}/{len(res)} passed'); raise SystemExit(0 if all(res) else 1)
