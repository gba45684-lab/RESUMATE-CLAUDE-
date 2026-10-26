# Checks Import PDF resume: reads text from a PDF, suggests details, applies only what the person keeps.
import os, pathlib, tempfile, json, threading, functools, socket
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
HERE = pathlib.Path(__file__).resolve().parent
WWW = str(HERE.parent / 'www')
TMP = tempfile.mkdtemp(prefix='resumate_import_') + '/'
from reportlab.pdfgen import canvas
from playwright.sync_api import sync_playwright
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))

# a text resume (as a real PDF) and a blank one (stands in for a scan)
resume = TMP + 'resume.pdf'
c = canvas.Canvas(resume)
lines = ['Krapal Singh', 'Senior Product Manager', 'Noida, India',
         'krapal.test@example.com | +91 98100 12345 | linkedin.com/in/krapal-singh-demo',
         'Summary', 'Product manager with eight years of experience building mobile apps.',
         'Skills', 'Python, SQL, Figma, Power BI', 'Experience', 'Senior Product Manager | Acme Corp | 2019 - 2024',
         '- Grew active users by 40%', '- Led a team of 6', 'Education', 'B.Tech Computer Science | IIT Delhi | 2014 - 2018']
y = 800
for ln in lines:
    c.drawString(60, y, ln); y -= 22
c.save()
blank = TMP + 'blank.pdf'; c2 = canvas.Canvas(blank); c2.showPage(); c2.save()

# serve the app over http (the PDF engine loads as a module, which file:// does not allow)
def free_port():
    s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close(); return port
port = free_port()
handler = functools.partial(SimpleHTTPRequestHandler, directory=WWW)
handler.log_message = lambda *a, **k: None
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
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)

    pg.evaluate("document.querySelector('[data-tool=importpdf]').click()"); pg.wait_for_timeout(700)
    chk('import tool opens with a PDF picker', pg.evaluate("!!document.querySelector('#impFile')"))

    pg.set_input_files('#impFile', blank); pg.wait_for_timeout(2500)
    chk('a PDF with no text says so', 'no text' in pg.evaluate("document.getElementById('impMsg').textContent"), pg.evaluate("document.getElementById('impMsg').textContent"))

    pg.set_input_files('#impFile', resume); pg.wait_for_timeout(3500)
    val = lambda k: pg.evaluate(f"(document.getElementById('imp-{k}')||{{}}).value || ''")
    chk('review shows the name', val('name') == 'Krapal Singh', val('name'))
    chk('review shows the job title', val('role') == 'Senior Product Manager', val('role'))
    chk('review shows the email', val('email') == 'krapal.test@example.com', val('email'))
    chk('review shows the phone', '98100' in val('phone'), val('phone'))
    chk('review shows the LinkedIn link', val('linkedin') == 'linkedin.com/in/krapal-singh-demo', val('linkedin'))
    chk('review shows the summary', 'eight years' in val('summary'), val('summary'))
    chk('review shows the skills', 'Python' in val('skills') and 'Figma' in val('skills'), val('skills'))
    chk('review shows the experience entry', 'Acme Corp' in val('experience') and 'Grew active users' in val('experience'), val('experience'))
    chk('review shows the education entry', 'IIT Delhi' in val('education'), val('education'))

    pg.fill('#imp-role', 'Head of Product')   # the person edits one field before using the rest
    pg.evaluate("document.getElementById('impUse').click()"); pg.wait_for_timeout(900)
    saved = json.loads(pg.evaluate("localStorage.getItem('resumate_resume_v1') || 'null'") or 'null') or {}
    chk('applied: name saved to the resume', saved.get('name') == 'Krapal Singh', saved.get('name'))
    chk('applied: the edited job title is saved', saved.get('role') == 'Head of Product', saved.get('role'))
    chk('applied: email and phone saved', saved.get('email') == 'krapal.test@example.com' and '98100' in saved.get('phone', ''))
    chk('applied: skills saved', 'Figma' in saved.get('skills', ''))
    exp = (saved.get('experience') or [{}])[0]
    chk('applied: experience title, company and bullets saved', exp.get('title') == 'Senior Product Manager' and exp.get('org') == 'Acme Corp' and len(exp.get('bullets', [])) == 2, saved.get('experience'))
    chk('applied: demo sample entries are removed', 'Google Project Management' not in pg.evaluate("localStorage.getItem('resumate_resume_v1') || ''") and 'PayLite' not in pg.evaluate("localStorage.getItem('resumate_resume_v1') || ''"))
    chk('applied: education saved', (saved.get('education') or [{}])[0].get('org') == 'IIT Delhi', saved.get('education'))
    chk('after import: Templates tab is active', pg.evaluate("document.querySelector('.panel.active').dataset.panel") == 'templates')
    chk('after import: the editor is open', pg.evaluate("document.querySelector('.panel.push[data-panel=\"edit\"]').classList.contains('open')"))
    chk('after import: Preview is showing the resume', pg.evaluate("document.querySelector('#segwrap .on').dataset.seg") == 'preview')
    chk('tool closed after use', pg.evaluate("document.getElementById('toolPage').hidden") is True or pg.evaluate("!document.getElementById('toolPage').classList.contains('go')"))

    chk('no script errors', not errs, errs)
    b.close()
srv.shutdown()
print(f"\n{sum(ok for _, ok in res)}/{len(res)} passed")
