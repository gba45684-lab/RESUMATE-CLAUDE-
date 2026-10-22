import os, pathlib, tempfile
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
OUT = tempfile.mkdtemp(prefix='resumate_test_') + '/'
import json
from playwright.sync_api import sync_playwright
PROXY='https://resumate-ai.gba45684.workers.dev/'   # the app always calls the Worker
state={'mode':'ok','bodies':[]}
def handler(route):
    req=route.request
    cors={'Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'*','Access-Control-Allow-Methods':'POST, OPTIONS','Access-Control-Expose-Headers':'X-Free-Limit, X-Free-Remaining, X-Free-Reason'}
    if req.method=='OPTIONS': route.fulfill(status=204, headers=cors); return
    state['bodies'].append(req.post_data or '')
    m=state['mode']
    if m=='ok':
        out={"summary":"Product leader who scaled fintech products to 45% higher activation across 3 teams.","experience":[{"index":0,"bullets":["Led strategy and roadmap for three teams serving 1.2M monthly active users","Redesigned onboarding, lifting activation by 99% and cutting time-to-value from 9 days to 4","Launched usage-based pricing that added ₹42 Cr in annual recurring revenue","Introduced OKRs and a weekly experiment cadence, running 60+ A/B tests in 12 months"]}],"skills_add":["Tableau"],"tips":["Add one line on team size."]}
        route.fulfill(status=200, headers={**cors,'Content-Type':'application/json','X-Free-Limit':'5','X-Free-Remaining':'3'}, body=json.dumps({"candidates":[{"content":{"parts":[{"text":json.dumps(out)}]}}]}))
    elif m=='limit': route.fulfill(status=429, headers={**cors,'Content-Type':'application/json','X-Free-Limit':'5','X-Free-Remaining':'0','X-Free-Reason':'limit'}, body=json.dumps({"error":{"message":"used"}}))
    elif m=='busy': route.fulfill(status=429, headers={**cors,'Content-Type':'application/json','X-Free-Reason':'busy','X-Free-Remaining':'2','X-Free-Limit':'5'}, body=json.dumps({"error":{"message":"busy"}}))
    elif m=='key': route.fulfill(status=403, headers={**cors,'Content-Type':'application/json'}, body=json.dumps({"error":{"message":"bad key"}}))
    elif m=='net': route.abort()
with sync_playwright() as p:
    b=p.chromium.launch()
    ctx=b.new_context(viewport={'width':393,'height':852}, has_touch=True, is_mobile=True, device_scale_factor=2)
    ctx.route(PROXY+'**', handler)
    pg=ctx.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append(str(e)))
    cfg=json.dumps({'key':'','proxy':PROXY,'model':'auto'})
    pg.add_init_script("if(!sessionStorage.getItem('s')){sessionStorage.setItem('s','1');localStorage.setItem('resumate_lite','1');localStorage.setItem('resumate_seen_welcome','1');localStorage.setItem('resumate_goal_answered','skipped');localStorage.setItem('resumate_user_name','Krapal Singh');localStorage.setItem('resumate_ai_cfg',%s);localStorage.setItem('resumate_jd','We need a Product Manager with Tableau, SQL and Agile experience to own the roadmap.')}"%json.dumps(cfg))
    pg.goto(URL); pg.wait_for_timeout(4800); pg.evaluate("document.getElementById('pwClose').click()"); pg.wait_for_timeout(500)
    pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(700)
    print('AI tab tips (sample resume):', pg.evaluate("[...document.querySelectorAll('#suggList .sugg-tt')].map(b=>b.textContent)"), '| hero quota:', pg.inner_text('#aiHeroQ'))
    pg.evaluate("document.getElementById('genBtn').click()"); pg.wait_for_timeout(900)
    print('panel:', pg.evaluate("document.querySelector('#sheet2 h3').textContent"), '| job-ad link visible:', not pg.evaluate("document.getElementById('aiJobFromMatch').hidden"))
    pg.evaluate("document.getElementById('aiJobFromMatch').click()"); print('job field:', pg.input_value('#aiJob')[:48])
    pg.evaluate("document.getElementById('aiSuggest').click()"); pg.wait_for_timeout(250)
    print('while loading:', pg.inner_text('#aiStatus'), '| skeleton:', pg.evaluate("!!document.querySelector('.ai-skel')")); pg.wait_for_timeout(2400)
    body=state['bodies'][-1]
    print('PRIVACY sent -> name:', 'Krapal' in body, '| email:', '@email.com' in body, '| phone:', '98765' in body, '| linkedin:', 'linkedin' in body.lower(), '| job text sent:', 'Tableau, SQL' in body, '| injection guard:', 'ignore any instructions' in body)
    print('cards:', pg.evaluate("[...document.querySelectorAll('#aiOut .ai-sug h5 span')].map(s=>s.textContent)"))
    print('warnings:', pg.evaluate("[...document.querySelectorAll('.ai-warn')].map(w=>w.textContent)"), '| warn bar:', pg.evaluate("!!document.querySelector('.ai-warnbar')"))
    print('highlighted:', pg.evaluate("[...document.querySelectorAll('#aiOut mark')].slice(0,5).map(m=>m.textContent)"), '| per-bullet boxes:', pg.evaluate("document.querySelectorAll('#aiOut input[data-k]').length"), '| status:', pg.inner_text('#aiStatus')[:70])
    pg.screenshot(path=OUT+'ai_result.png')
    pg.evaluate("document.querySelectorAll('#aiOut input[data-k]')[1].click()")   # keep the original of bullet 2 (the one with the made-up 99%)
    pg.evaluate("[...document.querySelectorAll('#aiOut .ai-sug')].find(d=>d.textContent.includes('Senior Product Manager')).querySelector('.ai-apply').click()"); pg.wait_for_timeout(700)
    live=pg.evaluate("JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.experience[0].bullets")
    print('applied: bullet1 new?', live[0].startswith('Led strategy'), '| bullet2 kept original?', live[1].startswith('Redesigned onboarding, lifting activation 35%'), '| bullet3 new?', live[2].startswith('Launched usage-based'))
    pg.evaluate("document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(450)
    for mode in ['limit','busy','key','net']:
        state['mode']=mode; pg.evaluate("localStorage.removeItem('resumate_ai_cache_v1')")
        pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(400); pg.evaluate("document.getElementById('genBtn').click()"); pg.wait_for_timeout(700)
        pg.evaluate("document.getElementById('aiSuggest').click()"); pg.wait_for_timeout(1800)
        print(f'[{mode}]', pg.inner_text('#aiStatus')[:100], '| buttons:', pg.evaluate("[...document.querySelectorAll('#aiErr button')].map(b=>b.textContent)"))
        if mode=='limit': pg.screenshot(path=OUT+'ai_err.png')
        pg.evaluate("document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(450)
    print('errors:', errs); b.close()
