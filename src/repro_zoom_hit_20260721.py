# -*- coding: utf-8 -*-
"""复现并量化 html zoom 1.25 下 ECharts 鼠标命中偏移:
1) 悬停 tooltip 显示日期 vs 鼠标位置应有日期（convertFromPixel 期望值）
2) tooltip 视觉位置 vs 鼠标位置
3) dataZoom 滑块拖动是否跟随
A/B: 同一脚本内在 zoom=1.25 与 zoom=1.0 下各测一轮。
"""
import json
import re
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "5199"
CHART_SEL = "#market .echart"

HOVER_JS = """([sel, f]) => {
  const el = document.querySelector(sel);
  const inst = window.__echarts.getInstanceByDom(el);
  const rect = el.getBoundingClientRect();
  const px = rect.width * f;
  const opt = inst.getOption();
  const dates = opt.xAxis && opt.xAxis[0] && opt.xAxis[0].data;
  const expect = inst.convertFromPixel({xAxisIndex: 0}, px);
  const tip = document.querySelector('.echarts-tooltip');
  const trect = tip ? tip.getBoundingClientRect() : null;
  return {
    expectIdx: expect,
    expectDate: dates ? dates[Math.max(0, Math.min(dates.length-1, Math.round(expect)))] : null,
    tipText: tip ? tip.textContent.slice(0, 120) : null,
    tipCenterX: trect ? trect.left + trect.width / 2 : null,
    visible: tip ? getComputedStyle(tip).visibility : 'none',
    htmlZoom: getComputedStyle(document.documentElement).zoom,
    rectW: rect.width,
    clientW: el.clientWidth,
    zrW: inst.getWidth(),
  };
}"""

DZ_JS = """(sel) => {
  const inst = window.__echarts.getInstanceByDom(document.querySelector(sel));
  const dz = inst.getOption().dataZoom[0];
  return {start: dz.start, end: dz.end};
}"""


def hover_tests(page):
    out = []
    box = page.locator(CHART_SEL).first.bounding_box()
    for f in (0.25, 0.5, 0.75):
        cx = box["x"] + box["width"] * f
        cy = box["y"] + box["height"] * 0.45
        page.mouse.move(cx, cy)
        page.wait_for_timeout(500)
        r = page.evaluate(HOVER_JS, [CHART_SEL, f])
        m = re.search(r"\d{4}-\d{2}-\d{2}", r.get("tipText") or "")
        r["tipDate"] = m.group(0) if m else None
        r["f"] = f
        r["mouseX"] = round(cx, 1)
        out.append(r)
    return out


def drag_test(page):
    before = page.evaluate(DZ_JS, CHART_SEL)
    box = page.locator(CHART_SEL).first.bounding_box()
    y = box["y"] + box["height"] - 12
    x0 = box["x"] + box["width"] * 0.5
    x1 = x0 + box["width"] * 0.2
    page.mouse.move(x0, y)
    page.mouse.down()
    page.mouse.move(x1, y, steps=15)
    page.mouse.up()
    page.wait_for_timeout(700)
    after = page.evaluate(DZ_JS, CHART_SEL)
    return {"before": before, "after": after}


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.0)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4000)
    page.locator("#market").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1500)

    print("===== A. zoom=1.25（当前线上状态）=====")
    for r in hover_tests(page):
        print(json.dumps(r, ensure_ascii=False))
    print("drag:", json.dumps(drag_test(page), ensure_ascii=False))

    print("===== B. zoom=1.0（运行时临时改小，对照组）=====")
    page.evaluate("""() => {
      document.documentElement.style.zoom = '1';
      // 让所有图表按新布局 resize
      document.querySelectorAll('.echart').forEach(el => {
        const inst = window.__echarts.getInstanceByDom(el);
        if (inst) inst.resize();
      });
    }""")
    page.wait_for_timeout(1200)
    page.locator("#market").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(800)
    for r in hover_tests(page):
        print(json.dumps(r, ensure_ascii=False))
    print("drag:", json.dumps(drag_test(page), ensure_ascii=False))

    print("pageerrors:", errors[:3] if errors else "无")
    browser.close()
