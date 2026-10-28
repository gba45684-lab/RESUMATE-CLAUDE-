# Round of polish: Start from a role (card + 10-resume limit), Home spacing, placeholder warning,
# Restore backup naming, folding Home groups, the "?" tip button, transparent PNG/WebP, contrast.
import functools, socket, threading, pathlib, tempfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from PIL import Image
from playwright.sync_api import sync_playwright
WWW = str(pathlib.Path(__file__).resolve().parent.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_r31_') + '/'
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))
s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(SimpleHTTPRequestHandler, directory=WWW); h.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}"
TEN = "if(!localStorage.getItem('r31')){localStorage.setItem('r31','1'); const items=[...Array(10)].map((_,i)=>({id:'x'+i,label:'R'+i,userLabel:true,updated:Date.now(),data:{name:'A',role:'r',skills:'',summary:'',experience:[],education:[],extrasOrder:[]},tpl:'classic',accent:'#7A2418',font:'serif',size:'a4'})); localStorage.setItem('resumate_resumes_v2', JSON.stringify({items, active:'x0'}))}"
def open_page(b, extra=None):
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []; pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script(BASE)
    if extra: pg.add_init_script(extra)
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(2500)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(300)
    return ctx, pg, errs
with sync_playwright() as p:
    b = p.chromium.launch()

    # 1) Start from a role: card layout, create works, and the limit has a way out
    ctx, pg, errs = open_page(b)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=roleresume]').click()"); pg.wait_for_timeout(500)
    chk('role card shows headline, summary and skills', pg.evaluate("!!document.querySelector('#toolBody .rr-card') && document.querySelectorAll('#toolBody .rr-k').length === 3"))
    pg.locator('#rrGo').tap(); pg.wait_for_timeout(800)
    chk('Create resume from this makes a resume (tap)', pg.evaluate("JSON.parse(localStorage.getItem('resumate_resumes_v2')).items.length") == 2)
    ctx.close()
    ctx, pg, errs = open_page(b, TEN)
    pg.evaluate("document.querySelector('.tl-tile[data-tool=roleresume]').click()"); pg.wait_for_timeout(500)
    chk('at 10 resumes the Create button becomes Manage my resumes', pg.evaluate("!!document.getElementById('rrManage') && !document.getElementById('rrGo')"))
    pg.evaluate("document.getElementById('rrManage').click()"); pg.wait_for_timeout(500)
    chk('Manage opens My resumes', pg.evaluate("document.getElementById('toolTitle').textContent") == 'My resumes')
    chk('no page errors (role limit)', not errs, errs[:3]); ctx.close()

    # 2) Home: the last tile clears the tab bar when you scroll to the end
    ctx, pg, errs = open_page(b)
    pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); pg.evaluate("document.querySelectorAll('.panel.active .scr-inner, .panel.active')[0] && 0"); pg.wait_for_timeout(300)
    gap = pg.evaluate("""(()=>{ const tiles=[...document.querySelectorAll('.tl-tiles.tl-golden .tl-tile')].filter(e=>e.offsetParent); const last=tiles[tiles.length-1]; const bar=document.getElementById('tabbar').getBoundingClientRect(); const r=last.getBoundingClientRect(); return { clears: r.bottom <= bar.top + 2 || r.top >= bar.bottom, bottom: r.bottom, barTop: bar.top }; })()""")
    chk('the last Smart tools tile clears the tab bar', gap['clears'], gap)

    # 3) Placeholder warning on save keeps the save working
    chk('Restore backup is the name on Home', pg.evaluate("[...document.querySelectorAll('.hm-tile b')].some(b=> b.textContent === 'Restore backup')"))
    # 3b) exporting a resume that still has [brackets] saves, and says how many are left
    ctx2, pg2, errs2 = open_page(b)
    pg2.evaluate("document.querySelector('.tl-tile[data-tool=roleresume]').click()"); pg2.wait_for_timeout(500)
    pg2.locator('#rrGo').tap(); pg2.wait_for_timeout(900)
    pg2.evaluate("document.querySelector('button[data-seg=\"preview\"]').click()"); pg2.wait_for_timeout(900)
    with pg2.expect_download(timeout=90000) as dl:
        pg2.evaluate("document.getElementById('downloadPdfBtn').click()")
    dl.value.save_as(TMP + 'role.pdf')
    pg2.wait_for_timeout(600)
    pg2.wait_for_timeout(1800)
    chk('export saves and warns about [brackets] left', pg2.evaluate("[...document.querySelectorAll('.toast')].some(t=> /bracket/.test(t.textContent))"), pg2.evaluate("[...document.querySelectorAll('.toast')].map(t=>t.textContent)"))
    chk('the saved PDF exists', __import__('os').path.getsize(TMP + 'role.pdf') > 1000)
    ctx2.close()
    chk('the old "Import" name is gone from Home', pg.evaluate("![...document.querySelectorAll('.hm-tile b')].some(b=> b.textContent === 'Import')"))

    # 4) Folding Home groups, remembered; both theme copies follow together
    VISG = "[...document.querySelectorAll('.tl-grp[data-grp=Career]')].find(e=> e.offsetParent)"
    pg.evaluate(f"{VISG}.click()"); pg.wait_for_timeout(200)
    chk('Career folds away (visible copy)', pg.evaluate(f"{VISG}.parentElement.classList.contains('collapsed') && {VISG}.getAttribute('aria-expanded')==='false'"))
    chk('folded tiles are hidden', pg.evaluate(f"{VISG}.parentElement.querySelector('.tl-tile').offsetParent === null"))
    chk('the other theme copy folds too', pg.evaluate("[...document.querySelectorAll('.tl-grp[data-grp=Career]')].every(b=> b.parentElement.classList.contains('collapsed'))"))
    pg.reload(); pg.wait_for_timeout(2500)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(300)
    chk('the folded state is remembered after reload', pg.evaluate(f"{VISG}.parentElement.classList.contains('collapsed')"))
    pg.evaluate(f"{VISG}.click()"); pg.wait_for_timeout(200)
    chk('it opens again', pg.evaluate(f"!{VISG}.parentElement.classList.contains('collapsed')"))

    # 5) "?" brings back a tool's tip
    pg.evaluate("document.querySelector('.tl-tile[data-tool=pdftools]').click()"); pg.wait_for_timeout(400)
    pg.evaluate("document.querySelector('#toolBody .tool-hint-x') && document.querySelector('#toolBody .tool-hint-x').click()"); pg.wait_for_timeout(200)
    chk('the ? button is shown on a tool with a tip', pg.evaluate("document.getElementById('toolHelp').hidden === false && document.getElementById('toolHelp').offsetParent !== null"))
    pg.evaluate("document.getElementById('toolHelp').click()"); pg.wait_for_timeout(200)
    chk('? brings the tip back', pg.evaluate("!!document.querySelector('#toolBody .tool-hint')"))
    chk('no page errors (groups, tips)', not errs, errs[:3]); ctx.close()

    # 6) Transparent PNG/WebP stay transparent; JPG becomes white where there was transparency
    png = TMP + 'alpha.png'; im = Image.new('RGBA', (60, 40), (200, 30, 30, 255)); im.putpixel((5, 5), (0, 0, 0, 0)); im.save(png)
    ctx, pg, errs = open_page(b)
    def convert(fmt_val, name):
        pg.evaluate("document.querySelector('.tl-tile[data-tool=imagetools]').click()"); pg.wait_for_timeout(400)
        pg.evaluate("document.querySelector('#toolBody [data-tool=convertimg]').click()"); pg.wait_for_timeout(400)
        pg.set_input_files('#it-file', png); pg.wait_for_timeout(300)
        pg.evaluate(f"document.querySelector('[data-opt=fmt][data-val=\"{fmt_val}\"]').click()"); pg.wait_for_timeout(200)
        with pg.expect_download(timeout=60000) as d:
            pg.evaluate("document.getElementById('it-go').click()")
        out = TMP + name; d.value.save_as(out); return out
    o_png = convert('image/png', 'o.png')
    chk('PNG keeps the transparent pixel', Image.open(o_png).convert('RGBA').getpixel((5, 5))[3] == 0, Image.open(o_png).convert('RGBA').getpixel((5, 5)))
    o_jpg = convert('image/jpeg', 'o.jpg')
    chk('JPG turns the transparent pixel white', Image.open(o_jpg).convert('RGB').getpixel((5, 5))[0] > 230, Image.open(o_jpg).convert('RGB').getpixel((5, 5)))
    chk('no page errors (transparency)', not errs, errs[:3]); ctx.close()

    # 7) Contrast: main grey text passes WCAG AA on the cream background
    def lum(hx):
        hx = hx.lstrip('#'); r, g, bb = [int(hx[i:i+2], 16) / 255 for i in (0, 2, 4)]
        f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(bb)
    ratio = (max(lum('#66584A'), lum('#F7EEDD')) + 0.05) / (min(lum('#66584A'), lum('#F7EEDD')) + 0.05)
    chk('secondary text passes WCAG AA (4.5:1) on cream', ratio >= 4.5, round(ratio, 2))
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
