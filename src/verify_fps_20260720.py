# -*- coding: utf-8 -*-
"""实测 04 区块各图拖动 dataZoom 的流畅度：连续 15 次缩放操作的总耗时 + 视觉抽查。"""
import json
import sys
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4494"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.5)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://localhost:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4500)
    page.locator("#daily").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1500)

    charts = {
        "deferred": "#daily .chart-panel:nth-of-type(1) .echart",
        "domestic": "#daily .chart-panel:nth-of-type(2) .echart",
        "comex": "#daily .chart-panel:nth-of-type(3) .echart",
        "lbma": "#daily .chart-panel:nth-of-type(4) .echart",
    }
    report = {}
    for name, sel in charts.items():
        box = page.locator(sel).first.bounding_box()
        slider_y = box["y"] + box["height"] - 8 - 9
        plot_left = box["x"] + 72
        plot_w = box["width"] - 72 - 16
        # 连续 15 次"拖到最左（数据最多的历史段）"操作，测总耗时
        page.mouse.move(plot_left + plot_w * 0.6, slider_y)
        page.mouse.down()
        page.mouse.move(plot_left + plot_w * 0.02, slider_y, steps=8)
        page.mouse.up()
        page.wait_for_timeout(300)
        t0 = time.perf_counter()
        for i in range(15):
            # 小幅来回拖动滑块，模拟用户连续浏览
            x0 = plot_left + plot_w * (0.02 + i * 0.04)
            x1 = x0 + plot_w * 0.04
            page.mouse.move(x0, slider_y)
            page.mouse.down()
            page.mouse.move(x1, slider_y, steps=3)
            page.mouse.up()
        elapsed = time.perf_counter() - t0
        report[name] = {"ops": 15, "seconds": round(elapsed, 2), "ops_per_sec": round(15 / elapsed, 1)}
        page.locator(sel).first.screenshot(path=str(OUT / f"perf_{name}.png"))

    print(json.dumps(report, indent=2))
    print("page errors:", errors if errors else "none")
    browser.close()
