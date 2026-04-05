"""
BrowserTool — Playwright-based browser automation for OpenClaw agents.
Uses the sync API so it integrates cleanly with the synchronous agent loop.
"""
from __future__ import annotations

import os
from typing import Any

try:
    from playwright.sync_api import sync_playwright, Browser, Page, Playwright
    _PLAYWRIGHT_AVAILABLE = True
except ImportError:
    _PLAYWRIGHT_AVAILABLE = False

# ── Anthropic tool schema ─────────────────────────────────────────────────────

BROWSER_TOOL_SCHEMA = {
    "name": "browser_action",
    "description": (
        "Control a real Chrome browser to navigate websites, fill forms, "
        "click buttons, create accounts, and take any web action."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": [
                    "navigate",
                    "click",
                    "type",
                    "get_page_text",
                    "get_page_url",
                    "screenshot",
                    "scroll",
                    "wait_for",
                    "select_option",
                    "press_key",
                    "get_links",
                    "find_element",
                ],
                "description": "The browser action to perform",
            },
            "url": {
                "type": "string",
                "description": "URL to navigate to (for navigate action)",
            },
            "selector": {
                "type": "string",
                "description": "CSS selector or element text to target",
            },
            "text": {
                "type": "string",
                "description": "Text to type or search for",
            },
            "direction": {
                "type": "string",
                "enum": ["up", "down"],
                "description": "Scroll direction",
            },
            "key": {
                "type": "string",
                "description": "Key to press (Enter, Tab, Escape, etc.)",
            },
            "value": {
                "type": "string",
                "description": "Value to select in dropdown",
            },
            "timeout": {
                "type": "number",
                "description": "Timeout in seconds for wait_for",
            },
        },
        "required": ["action"],
    },
}

# ── BrowserTool ───────────────────────────────────────────────────────────────

_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

_DEFAULT_TIMEOUT_MS = 10_000  # 10 seconds


