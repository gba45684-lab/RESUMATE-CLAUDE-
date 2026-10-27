# Checks the Smart tools for photos and PDFs: passport photo, images to PDF, compress image, merge PDFs.
import os, pathlib, tempfile, subprocess, io, re
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
TMP = tempfile.mkdtemp(prefix='resumate_tools_') + '/'
from PIL import Image
from playwright.sync_api import sync_playwright
res = []
def chk(name, ok, extra=''):
    res.append((name, bool(ok))); print(('PASS ' if ok else 'FAIL ') + name + ('' if ok or not extra else ' — ' + str(extra)))

# fixtures: a portrait photo, a landscape photo, two small PDFs, and a broken "PDF"
portrait = TMP + 'portrait.jpg'; Image.new('RGB', (1200, 1600), (150, 110, 90)).save(portrait, 'JPEG', quality=95)
landscape = TMP + 'scan.png'; Image.new('RGB', (2400, 1200), (240, 240, 235)).save(landscape)
pdf1 = TMP + 'a.pdf'; Image.new('RGB', (600, 800), (200, 80, 80)).save(pdf1, 'PDF')
pdf2 = TMP + 'b.pdf'; Image.new('RGB', (600, 800), (80, 80, 200)).save(pdf2, 'PDF', save_all=True, append_images=[Image.new('RGB', (600, 800), (80, 200, 80))])
broken = TMP + 'broken.pdf'; open(broken, 'wb').write(b'not really a pdf')
def pages(path):
    out = subprocess.run(['pdfinfo', path], capture_output=True, text=True).stdout
    m = re.search(r'Pages:\s+(\d+)', out); return int(m.group(1)) if m else -1

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={'width': 393, 'height': 852}, has_touch=True, is_mobile=True, accept_downloads=True)
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg = ctx.new_page(); errs = []
    pg.on('pageerror', lambda e: errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_user_name','Krapal Singh')}")
    pg.goto(URL); pg.wait_for_timeout(4800)
    pg.evaluate("const p=document.getElementById('paywall'); if(p && !p.hidden) document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)

    # --- Passport photo
    pg.evaluate("document.querySelector('[data-tool=idphoto]').click()"); pg.wait_for_timeout(700)
    chk('passport tool opens with a file picker', pg.evaluate("!!document.querySelector('#ipFile')"))
    pg.set_input_files('#ipFile', portrait); pg.wait_for_timeout(1200)
    chk('passport: preview shows after choosing a photo', pg.evaluate("!!document.querySelector('#ipPrev')"))
    with pg.expect_download(timeout=30000) as d: pg.evaluate("document.getElementById('ipSave').click()")
    d.value.save_as(TMP + 'passport.jpg'); im = Image.open(TMP + 'passport.jpg')
    chk('passport: saved at 413 x 531 px (35x45 mm at 300 dpi)', im.size == (413, 531), im.size)
    pg.select_option('#ipMax', '50'); pg.wait_for_timeout(200)
    with pg.expect_download(timeout=30000) as d: pg.evaluate("document.getElementById('ipSave').click()")
    d.value.save_as(TMP + 'passport50.jpg')
    chk('passport: 50 KB limit is respected', os.path.getsize(TMP + 'passport50.jpg') <= 50 * 1024, os.path.getsize(TMP + 'passport50.jpg'))
    pg.evaluate("document.getElementById('ipProfile').click()"); pg.wait_for_timeout(900)
    chk('passport: "Use as profile photo" saves the photo', pg.evaluate("(localStorage.getItem('resumate_profile_photo')||'').startsWith('data:image/jpeg')"))
    pg.evaluate("document.querySelector('.tool-bar #toolBack, #toolBack').click()"); pg.wait_for_timeout(600)

    # --- Images to PDF
    pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(500); pg.evaluate("document.querySelector('#toolBody [data-tool=imgpdf]').click()"); pg.wait_for_timeout(700)
    pg.set_input_files('#imgFile', [portrait, landscape, portrait]); pg.wait_for_timeout(800)
    chk('images to PDF: three images listed', pg.evaluate("document.querySelectorAll('#toolBody .tl-file').length") == 3)
    pg.evaluate("document.querySelector('#toolBody .tl-file [data-act=down]').click()"); pg.wait_for_timeout(300)
    chk('images to PDF: move down reorders', pg.evaluate("document.querySelectorAll('#toolBody .tl-file')[0].querySelector('b').textContent") == 'scan.png')
    pg.evaluate("document.querySelectorAll('#toolBody .tl-file')[2].querySelector('[data-act=rm]').click()"); pg.wait_for_timeout(300)
    chk('images to PDF: remove leaves two', pg.evaluate("document.querySelectorAll('#toolBody .tl-file').length") == 2)
    pg.evaluate("document.querySelector('[data-size=letter]').click()"); pg.wait_for_timeout(200)
    with pg.expect_download(timeout=60000) as d: pg.evaluate("document.getElementById('imgGo').click()")
    d.value.save_as(TMP + 'photos.pdf')
    chk('images to PDF: file has 2 pages', pages(TMP + 'photos.pdf') == 2, pages(TMP + 'photos.pdf'))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(600)

    # --- Compress image
    pg.evaluate("document.querySelector('[data-tool=compress]').click()"); pg.wait_for_timeout(700)
    pg.set_input_files('#cmpFile', landscape); pg.wait_for_timeout(1000)
    pg.evaluate("document.querySelector('[data-side=\"800\"]').click()"); pg.wait_for_timeout(1200)
    pg.evaluate("const q=document.getElementById('cmpQ'); q.value=60; q.dispatchEvent(new Event('change'))"); pg.wait_for_timeout(900)
    chk('compress: shows a size estimate', pg.evaluate("/About/.test(document.getElementById('cmpEst').textContent)"), pg.evaluate("document.getElementById('cmpEst').textContent"))
    with pg.expect_download(timeout=30000) as d: pg.evaluate("document.getElementById('cmpSave').click()")
    d.value.save_as(TMP + 'small.jpg'); im2 = Image.open(TMP + 'small.jpg')
    chk('compress: longest side is 800 px', max(im2.size) == 800, im2.size)
    chk('compress: smaller than the original', os.path.getsize(TMP + 'small.jpg') < os.path.getsize(landscape), os.path.getsize(TMP + 'small.jpg'))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(600)

    # --- Merge PDFs
    pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(500); pg.evaluate("document.querySelector('#toolBody [data-tool=mergepdf]').click()"); pg.wait_for_timeout(700)
    chk('merge: button disabled with fewer than two files', pg.evaluate("document.getElementById('mpGo').disabled"))
    pg.set_input_files('#mpFile', [pdf1, pdf2]); pg.wait_for_timeout(800)
    chk('merge: two files listed', pg.evaluate("document.querySelectorAll('#toolBody .tl-file').length") == 2)
    with pg.expect_download(timeout=90000) as d: pg.evaluate("document.getElementById('mpGo').click()")
    d.value.save_as(TMP + 'merged.pdf')
    chk('merge: merged file has 3 pages (1 + 2)', pages(TMP + 'merged.pdf') == 3, pages(TMP + 'merged.pdf'))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.querySelector('[data-tool=pdftools]').click()"); pg.wait_for_timeout(500); pg.evaluate("document.querySelector('#toolBody [data-tool=mergepdf]').click()"); pg.wait_for_timeout(700)
    pg.set_input_files('#mpFile', [pdf1, broken]); pg.wait_for_timeout(600)
    pg.evaluate("document.getElementById('mpGo').click()"); pg.wait_for_timeout(4000)
    msg = pg.evaluate("document.getElementById('mpMsg').textContent")
    chk('merge: a damaged file is named in the message', 'broken.pdf' in msg, msg)

    chk('no script errors', not errs, errs)
    b.close()

print(f"\n{sum(ok for _, ok in res)}/{len(res)} passed")
