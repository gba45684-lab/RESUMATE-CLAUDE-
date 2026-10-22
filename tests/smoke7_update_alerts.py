# App update alerts: an update that arrives shows a toast with a vibration and beep when the app is open,
# and a system notification with sound and vibration when it is in the background. Each version alerts once.
# The native plugins are stubbed here (the real ones only run in the Android app).
import os, pathlib
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
PROXY = 'https://resumate-ai.gba45684.workers.dev/'
STUB = """
window.__vib = 0; window.__sched = null; window.__chan = null; window.__upd = null;
window.Capacitor = { Plugins: {
  CapacitorUpdater: {
    notifyAppReady(){},
    addListener(name, fn){ if(name === 'updaterEvent') window.__upd = fn; return Promise.resolve({ remove(){} }); }
  },
  Haptics: { vibrate(){ window.__vib++; return Promise.resolve(); } },
  LocalNotifications: {
    checkPermissions(){ return Promise.resolve({ display:'granted' }); },
    requestPermissions(){ return Promise.resolve({ display:'granted' }); },
    createChannel(c){ window.__chan = c; return Promise.resolve(); },
    schedule(o){ window.__sched = o; return Promise.resolve({ notifications: [] }); }
  }
}};
"""
results = []
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
with sync_playwright() as p:
    b = p.chromium.launch(); errs = []
    ctx = b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True)
    ctx.route(PROXY + '**', lambda r: r.fulfill(status=204, headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'}))
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(STUB + "if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(URL); pg.wait_for_timeout(4500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c) c.click();})()"); pg.wait_for_timeout(400)
    check('updater listener registered at startup', pg.evaluate("typeof window.__upd === 'function'"))

    # open app: toast + vibration, once per version
    pg.evaluate("window.__upd({type:'updateAvailable', data:{bundle:{version:'1.1.23'}}})"); pg.wait_for_timeout(400)
    check('open app: vibrates', pg.evaluate("window.__vib") >= 1)
    check('open app: toast says the version', 'Update found: version 1.1.23' in pg.evaluate("document.body.innerText"))
    check('open app: no system notification', pg.evaluate("window.__sched") is None)
    before = pg.evaluate("window.__vib")
    pg.evaluate("window.__upd({type:'updateAvailable', data:{bundle:{version:'1.1.23'}}})"); pg.wait_for_timeout(300)
    check('same version again: no second alert', pg.evaluate("window.__vib") == before)
    pg.evaluate("window.__upd({type:'download', data:{bundle:{version:'1.1.23'}}})"); pg.wait_for_timeout(200)
    check('other events do not alert', pg.evaluate("window.__vib") == before)

    # background: system notification on the updates channel, with vibration
    pg.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>true})")
    pg.evaluate("window.__upd({type:'updateAvailable', data:{bundle:{version:'1.1.24'}}})"); pg.wait_for_timeout(500)
    sched = pg.evaluate("window.__sched")
    check('background: system notification scheduled', sched is not None and sched['notifications'][0]['body'].find('1.1.24') >= 0)
    check('background: uses the updates channel', sched is not None and sched['notifications'][0]['channelId'] == 'updates')
    check('background: channel vibrates', pg.evaluate("window.__chan") is not None and pg.evaluate("window.__chan.vibration") is True)
    check('background: vibrates too', pg.evaluate("window.__vib") > before)
    check('no page errors', not errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed")
