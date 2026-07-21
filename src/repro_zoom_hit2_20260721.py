# -*- coding: utf-8 -*-
"""第二轮:精确测定 zoom 1.25 下鼠标→图表坐标的真实映射。
- 注入监听器记录真实 clientX / rect.left / zr 宽
- 悬停读"可见" tooltip 的日期,与期望日期对比得出偏移比率
- dataZoom 先设小窗口,再测滑块窗口拖动是否跟随
"""
import json
import re
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "5199"
CHART_SEL = "#market .echart"

INJECT = """(sel) => {
  const el = document.querySelector(sel);
  window.__probe = [];
  el.addEventListener('mousemove', (e) => {
    const r = el.getBoundingClientRect();
    const inst = window.__echarts.getInstanceByDom(el);
    window.__probe.push({
      clientX: e.clientX, rectLeft: r.left, rectW: r.width,
      zrW: inst.getWidth(), clientW: el.clientWidth,
    });
    if (window.__probe.length > 50) window.__probe.shift();
  }, {passive: true});
  return true;
}"""

HOVER_JS = """([sel, f]) => {
  const el = document.querySelector(sel);
  const inst = window.__echarts.getInstanceByDom(el);
  const rect = el.getBoundingClientRect();
  const opt = inst.getOption();
  const dates = opt.xAxis && opt.xAxis[0] && opt.xAxis[0].data;
  const expect = inst.convertFromPixel({xAxisIndex: 0}, inst.getWidth() * f);
  const tips = [...document.querySelectorAll('.echarts-tooltip')]
    .filter(t => getComputedStyle(t).visibility === 'visible');
  const tip = tips[0] || null;
  const probe = (window.__probe || []).slice(-1)[0] || null;
  return {
    f,
    expectIdx: expect,
    expectDate: dates ? dates[Math.max(0, Math.min(dates.length-1, Math.round(expect)))] : null,
    tipText: tip ? tip.textContent.slice(0, 120) : null,
    probe,
    zrW: inst.getWidth(),
    rectW: rect.width,
  };
}"""

DZ_JS = """(sel) => {
  const inst = window.__echarts.getInstanceByDom(document.querySelector(sel));
  const dz = inst.getOption().dataZoom[0];
  return {start: dz.start, end: dz.end, startValue: dz.startValue, endValue: dz.endValue};
}"""

SET_WINDOW_JS = """(sel) => {
  const inst = window.__echarts.getInstanceByDom(document.querySelector(sel));
  const opt = inst.getOption();
  const dates = opt.xAxis[0].data;
  const n = dates.length;
  inst.dispatchAction({type: 'dataZoom', startValue: dates[Math.floor(n*0.4)], endValue: dates[Math.floor(n*0.7)]});
  return {n, s: dates[Math.floor(n*0.4)], e: dates[Math.floor(n*0.7)]};
}"""


def hover_tests(page, tag):
    box = page.locator(CHART_SEL).first.bounding_box()
    for f in (0.3, 0.5, 0.7):
        cx = box["x"] + box["width"] * f
        cy = box["y"] + box["height"] * 0.45
        page.mouse.move(cx - 30, cy)
        page.mouse.move(cx, cy, steps=4)
        page.wait_for_timeout(600)
        r = page.evaluate(HOVER_JS, [CHART_SEL, f])
        m = re.search(r"\d{4}-\d{2}-\d{2}", r.get("tipText") or "")
        r["tipDate"] = m.group(0) if m else None
        print(f"[{tag}] " + json.dumps(r, ensure_ascii=False))


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.0)
    page.on("pageerror", lambda e: print("PAGEERROR:", e))
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4000)
    page.locator("#market").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1500)

    page.evaluate(INJECT, CHART_SEL)
    print("===== 悬停映射测定 (zoom=1.25) =====")
    hover_tests(page, "hover")

    print("===== dataZoom 窗口拖动测定 =====")
    w = page.evaluate(SET_WINDOW_JS, CHART_SEL)
    print("预设窗口:", json.dumps(w, ensure_ascii=False))
    page.wait_for_timeout(800)
    before = page.evaluate(DZ_JS, CHART_SEL)
    box = page.locator(CHART_SEL).first.bounding_box()
    y = box["y"] + box["height"] - 12
    x0 = box["x"] + box["width"] * 0.55
    x1 = x0 + box["width"] * 0.15
    page.mouse.move(x0, y)
    page.mouse.down()
    page.mouse.move(x1, y, steps=15)
    page.mouse.up()
    page.wait_for_timeout(700)
    after = page.evaluate(DZ_JS, CHART_SEL)
    print("拖动前:", json.dumps(before), " 拖动后:", json.dumps(after))
    browser.close()
