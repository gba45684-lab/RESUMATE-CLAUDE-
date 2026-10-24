import os, pathlib, json
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
results=[]
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name)
from playwright.sync_api import sync_playwright
bad={"app":"ResuMate","version":2,"resumes":[{"id":"rbad1","data":{"name":123,"summary":["x"],"skills":None,"experience":"nope","education":[1,"a",{"degree":"BSc","org":{"x":1}}],"certifications":{"a":1},"extrasOrder":["projects","evil","projects"],"extra":"<script>1</script>"}},
 {"id":"rbad2","data":{"name":"Sam","experience":[{"title":"Dev","org":"Acme","dates":"2020","bullets":"not a list"},{"title":"QA","bullets":[1,2,None]}]}}]}
with sync_playwright() as p:
    b=p.chromium.launch(); ctx=b.new_context(viewport={'width':393,'height':852},has_touch=True,is_mobile=True)
    pg=ctx.new_page(); errs=[]; pg.on('pageerror',lambda e:errs.append(str(e)))
    pg.add_init_script("localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped')")
    pg.goto(URL); pg.wait_for_timeout(4800); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    open('/tmp/bad_backup.json','w').write(json.dumps(bad))
    pg.set_input_files('#importFileInput','/tmp/bad_backup.json'); pg.wait_for_timeout(1500)
    check('damaged backup imports without a crash', not errs)
    for tab in ['templates']:
        pg.evaluate(f"document.querySelector('[data-tab={tab}]').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-open-edit]')&&document.querySelector('[data-open-edit]').click()"); pg.wait_for_timeout(500)
    for seg in ['content','preview']:
        pg.evaluate(f"document.querySelector('button[data-seg={seg}]').click()"); pg.wait_for_timeout(1200)
    check('editor and preview still open after the import', not errs)
    stored=pg.evaluate("localStorage.getItem('resumate_resumes_v2')") or ''
    check('stored data has no stray fields', 'evil' not in stored and '<script>' not in stored)
    check('stored data has lists as lists', '"experience":"nope"' not in stored)
    check('no page errors', not errs)
    if errs: print(errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed"); raise SystemExit(0 if all(results) else 1)
