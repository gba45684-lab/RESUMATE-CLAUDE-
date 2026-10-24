# Regression checks: (1) text typed in the AI job box stays readable in every theme, including
# when focused; (2) the newest theme choice always wins, even after quick switches.
import os, pathlib, re
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
PROXY = 'https://resumate-ai.gba45684.workers.dev/'
results = []
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ') + name)
def lum(rgb):
    v = [float(x) for x in re.findall(r'[\d.]+', rgb)[:3]]
    def c(x):
        x /= 255; return x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, bb = [c(x) for x in v]; return 0.2126 * r + 0.7152 * g + 0.0722 * bb
def contrast(a, b):
    la, lb = lum(a), lum(b); return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)
STATE = "(()=>({attr:document.documentElement.getAttribute('data-theme'), mode:document.documentElement.getAttribute('data-mode'), saved:localStorage.getItem('resumate_theme'), seg:[...document.querySelectorAll('.th-opt')].filter(b=>b.getAttribute('aria-checked')==='true').map(b=>b.dataset.th).join('')}))()"

with sync_playwright() as p:
    b = p.chromium.launch(); errs = []
    ctx = b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=2)
    ctx.route(PROXY + '**', lambda r: r.fulfill(status=204, headers={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*'}))
    pg = ctx.new_page(); pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(URL); pg.wait_for_timeout(4500)
    pg.evaluate("(()=>{const c=document.getElementById('pwClose'); if(c) c.click();})()"); pg.wait_for_timeout(400)

    # 1. job box, focused, in every theme: readable text (WCAG AA = 4.5:1)
    for th in ['golden', 'branchdesk', 'midnight']:
        pg.evaluate(f"document.querySelector('.th-opt[data-th={th}]').click()"); pg.wait_for_timeout(1000)
        pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(600)
        pg.evaluate("document.querySelector('[data-ai-open=tailor]').click()"); pg.wait_for_timeout(800)
        pg.evaluate("document.getElementById('aiJob').focus()"); pg.wait_for_timeout(300)
        pg.keyboard.type('We need a PM'); pg.wait_for_timeout(200)
        c = pg.evaluate("(()=>{const t=document.getElementById('aiJob'); const s=getComputedStyle(t); return {color:s.color,bg:s.backgroundColor,focused:document.activeElement===t}})()")
        check(f'{th}: job text readable while focused ({contrast(c["color"], c["bg"]):.1f}:1)', c['focused'] and contrast(c['color'], c['bg']) >= 4.5)
        pg.evaluate("document.getElementById('sheet2Close') && document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(500)

    # 2. the newest theme choice wins after quick switches
    for seq in [['branchdesk', 'golden'], ['branchdesk', 'branchdesk', 'golden'], ['golden', 'midnight', 'branchdesk', 'golden']]:
        for gap in [0, 40]:
            pg.evaluate("document.querySelector('.th-opt[data-th=golden]').click()"); pg.wait_for_timeout(1000)
            for th in seq:
                pg.evaluate(f"document.querySelector('.th-opt[data-th={th}]').click()")
                if gap: pg.wait_for_timeout(gap)
            pg.wait_for_timeout(1400)
            s = pg.evaluate(STATE)
            check(f'{"→".join(seq)} (gap {gap}): ends on {seq[-1]}, saved and shown match',
                  s['saved'] == seq[-1] and s['seg'] == seq[-1] and ((seq[-1] == 'golden') == (s['attr'] is None)))
    # 3. the small theme button in front of the ResuMate name (Home, AI, Profile) cycles Golden → Branchdesk → Midnight → Golden
    pg.evaluate("document.querySelector('.th-opt[data-th=golden]').click()"); pg.wait_for_timeout(1000)
    for tab in ['home', 'ai', 'profile']:
        pg.evaluate(f"document.querySelector('[data-tab={tab}]').click()"); pg.wait_for_timeout(600)
        btn = pg.locator('.panel.active .th-quick')
        check(f'{tab}: theme button is shown before the name', btn.is_visible())
        got = []
        for _ in range(3):
            btn.click(timeout=3000); pg.wait_for_timeout(1300); got.append(pg.evaluate(STATE)['saved'])
        check(f'{tab}: button cycles branchdesk → midnight → golden', got == ['branchdesk', 'midnight', 'golden'])
    check('no page errors', not errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed")
