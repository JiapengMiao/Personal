# -*- coding: utf-8 -*-
"""验证 2026-07-20 改动：03/04 整行布局、实线、高度、缩放后折线可见。"""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4494"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

def drag_zoom(page, chart_locator, frac_to=0.35):
    box = chart_locator.bounding_box()
    if not box:
        return
    slider_y = box["y"] + box["height"] - 8 - 9
    x0 = box["x"] + 80
    x1 = box["x"] + 80 + (box["width"] - 96) * frac_to
    page.mouse.move(x0, slider_y)
    page.mouse.down()
    page.mouse.move(x1, slider_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(1000)

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.5)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://localhost:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4000)

    report = {}

    # —— 03 市场脉搏：整行布局 + 高度 ——
    page.locator("#market").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1500)
    info = page.evaluate("""() => {
      const panels = [...document.querySelectorAll('#market .market-panel')];
      return panels.map(el => {
        const r = el.getBoundingClientRect();
        const chart = el.querySelector('.echart');
        return { width: Math.round(r.width), chartH: chart ? Math.round(chart.getBoundingClientRect().height) : 0 };
      });
    }""")
    report["market_panels"] = info
    page.locator("#market").first.screenshot(path=str(OUT / "v_market_full.png"))

    # —— 04 库存：整行布局、实线、缩放 ——
    page.locator("#daily").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1500)
    info4 = page.evaluate("""() => {
      const panels = [...document.querySelectorAll('#daily .chart-panel')];
      return panels.map(el => {
        const r = el.getBoundingClientRect();
        const chart = el.querySelector('.echart');
        return { title: el.querySelector('h3')?.textContent ?? '', width: Math.round(r.width), chartH: chart ? Math.round(chart.getBoundingClientRect().height) : 0 };
      });
    }""")
    report["daily_panels"] = info4
    page.locator("#daily").first.screenshot(path=str(OUT / "v_daily_full.png"))

    # 检查 COMEX 面板线型：直接遍历 canvas 上一条路径不行，改从 DOM 事件里拿实例。
    # echarts 把实例存在 dom 的 __ec_component__ 不可达；用官方 API 需要全局 echarts。
    # 项目用 echarts/core 局部引入，没有挂 window。退而求其次：检查 canvas 非空白 + 视觉截图。
    linetypes = "see-screenshot"
    report["comex_linetypes"] = linetypes

    # 缩放 COMEX 图 → 检查 canvas 像素仍有内容（折线未消失）
    comex_chart = page.locator("#daily .chart-panel", has_text="COMEX 库存").locator(".echart").first
    drag_zoom(page, comex_chart, 0.3)
    pixel_check = page.evaluate("""() => {
      const panels = [...document.querySelectorAll('#daily .chart-panel')];
      const comex = panels.find(el => el.querySelector('h3')?.textContent.includes('COMEX 库存'));
      const canvas = comex.querySelector('canvas');
      if (!canvas) return 'no-canvas';
      const ctx = canvas.getContext('2d');
      const d = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
      let painted = 0;
      for (let i = 3; i < d.length; i += 16) { if (d[i] > 0) painted++; }
      return { sampledPaintedPixels: painted, canvasW: canvas.width, canvasH: canvas.height };
    }""")
    report["comex_after_zoom"] = pixel_check
    page.screenshot(path=str(OUT / "v_comex_zoomed.png"), clip={"x": 0, "y": 0, "width": 1600, "height": 1100})

    # 缩放回全量
    drag_zoom(page, comex_chart, 1.0)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print("page errors:", errors if errors else "none")
    browser.close()
