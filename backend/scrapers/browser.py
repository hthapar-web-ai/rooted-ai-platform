import asyncio
from playwright.async_api import async_playwright

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36 RootedBot/1.0"

async def _fetch_dynamic(url: str, wait_selector: str | None = None, timeout_ms: int = 20000) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            ctx = await browser.new_context(user_agent=UA, viewport={"width":1280,"height":1200})
            page = await ctx.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
            if wait_selector:
                try:
                    await page.wait_for_selector(wait_selector, timeout=timeout_ms)
                except:
                    pass
            await page.wait_for_timeout(1200)
            html = await page.content()
            await ctx.close()
            return html
        finally:
            await browser.close()

def fetch_dynamic(url: str, wait_selector: str | None = None, timeout_ms: int = 20000) -> str:
    return asyncio.run(_fetch_dynamic(url, wait_selector, timeout_ms))
