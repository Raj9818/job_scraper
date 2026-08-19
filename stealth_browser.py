"""
Handles launching a Playwright browser that looks like a real Chrome instance:
- stealth patches (hides navigator.webdriver, fixes canvas/webgl fingerprint leaks)
- realistic viewport, user agent, locale, timezone
- optional proxy per-session
"""
import random
import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async
import config

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/127.0.0.0 Safari/537.36",
]

VIEWPORTS = [(1366, 768), (1440, 900), (1920, 1080)]


class StealthSession:
    """One 'identity': a browser context bound to one proxy + fingerprint + cookie jar."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.request_count = 0

    async def start(self):
        self.playwright = await async_playwright().start()
        proxy = config.get_proxy()
        launch_args = {"headless": True, }
        #launch_args = {"headless": True, "channel": "chrome"}
        if proxy:
            launch_args["proxy"] = {"server": proxy}

        self.browser = await self.playwright.chromium.launch(**launch_args)
        width, height = random.choice(VIEWPORTS)
        self.context = await self.browser.new_context(
            user_agent=random.choice(USER_AGENTS),
            viewport={"width": width, "height": height},
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )
        self.page = await self.context.new_page()
        await stealth_async(self.page)
        return self.page

    async def human_pause(self):
        delay = random.uniform(config.MIN_DELAY, config.MAX_DELAY)
        await asyncio.sleep(delay)

    async def human_scroll(self):
        # Small randomized scrolls so the page doesn't get zero interaction before scraping.
        for _ in range(random.randint(2, 4)):
            await self.page.mouse.wheel(0, random.randint(300, 900))
            await asyncio.sleep(random.uniform(0.4, 1.2))

    def needs_rotation(self):
        return self.request_count >= config.REQUESTS_PER_IDENTITY

    async def close(self):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
