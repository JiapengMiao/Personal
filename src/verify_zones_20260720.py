# -*- coding: utf-8 -*-
"""验证：04 各图多区间拖拽折线不消失 + 日期区间选择器功能。"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4494"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

CANVAS_PIXEL_JS = """(sel) => {
  const el = document.querySelector(sel);
  if (!el) return null;
  const canvas = el.querySelector('canvas');
  if (!canvas) return 'no-canvas';
  const ctx = canvas.getContext('2d');
  const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
  let painted = 0;
  for (let i = 3; i < d.length; i += 16) { if (d[i] > 0) painted++; }
  return painted;
}"""

def drag(page, sel, start_frac, end_frac):
    box = page.locator(sel).first.bounding_box()
    slider_y = box["y"] + box["height"] - 8 - 9
    plot_left = box["x"] + 72
    plot_w = box["width"] - 72 - 16
    x0 = plot_left + plot_w * start_frac
    x1 = plot_left + plot_w * end_frac
    page.mouse.move(x0, slider_y)
    page.mouse.down()
    page.mouse.move(x1, slider_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(900)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.5)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://localhost:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4500)
    page.locator("#daily").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1800)

    charts = {
        "deferred": "#daily .chart-panel:nth-of-type(1) .echart",
        "domestic": "#daily .chart-panel:nth-of-type(2) .echart",
        "comex": "#daily .chart-panel:nth-of-type(3) .echart",
        "lbma": "#daily .chart-panel:nth-of-type(4) .echart",
    }
    report = {}

    # 每个图：连续 4 个不同区间拖拽，检查折线像素不为零
    zones = [(0.0, 0.25), (0.3, 0.5), (0.6, 0.8), (0.85, 1.0)]
    for name, sel in charts.items():
        pixels = []
        for i, (a, b) in enumerate(zones):
            drag(page, sel, a, b)
            px = page.evaluate(CANVAS_PIXEL_JS, sel)
            pixels.append(px)
            if i == 1:
                page.locator(sel).first.screenshot(path=str(OUT / f"zone_{name}_{i}.png"))
        report[name] = pixels

    # 日期区间选择器测试：COMEX 图选 2024-01-01 ~ 2024-12-31
    comex_panel = page.locator("#daily .chart-panel", has_text="COMEX 库存")
    picker = comex_panel.locator(".range-picker")
    report["picker_visible"] = picker.count() > 0
    if picker.count():
        picker.locator("input").nth(0).fill("2024-01-01")
        picker.locator("input").nth(1).fill("2024-12-31")
        picker.locator("button").click()
        page.wait_for_timeout(1200)
        report["comex_after_picker"] = page.evaluate(CANVAS_PIXEL_JS, charts["comex"])
        comex_panel.screenshot(path=str(OUT / "picker_comex_2024.png"))

    print(json.dumps(report, indent=2))
    print("page errors:", errors if errors else "none")
    browser.close()
