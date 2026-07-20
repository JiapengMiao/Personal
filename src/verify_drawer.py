# -*- coding: utf-8 -*-
"""抽屉交互补验：点击指标行打开详情抽屉并截图。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4492"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3000)
    page.locator("#indicators").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1000)
    rows = page.locator("#indicators .table-row")
    print("table rows:", rows.count())
    assert rows.count() > 0
    rows.nth(0).click()
    page.wait_for_timeout(2200)
    page.screenshot(path=str(OUT / "act_drawer.png"))
    drawer = page.locator(".detail-drawer")
    print("drawer visible:", drawer.count() > 0 and drawer.first.is_visible())
    # 键盘右箭头切换下一个指标
    page.keyboard.press("ArrowRight")
    page.wait_for_timeout(1200)
    page.screenshot(path=str(OUT / "act_drawer_next.png"))
    # Esc 关闭
    page.keyboard.press("Escape")
    page.wait_for_timeout(600)
    print("drawer after esc:", drawer.count() == 0 or not drawer.first.is_visible())
    print("pageerrors:", errors)
    browser.close()
print("done")
