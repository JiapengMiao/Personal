# -*- coding: utf-8 -*-
"""全图表回归 v2:对每个 .echart 悬停中心点,验证 zrender 收到的
offsetX/clientW ≈ 0.5 (±0.06),即坐标已修正为布局坐标。
"""
import json
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "5199"
FAILS = []

STEP = """(i) => {
  const els = document.querySelectorAll('.echart');
  const el = els[i];
  if (!el) return null;
  const inst = window.__echarts.getInstanceByDom(el);
  if (!inst) return {skip: true};
  const zr = inst.getZr();
  window.__hit = null;
  if (window.__hitH) zr.off('mousemove', window.__hitH);
  window.__hitH = (e) => { window.__hit = {ox: e.offsetX, oy: e.offsetY, target: e.target && e.target.type}; };
  zr.on('mousemove', window.__hitH);
  el.scrollIntoView({block: 'center', behavior: 'instant'});
  return {ok: true, section: (el.closest('section,div[id]')||{}).id || ''};
}"""

POINT = """(i) => {
  const el = document.querySelectorAll('.echart')[i];
  const rect = el.getBoundingClientRect();
  return {sx: rect.x + rect.width / 2, sy: rect.y + rect.height * 0.45, cw: el.clientWidth, inView: rect.y > 0 && rect.y < innerHeight - 50};
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1.0)
    page.on("pageerror", lambda e: FAILS.append(f"pageerror: {e}") or print("PAGEERROR:", e))
    page.goto(f"http://127.0.0.1:{PORT}", wait_until="networkidle", timeout=90000)
    page.wait_for_timeout(5000)

    n = page.evaluate("() => document.querySelectorAll('.echart').length")
    print(f"共 {n} 个图表容器")
    for i in range(n):
        st = page.evaluate(STEP, i)
        if not st or st.get("skip"):
            print(f"[{i}] 跳过(无实例)")
            continue
        page.wait_for_timeout(500)
        pt = page.evaluate(POINT, i)
        page.mouse.move(pt["sx"] - 40, pt["sy"])
        page.wait_for_timeout(200)
        page.evaluate("() => window.__hit = null")
        page.mouse.move(pt["sx"], pt["sy"], steps=4)
        page.wait_for_timeout(500)
        hit = page.evaluate("() => window.__hit")
        if not hit:
            FAILS.append(f"chart{i} 无事件 inView={pt['inView']}")
            print(f"[{i}] {st['section']} FAIL: 无事件 inView={pt['inView']}")
            continue
        ratio = hit["ox"] / pt["cw"]
        ok = abs(ratio - 0.5) < 0.06
        if not ok:
            FAILS.append(f"chart{i} {st['section']}")
        print(f"[{i}] {st['section']:12s} {'PASS' if ok else 'FAIL'} ox/cw={ratio:.3f} target={hit['target']}")

    browser.close()

print("===== 结果 =====")
if FAILS:
    print("FAILED:", json.dumps(FAILS, ensure_ascii=False))
    sys.exit(1)
print("ALL PASS")
