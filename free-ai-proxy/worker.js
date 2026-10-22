/**
 * ResuMate free-AI proxy — a tiny Cloudflare Worker.
 *
 * What it does
 *  - Keeps your AI keys secret (they live here, never inside the app).
 *  - Gives every phone a small free daily allowance, and protects the whole service with a global daily cap.
 *  - Tries Gemini first; if Gemini is busy or out of quota it automatically tries Groq, then Cloudflare Workers AI.
 *  - Answers in the same shape the app already understands (Gemini "generateContent"), so the app needs no other change.
 *  - Never stores or logs resume text.
 *
 * Setup is in README.md (about 10 minutes, free).
 */

const DEFAULTS = {
  PER_DEVICE_DAILY: 5,        // free AI runs per phone per day
  GLOBAL_DAILY: 800,          // free AI runs for everybody together per day (protects your free quotas)
  IP_DAILY: 40,               // free AI runs per internet address per day (stops one person faking many phone ids)
  MAX_PROMPT_CHARS: 24000,
  GEMINI_MODELS: ['gemini-3.5-flash-lite', 'gemini-3.8-flash'],   // current free-tier models
  GROQ_MODEL: 'openai/gpt-oss-120b',   // llama-3.3-70b-versatile was shut down 16 Aug 2026
  WORKERS_AI_MODEL: '@cf/meta/llama-3.1-8b-instruct'
};

const num = (v, d) => { const n = parseInt(v, 10); return Number.isFinite(n) && n > 0 ? n : d; };
const today = () => new Date().toISOString().slice(0, 10);

function cors(env, req) {
  const allowed = (env.ALLOWED_ORIGINS || '*').split(',').map(s => s.trim()).filter(Boolean);
  const origin = req.headers.get('Origin') || '';
  const ok = allowed.includes('*') || allowed.includes(origin);
  return {
    'Access-Control-Allow-Origin': ok ? (allowed.includes('*') ? '*' : origin) : allowed[0],
    'Access-Control-Allow-Headers': 'Content-Type, X-Device-Id, X-Gemini-Model',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Expose-Headers': 'X-Free-Limit, X-Free-Remaining, X-Free-Reason, X-Provider',
    'Access-Control-Max-Age': '86400',
    'Vary': 'Origin'
  };
}

const json = (obj, status, headers) => new Response(JSON.stringify(obj), { status, headers: { 'Content-Type': 'application/json', ...headers } });
const fail = (status, message, headers, reason) => json({ error: { message, status } }, status, { ...headers, ...(reason ? { 'X-Free-Reason': reason } : {}) });

// ---- counters (Workers KV: approximate, which is fine for a free allowance) ----
async function readCount(env, key) { try { return env.QUOTA ? (parseInt(await env.QUOTA.get(key), 10) || 0) : 0; } catch (e) { return 0; } }
async function bump(env, key) { try { if (env.QUOTA) await env.QUOTA.put(key, String((await readCount(env, key)) + 1), { expirationTtl: 172800 }); } catch (e) { /* ignore */ } }

