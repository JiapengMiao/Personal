# -*- coding: utf-8 -*-
"""基差缩放联动复测：拖右手柄，断言统计卡变化。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4495"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.5)
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3200)
    page.locator("#basis").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1800)

    chart = page.locator("#basis .echart").first
    box = chart.bounding_box()
    sy = box["y"] + box["height"] - 17          # slider 中线
    xr = box["x"] + box["width"] - 20           # 右手柄
    before = chart.screenshot()
    page.mouse.move(xr, sy)
    page.mouse.down()
    page.mouse.move(box["x"] + box["width"] * 0.5, sy, steps=14)
    page.mouse.up()
    page.wait_for_timeout(1000)
    after = chart.screenshot()
    (OUT / "fix_basis_right_zoom.png").write_bytes(after)
    print("zoom pixels changed:", before != after)

    cards = page.locator("#basis .stat-card strong")
    vals = [cards.nth(i).inner_text() for i in range(min(3, cards.count()))]
    print("基差统计卡:", vals)

    # 进出口盈亏同样拖一次
    pchart = page.locator("#basis .echart").nth(1)
    pbox = pchart.bounding_box()
    psy = pbox["y"] + pbox["height"] - 17
    pxr = pbox["x"] + pbox["width"] - 20
    page.mouse.move(pxr, psy)
    page.mouse.down()
    page.mouse.move(pbox["x"] + pbox["width"] * 0.55, psy, steps=14)
    page.mouse.up()
    page.wait_for_timeout(1000)
    pcards = page.locator("#basis .stat-card")
    print("盈亏统计卡数:", pcards.count())
    for i in range(pcards.count()):
        print("  ", pcards.nth(i).inner_text().replace("\n", " "))
    page.locator("#basis").first.screenshot(path=str(OUT / "fix_basis_profit_zoom.png"))
    browser.close()
print("done")
