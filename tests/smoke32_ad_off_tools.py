# The native ad banner must be taken down the moment a tool opens (it sits over the bottom of the screen
# and would cover buttons such as "Create resume from this").
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = HERE.parent.joinpath('www', 'index.html').as_uri()
res = []
def chk(name, ok, extra=''):
    res.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' — ' + str(extra)))
from playwright.sync_api import sync_playwright
MOCK = """
window.__log=[];
const rec = n => async (o)=>{ window.__log.push({fn:n, o:o||null}); if(n==='requestConsentInfo') return {status:'NOT_REQUIRED', isConsentFormAvailable:false}; return {}; };
window.Capacitor = { isNativePlatform:()=>true, Plugins:{
  AdMob:{ requestConsentInfo:rec('requestConsentInfo'), showConsentForm:rec('showConsentForm'), initialize:rec('initialize'), showBanner:rec('showBanner'), hideBanner:rec('hideBanner'), resumeBanner:rec('resumeBanner') },
  Browser:{ open:rec('browserOpen') } } };
localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1');
"""
with sync_playwright() as p:
    b = p.chromium.launch(); ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(MOCK)
    pg.goto(URL); pg.wait_for_timeout(5000); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(600)
    pg.wait_for_timeout(8000); pg.evaluate("window.__ads.tick()"); pg.wait_for_timeout(600)
    calls = lambda n: [c for c in pg.evaluate("window.__log") if c['fn'] == n]
    chk('the banner is showing on Home before a tool opens', len(calls('showBanner')) >= 1)
    before = len(calls('hideBanner'))
    pg.evaluate("document.querySelector('.tl-tile[data-tool=roleresume]').click()")   # no waiting: check right away
    chk('the banner is hidden the moment a tool opens', len(calls('hideBanner')) > before, len(calls('hideBanner')))
    pg.wait_for_timeout(1500)
    chk('and stays hidden while the tool is open', pg.evaluate("window.__ads.state") in ('hidden', 'off'), pg.evaluate("window.__ads.state"))
    chk('no page errors', not errs, errs[:3])
    b.close()
print(f"\n{sum(res)}/{len(res)} passed")
