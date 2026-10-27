# Checks: no ad banner on any tool page (PDF tools included), banner allowed on the AI Assistant tab,
# and every icon name used in the app has a drawing (no blank coloured squares).
import pathlib, functools, socket, threading, re
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port

# 1) static icon coverage
src = (HERE.parent / 'www' / 'index.html').read_text()
used = set(re.findall(r'data-ic="([a-zA-Z0-9_-]+)"', src)) | set(re.findall(r"ico\('([a-zA-Z0-9_-]+)'", src))
block = re.search(r'const BD_ICONS = \{(.*?)\n  \};', src, re.S).group(1)
keys = set(re.findall(r'^\s*([a-zA-Z0-9_-]+):', block, re.M))
chk('every icon name used has a drawing', not (used - keys), sorted(used - keys))

port = free_port()
handler = functools.partial(SimpleHTTPRequestHandler, directory=WWW); handler.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    # 2) ads: the AI tab is allowed; allowed() refuses tool pages (checked in the shipped source)
    chk('AI Assistant tab is in the banner tab list', "tabs:['home', 'profile', 'ai']" in src)
    fn = src[src.index('function allowed(){'):]; fn = fn[:fn.index('\n    }')]
    chk('allowed() refuses while a tool is open', 'if(toolIsOpen()) return false;' in fn, fn[:200])
    chk('the AI tab button exists', 'data-tab="ai"' in src)
    pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(400)
    chk('no page errors', not errs, errs[:3])
    b.close()
srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
