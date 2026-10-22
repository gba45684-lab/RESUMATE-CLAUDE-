# Tests

Everything runs against `../ResuMate-final.html` (override with env `RESUMATE_URL=file:///…`).

## Setup (once)
    pip install playwright pillow python-docx && playwright install chromium
    # also needs poppler-utils (pdftotext) for the PDF text checks

## Run
    python tests/smoke1_main_flows.py        # 26 checks: boot, tabs, templates, preview, full screen, PDF/Word/ATS export, downloads, profile rows, tools, themes, Back button, keyboard guard
    python tests/smoke2_studio_flows.py      # 14 checks: several resumes, backup + reminder + re-import, job match, cover letter, photo, AI tab, upgrade screen
    python tests/smoke3_rewrite_flows.py     # 13 checks: select text in the preview -> rewrite with AI -> live change, undo, number guard, no contact details sent
    python tests/ai_mock_test.py             # AI against a simulated free-AI server: privacy masking, number warnings, diff, per-bullet apply, limit/busy/key/network errors
    node   tests/worker_test.mjs             # the Cloudflare Worker with mocked providers and quota store

All tests block the network (the app is fully offline) and use a phone-sized touch viewport (393×852).
Each prints PASS/FAIL lines; smoke tests end with "N/N passed".
