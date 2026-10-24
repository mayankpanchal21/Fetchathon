import os
import asyncio
import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

logger = logging.getLogger("agentos.executor.browser")


class BrowserAutomation:
    def __init__(self):
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._lock = asyncio.Lock()

    async def _ensure_page(self) -> Page:
        if self._page and not self._page.is_closed():
            return self._page

        if not self._playwright:
            self._playwright = await async_playwright().start()

        if not self._browser or not self._browser.is_connected():
            # Visible headful mode by default so user sees browser on Mac & Windows laptop
            headless_mode = os.getenv("BROWSER_HEADLESS", "false").strip().lower() in ("true", "1", "yes")
            self._browser = await self._playwright.chromium.launch(
                headless=headless_mode,
                args=["--no-sandbox", "--disable-setuid-sandbox"]
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="AgentOS-Desktop-Automation/1.0"
            )

        self._page = await self._context.new_page()
        return self._page

    def _validate_url(self, url: str) -> str:
        clean_url = url.strip()
        if not (clean_url.startswith("http://") or clean_url.startswith("https://")):
            clean_url = "https://" + clean_url
        return clean_url

    async def browser_open(self, url: Optional[str] = None) -> Dict[str, Any]:
        async with self._lock:
            page = await self._ensure_page()
            target_url = self._validate_url(url) if url else "about:blank"
            if url:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)

            title = await page.title()
            return {
                "action": "browser_open",
                "current_url": page.url,
                "title": title,
                "status": "success"
            }

    async def browser_navigate(self, url: str) -> Dict[str, Any]:
        if not url or not url.strip():
            raise ValueError("URL cannot be empty.")

        async with self._lock:
            page = await self._ensure_page()
            target_url = self._validate_url(url)
            logger.info(f"Navigating Playwright browser to: {target_url}")

            response = await page.goto(target_url, wait_until="domcontentloaded", timeout=30000)
            status_code = response.status if response else 200
            title = await page.title()

            return {
                "action": "browser_navigate",
                "requested_url": url,
                "resolved_url": page.url,
                "title": title,
                "status_code": status_code,
                "verified": bool(response and response.ok)
            }

    async def browser_get_page_content(self, max_chars: int = 4000) -> Dict[str, Any]:
        async with self._lock:
            page = await self._ensure_page()
            title = await page.title()
            # Extract main visible text content without script tags
            text_content = await page.evaluate("""() => {
                const scripts = document.querySelectorAll('script, style, noscript');
                scripts.forEach(s => s.remove());
                return document.body ? document.body.innerText : '';
            }""")

            clean_text = " ".join(text_content.split())
            truncated = clean_text[:max_chars]

            return {
                "action": "browser_get_page_content",
                "url": page.url,
                "title": title,
                "character_count": len(clean_text),
                "text_sample": truncated
            }

    async def close(self):
        async with self._lock:
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None


browser_manager = BrowserAutomation()
