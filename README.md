# Naukri Job Scraper — Design Doc + Setup

## 1. Detection surface addressed
- **Headless fingerprint**: `playwright-stealth` patches `navigator.webdriver` and other JS-visible tells.
- **Browser authenticity**: launches via `channel="chrome"` — uses the real installed Chrome binary, not bundled Chromium, so TLS/HTTP2 fingerprint matches a genuine browser.
- **Request timing**: `human_pause()` uses randomized delays (`MIN_DELAY`–`MAX_DELAY`, env-configurable), plus explicit render waits (`wait_for_timeout`) after page load and after scrolling — not fixed sleeps.
- **Behavioral signals**: `human_scroll()` fires randomized mouse-wheel events before scraping, since zero-interaction loads are a tell.
- **IP reputation**: proxy rotation via `PROXY_POOL` env var, avoiding datacenter IPs.

## 2. Ingestion strategy
- One `StealthSession` = one identity (proxy + fingerprint + cookies), rotated every `REQUESTS_PER_IDENTITY` requests.
- Only public search-result pages are hit — no login, no account to burn.
- **Hard caps, not just page limits**: `MAX_PAGES` and `URLS_LIMIT` both bound a run — whichever is hit first stops the run, so a run can't runaway even if pages keep returning results.
- **Every run is tracked**, not just logged: `start_scrape_run()` opens a `ScrapeRun` row, `update_scrape_run()` closes it with final status (`completed` / `blocked` / `error`), page-by-page success counts, and a human-readable note — visible via the DB, giving a full audit trail per run instead of just point-in-time health pings.
- Plan B if blocked mid-run: circuit breaker (`MAX_CONSECUTIVE_FAILURES`) trips, marks the run `blocked`, and stops cleanly. Cooldown (`CIRCUIT_BREAK_COOLDOWN_SEC`) governs when the next scheduled run can retry. In production this would fail over to a secondary source (Wellfound) rather than sit idle.

## 3. Resilience
- Selectors are versioned (`NAUKRI_SELECTOR_VERSION` env var, `NAUKRI_SELECTORS` dict) — a markup change only needs a new version added, not a rewrite.
- `parse_listings()` falls back to a loose anchor-tag scan if the primary CSS selectors return nothing.
- Empty parses and errors are logged to both `source_health` (point-in-time status) and `scrape_runs` (full run summary: pages attempted/succeeded, listings found/saved, failure count) — never crashes, always flags and continues.
- `tenacity` retry with exponential backoff on page fetch failures (network blips, transient blocks).
- All DB writes wrapped in try/except/rollback/finally — a failed write can't leave a dangling session or half-committed state.

## 4. Where we stop
- No login/account scraping — avoids account bans and impersonation concerns.
- No CAPTCHA-solving services — a CAPTCHA wall is treated as a block by the circuit breaker, not something we try to defeat.
- Hard-capped run size (`MAX_PAGES`, `URLS_LIMIT`) keeps volume in "curious human" territory by design, not just by convention.
- `robots.txt` directives are checked manually before adding any new page path.

## Setup

Create a `.env` file (all values below are required unless noted):
```env
DB_URL=postgresql+psycopg://user:password@localhost:5432/naukri_scraper
NAUKRI_BASE_URL=https://www.naukri.com
KEYWORD=python developer
LOCATION=delhi
MAX_PAGES=3
URLS_LIMIT=20
MIN_DELAY=2.5
MAX_DELAY=7.0
REQUESTS_PER_IDENTITY=15
MAX_CONSECUTIVE_FAILURES=4
CIRCUIT_BREAK_COOLDOWN_SEC=900
PROXY_POOL=
```

Install and run:
```bash
pip install -r requirements.txt
playwright install chromium   # or skip if using channel="chrome" with local Chrome
python main.py                # runs one scrape (respects MAX_PAGES / URLS_LIMIT)
python app.py                 # serves dashboard at localhost:8080
```

## Dashboard (`templates/index.html`)
Served at `/`, backed by `/api/jobs` and `/api/health`. Client-side sortable/filterable table with per-column dropdown filters (search + select-all/clear), pagination (configurable page size), and a live total/filtered result count. Pure JS, no framework — everything runs off the two JSON endpoints.

## Deploy (Railway/Render)
1. Push repo to GitHub.
2. Create service from repo; add a managed Postgres addon (matches `psycopg` driver now in use).
3. Set all `.env` vars above as environment variables in the platform dashboard.
4. Start command: `python app.py`
5. Schedule `python main.py` as a separate Cron job (Railway Cron / Render Cron Job) — keep it out of the web dyno.
6. `playwright install chromium --with-deps` in the build step (their containers won't have Chrome pre-installed like a local machine does — `channel="chrome"` only works where Chrome already exists).

## Not included in this scaffold (add before real use)
- A real residential proxy subscription (`PROXY_POOL` is empty by default)
- Wellfound scraper module (same pattern as `scrapers/naukri.py`, different selectors)
- CAPTCHA detection/handling (currently just treated as a generic block via the circuit breaker)