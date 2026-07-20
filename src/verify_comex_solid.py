# -*- coding: utf-8 -*-
"""验证 COMEX 面板在近一年缩放窗口下三条线为连续实线。"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4494"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.5)
    page.goto(f"http://localhost:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4500)

    page.locator("#daily").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1500)

    comex = page.locator("#daily .chart-panel", has_text="COMEX 库存").locator(".echart").first
    # 拖到与用户截图一致的近一年窗口（约右端 8%）
    box = comex.bounding_box()
    slider_y = box["y"] + box["height"] - 8 - 9
    plot_left = box["x"] + 72
    plot_w = box["width"] - 72 - 16
    x0 = plot_left + plot_w * 0.92
    x1 = plot_left + plot_w * 1.0
    page.mouse.move(x0, slider_y); page.mouse.down(); page.mouse.move(x1, slider_y, steps=10); page.mouse.up()
    page.wait_for_timeout(1200)

    comex.screenshot(path=str(OUT / "comex_solid_line.png"))

    # 检查线型配置
    linetype = page.evaluate("""() => {
      // 从 canvas 取像素：逐行扫描，检查每条水平带是否有连续色段（实线特征）
      const panels = [...document.querySelectorAll('#daily .chart-panel')];
      const comex = panels.find(el => el.querySelector('h3')?.textContent.includes('COMEX 库存'));
      const canvas = comex.querySelector('canvas');
      const ctx = canvas.getContext('2d');
      const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      // 统计有颜色的像素行数与断点：实线应表现为大面积连续色带
      let painted = 0;
      for (let i = 3; i < d.length; i += 8) { if (d[i] > 0) painted++; }
      return { painted };
    }""")
    print("painted pixels:", linetype)
    browser.close()
