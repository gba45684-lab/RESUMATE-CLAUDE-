import os, pathlib, tempfile
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
OUT = tempfile.mkdtemp(prefix='resumate_test_') + '/'
import json, time
from playwright.sync_api import sync_playwright
res=[]
def chk(name, ok, extra=''): res.append((name, bool(ok), extra)); print(('PASS ' if ok else 'FAIL ')+name+(' — '+str(extra) if extra and not ok else ''))
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=2, accept_downloads=True)
    pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    old=int((time.time()-5*86400)*1000)
    pg.add_init_script(f"if(!sessionStorage.getItem('s')){{sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_user_name','Krapal Singh');localStorage.setItem('resumate_first_seen','{old}')}}")
    pg.goto(URL); pg.wait_for_timeout(4800); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    # --- several resumes
    pg.evaluate("[...document.querySelectorAll('[data-tool=resumes]')].find(e=>e.getBoundingClientRect().width>0).click()"); pg.wait_for_timeout(600)
    pg.evaluate("document.getElementById('rsNewBlank').click()"); pg.wait_for_timeout(1100)
    chk('new blank resume opens editor', pg.evaluate("document.querySelector('.panel.push').classList.contains('open')"))
    pg.fill('[data-key=role]','Designer'); pg.wait_for_timeout(500); pg.evaluate("document.querySelector('.back-btn').click()"); pg.wait_for_timeout(500)
    pg.reload(); pg.wait_for_timeout(5000); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    chk('2 resumes survive reload', len(json.loads(pg.evaluate("localStorage.getItem('resumate_resumes_v2')"))['items'])==2)
    chk('backup reminder shows (5 days, no backup)', not pg.evaluate("document.getElementById('backupNudge').hidden"))
    with pg.expect_download(timeout=15000) as d: pg.evaluate("document.getElementById('bkGo').click()")
    d.value.save_as(OUT+'bk.json'); bk=json.load(open(OUT+'bk.json')); chk('backup holds both resumes', bk['version']==2 and len(bk['resumes'])==2)
    chk('reminder hides after backup', pg.evaluate("document.getElementById('backupNudge').hidden"))
    pg.set_input_files('#importFileInput',OUT+'bk.json'); pg.wait_for_timeout(1000)
    chk('re-import skips duplicates', 'already' in pg.inner_text('#toastMsg').lower(), pg.inner_text('#toastMsg'))
    # --- job match + letter
    pg.evaluate("[...document.querySelectorAll('[data-tool=job]')].find(e=>e.getBoundingClientRect().width>0).click()"); pg.wait_for_timeout(600)
    pg.fill('#jdText','Acme Payments is looking for a Product Manager. You will own the roadmap, run A/B testing, analyse funnels with SQL, use Tableau dashboards, and manage stakeholders across compliance and KYC. Experience with Agile and Jira required.')
    pg.evaluate("document.getElementById('jdGo').click()"); pg.wait_for_timeout(800)
    miss=pg.evaluate("[...document.querySelectorAll('.tl-chip.miss')].map(c=>c.textContent.trim())")
    chk('job match finds missing keywords, ignores company names', len(miss)>=1 and not any('acme' in m for m in miss), miss)
    pg.evaluate("document.getElementById('jdLetter').click()"); pg.wait_for_timeout(700)
    chk('cover letter picks company from the ad', pg.input_value('#clCompany').startswith('Acme'), pg.input_value('#clCompany'))
    pg.evaluate("document.getElementById('toolBack').click()"); pg.wait_for_timeout(400)
    # --- photo + AI tab + sheets
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(500)
    from PIL import Image; Image.new('RGB',(900,1200),(30,120,200)).save(OUT+'ph.jpg')
    pg.set_input_files('#profPhotoInput',OUT+'ph.jpg'); pg.wait_for_timeout(1200)
    chk('photo upload works', pg.evaluate("/url/.test(getComputedStyle(document.getElementById('profAvatar')).backgroundImage)"))
    pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(600)
    chk('AI tab shows personal tips', pg.evaluate("document.querySelectorAll('#suggList .sugg-row').length")>=1)
    pg.evaluate("document.getElementById('genBtn').click()"); pg.wait_for_timeout(800)
    chk('AI panel opens with privacy note', pg.evaluate("document.querySelector('#sheet2 .ai-note')&&/not<\\/b> your name|not\\s+your name/i.test(document.querySelector('#sheet2 .ai-note').innerHTML)") or pg.evaluate("/What is sent/.test(document.querySelector('#sheet2').textContent)"))
    pg.evaluate("document.getElementById('aiSuggest').click()"); pg.wait_for_timeout(1500)
    chk('AI without key/proxy gives a friendly message with buttons', pg.evaluate("document.querySelectorAll('#aiErr button, .ai-status').length")>=1, pg.inner_text('#aiStatus'))
    pg.evaluate("document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(400)
    # --- upgrade screen via header button, settings switches
    pg.evaluate("document.querySelector('[data-tab=profile]').click()"); pg.wait_for_timeout(300)
    pg.evaluate("document.querySelector('.panel.active .badge-premium').click()"); pg.wait_for_timeout(1200)
    chk('Upgrade button opens the same upgrade screen', not pg.evaluate("document.getElementById('paywall').hidden"))
    pg.evaluate("document.getElementById('pwLater').click()"); pg.wait_for_timeout(700)
    chk('no script errors at the end', not errs, errs)
    b.close()
fails=[r for r in res if not r[1]]; print(f'\n{len(res)-len(fails)}/{len(res)} passed')
