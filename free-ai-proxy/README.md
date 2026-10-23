# ResuMate free-AI proxy (Cloudflare Worker) — setup in about 10 minutes, free

This gives every user free AI suggestions **without** them pasting a key. Your keys stay secret on the Worker.

## 1. Get free keys (all optional except the first)
- **Gemini** (required): https://aistudio.google.com/apikey → "Create API key".
- **Groq** (recommended backup): https://console.groq.com/keys
- **Cloudflare Workers AI** (second backup): no key needed — it is a binding (step 3).

## 2. Create the Worker
1. Make a free Cloudflare account → *Workers & Pages* → *Create* → *Hello World* Worker → name it `resumate-ai`.
2. *Edit code* → paste the whole of `worker.js` → *Deploy*.

## 3. Add the keys and the counter
In the Worker → *Settings*:
- **Variables and Secrets** → add secrets: `GEMINI_API_KEY` (and `GROQ_API_KEY` if you have it).
- **Bindings** → *KV namespace* → create one called `resumate-quota` → bind it as **`QUOTA`**.
- **Bindings** → *Workers AI* → bind it as **`AI`** (optional backup).
- Optional variables: `PER_DEVICE_DAILY` (default 5), `GLOBAL_DAILY` (default 800), `ALLOWED_ORIGINS` (default: `https://localhost,capacitor://localhost,http://localhost,https://resumate-claude.vercel.app` — only the app's own origins; set `*` only for testing).

## 4. Point the app at it
Your Worker address looks like `https://resumate-ai.<your-name>.workers.dev`.
- Quick test: open the app → Profile → AI Assistant → paste it into **Proxy URL**.
- For everyone: in `ResuMate-final.html` set `const DEFAULT_AI_PROXY = 'https://resumate-ai.<your-name>.workers.dev';`

## Good to know
- Free quotas are shared by all your users (Google counts them per project), so keep `GLOBAL_DAILY` below what your free keys allow. When it is reached, users see a friendly "busy today" message and can still use their own key.
- A run is counted only when an AI actually answered, never for failed attempts.
- The Worker never stores or logs resume text. Check each provider's current free-tier data terms and mention them in your privacy policy.
- To give Upgrade users more runs later, add a second limit keyed on a purchase check.
