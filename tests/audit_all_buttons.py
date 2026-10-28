# Audit: press every visible button on every main screen and every tool, one at a time.
# Records page errors, buttons covered by something else, and clicks that do nothing visible.
# Skips anything destructive or that buys/upgrades. Run: python3 tests/audit_all_buttons.py
import functools, socket, threading, pathlib, json, sys
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
WWW = str(pathlib.Path(__file__).resolve().parent.parent / 'www')
SKIP = ('delete', 'clear', 'reset', 'upgrade', 'buy', 'subscribe', 'purchase', 'restore purchases', 'logout', 'sign out', 'remove', 'cancel anytime', 'maybe later', 'close')
s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
h = functools.partial(SimpleHTTPRequestHandler, directory=WWW); h.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), h); threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = "if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_tour_done','1')}"
ENUM = """(()=>{ const out=[]; const sel='button, a, [role=button], [role=tab], [role=radio], [data-tool], [data-nav], [data-tab], input[type=checkbox]';
  document.querySelectorAll(sel).forEach((el,i)=>{ if(!el.offsetParent) return; if(el.disabled) return; let a=el, dead=false; while(a&&a!==document.body){const cs=getComputedStyle(a); if(cs.visibility==='hidden'||cs.opacity==='0'||cs.display==='none'||a.hidden||a.getAttribute('aria-hidden')==='true'){dead=true;break} a=a.parentElement} if(dead) return; const r=el.getBoundingClientRect(); if(r.width<2||r.height<2) return;
    const label=((el.getAttribute('aria-label')||el.textContent||el.id||el.className||'')+'').trim().replace(/\\s+/g,' ').slice(0,60);
    out.push({i, label, id:el.id||'', tool:el.dataset.tool||'', tag:el.tagName}); el.setAttribute('data-audit', String(i)); }); return out; })()"""
def fresh(b, extra=''):
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, is_mobile=True, has_touch=True, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)[:120]))
    pg.add_init_script(BASE + extra)
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(2200)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(250)
    return ctx, pg, errs
report = {'screens': {}, 'errors': [], 'covered': []}
def skip(label):
    l = label.lower(); return any(w in l for w in SKIP)
def audit_screen(b, name, prep, extra=''):
    ctx, pg, errs = fresh(b, extra)
    prep(pg); pg.wait_for_timeout(400)
    items = pg.evaluate(ENUM)
    tested = 0
    for it in items:
        if skip(it['label']) and it['tool'] == '': continue
        if it['label'] == '' and it['id'] == '': continue
        n_before = len(errs)
        try:
            # re-open the screen if a previous click moved us away
            pg.evaluate(f"(()=>{{ const el=document.querySelector('[data-audit=\"{it['i']}\"]'); if(!el) return 'gone'; const r=el.getBoundingClientRect(); const top=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); if(top && top!==el && !el.contains(top)) return 'covered:'+(top.id||top.className||top.tagName); return 'ok'; }})()")
            st = pg.evaluate(f"(()=>{{ const el=document.querySelector('[data-audit=\"{it['i']}\"]'); if(!el) return 'gone'; el.scrollIntoView({{block:'center'}}); const r=el.getBoundingClientRect(); const top=document.elementFromPoint(r.left+r.width/2, r.top+r.height/2); return (top && (top===el || el.contains(top))) ? 'ok' : ('covered by '+(top? (top.id||top.className||top.tagName) : 'nothing')); }})()")
            if st.startswith('covered') or st.startswith('covered by'):
                report['covered'].append({'screen': name, 'label': it['label'], 'by': st})
            if st == 'gone':
                continue
            pg.evaluate(f"document.querySelector('[data-audit=\"{it['i']}\"]').click()"); pg.wait_for_timeout(260)
            tested += 1
            if len(errs) > n_before:
                report['errors'].append({'screen': name, 'button': it['label'], 'error': errs[-1]})
            # get back to where the audit started
            for _ in range(3):
                back = pg.evaluate("(()=>{ const t=document.getElementById('toolPage'); return t && !t.hidden; })()")
                if not back: break
                pg.evaluate("document.getElementById('toolBack') && document.getElementById('toolBack').click()"); pg.wait_for_timeout(200)
            pg.evaluate("document.querySelectorAll('.sheet.show, .dlv.go, #dlViewer:not([hidden])').forEach(x=>{ try{x.classList.remove('show','go'); }catch(e){} })")
            pg.keyboard.press('Escape'); pg.wait_for_timeout(120)
            prep(pg, quiet=True) if pg.evaluate("!document.querySelector('[data-audit]')") else None
        except Exception as e:
            report['errors'].append({'screen': name, 'button': it['label'], 'error': 'audit: ' + str(e)[:120]})
            ctx.close(); ctx, pg, errs = fresh(b, extra); prep(pg)
    report['screens'][name] = {'buttons': len(items), 'clicked': tested}
    ctx.close()
def home(pg, quiet=False): pg.wait_for_timeout(100)
def tab(name):
    return lambda pg, quiet=False: (pg.evaluate(f"document.querySelector('[data-tab={name}]').click()"), pg.wait_for_timeout(300))
def tool(key):
    def f(pg, quiet=False):
        pg.evaluate("document.getElementById('toolBack') && document.getElementById('toolBack').click()"); pg.wait_for_timeout(150)
        pg.evaluate(f"(()=>{{ const t=document.querySelector('.tl-tile[data-tool={key}]') || document.querySelector('#toolBody [data-tool={key}]'); if(t) t.click(); }})()"); pg.wait_for_timeout(450)
    return f
with sync_playwright() as p:
    b = p.chromium.launch()
    audit_screen(b, 'Home', home)
    audit_screen(b, 'Templates tab', tab('templates'))
    audit_screen(b, 'AI Assistant tab', tab('ai'))
    audit_screen(b, 'Profile tab', tab('profile'))
    tools = sys.argv[1:] or ['resumes','score','roleresume','importpdf','job','interview','jobtracker','letter','messages','pdftools','imagetools','imgpdf','mergepdf','splitpdf','rotatepdf','croppdf','shrinkpdf','signpdf','pagenums','watermark','pdf2jpg','pdf2txt','protectpdf','unlockpdf','rotateimg','flipimg','cropimg','resizeimg','grayimg','convertimg','idphoto','compress','premium']
    for k in tools:
        audit_screen(b, 'tool:' + k, lambda pg, quiet=False, k=k: tool(k)(pg))
    b.close()
srv.shutdown()
out = pathlib.Path('/tmp/claude-0/-home-claude/3f08c25f-de67-5997-a6e3-1b4821c2fe7f/scratchpad/audit.json')
out.write_text(json.dumps(report, indent=1))
print('screens:', len(report['screens']), 'clicks:', sum(v['clicked'] for v in report['screens'].values()))
print('errors:', len(report['errors']), 'covered:', len(report['covered']))