// ---- providers: each returns the model's raw text, or throws {retry:true} when the next provider should be tried ----
async function viaGemini(env, text, temperature, wantedModel) {
  if (!env.GEMINI_API_KEY) throw { retry: true, why: 'no gemini key' };
  const models = [wantedModel, ...DEFAULTS.GEMINI_MODELS].filter((m, i, a) => m && /^[\w.\-]+$/.test(m) && a.indexOf(m) === i);
  let last = null;
  for (const model of models) {
    const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(model)}:generateContent`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'x-goog-api-key': env.GEMINI_API_KEY },
      body: JSON.stringify({ contents: [{ role: 'user', parts: [{ text }] }], generationConfig: { temperature, responseMimeType: 'application/json' } })
    });
    if (r.ok) {
      const j = await r.json();
      const out = ((j.candidates || [])[0] || {}).content;
      const t = out && out.parts ? out.parts.map(p => p.text || '').join('') : '';
      if (t) return { text: t, provider: 'gemini:' + model };
      last = { retry: true, why: 'empty' };
      continue;
    }
    last = { retry: r.status === 429 || r.status >= 500 || r.status === 404 || r.status === 400, status: r.status };
    if (r.status === 401 || r.status === 403) throw { retry: true, why: 'gemini key problem' };   // do not keep hammering a bad key
  }
  throw last || { retry: true };
}

async function viaGroq(env, text, temperature) {
  if (!env.GROQ_API_KEY) throw { retry: true, why: 'no groq key' };
  const r = await fetch('https://api.groq.com/openai/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + env.GROQ_API_KEY },
    body: JSON.stringify({ model: env.GROQ_MODEL || DEFAULTS.GROQ_MODEL, temperature, response_format: { type: 'json_object' }, messages: [{ role: 'user', content: text }] })
  });
  if (!r.ok) throw { retry: true, status: r.status };
  const j = await r.json(); const t = j.choices && j.choices[0] && j.choices[0].message && j.choices[0].message.content;
  if (!t) throw { retry: true, why: 'empty' };
  return { text: t, provider: 'groq' };
}

async function viaWorkersAI(env, text, temperature) {
  if (!env.AI) throw { retry: true, why: 'no workers ai' };
  const out = await env.AI.run(env.WORKERS_AI_MODEL || DEFAULTS.WORKERS_AI_MODEL, { messages: [{ role: 'system', content: 'Reply with a single valid JSON object only.' }, { role: 'user', content: text }], temperature, max_tokens: 1800 });
  const t = out && (out.response || (out.result && out.result.response));
  if (!t) throw { retry: true, why: 'empty' };
  return { text: String(t), provider: 'workers-ai' };
}

export default {
  async fetch(req, env) {
    const h = cors(env, req);
    if (req.method === 'OPTIONS') return new Response(null, { status: 204, headers: h });
    if (req.method !== 'POST') return fail(405, 'Use POST.', h);

    const perDevice = num(env.PER_DEVICE_DAILY, DEFAULTS.PER_DEVICE_DAILY), perDay = num(env.GLOBAL_DAILY, DEFAULTS.GLOBAL_DAILY);
    const device = (req.headers.get('X-Device-Id') || '').trim();
    if (!/^[A-Za-z0-9_-]{8,64}$/.test(device)) return fail(400, 'Missing device id.', h);

    // only the prompt text is accepted — this is not a general-purpose AI gateway
    let body; try { body = await req.json(); } catch (e) { return fail(400, 'Bad request.', h); }
    const text = body && body.contents && body.contents[0] && body.contents[0].parts && body.contents[0].parts[0] && body.contents[0].parts[0].text;
    if (typeof text !== 'string' || !text.trim()) return fail(400, 'Missing prompt.', h);
    if (text.length > num(env.MAX_PROMPT_CHARS, DEFAULTS.MAX_PROMPT_CHARS)) return fail(413, 'That resume is too long for a free run.', h);
    const t = Number(body.generationConfig && body.generationConfig.temperature); const temperature = Number.isFinite(t) ? Math.min(1, Math.max(0.2, t)) : 0.5;

    // per-address limit: a new device id costs nothing, so also cap each internet address (phones on one network share it, so the cap is generous)
    const ip = (req.headers.get('CF-Connecting-IP') || 'unknown').slice(0, 64);
    const day = today(), dKey = `d:${day}:${device}`, gKey = `g:${day}`, iKey = `i:${day}:${ip}`;
    const [used, total, ipUsed] = await Promise.all([readCount(env, dKey), readCount(env, gKey), readCount(env, iKey)]);
    if (ipUsed >= num(env.IP_DAILY, DEFAULTS.IP_DAILY)) return fail(429, 'Too many free AI runs from this network today. Please try again tomorrow.', meta(0), 'limit');
    const left = () => Math.max(0, perDevice - used);
    const meta = extra => ({ ...h, 'X-Free-Limit': String(perDevice), 'X-Free-Remaining': String(extra == null ? left() : extra) });
    if (used >= perDevice) return fail(429, 'Your free AI runs for today are used. They reset tomorrow.', meta(0), 'limit');
    if (total >= perDay) return fail(429, 'Free AI is very busy today. Please try again tomorrow, or use your own key.', meta(left()), 'busy');

    const chain = [() => viaGemini(env, text, temperature, req.headers.get('X-Gemini-Model') || ''), () => viaGroq(env, text, temperature), () => viaWorkersAI(env, text, temperature)];
    let result = null;
    for (const step of chain) {
      try { result = await step(); break; } catch (e) { if (!(e && e.retry)) break; }
    }
    if (!result) return fail(503, 'The free AI is busy right now. Please try again in a minute.', meta(), 'busy');

    // count the run only after it worked, so failed attempts never cost anyone their allowance
    await Promise.all([bump(env, dKey), bump(env, gKey), bump(env, iKey)]);
    return json({ candidates: [{ content: { parts: [{ text: result.text }] } }] }, 200, { ...meta(Math.max(0, perDevice - used - 1)), 'X-Provider': result.provider.split(':')[0] });
  }
};
