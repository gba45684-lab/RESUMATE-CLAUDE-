import os, pathlib, tempfile
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
OUT = tempfile.mkdtemp(prefix='resumate_test_') + '/'
import json, os, re, subprocess
from playwright.sync_api import sync_playwright
res=[]
def chk(name, ok, extra=''): res.append((name, bool(ok), extra)); print(('PASS ' if ok else 'FAIL ')+name+(' — '+str(extra) if extra and not ok else ''))
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=2, accept_downloads=True, permissions=['clipboard-read','clipboard-write'])
    ctx.route('**/*', lambda r: r.continue_() if r.request.url.startswith('file:') else r.abort())
    pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_user_name','Krapal Singh')}")
    pg.goto(URL); pg.wait_for_timeout(4800)
    chk('boot: no script errors', not errs, errs)
    chk('upgrade screen shows at launch', not pg.evaluate("document.getElementById('paywall').hidden"))
    pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(600)
    for tab in ['templates','ai','profile','home']:
        pg.evaluate(f"document.querySelector('[data-tab={tab}]').click()"); pg.wait_for_timeout(500)
        chk(f'tab {tab} opens', pg.evaluate("document.querySelector('.panel.active').dataset.panel")==tab)
    # templates -> preview
    pg.evaluate("document.querySelector('[data-tab=templates]').click()"); pg.wait_for_timeout(900)
    pg.touchscreen.tap(196,430); pg.wait_for_timeout(1200)
    chk('tap template opens Preview', pg.evaluate("document.querySelector('#segwrap .on').dataset.seg")=='preview')
    chk('preview is read-only (no contenteditable)', pg.evaluate("document.querySelectorAll('#previewMount [contenteditable]').length")==0)
    pg.evaluate("document.getElementById('previewMount').click()"); pg.wait_for_timeout(900)
    chk('tap resume -> full screen', not pg.evaluate("document.getElementById('resumeFs').hidden"))
    pg.evaluate("document.getElementById('rfsScroll').click()"); pg.wait_for_timeout(800)
    chk('tap again -> back in place', pg.evaluate("document.getElementById('resumeFs').hidden") and pg.evaluate("getComputedStyle(document.getElementById('previewMount')).visibility")=='visible')
    # exports
    with pg.expect_download(timeout=40000) as d: pg.evaluate("document.getElementById('downloadPdfBtn').click()")
    d.value.save_as(OUT+'out.pdf'); t=subprocess.run(['pdftotext',OUT+'out.pdf','-'],capture_output=True,text=True).stdout
    chk('PDF export works offline + text is searchable', 'Krapal Singh' in t and os.path.getsize(OUT+'out.pdf')>20000, os.path.getsize(OUT+'out.pdf'))
    with pg.expect_download(timeout=30000) as d: pg.evaluate("document.getElementById('exportDocxBtn').click()")
    d.value.save_as(OUT+'out.docx')
    import docx; dd=docx.Document(OUT+'out.docx'); chk('Word export opens', len(dd.paragraphs)>15)
    with pg.expect_download(timeout=30000) as d: pg.evaluate("document.getElementById('exportAtsBtn').click()")
    d.value.save_as(OUT+'out_ats.pdf'); chk('ATS text PDF is small + searchable', os.path.getsize(OUT+'out_ats.pdf')<60000 and 'Senior Product Manager' in subprocess.run(['pdftotext',OUT+'out_ats.pdf','-'],capture_output=True,text=True).stdout)
    chk('ATS keeps the rupee sign (no Rs)', '₹15 Cr' in subprocess.run(['pdftotext',OUT+'out_ats.pdf','-'],capture_output=True,text=True,encoding='utf-8').stdout)
    chk('page allows native pinch-zoom (accessibility)', 'user-scalable=no' not in pg.evaluate("document.querySelector('meta[name=viewport]').content"))
    pg.evaluate("document.querySelector('.back-btn').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("[...document.querySelectorAll('#profileList .prow')].find(r=>r.textContent.includes('Downloads')).click()"); pg.wait_for_timeout(1000)
    chk('My Downloads lists 3 files', pg.evaluate("document.querySelectorAll('.dl-row').length")==3, pg.evaluate("document.querySelectorAll('.dl-row').length"))
    names_before = pg.evaluate("[...document.querySelectorAll('.dl-row .dl-meta b')].map(b=>b.textContent)")
    last_name = names_before[-1]
    pg.evaluate("document.querySelectorAll('.dl-row')[%d].querySelector('.dl-act[aria-label^=Pin]').click()" % (len(names_before)-1)); pg.wait_for_timeout(900)
    chk('pin moves the download to the top', pg.evaluate("document.querySelector('.dl-row .dl-meta b').textContent")==last_name, names_before)
    chk('pinned button shows pressed', pg.evaluate("document.querySelector('.dl-row .dl-act[aria-label^=Unpin]') && document.querySelector('.dl-row .dl-act[aria-label^=Unpin]').getAttribute('aria-pressed')")=='true')
    pg.evaluate("document.querySelector('.dl-row .dl-act[aria-label^=Rename]').click()"); pg.wait_for_timeout(300)
    chk('rename shows an input', pg.evaluate("!!document.querySelector('.dl-row input.dl-rename')"))
    pg.fill('.dl-row input.dl-rename', 'Sharma CV 2026'); pg.keyboard.press('Enter'); pg.wait_for_timeout(900)
    chk('rename saved and shown', pg.evaluate("document.querySelector('.dl-row .dl-meta b').textContent")=='Sharma CV 2026')
    pg.evaluate("document.querySelector('.back-btn').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("[...document.querySelectorAll('#profileList .prow')].find(r=>r.textContent.includes('Downloads')).click()"); pg.wait_for_timeout(1000)
    chk('pin and rename survive reopening', pg.evaluate("document.querySelector('.dl-row .dl-meta b').textContent")=='Sharma CV 2026' and pg.evaluate("document.querySelector('.dl-row .dl-act[aria-label^=Unpin]') && 1")==1)
    pg.evaluate("document.querySelector('.dl-row .dl-act[aria-label^=Rename]').click()"); pg.wait_for_timeout(300)
    pg.fill('.dl-row input.dl-rename', 'Should not save'); pg.keyboard.press('Escape'); pg.wait_for_timeout(700)
    chk('escape cancels rename', pg.evaluate("document.querySelector('.dl-row .dl-meta b').textContent")=='Sharma CV 2026')
    pg.evaluate("document.querySelector('.dl-row').click()"); pg.wait_for_timeout(800)
    chk('saved file opens in viewer', not pg.evaluate("document.getElementById('dlViewer').hidden"))
    pg.keyboard.press('Escape'); pg.wait_for_timeout(500); pg.evaluate("document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(500)
    # every profile row opens
    rows=pg.evaluate("[...document.querySelectorAll('#profileList .prow .prow-t')].map(e=>e.textContent.trim().split('\\n')[0])")
    ok=True; bad=[]
    for i,name in enumerate(rows):
        pg.evaluate(f"document.querySelectorAll('#profileList .prow')[{i}].click()"); pg.wait_for_timeout(600)
        opened = pg.evaluate("document.getElementById('sheet2').classList.contains('show') || !document.getElementById('toolPage').hidden")
        if not opened: ok=False; bad.append(name)
        pg.evaluate("document.getElementById('sheet2').classList.contains('show') ? document.getElementById('sheet2Close').click() : document.getElementById('toolBack').click()"); pg.wait_for_timeout(450)
    chk(f'all {len(rows)} profile rows open', ok, bad)
    # smart tools
    pg.evaluate("document.querySelector('[data-tab=home]').click()"); pg.wait_for_timeout(500)
    for t in ['resumes','score','job','letter']:
        pg.evaluate(f"[...document.querySelectorAll('[data-tool={t}]')].find(e=>e.getBoundingClientRect().width>0).click()"); pg.wait_for_timeout(600)
        chk(f'tool {t} opens', not pg.evaluate("document.getElementById('toolPage').hidden"))
        pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(450)
    # themes
    for th in ['branchdesk','midnight','golden']:
        pg.evaluate(f"document.querySelector('.th-opt[data-th={th}]').click()"); pg.wait_for_timeout(700)
        attr=pg.evaluate("[document.documentElement.getAttribute('data-theme'),document.documentElement.getAttribute('data-mode')]")
        chk(f'theme {th} applies', (attr==[None,None]) if th=='golden' else (attr==['branchdesk','dark'] if th=='midnight' else attr==['branchdesk',None]), attr)
    # back button
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(400); pg.evaluate("history.back()"); pg.wait_for_timeout(600)
    chk('Back from Profile -> Home', pg.evaluate("document.querySelector('.panel.active').dataset.panel")=='home')
    # keyboard guard
    pg.evaluate("document.querySelector('.hm-card.light').click()"); pg.wait_for_timeout(800); pg.evaluate("document.querySelector('[data-seg=content]').click()"); pg.wait_for_timeout(400)
    pg.set_viewport_size({'width':393,'height':500}); pg.wait_for_timeout(300); pg.evaluate("(document.querySelector('[data-key=name]')||document.querySelector('.panel.push input')).focus()"); pg.wait_for_timeout(600)
    chk('keyboard open hides pinned bars', pg.evaluate("document.documentElement.classList.contains('kb')"))
    pg.evaluate("document.activeElement.blur()"); pg.set_viewport_size({'width':393,'height':852}); pg.wait_for_timeout(500)
    chk('final: no script errors', not errs, errs)
    b.close()
fails=[r for r in res if not r[1]]; print(f'\n{len(res)-len(fails)}/{len(res)} passed'); 
