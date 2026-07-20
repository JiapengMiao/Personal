import asyncio, sys
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        page = await browser.new_page(viewport={"width": 1520, "height": 950})
        await page.goto("http://127.0.0.1:7100/", wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(2500)
        out = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\output\verify\preview_top.png"
        await page.screenshot(path=out)
        # scroll to middle sections
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.35)")
        await page.wait_for_timeout(1500)
        out2 = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\output\verify\preview_mid.png"
        await page.screenshot(path=out2)
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.7)")
        await page.wait_for_timeout(1500)
        out3 = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\output\verify\preview_bottom.png"
        await page.screenshot(path=out3)
        await browser.close()
        print("OK")

asyncio.run(main())
