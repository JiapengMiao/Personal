# -*- coding: utf-8 -*-
"""第二轮验证：五项修复的截图+交互断言。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4494"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

def drag_left_handle(page, chart_div, frac_to=0.4):
    box = chart_div.bounding_box()
    slider_y = box["y"] + box["height"] - 8 - 9
    x0 = box["x"] + 72 + 4
    x1 = box["x"] + 72 + (box["width"] - 72 - 16) * frac_to
    page.mouse.move(x0, slider_y)
    page.mouse.down()
    page.mouse.move(x1, slider_y, steps=10)
    page.mouse.up()
    page.wait_for_timeout(900)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.5)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3500)

    # 1. Hero 国内库存构成
    hero_text = page.locator("main").first.inner_text()
    print("hero has 2,038:", "2,038" in hero_text)
    print("hero has 构成小字:", "起沿用" in hero_text or "990.039" in hero_text)
    page.screenshot(path=str(OUT / "fix_hero.png"), clip={"x": 0, "y": 0, "width": 1600, "height": 700})

    # 2. StocksPanel 重排（市场脉搏区）
    page.locator("#market").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1200)
    mkt_text = page.locator("#market").first.inner_text()
    print("market has 国内/海外:", ("国内" in mkt_text and "海外" in mkt_text), "| no 上金所白银库存（周频）:", "周频" not in mkt_text)
    page.locator("#market").first.screenshot(path=str(OUT / "fix_market.png"))

    # 3. 递延费色带图 + tooltip
    page.locator("#daily").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1200)
    deferred = page.locator("#daily .echart").first
    page.screenshot(path=str(OUT / "fix_deferred.png"))
    dbox = deferred.bounding_box()
    page.mouse.move(dbox["x"] + dbox["width"] * 0.45, dbox["y"] + 90)
    page.wait_for_timeout(800)
    page.screenshot(path=str(OUT / "fix_deferred_tooltip.png"))
    tip_text = page.locator("body").inner_text()
    print("deferred tooltip ok (无 undefined):", "undefined" not in tip_text)

    # 4. 持仓/虚实比 3 合约
    page.locator("#positions").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1200)
    pos_text = page.locator("#positions").first.inner_text()
    print("positions even contracts:", ("ag2608" in pos_text and "ag2610" in pos_text and "ag2612" in pos_text), "| no odd:", ("ag2607" not in pos_text and "ag2609" not in pos_text and "ag2611" not in pos_text))
    page.locator("#positions").first.screenshot(path=str(OUT / "fix_positions.png"))

    # 5. 基差缩放联动统计卡
    page.locator("#basis").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1800)
    cards = page.locator("#basis .stat-card strong")
    mean_before = cards.nth(1).inner_text()
    pct_before = cards.nth(2).inner_text()
    basis_chart = page.locator("#basis .echart").first
    drag_left_handle(page, basis_chart, 0.45)
    mean_after = cards.nth(1).inner_text()
    pct_after = cards.nth(2).inner_text()
    print(f"basis 区间均值: {mean_before} -> {mean_after} | 百分位: {pct_before} -> {pct_after}")
    print("basis stats linked:", mean_before != mean_after or pct_before != pct_after)
    page.locator("#basis").first.screenshot(path=str(OUT / "fix_basis_zoomed.png"))

    print("pageerrors:", errors[:5])
    browser.close()
print("done")
