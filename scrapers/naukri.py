"""
Site-specific scraper for Naukri.com search results.
Only visible/public search pages are used — no login.
"""
import re
from tenacity import retry, stop_after_attempt, wait_exponential
import config

SOURCE = "naukri"


def build_search_url(keyword: str, location: str = "", page: int = 1):
    kw = keyword.replace(" ", "-").lower()
    base_url = config.NAUKRI_BASE_URL.rstrip("/")
    url = f"{base_url}/{kw}-jobs"
    if location:
        url += f"-in-{location.lower()}"
    if page > 1:
        url += f"-{page}"
    return url


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=20)
)
async def fetch_page(session, url):
    print(f"\n[fetch] Page: {url}")

    resp = await session.page.goto(
        url,
        wait_until="domcontentloaded",
        timeout=30000
    )

    if resp is None or resp.status >= 400:
        raise RuntimeError(
            f"Bad response status: {resp.status if resp else 'None'}"
        )

    # Give the page a little time to finish rendering.
    await session.page.wait_for_timeout(3000)

    await session.human_scroll()

    # Give the page another moment after scrolling.
    await session.page.wait_for_timeout(2000)

    return await session.page.content()


def parse_listings(html: str, selector_version="v1"):
    """
    Parses job cards. Falls back to a looser regex-based extraction if the
    primary CSS selectors return nothing (site markup changed).
    Returns [] (never raises) so pipeline can flag+continue instead of crashing.
    """
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    sel = config.NAUKRI_SELECTORS[selector_version]
    cards = soup.select(sel["job_card"])

    results = []
    if cards:
        for c in cards:
            try:
                title_el = c.select_one(sel["title"])
                company_el = c.select_one(sel["company"])
                loc_el = c.select_one(sel["location"])
                exp_el = c.select_one(sel["experience"])
                results.append({
                    "source": SOURCE,
                    "title": title_el.get_text(strip=True) if title_el else None,
                    "company": company_el.get_text(strip=True) if company_el else None,
                    "location": loc_el.get_text(strip=True) if loc_el else None,
                    "experience": exp_el.get_text(strip=True) if exp_el else None,
                    "url": title_el.get(sel["link_attr"]) if title_el else None,
                })
            except Exception:
                continue  # skip malformed card, don't kill the whole batch

    if not results:
        # Fallback: markup likely changed. Try a looser heuristic scan.
        results = _fallback_extract(html)

    return results


def _fallback_extract(html: str):
    """Very loose fallback: look for anchor tags with '/job-listings-' in href."""
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    found = []
    for a in soup.find_all("a", href=re.compile(r"/job-listings-")):
        title = a.get_text(strip=True)
        if title:
            found.append({
                "source": SOURCE,
                "title": title,
                "company": None,
                "location": None,
                "experience": None,
                "url": a.get("href"),
            })
    return found[:20]
