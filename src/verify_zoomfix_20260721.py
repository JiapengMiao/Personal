# -*- coding: utf-8 -*-
"""验证 zoom 命中修复:坐标修正 + dataZoom 滑块拖动。
断言:
1. 悬停 f=0.3/0.5/0.7 时,图表侧收到的 clientX 已换算回布局坐标
   (clientX - rect.left) / clientW ≈ f (±0.03)
2. dataZoom 预设 40%~70% 窗口后,拖窗口中部向右 15% 图宽,
   start/end 应平移约 +15 (±4)
3. 无 pageerror
"""
import json
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "5199"
CHART_SEL = "#market .echart"
FAILS = []

INJECT = """(sel) => {
  const el = document.querySelector(sel);
  window.__probe = [];
  el.addEventListener('pointermove', (e) => {
    const r = el.getBoundingClientRect();
    window.__probe.push({clientX: e.clientX, rectLeft: r.left, clientW: el.clientWidth});
    if (window.__probe.length > 50) window.__probe.shift();
  }, {passive: true});
  return true;
}"""

DZ_JS = """(sel) => {
  const inst = window.__echarts.getInstanceByDom(document.querySelector(sel));
  const dz = inst.getOption().dataZoom[0];
  return {start: dz.start, end: dz.end, startValue: dz.startValue, endValue: dz.endValue};
}"""

SET_WINDOW_JS = """(sel) => {
  const inst = window.__echarts.getInstanceByDom(document.querySelector(sel));
  const dates = inst.getOption().xAxis[0].data;
  const n = dates.length;
  inst.dispatchAction({type: 'dataZoom', startValue: dates[Math.floor(n*0.4)], endValue: dates[Math.floor(n*0.7)]});
  return {n, s: dates[Math.floor(n*0.4)], e: dates[Math.floor(n*0.7)]};
}"""

PROBE_JS = """() => (window.__probe || []).slice(-1)[0] || null"""


def check(name, ok, detail):
    print(("PASS " if ok else "FAIL ") + name + " | " + detail)
    if not ok:
        FAILS.append(name)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.0)
    page.on("pageerror", lambda e: FAILS.append(f"pageerror: {e}") or print("PAGEERROR:", e))
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(4000)
    page.locator("#market").first.scroll_into_view_if_needed(timeout=10000)
    page.wait_for_timeout(1500)

    page.evaluate(INJECT, CHART_SEL)
    print("===== 1. 悬停坐标修正 =====")
    box = page.locator(CHART_SEL).first.bounding_box()
    for f in (0.3, 0.5, 0.7):
        cx = box["x"] + box["width"] * f
        cy = box["y"] + box["height"] * 0.45
        page.mouse.move(cx - 30, cy)
        page.mouse.move(cx, cy, steps=4)
        page.wait_for_timeout(500)
        pr = page.evaluate(PROBE_JS)
        if not pr:
            check(f"hover f={f}", False, "probe 无记录")
            continue
        ratio = (pr["clientX"] - pr["rectLeft"]) / pr["clientW"]
        check(
            f"hover f={f}",
            abs(ratio - f) < 0.03,
            f"zrX/clientW={ratio:.4f} 期望≈{f} (clientX={pr['clientX']:.1f})",
        )

    print("===== 2. dataZoom 窗口拖动 =====")
    w = page.evaluate(SET_WINDOW_JS, CHART_SEL)
    print("预设窗口:", json.dumps(w, ensure_ascii=False))
    page.wait_for_timeout(800)
    before = page.evaluate(DZ_JS, CHART_SEL)
    # 按 dataZoom 实际布局参数计算滑块窗口中点的屏幕坐标
    grab = page.evaluate("""(sel) => {
      const el = document.querySelector(sel);
      const inst = window.__echarts.getInstanceByDom(el);
      const opt = inst.getOption();
      const dzs = opt.dataZoom || [];
      const dz = dzs.find(d => d.type === 'slider') || dzs[0];
      const grid = (opt.grid || [{}])[0];
      const zoom = parseFloat(getComputedStyle(document.documentElement).zoom) || 1;
      const rect = el.getBoundingClientRect();
      const cw = el.clientWidth, ch = el.clientHeight;
      const num = (v, total, dflt) => (v == null || typeof v === 'string' && !v.endsWith('%') && isNaN(parseFloat(v))) ? dflt : (typeof v === 'string' && v.endsWith('%') ? parseFloat(v)/100*total : parseFloat(v));
      const gLeft = num(grid.left, cw, 60), gRight = num(grid.right, cw, 60);
      const left = num(dz.left, cw, gLeft);
      const right = num(dz.right, cw, gRight);
      const bottom = num(dz.bottom, ch, 10);
      const height = num(dz.height, ch, 20);
      const barW = cw - left - right;
      const start = dz.start != null ? dz.start : 0, end = dz.end != null ? dz.end : 100;
      const lx = left + barW * (start + end) / 200;
      const ly = ch - bottom - height / 2;
      return {sx: rect.left + lx * zoom, sy: rect.top + ly * zoom, lx, ly, zoom, cw, ch, dz, grid};
    }""", CHART_SEL)
    print("抓取点:", json.dumps(grab))
    x0, y = grab["sx"], grab["sy"]
    box = page.locator(CHART_SEL).first.bounding_box()
    x1 = x0 + box["width"] * 0.15
    page.mouse.move(x0, y)
    page.mouse.down()
    page.mouse.move(x1, y, steps=15)
    page.mouse.up()
    page.wait_for_timeout(700)
    after = page.evaluate(DZ_JS, CHART_SEL)
    ds = after["start"] - before["start"]
    de = after["end"] - before["end"]
    print("拖动前:", json.dumps(before), " 拖动后:", json.dumps(after))
    check("slider start 平移≈+15", abs(ds - 15) < 4, f"Δstart={ds:.2f}")
    check("slider end 平移≈+15", abs(de - 15) < 4, f"Δend={de:.2f}")

    browser.close()

print("===== 结果 =====")
if FAILS:
    print("FAILED:", json.dumps(FAILS, ensure_ascii=False))
    sys.exit(1)
print("ALL PASS")