class BrowserTool:
    """
    Persistent browser session powered by Playwright (sync).

    Usage:
        browser = BrowserTool()
        result = browser.execute("navigate", url="https://example.com")
        browser.close()
    """

    def __init__(self, headless: bool = False) -> None:
        self._headless = headless
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def _ensure_page(self) -> Page:
        """Lazily start the browser and return the active page."""
        if self._playwright is None:
            self._playwright = sync_playwright().start()

        if self._browser is None or not self._browser.is_connected():
            self._browser = self._playwright.chromium.launch(
                headless=self._headless,
                args=["--no-sandbox", "--disable-dev-shm-usage"],
            )

        if self._page is None or self._page.is_closed():
            context = self._browser.new_context(user_agent=_USER_AGENT)
            self._page = context.new_page()
            self._page.set_default_timeout(_DEFAULT_TIMEOUT_MS)

        return self._page

    def close(self) -> None:
        """Shut down the browser and Playwright runtime."""
        try:
            if self._page and not self._page.is_closed():
                self._page.close()
        except Exception:
            pass
        try:
            if self._browser and self._browser.is_connected():
                self._browser.close()
        except Exception:
            pass
        try:
            if self._playwright:
                self._playwright.stop()
        except Exception:
            pass
        self._page = None
        self._browser = None
        self._playwright = None

    # ── Dispatch ──────────────────────────────────────────────────────────────

    def execute(self, action: str, **kwargs: Any) -> str:
        """Dispatch to the correct action method.  Always returns a string."""
        dispatch = {
            "navigate": self._navigate,
            "click": self._click,
            "type": self._type,
            "get_page_text": self._get_page_text,
            "get_page_url": self._get_page_url,
            "screenshot": self._screenshot,
            "scroll": self._scroll,
            "wait_for": self._wait_for,
            "select_option": self._select_option,
            "press_key": self._press_key,
            "get_links": self._get_links,
            "find_element": self._find_element,
        }
        handler = dispatch.get(action)
        if handler is None:
            return f"Error: unknown action '{action}'"
        try:
            return handler(**kwargs)
        except Exception as exc:  # noqa: BLE001
            return f"Error in browser action '{action}': {exc}"

    # ── Action implementations ────────────────────────────────────────────────

    def _navigate(self, url: str = "", **_: Any) -> str:
        if not url:
            return "Error: url is required for navigate"
        page = self._ensure_page()
        page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        return f"Navigated to: {page.url}\nTitle: {page.title()}"

    def _click(self, selector: str = "", text: str = "", **_: Any) -> str:
        page = self._ensure_page()
        target = selector or text
        if not target:
            return "Error: selector or text is required for click"

        # Try CSS selector first; fall back to visible text matching.
        try:
            page.click(target, timeout=_DEFAULT_TIMEOUT_MS)
            return f"Clicked element: {target}"
        except Exception:
            pass

        try:
            page.get_by_text(target, exact=False).first.click(timeout=_DEFAULT_TIMEOUT_MS)
            return f"Clicked element with text: {target}"
        except Exception as exc:
            return f"Error: could not click '{target}': {exc}"

    def _type(self, selector: str = "", text: str = "", **_: Any) -> str:
        if not selector:
            return "Error: selector is required for type"
        page = self._ensure_page()
        page.fill(selector, text, timeout=_DEFAULT_TIMEOUT_MS)
        return f"Typed into {selector}: {text!r}"

    def _get_page_text(self, **_: Any) -> str:
        page = self._ensure_page()
        raw = page.inner_text("body")
        truncated = raw[:3000]
        if len(raw) > 3000:
            truncated += "\n... [truncated]"
        return truncated

    def _get_page_url(self, **_: Any) -> str:
        page = self._ensure_page()
        return page.url

    def _screenshot(self, **_: Any) -> str:
        page = self._ensure_page()
        path = "/tmp/openclaw_screen.png"
        page.screenshot(path=path, full_page=False)
        return path

    def _scroll(self, direction: str = "down", **_: Any) -> str:
        page = self._ensure_page()
        if direction == "down":
            page.evaluate("window.scrollBy(0, 600)")
        else:
            page.evaluate("window.scrollBy(0, -600)")
        return f"Scrolled {direction}"

    def _wait_for(self, selector: str = "", timeout: float = 10, **_: Any) -> str:
        if not selector:
            return "Error: selector is required for wait_for"
        page = self._ensure_page()
        timeout_ms = int(timeout * 1000)
        page.wait_for_selector(selector, timeout=timeout_ms)
        return f"Element appeared: {selector}"

    def _select_option(self, selector: str = "", value: str = "", **_: Any) -> str:
        if not selector:
            return "Error: selector is required for select_option"
        page = self._ensure_page()
        page.select_option(selector, value=value, timeout=_DEFAULT_TIMEOUT_MS)
        return f"Selected '{value}' in {selector}"

    def _press_key(self, key: str = "", selector: str = "", **_: Any) -> str:
        if not key:
            return "Error: key is required for press_key"
        page = self._ensure_page()
        if selector:
            page.press(selector, key, timeout=_DEFAULT_TIMEOUT_MS)
        else:
            page.keyboard.press(key)
        return f"Pressed key: {key}"

    def _get_links(self, **_: Any) -> str:
        page = self._ensure_page()
        links = page.eval_on_selector_all(
            "a[href]",
            "els => els.map(el => ({ text: el.innerText.trim(), href: el.href }))"
        )
        if not links:
            return "No links found on page."
        lines = [f"- {lnk['text'] or '(no text)'}: {lnk['href']}" for lnk in links[:100]]
        result = "\n".join(lines)
        if len(links) > 100:
            result += f"\n... and {len(links) - 100} more links"
        return result

    def _find_element(self, text: str = "", selector: str = "", **_: Any) -> str:
        page = self._ensure_page()
        target = text or selector
        if not target:
            return "Error: text or selector is required for find_element"

        # Try text search in body first.
        body_text = page.inner_text("body")
        if text and text.lower() in body_text.lower():
            return "True"

        # Try CSS selector.
        if selector:
            try:
                el = page.query_selector(selector)
                return "True" if el is not None else "False"
            except Exception:
                return "False"

        return "False"
