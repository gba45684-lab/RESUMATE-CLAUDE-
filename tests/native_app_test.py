import os, pathlib, sys, json
HERE = pathlib.Path(__file__).resolve().parent
from playwright.sync_api import sync_playwright
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
MOCK = """
window.__calls = [];
window.Capacitor = { isNativePlatform: () => true, Plugins: {
  Filesystem: { writeFile: async (o) => { window.__calls.push({fn:'writeFile', path:o.path, directory:o.directory, len:(o.data||'').length, head:(o.data||'').slice(0,8)}); return { uri: 'file:///cache/' + o.path }; } },
  Share: { share: async (o) => { window.__calls.push({fn:'share', title:o.title, files:o.files||null, text:o.text||null}); return {}; } }
}};
if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_user_name','Krapal Singh')}
"""
results = []
def chk(name, ok, extra=''): results.append(ok); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' — ' + str(extra)))
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=1, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(MOCK)
    pg.goto(URL); pg.wait_for_timeout(4500)
    pg.evaluate("document.getElementById('pwClose') && document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-tab=templates]').click()"); pg.wait_for_timeout(900)
    pg.touchscreen.tap(196, 430); pg.wait_for_timeout(1200)
    # ATS export in the native app
    pg.evaluate("document.getElementById('exportAtsBtn').click()"); pg.wait_for_timeout(2500)
    calls = pg.evaluate("window.__calls")
    fs = [c for c in calls if c['fn']=='writeFile']; sh = [c for c in calls if c['fn']=='share']
    chk('ATS: saved to the device as a .pdf (Documents/ResuMate)', bool(fs) and fs[0]['path'].endswith('_Resume_ATS.pdf') and fs[0]['path'].startswith('ResuMate/') and fs[0]['directory']=='DOCUMENTS', calls)
    chk('ATS: data is a real PDF (base64 of %PDF)', bool(fs) and fs[0]['head'].startswith('JVBER'), fs and fs[0]['head'])
    chk('ATS: no share sheet opens by itself (Open and Share are in the notification)', not sh, calls)
    # Word export
    pg.evaluate("window.__calls.length = 0"); pg.evaluate("document.getElementById('exportDocxBtn').click()"); pg.wait_for_timeout(2500)
    calls = pg.evaluate("window.__calls")
    chk('Word: saved as .docx to the device, no share sheet by itself', any(c['fn']=='writeFile' and c['path'].endswith('.docx') for c in calls) and not any(c['fn']=='share' for c in calls), calls)
    chk('Word: PK zip header (base64 UEsD)', any(c['fn']=='writeFile' and c.get('head','').startswith('UEsDB') for c in calls), [c.get('head') for c in calls if c['fn']=='writeFile'])
    # My Downloads: both exports were kept; share the first one
    pg.evaluate("document.querySelector('.back-btn') && document.querySelector('.back-btn').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("[...document.querySelectorAll('#profileList .prow')].find(r=>r.textContent.includes('Downloads')).click()"); pg.wait_for_timeout(1000)
    n = pg.evaluate("document.querySelectorAll('.dl-row').length")
    chk('My Downloads: saved files are listed', n >= 2, n)
    pg.evaluate("window.__calls.length = 0")
    pg.evaluate("document.querySelector('.dl-row .dl-act[aria-label^=Share]').click()"); pg.wait_for_timeout(1500)
    calls = pg.evaluate("window.__calls")
    chk('My Downloads share: sheet opened with the saved file', any(c['fn']=='share' and c['files'] for c in calls), calls)
    # App share button
    pg.evaluate("window.__calls.length = 0")
    pg.evaluate("document.querySelector('.back-btn') && document.querySelector('.back-btn').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.getElementById('shareAppBtn') && document.getElementById('shareAppBtn').click()"); pg.wait_for_timeout(800)
    calls = pg.evaluate("window.__calls")
    chk('Share app: native share sheet with text', any(c['fn']=='share' and c['text'] for c in calls), calls)
    chk('no script errors', not errs, errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed")
