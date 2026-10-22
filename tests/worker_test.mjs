// Unit test of the free-AI proxy with mocked providers + KV (no network). Run:  node tests/worker_test.mjs
import worker from '../free-ai-proxy/worker.js';
const store = new Map(); const KV = { async get(k){ return store.get(k) ?? null; }, async put(k,v){ store.set(k,v); } };
let calls = []; let geminiMode = 'ok', groqMode = 'ok';
globalThis.fetch = async (url) => {
  const u = String(url); calls.push(u.includes('generativelanguage') ? 'gemini' : u.includes('groq') ? 'groq' : 'other');
  if(u.includes('generativelanguage')){ if(geminiMode==='ok') return new Response(JSON.stringify({candidates:[{content:{parts:[{text:'{"summary":"hi"}'}]}}]}),{status:200}); return new Response('{}',{status:geminiMode==='429'?429:geminiMode==='403'?403:503}); }
  if(u.includes('groq')){ if(groqMode==='ok') return new Response(JSON.stringify({choices:[{message:{content:'{"summary":"from groq"}'}}]}),{status:200}); return new Response('{}',{status:500}); }
  return new Response('{}',{status:500});
};
const env = { GEMINI_API_KEY:'g', GROQ_API_KEY:'q', QUOTA:KV, PER_DEVICE_DAILY:'3', GLOBAL_DAILY:'5' };
const mk = (dev, text='resume text') => new Request('https://x/', { method:'POST', headers:{'Content-Type':'application/json','X-Device-Id':dev}, body:JSON.stringify({contents:[{role:'user',parts:[{text}]}],generationConfig:{temperature:.5}}) });
const run = async (r)=>{ const res = await worker.fetch(r, env); return { s:res.status, left:res.headers.get('X-Free-Remaining'), why:res.headers.get('X-Free-Reason'), prov:res.headers.get('X-Provider') }; };
let fails = 0; const t = (name, ok) => { console.log((ok ? 'PASS ' : 'FAIL ') + name); if(!ok) fails++; };
t('preflight 204', (await worker.fetch(new Request('https://x/',{method:'OPTIONS'}),env)).status === 204);
t('GET rejected', (await worker.fetch(new Request('https://x/'),env)).status === 405);
t('missing device id', (await run(new Request('https://x/',{method:'POST',body:'{}'}))).s === 400);
t('oversize prompt', (await run(mk('device-aaaa1','x'.repeat(30000)))).s === 413);
let r = await run(mk('device-aaaa1')); t('first run ok via gemini, 2 left', r.s===200 && r.prov==='gemini' && r.left==='2');
geminiMode='429'; r = await run(mk('device-aaaa1')); t('gemini busy -> falls back to groq', r.s===200 && r.prov==='groq');
geminiMode='403'; groqMode='fail'; r = await run(mk('device-aaaa1')); t('all providers fail -> 503 and allowance NOT used', r.s===503 && r.left==='1');
geminiMode='ok'; groqMode='ok'; r = await run(mk('device-aaaa1')); t('third run ok', r.s===200 && r.left==='0');
r = await run(mk('device-aaaa1')); t('4th run -> per-device limit', r.s===429 && r.why==='limit');
r = await run(mk('device-bbbb2')); t('another phone still works', r.s===200);
await run(mk('device-cccc3')); await run(mk('device-dddd4')); r = await run(mk('device-eeee5')); t('global daily cap -> busy', r.s===429 && r.why==='busy');
console.log(fails ? `\n${fails} FAILED` : '\nall passed'); process.exit(fails ? 1 : 0);
