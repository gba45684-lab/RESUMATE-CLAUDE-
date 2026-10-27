import os, pathlib, json
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
results=[]
def check(name, ok, extra=''):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name+('' if ok else ' — '+str(extra)))
from playwright.sync_api import sync_playwright
MOCK = """
window.__log=[];
const rec = n => async (o)=>{ window.__log.push({fn:n, o:o||null}); if(n==='requestConsentInfo') return {status:'NOT_REQUIRED', isConsentFormAvailable:false}; return {}; };
window.Capacitor = { isNativePlatform:()=>true, Plugins:{
  AdMob:{ requestConsentInfo:rec('requestConsentInfo'), showConsentForm:rec('showConsentForm'), initialize:rec('initialize'), showBanner:rec('showBanner'), hideBanner:rec('hideBanner'), resumeBanner:rec('resumeBanner') },
  Browser:{ open:rec('browserOpen') } } };
localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');
"""
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':393,'height':852},has_touch=True,is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.add_init_script(MOCK)
    pg.goto(URL); pg.wait_for_timeout(5000); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(600)
    log=lambda: pg.evaluate("window.__log")
    calls=lambda n: [c for c in log() if c['fn']==n]
    check('no ad in the first seconds', not calls('showBanner'))
    pg.wait_for_timeout(8000); pg.evaluate("window.__ads.tick()"); pg.wait_for_timeout(800)
    sb=calls('showBanner')
    check('Home shows one test banner', len(sb)==1 and sb[0]['o']['isTesting'] is True and sb[0]['o']['adId'].startswith('ca-app-pub-3940256099942544/'), log())
    check('banner is anchored at the bottom, adaptive, above the tab bar', sb and sb[0]['o']['position']=='BOTTOM_CENTER' and sb[0]['o']['adSize']=='ADAPTIVE_BANNER' and sb[0]['o']['margin']>=60, sb and sb[0]['o'])
    names=[c['fn'] for c in log()]
    check('consent is asked before ads are initialised', names.index('requestConsentInfo') < names.index('initialize') < names.index('showBanner'), names)
    def state_after(js, wait=900):
        pg.evaluate(js); pg.wait_for_timeout(wait); pg.evaluate("window.__ads.tick()"); pg.wait_for_timeout(500); return pg.evaluate("window.__ads.state")
    check('Templates: no ad', state_after("document.querySelector('[data-tab=templates]').click()")=='hidden')
    check('AI Assistant: ad shown (requested)', state_after("document.querySelector('[data-tab=ai]').click()")=='shown')
    check('Profile: ad again', state_after("document.querySelector('[data-tab=profile]').click()")=='shown' and len(calls('resumeBanner'))>=1)
    check('Open sheet: no ad', state_after("document.querySelector('.prow').click()")=='hidden')
    check('Close sheet: ad again', state_after("document.getElementById('sheet2Close').click()", 1200)=='shown')
    check('Upgrade screen: no ad', state_after("window.__openUpgrade()", 1500)=='hidden')
    pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(900)
    check('Editor open: no ad', state_after("document.querySelector('[data-tab=templates]').click(); document.querySelector('[data-open-edit]').click()")=='hidden')
    pg.evaluate("document.querySelector('[data-close-edit]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('[data-tab=home]').click()"); pg.wait_for_timeout(600)
    pg.evaluate("window.__billing.upgraded = ()=>true"); pg.evaluate("window.__ads.tick()"); pg.wait_for_timeout(500)
    check('Premium: banner is hidden', pg.evaluate("window.__ads.state")=='hidden')
    # privacy page opens inside the app and the online copy goes through the browser plugin
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("[...document.querySelectorAll('.prow')].find(r=>r.textContent.startsWith('About')).click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('#sheet2 [data-open-privacy]').click()"); pg.wait_for_timeout(500)
    txt=pg.inner_text('#sheet2')
    check('privacy policy opens inside the app and mentions ads', 'Advertising' in txt and 'AdMob' in txt)
    pg.evaluate("document.getElementById('privOnline').click()"); pg.wait_for_timeout(300)
    bo=calls('browserOpen')
    check('online copy opens through the browser plugin', bo and bo[-1]['o']['url']=='https://resumate-claude.vercel.app/privacy.html', bo)
    # serial numbers
    pg.evaluate("document.querySelector('[data-tab=templates]').click()"); pg.wait_for_timeout(900)
    check('first card says 1 and the info says No. 1', pg.evaluate("document.querySelector('#track .tfoot span').textContent.startsWith('1 ·')") and 'No. 1' in pg.inner_text('#tplInfoStyle'))
    check('position reads 1 / 58', pg.inner_text('#tplPos').strip()=='1 / 58')
    # an installed app that has no Browser/AdMob part must not fail silently
    pg2=ctx.new_page(); e2=[]; pg2.on('pageerror',lambda e:e2.append(str(e)))
    pg2.add_init_script("window.Capacitor={isNativePlatform:()=>true,Plugins:{}};localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');")
    pg2.goto(URL); pg2.wait_for_timeout(5000); pg2.evaluate("document.getElementById('pwClose').click()"); pg2.wait_for_timeout(500)
    pg2.evaluate("document.querySelector('[data-tab=profile]').click()"); pg2.wait_for_timeout(400)
    pg2.evaluate("[...document.querySelectorAll('.prow')].find(r=>r.textContent.startsWith('About')).click()"); pg2.wait_for_timeout(500)
    pg2.evaluate("document.querySelector('#sheet2 [data-open-privacy]').click()"); pg2.wait_for_timeout(400)
    pg2.evaluate("document.getElementById('privOnline').click()"); pg2.wait_for_timeout(500)
    check('old app without browser part: says the link was copied', 'Link copied' in pg2.inner_text('#toast'))
    check('old app: no page errors', not e2, e2)
    check('no page errors', not errs)
    if errs: print(errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed"); raise SystemExit(0 if all(results) else 1)
