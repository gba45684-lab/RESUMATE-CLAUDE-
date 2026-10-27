# ResuMate

ResuMate is an Android app (built with Capacitor) for making professional resumes on a phone.
The whole app is one page, `www/index.html`. Resumes are stored on the phone. The optional
AI tools call a small free-AI proxy (`free-ai-proxy/`), and only when the person taps an AI button.

## Layout

| Path | What it is |
|---|---|
| `www/index.html` | The whole app: screens, styles and scripts (bundled PDF libraries are inside it) |
| `api/updates.js` | Vercel function that tells the app when a new over-the-air update exists |
| `free-ai-proxy/` | Cloudflare Worker that calls Gemini with per-device and daily limits |
| `tests/` | Browser tests (Playwright, Python) and a Worker test (Node) |
| `.github/workflows/` | CI: tests, Android debug APK, signed release, over-the-air bundle |
| `capacitor.config.json` | Capacitor settings, including the update server URL |
| `privacy.html` | Privacy page (not yet inside the app bundle; see the open items) |
| `AGENTS.md` | Guidance for AI coding agents working in this repo |

## Run the tests

```bash
pip install -r tests/requirements.txt && playwright install chromium
python tests/smoke1_main_flows.py
```

See `tests/README.md` for the full list and what each one checks.

## Build

- **Debug APK:** runs on push to `main` (`resumate-android.yml`). Download the `ResuMate-debug-apk` artifact.
- **Over-the-air update:** a push to `main` that changes `www/**` or `api/updates.js` runs the test suite and, only if it passes, publishes a new bundle (`resumate-ota.yml`). Phones pick it up automatically.
- **Signed release:** `resumate-release.yml` (needs the signing secrets).

## Notes

- The app version shown in the app is stamped by CI. Keep the `APP_VERSION` line in `www/index.html` as is.
- Every AI call sends only resume text, with email, phone and links masked (`aiScrub`).
