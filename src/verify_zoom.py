# -*- coding: utf-8 -*-
"""实证：递延费 dataZoom 是否失效 + 基差缩放后统计卡是否联动。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4493"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

def drag_slider(page, chart_div, frac_from=0.0, frac_to=0.35):
    """拖动图表左滑块手柄：从 frac_from 位置拖到 frac_to。返回 (before_png_bytes, after_png_bytes)"""
    box = chart_div.bounding_box()
    h = box["height"]
    slider_y = box["y"] + h - 8 - 9  # bottom:8 height:18 的中线
    x0 = box["x"] + 72 + (box["width"] - 72 - 16) * frac_from + 4
    x1 = box["x"] + 72 + (box["width"] - 72 - 16) * frac_to
    before = chart_div.screenshot()
    page.mouse.move(x0, slider_y)
    page.mouse.down()
    page.mouse.move(x1, slider_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(900)
    after = chart_div.screenshot()
    return before, after

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=1)
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3200)

    # —— 递延费图 ——
    page.locator("#daily").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1000)
    deferred = page.locator("#daily .echart").first
    b, a = drag_slider(page, deferred)
    (OUT / "zoom_deferred_before.png").write_bytes(b)
    (OUT / "zoom_deferred_after.png").write_bytes(a)
    print("deferred zoom changed pixels:", b != a)

    # —— 国内库存图（对照组，MultiLineChart）——
    domestic = page.locator("#daily .echart").nth(1)
    b2, a2 = drag_slider(page, domestic)
    print("domestic zoom changed pixels:", b2 != a2)

    # —— 基差图 + 统计卡 ——
    page.locator("#basis").first.scroll_into_view_if_needed(timeout=8000)
    page.wait_for_timeout(1500)
    mean_before = page.locator("#basis .stat-card strong").nth(1).inner_text()
    basis_chart = page.locator("#basis .echart").first
    b3, a3 = drag_slider(page, basis_chart)
    (OUT / "zoom_basis_after.png").write_bytes(a3)
    page.wait_for_timeout(400)
    mean_after = page.locator("#basis .stat-card strong").nth(1).inner_text()
    print("basis zoom changed pixels:", b3 != a3)
    print("basis 区间均值 before:", mean_before, " after:", mean_after)

    # —— 递延费 tooltip ——
    page.locator("#daily").first.scroll_into_view_if_needed(timeout=5000)
    page.wait_for_timeout(600)
    dbox = deferred.bounding_box()
    page.mouse.move(dbox["x"] + dbox["width"] * 0.5, dbox["y"] + 100)
    page.wait_for_timeout(700)
    tip = page.locator(".echart .tooltip, body > div[class*='tooltip']").last
    page.screenshot(path=str(OUT / "zoom_deferred_tooltip.png"))
    browser.close()
print("done")
