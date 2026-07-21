# -*- coding: utf-8 -*-
"""校验演示缩放在不同逻辑视口 × 档位下的布局安全性。
量两条投屏红线:横向滚动条(scrollWidth>clientWidth)、顶栏挤爆。
串行执行避免资源争抢。
"""
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4495"
URL = f"http://127.0.0.1:{PORT}"
OUT = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\output\verify"
ZOOMS = [100, 125, 150, 175, 200]
WIDTHS = [1920, 1536]

METRIC = """() => {
  const de = document.documentElement;
  const cz = getComputedStyle(de).zoom;
  const horiz = de.scrollWidth > de.clientWidth + 2;
  const tb = document.querySelector('.topbar');
  const tbOverflow = tb ? tb.scrollWidth > tb.clientWidth + 2 : null;
  const nav = document.querySelector('.topbar nav');
  const navVisible = nav ? (nav.offsetParent !== null && nav.getBoundingClientRect().width > 0) : null;
  const ctl = document.querySelector('.zoom-ctl');
  const ctlVisible = ctl ? (ctl.offsetParent !== null) : null;
  return {cz, horiz, tbOverflow, navVisible, ctlVisible};
}"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="msedge", headless=True)
    for w in WIDTHS:
        pg = b.new_page(viewport={"width": w, "height": 1080}, device_scale_factor=1)
        pg.goto(URL, wait_until="networkidle", timeout=60000)
        pg.wait_for_timeout(3000)
        for z in ZOOMS:
            pg.evaluate(f"localStorage.setItem('ag-monitor-zoom','{z}')")
            pg.reload(wait_until="networkidle", timeout=60000)
            pg.wait_for_timeout(3500)
            m = pg.evaluate(METRIC)
            if w == 1920:
                pg.screenshot(path=f"{OUT}\\zoom_{z}.png")
            print(f"  {w}×{z}%: zoom={m['cz']} horiz={m['horiz']} tbOverflow={m['tbOverflow']} navVisible={m['navVisible']}")
        pg.close()
    # 4K 清晰度对照:dpr=2, css 视口 1920 = 物理 3840
    pg2 = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=2)
    pg2.goto(URL, wait_until="networkidle", timeout=60000)
    pg2.wait_for_timeout(3000)
    pg2.evaluate("localStorage.setItem('ag-monitor-zoom','150')")
    pg2.reload(wait_until="networkidle", timeout=60000)
    pg2.wait_for_timeout(3500)
    pg2.screenshot(path=f"{OUT}\\zoom_150_dpr2_4k.png")
    pg2.close()
    b.close()
    print("DONE")
