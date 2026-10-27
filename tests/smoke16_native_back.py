# Checks the Android back button and back gesture: a native backButton event closes the top layer first, then warns, then leaves.
import os, pathlib
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
from playwright.sync_api import sync_playwright
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))

# fake the Capacitor App plugin so the page believes it runs on Android
NATIVE = """
window.__exited = false; window.__backCb = null;
window.Capacitor = { isNativePlatform: () => true, Plugins: { App: {
  addListener: (evt, cb) => { if (evt === 'backButton') window.__backCb = cb; return { remove() {} }; },
  exitApp: () => { window.__exited = true; } } } };
if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}
"""
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(NATIVE)
    pg.goto(URL); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    chk('native back listener is attached', pg.evaluate("typeof window.__backCb === 'function'"))

    pg.evaluate("document.querySelector('[data-tool=score]').click()"); pg.wait_for_timeout(700)
    chk('tool page is open before back', pg.evaluate("document.getElementById('toolPage').classList.contains('go')"))
    pg.evaluate("window.__backCb()"); pg.wait_for_timeout(600)
    chk('back closes the tool page first', not pg.evaluate("document.getElementById('toolPage').classList.contains('go')"))
    chk('closing a layer does not exit the app', pg.evaluate("window.__exited") is False)

    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("window.__backCb()"); pg.wait_for_timeout(500)
    chk('back from another tab goes to Home', pg.evaluate("document.querySelector('.panel.active').dataset.panel") == 'home')

    pg.evaluate("window.__backCb()"); pg.wait_for_timeout(400)
    chk('first back on Home warns instead of exiting', pg.evaluate("window.__exited") is False)
    chk('warning text is shown', 'Press back again' in pg.evaluate("document.body.innerText"))
    pg.evaluate("window.__backCb()"); pg.wait_for_timeout(300)
    chk('second back within 2 s exits the app', pg.evaluate("window.__exited") is True)

    chk('no script errors', not errs, errs)
    b.close()
print(f"\n{sum(ok for _, ok in res)}/{len(res)} passed")
