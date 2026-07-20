import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1520, "height": 950})
        await page.goto("http://127.0.0.1:7100/", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(4000)
        
        # Screenshot 1: Hero section (top)
        await page.screenshot(path=r"C:\Users\56558\.codex\visualizations\2026\07\20\019f7d1a-b7a2-72e0-a561-61f761a1c423\v2_hero.png")
        
        # Screenshot 2: Scroll to daily section (deferred + domestic inventory with dataZoom)
        await page.evaluate("document.getElementById('daily')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=r"C:\Users\56558\.codex\visualizations\2026\07\20\019f7d1a-b7a2-72e0-a561-61f761a1c423\v2_daily.png")
        
        # Screenshot 3: Scroll to positions section
        await page.evaluate("document.getElementById('positions')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=r"C:\Users\56558\.codex\visualizations\2026\07\20\019f7d1a-b7a2-72e0-a561-61f761a1c423\v2_positions.png")
        
        # Screenshot 4: Scroll to market section
        await page.evaluate("document.getElementById('market')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=r"C:\Users\56558\.codex\visualizations\2026\07\20\019f7d1a-b7a2-72e0-a561-61f761a1c423\v2_market.png")
        
        # Screenshot 5: Scroll to basis section
        await page.evaluate("document.getElementById('basis')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=r"C:\Users\56558\.codex\visualizations\2026\07\20\019f7d1a-b7a2-72e0-a561-61f761a1c423\v2_basis.png")
        
        # Screenshot 6: Scroll to seasonality
        await page.evaluate("document.getElementById('season')?.scrollIntoView({behavior:'instant'})")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=r"C:\Users\56558\.codex\visualizations\2026\07\20\019f7d1a-b7a2-72e0-a561-61f761a1c423\v2_season.png")
        
        await browser.close()
        print("OK - 6 screenshots taken")

asyncio.run(main())
