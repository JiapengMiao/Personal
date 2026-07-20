import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1520, "height": 950})
        await page.goto("http://127.0.0.1:7100/", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(4000)
        
        out = r"C:\Users\56558\.codex\visualizations\2026\07\20\019f7d1a-b7a2-72e0-a561-61f761a1c423"
        
        # 1. Hero
        await page.screenshot(path=f"{out}/v3_hero.png")
        
        # 2. Market section (should only have Price + Fund)
        await page.evaluate("document.getElementById('market')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{out}/v3_market.png")
        
        # 3. Daily section (deferred + domestic + overseas)
        await page.evaluate("document.getElementById('daily')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{out}/v3_daily.png")
        
        # 4. Scroll down a bit more to see overseas panels in daily
        await page.evaluate("window.scrollBy(0, 500)")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=f"{out}/v3_daily2.png")
        
        # 5. Positions section
        await page.evaluate("document.getElementById('positions')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=f"{out}/v3_positions.png")
        
        await browser.close()
        print("OK - 5 screenshots")

asyncio.run(main())
