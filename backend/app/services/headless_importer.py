from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import urlparse

from app.config import settings

logger = logging.getLogger("replyweave.importer")


class HeadlessImporter:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._playwright = None
        self._browser = None

    async def _ensure_started(self) -> None:
        async with self._lock:
            if self._browser is not None:
                try:
                    await self._browser.version()
                    return
                except Exception:
                    logger.warning("Browser appears unhealthy, restarting")
                    self._browser = None
                    self._playwright = None
            try:
                from playwright.async_api import async_playwright
            except ImportError as exc:
                raise RuntimeError(
                    "Playwright is not installed. Install with `uv sync --extra scraping`."
                ) from exc
            self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(headless=True)

    async def close(self) -> None:
        async with self._lock:
            if self._browser is not None:
                await self._browser.close()
            if self._playwright is not None:
                await self._playwright.stop()
            self._browser = None
            self._playwright = None

    async def fetch_payload(self, url: str) -> dict[str, Any]:
        await self._ensure_started()
        assert self._browser is not None
        context = await self._browser.new_context(
            user_agent=settings.importer_user_agent,
            viewport={"width": 1280, "height": 800},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = await context.new_page()
        claude_payloads: list[dict[str, Any]] = []
        claude_snapshot: dict[str, Any] | None = None

        async def handle_claude_response(response: Any) -> None:
            if not self._is_claude(url):
                return
            url_lower = response.url.lower()
            if ("claude.ai/api" in url_lower or "anthropic.com/api" in url_lower) and response.status == 200:
                try:
                    payload = await response.json()
                except Exception:
                    return
                if "chat_snapshots" in url_lower:
                    if isinstance(payload, dict):
                    nonlocal claude_snapshot
                    claude_snapshot = payload
                elif not claude_payloads:
                    if isinstance(payload, dict):
                claude_payloads.append(payload)

        page.on("response", handle_claude_response)
        try:
            await page.add_init_script(
                "Object.defineProperty(navigator, 'webdriver', { get: () => undefined });"
            )
            response = await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=settings.importer_timeout_seconds * 1000,
            )
            if response is None:
                logger.warning("No response returned for url=%s", url)
            elif response.status >= 400:
                raise ValueError(f"Upstream returned HTTP {response.status}")

            if self._is_claude(url):
                await page.wait_for_timeout(3000)
                if claude_snapshot is not None:
                    logger.info("Imported payload source=claude-snapshot")
                    return {"source": "claude-snapshot", "payload": claude_snapshot}
                if claude_payloads:
                    logger.info("Imported payload source=claude-api")
                    return {"source": "claude-api", "payload": claude_payloads[0]}
                claude_payload = await self._fetch_claude_dom(page)
                logger.info("Imported payload source=dom")
                return claude_payload

            chatgpt_payload = await self._fetch_chatgpt_dom(page)
            logger.info("Imported payload source=dom")
            return chatgpt_payload
        finally:
            await page.close()
            await context.close()

    def _is_claude(self, url: str) -> bool:
        parsed = urlparse(url)
        return "claude.ai" in parsed.netloc

    async def _fetch_claude_dom(self, page: Any) -> dict[str, Any]:
        selectors = [
            "[data-testid='message']",
            "[data-message-author-role]",
            "[data-message-role]",
            ".font-claude-message",
        ]
        selector_list = ", ".join(selectors)
        try:
            await page.wait_for_selector(selector_list, timeout=15000)
        except Exception as exc:
            title = await page.title()
            html = await page.content()
            logger.warning("Claude debug title=%s", title)
            logger.warning("Claude debug html_snippet=%s", html[:2000])
            raise ValueError("Claude conversation elements never appeared in DOM") from exc
        messages = await page.evaluate(
            """
            (selectors) => {
                const selectorList = selectors.join(', ');
                const els = document.querySelectorAll(selectorList);
                const items = Array.from(els).map((el, i) => ({
                    role: el.getAttribute('data-message-author-role')
                        || el.getAttribute('data-message-role')
                        || (i % 2 === 0 ? 'user' : 'assistant'),
                    content: (el.innerText || '').trim()
                })).filter(item => item.content && item.content.length > 0);
                return items;
            }
            """,
            selectors,
        )
        if not messages:
            raise ValueError("No messages found in Claude DOM")
        return {"source": "dom", "payload": {"messages": messages}}

    async def _fetch_chatgpt_dom(self, page: Any) -> dict[str, Any]:
        selectors = [
            "div[data-message-author-role]",
            "article[data-message-author-role]",
            "div[data-message-id]",
        ]
        selector_list = ", ".join(selectors)
        try:
            await page.wait_for_selector(selector_list, timeout=15000)
        except Exception as exc:
            raise ValueError("Conversation messages never appeared in DOM") from exc
        count = await page.locator(selector_list).count()
        logger.info("Found %d message nodes in DOM", count)
        messages = await page.evaluate(
            """
            (selectors) => {
                const selectorList = selectors.join(', ');
                const nodes = document.querySelectorAll(selectorList);
                return Array.from(nodes).map((el, i) => ({
                    role: el.getAttribute('data-message-author-role') || 'unknown',
                    content: (el.innerText || '').trim(),
                    position: i
                })).filter(item => item.content && item.content.length > 0);
            }
            """,
            selectors,
        )
        if not messages:
            raise ValueError("No messages found in DOM")
        title = await page.title()
        return {"source": "dom", "payload": {"title": title, "messages": messages}}


headless_importer = HeadlessImporter()
