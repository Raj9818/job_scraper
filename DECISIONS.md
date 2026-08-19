# DECISIONS.md

## 1. Why this ingestion strategy over the alternative I rejected?

The obvious shortcut is hitting Naukri's internal JSON APIs directly with `requests` — no browser, way faster, way less resource-heavy. I rejected it because those endpoints aren't public/stable — they're not meant to be called outside the site's own frontend, they change without notice, and a raw HTTP client has no JS execution, no real TLS fingerprint, and no cookies/session behavior. It gets flagged almost immediately on a site with real anti-bot tooling. A full browser (Playwright + stealth patches) is slower and heavier, but it's the only approach that actually looks like a person using the site, which is the whole point of this exercise. Speed wasn't the goal — not getting blocked was.

## 2. One trade-off under the time limit

I only built out Naukri properly. Wellfound was supposed to be the second source (it's the easier target — weaker bot detection) but I didn't get to it. Also, the proxy layer is wired in but I'm not running a real residential proxy subscription right now — `PROXY_POOL` is just an empty config slot. That means the current demo run relies on pacing + stealth alone, which works for short/low-volume runs but won't hold up under repeated or higher-volume scraping.

With a real week I'd:
- Add the Wellfound scraper module (same pattern, different selectors — mechanical work at this point)
- Actually pay for a small residential proxy pool and test rotation under load
- Add CAPTCHA *detection* (not solving — just recognizing it and treating it as a block signal) since right now it just gets swallowed into the generic circuit breaker
- Write real tests for the selector fallback logic instead of eyeballing it

## 3. Where I used AI tools

I used Claude to scaffold the initial project structure — the stealth browser wrapper, the first pass at the DB models, and the first version of `main.py`'s run loop. I didn't just take that and ship it though. I rewrote the DB layer to add proper run tracking (`ScrapeRun` table, `start_scrape_run`/`update_scrape_run`) because the original version only logged point-in-time health pings and I wanted a full audit trail per run. I also added the URL/page hard limits (`URLS_LIMIT`, `MAX_PAGES`) myself since the first version could technically run unbounded, moved everything to `.env`-driven config instead of hardcoded values, switched the DB driver to `psycopg` for Postgres instead of the SQLite default, and built out the actual dashboard UI (`index.html`) from scratch since that wasn't part of the original scaffold. Every file I kept, I read through and changed something in — nothing went in untouched.