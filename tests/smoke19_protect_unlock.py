# Checks Protect PDF and Unlock PDF on the phone (qpdf WebAssembly): encrypt with AES-256, decrypt with the password.
import pathlib, tempfile, threading, functools, socket, time
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter
from playwright.sync_api import sync_playwright
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_lock_') + '/'
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))

plain = TMP + 'plain.pdf'; c = canvas.Canvas(plain, pagesize=(595, 842)); c.drawString(72, 760, 'Krapal Singh resume'); c.save()
locked = TMP + 'locked.pdf'
w = PdfWriter(); w.append(plain); w.encrypt(user_password='secret123', owner_password='owner-x', algorithm='AES-256'); w.write(locked)

def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port
port = free_port()
handler = functools.partial(SimpleHTTPRequestHandler, directory=WWW); handler.log_message = lambda *a, **k: None
srv = ThreadingHTTPServer(('127.0.0.1', port), handler)
threading.Thread(target=srv.serve_forever, daemon=True).start()

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith(f'http://127.0.0.1:{port}') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')}")
    pg.goto(f'http://127.0.0.1:{port}/index.html'); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(400)

    msg = lambda: pg.evaluate("(document.getElementById('pt-msg')||{}).textContent||''")
    def wait_msg(limit=120):
        t0 = time.time()
        while time.time() - t0 < limit:
            m = msg()
            if m and 'Working' not in m: return m
            pg.wait_for_timeout(400)
        return 'TIMEOUT'
    def open_tool(t):
        pg.evaluate(f"document.querySelector('[data-tool={t}]').click()"); pg.wait_for_timeout(600)
    def close_tool():
        pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(500)
    def set_pw(id_, v):
        pg.evaluate(f"(()=>{{const e=document.getElementById('{id_}'); e.value={v!r}; e.dispatchEvent(new Event('input'))}})()")
    def click_go():
        pg.evaluate("document.getElementById('pt-go').click()")

    chk('Security section and both tools on Home', pg.evaluate("[...document.querySelectorAll('.tl-subh')].map(e=>e.textContent).includes('Security') && !!document.querySelector('[data-tool=protectpdf]') && !!document.querySelector('[data-tool=unlockpdf]')"))

    # Protect: short and mismatched passwords are refused
    open_tool('protectpdf')
    pg.set_input_files('#pt-file', plain); pg.wait_for_timeout(500)
    set_pw('pt-pw', 'abc'); set_pw('pt-pw2', 'abc'); click_go(); pg.wait_for_timeout(300)
    chk('protect: short password refused', 'at least 6' in msg(), msg())
    set_pw('pt-pw', 'secret123'); set_pw('pt-pw2', 'secret124'); click_go(); pg.wait_for_timeout(300)
    chk('protect: mismatched passwords refused', "don't match" in msg(), msg())

    # Protect: a good password gives an encrypted file
    set_pw('pt-pw', 'secret123'); set_pw('pt-pw2', 'secret123')
    with pg.expect_download(timeout=120000) as dl:
        click_go()
    out = TMP + dl.value.suggested_filename; dl.value.save_as(out)
    chk('protect: file saved', out.endswith('.pdf'), out)
    r = PdfReader(out)
    chk('protect: file is encrypted', r.is_encrypted)
    chk('protect: wrong password does not open it', r.decrypt('nope') == 0)
    chk('protect: right password opens it', PdfReader(out, password='secret123').pages[0].extract_text().find('Krapal') >= 0)
    close_tool()

    # Unlock: a wrong password is refused, a right one gives an open file
    open_tool('unlockpdf')
    pg.set_input_files('#pt-file', locked); pg.wait_for_timeout(500)
    set_pw('pt-pw', 'nope'); click_go(); wait_msg()
    chk('unlock: wrong password message', "isn't right" in msg(), msg())
    set_pw('pt-pw', '')
    click_go(); wait_msg()
    chk('unlock: no password says it needs one', 'needs its password' in msg(), msg())
    set_pw('pt-pw', 'secret123')
    with pg.expect_download(timeout=120000) as dl:
        click_go()
    out2 = TMP + dl.value.suggested_filename; dl.value.save_as(out2)
    r2 = PdfReader(out2)
    chk('unlock: result opens without a password', not r2.is_encrypted and 'Krapal' in r2.pages[0].extract_text())
    close_tool()

    # Unlock: a plain PDF still saves
    open_tool('unlockpdf')
    pg.set_input_files('#pt-file', plain); pg.wait_for_timeout(500)
    with pg.expect_download(timeout=120000) as dl:
        click_go()
    out3 = TMP + dl.value.suggested_filename; dl.value.save_as(out3)
    chk('unlock: a PDF with no password saves', 'Krapal' in PdfReader(out3).pages[0].extract_text())
    close_tool()

    chk('no page errors', not errs, errs[:3])
    b.close()

srv.shutdown()
print(f"\n{sum(1 for _, v in res if v)}/{len(res)} passed")
