# Touch-target checks (44px hit area). Each target must be the element a finger hits when it
# taps 21px above and below its centre (a 42px+ vertical hit span; 44px layout boxes or
# invisible hit-area layers both count). Runs against ../www/index.html.
import os, pathlib, sys
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
INIT = "if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_user_name','Krapal Singh')}"
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok)))
    print(('PASS ' if ok else 'FAIL ') + name + ('' if ok else ' — ' + str(extra)))

# Hit test at 21px above and below the centre of the first visible element matching `sel`.
HIT_JS = """(sel) => {
  const el = [...document.querySelectorAll(sel)].find(e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0 && getComputedStyle(e).visibility !== 'hidden'; });
  if (!el) return { found: false };
  el.scrollIntoView({ block: 'center', inline: 'nearest' });
  const r = el.getBoundingClientRect();
  const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
  const hits = [cy - 21, cy + 21].map(y => { const h = document.elementFromPoint(cx, y); return !!h && (h === el || el.contains(h)); });
  return { found: true, ok: hits[0] && hits[1], h: Math.round(r.height), top: hits[0], bottom: hits[1] };
}"""

with sync_playwright() as p:
    b = p.chromium.launch(args=['--no-sandbox'])
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(INIT)
    pg.goto(URL); pg.wait_for_timeout(2500)
    pg.evaluate("document.getElementById('pwClose') && document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    home_targets = [('.hm-chip', 'template chip'), ('.sect-head a', '"View all" / "Browse" link'), ('.th-quick', 'theme button'), ('.badge-premium', 'Upgrade badge')]
    for sel, label in home_targets:
        r = pg.evaluate(HIT_JS, sel)
        chk(f'home: {label} can be hit 21px above and below its centre', r.get('found') and r.get('ok'), r)

    pg.evaluate("document.querySelector('[data-tab=templates]').click()"); pg.wait_for_timeout(500)
    r = pg.evaluate(HIT_JS, '.tp-prem')
    chk('templates: Upgrade button can be hit 21px above and below its centre', r.get('found') and r.get('ok'), r)
    chk('no page errors', not errs, errs)
    b.close()

passed = sum(1 for _, ok in res if ok)
print(f'{passed}/{len(res)} passed')
sys.exit(0 if passed == len(res) else 1)
