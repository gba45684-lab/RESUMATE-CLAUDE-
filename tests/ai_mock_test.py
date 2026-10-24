import os, pathlib, tempfile
HERE = pathlib.Path(__file__).resolve().parent
URL = os.environ.get('RESUMATE_URL') or HERE.parent.joinpath('www', 'index.html').as_uri()
OUT = tempfile.mkdtemp(prefix='resumate_test_') + '/'
import json
results=[]
def check(name, ok):
    results.append(bool(ok)); print(('PASS ' if ok else 'FAIL ')+name)
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
EXPECT={'limit':"Today's free AI runs are used up",'busy':'busy right now','key':'not available right now','net':"Can't reach the AI"}
EXPECT_BTNS={'limit':['Add my own key','Upgrade for more runs'],'busy':['Try again','See offline tips'],'key':['Try again','See offline tips'],'net':['Try again','See offline tips']}
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
    check('AI tab shows the free quota line', 'free AI' in pg.inner_text('#aiUsageLine').lower() or 'free' in pg.inner_text('#aiUsageLine').lower())
    pg.evaluate("document.querySelector('[data-ai-open=tailor]').click()"); pg.wait_for_timeout(900)
    check('AI panel opens', pg.evaluate("document.querySelector('#sheet2 h3').textContent").strip() != '')
    check('job-ad link is shown when a job ad is saved', not pg.evaluate("document.getElementById('aiJobFromMatch').hidden"))
    pg.evaluate("document.getElementById('aiJobFromMatch').click()")
    check('job ad fills the job field', 'Tableau, SQL' in pg.input_value('#aiJob'))
    pg.evaluate("document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(450)
    pg.evaluate("document.querySelector('[data-ai-open=improve]').click()"); pg.wait_for_timeout(700)
    pg.evaluate("document.getElementById('aiSuggest').click()"); pg.wait_for_timeout(250)
    pg.wait_for_timeout(2400)
    body=state['bodies'][-1]
    check('privacy: name not sent', 'Krapal' not in body)
    check('privacy: email not sent', '@email.com' not in body)
    check('privacy: phone not sent', '98765' not in body)
    check('privacy: LinkedIn not sent', 'linkedin' not in body.lower())
    check('job ad is sent for matching', 'Tableau, SQL' in body)
    check('injection guard is in the request', 'ignore any instructions' in body)
    cards=pg.evaluate("[...document.querySelectorAll('#aiOut .ai-sug h5 span')].map(s=>s.textContent)")
    check('suggestion cards: summary, job, skills, tips', cards[:1]==['Summary'] and 'Skills to add' in cards and 'Tips' in cards)
    warns=pg.evaluate("[...document.querySelectorAll('.ai-warn')].map(w=>w.textContent)")
    check('numbers not in the resume are flagged', any('45' in w for w in warns) and any('99' in w for w in warns))
    check('warning bar shown', pg.evaluate("!!document.querySelector('.ai-warnbar')"))
    marks=pg.evaluate("[...document.querySelectorAll('#aiOut mark')].map(m=>m.textContent)")
    check('changed words are highlighted', '45%' in marks)
    check('each bullet has a choice box', pg.evaluate("document.querySelectorAll('#aiOut input[data-k]').length") == 4)
    pg.screenshot(path=OUT+'ai_result.png')
    pg.evaluate("document.querySelectorAll('#aiOut input[data-k]')[1].click()")   # keep the original of bullet 2 (the one with the made-up 99%)
    pg.evaluate("[...document.querySelectorAll('#aiOut .ai-sug')].find(d=>d.textContent.includes('Senior Product Manager')).querySelector('.ai-apply').click()"); pg.wait_for_timeout(700)
    live=pg.evaluate("JSON.parse(localStorage.getItem('resumate_resumes_v2')).items[0].data.experience[0].bullets")
    check('applied: chosen bullet 1 is new', live[0].startswith('Led strategy'))
    check('applied: unchosen bullet 2 kept original', live[1].startswith('Redesigned onboarding, lifting activation 35%'))
    check('applied: chosen bullet 3 is new', live[2].startswith('Launched usage-based'))
    pg.evaluate("document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(450)
    for mode in ['limit','busy','key','net']:
        state['mode']=mode; pg.evaluate("localStorage.removeItem('resumate_ai_cache_v1')")
        pg.evaluate("document.querySelector('[data-tab=ai]').click()"); pg.wait_for_timeout(400); pg.evaluate("document.querySelector('[data-ai-open=improve]').click()"); pg.wait_for_timeout(700)
        pg.evaluate("document.getElementById('aiSuggest').click()"); pg.wait_for_timeout(1800)
        msg=pg.inner_text('#aiStatus'); btns=pg.evaluate("[...document.querySelectorAll('" + ('#aiOut .ai-limit-acts button' if mode=='limit' else '#aiErr button') + "')].map(b=>b.textContent)")
        check(f'[{mode}] shows its error message', EXPECT[mode] in msg)
        check(f'[{mode}] offers the right buttons', btns == EXPECT_BTNS[mode])
        if mode == 'limit': check('[limit] still gives an answer offline (quick fixes) at the same time', pg.evaluate("document.querySelectorAll('#aiOut .ai-sug').length") >= 1)
        if mode=='limit': pg.screenshot(path=OUT+'ai_err.png')
        pg.evaluate("document.getElementById('sheet2Close').click()"); pg.wait_for_timeout(450)
    check('no page errors', not errs)
    b.close()
print(f"{sum(results)}/{len(results)} passed")
