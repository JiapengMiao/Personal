# -*- coding: utf-8 -*-
"""回归验证：拖动时间轴后折线不消失（去 LTTB + 默认缩放起点）。"""
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

def drag(page, chart_sel, start_frac, end_frac):
    box = page.locator(chart_sel).first.bounding_box()
    if not box:
        return
    slider_y = box["y"] + box["height"] - 8 - 9
    plot_left = box["x"] + 72
    plot_w = box["width"] - 72 - 16
    x0 = plot_left + plot_w * start_frac
    x1 = plot_left + plot_w * end_frac
    page.mouse.move(x0, slider_y)
    page.mouse.down()
    page.mouse.move(x1, slider_y, steps=14)
    page.mouse.up()
    page.wait_for_timeout(1100)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.5)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://localhost:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4500)

    report = {}
    charts = {
        "deferred": "#daily .chart-panel:nth-of-type(1) .echart",
        "domestic": "#daily .chart-panel:nth-of-type(2) .echart",
        "comex": "#daily .chart-panel:nth-of-type(3) .echart",
        "lbma": "#daily .chart-panel:nth-of-type(4) .echart",
    }

    page.locator("#daily").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1800)

    # 初始状态像素
    for name, sel in charts.items():
        report[f"{name}_initial"] = page.evaluate(CANVAS_PIXEL_JS, sel)

    # 对每个图做三轮拖拽：缩到中段、缩到尾部小窗口、拉回大窗口
    for name, sel in charts.items():
        drag(page, sel, 0.0, 0.55)          # 缩到 0-55%
        report[f"{name}_zoom_mid"] = page.evaluate(CANVAS_PIXEL_JS, sel)
        page.locator(sel).first.screenshot(path=str(OUT / f"drag_{name}_mid.png"))
        drag(page, sel, 0.55, 0.85)         # 再拖到 55-85%
        report[f"{name}_zoom_late"] = page.evaluate(CANVAS_PIXEL_JS, sel)
        page.locator(sel).first.screenshot(path=str(OUT / f"drag_{name}_late.png"))
        drag(page, sel, 0.0, 1.0)           # 拉回全量
        report[f"{name}_zoom_full"] = page.evaluate(CANVAS_PIXEL_JS, sel)

    # 05 布局检查
    page.locator("#positions").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1200)
    report["positions_widths"] = page.evaluate("""() => [...document.querySelectorAll('#positions .chart-panel')].map(el => Math.round(el.getBoundingClientRect().width))""")
    page.locator("#positions").first.screenshot(path=str(OUT / "drag_positions.png"))

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("page errors:", errors if errors else "none")
    browser.close()
