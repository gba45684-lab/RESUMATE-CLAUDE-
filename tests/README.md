# Tests

Everything runs against `../www/index.html` (override with env `RESUMATE_URL=file:///…`).

## Setup (once)
    pip install -r tests/requirements.txt && playwright install chromium
    # also needs poppler-utils (pdftotext) for the PDF text checks

## Run
    python tests/smoke1_main_flows.py        # 34 checks: boot, tabs, templates, preview, full screen, PDF/Word/ATS export, downloads, profile rows, tools, themes, Back button, keyboard guard
    python tests/smoke2_studio_flows.py      # 14 checks: several resumes, backup + reminder + re-import, job match, cover letter, photo, AI tab, upgrade screen
    python tests/smoke3_rewrite_flows.py     # 37 checks: select text -> pick style -> Before/After -> Apply -> Undo / undo bar, number guard, tip card, no contact details sent
    python tests/smoke4_rewrite_followups.py # 10 checks: "For this job" style (uses the pasted job ad), word-change summary
    python tests/smoke5_content_ai.py        # 18 checks: Content editor AI: write/improve summary, rewrite a bullet, suggest skills
    python tests/smoke6_theme_and_text.py    # 10 checks: job text readable in every theme; newest theme choice wins
    python tests/smoke7_update_alerts.py     # 11 checks: update toast/vibration/sound (open app) and system notification (background), once per version
    python tests/smoke8_repo_fixes.py        # 4 checks: clear data also removes the own key and history; no page errors; worker origins
    python tests/smoke9_check_fixes.py       # 12 checks: Check my resume "Fix this" buttons, AI auto-fills empty bullets, limit options
    python tests/ai_mock_test.py             # 27 checks: AI against a simulated free-AI server: privacy masking, number warnings, per-bullet apply, limit/busy/key/network errors
    python tests/native_app_test.py          # native app checks
    node   tests/worker_test.mjs             # the Cloudflare Worker (free-ai-proxy) with mocked providers and quota store

All tests block the network (the app is fully offline) and use a phone-sized touch viewport (393×852).
Each prints PASS/FAIL lines; the suites end with "N/N passed".
