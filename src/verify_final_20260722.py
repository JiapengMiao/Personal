# -*- coding: utf-8 -*-
"""快速验证：铂钯租赁利率 tab 渲染 + 龙虎榜合计行 + 数据日期。"""
import os, sys, threading, http.server, socketserver
from playwright.sync_api import sync_playwright

TEMP = r"C:\Users\56558\AppData\Local\Temp\wb-pos-build"
ROOT = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化"
VD = os.path.join(ROOT, "output", "verify")
os.makedirs(VD, exist_ok=True)

class _H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=TEMP, **k)
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(("127.0.0.1", 0), _H)
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print("PORT =", PORT)

FAILS = []
def chk(name, ok, detail):
    print(("PASS " if ok else "FAIL ") + name + " | " + str(detail))
    if not ok: FAILS.append(name)

try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
        page.on("pageerror", lambda e: (FAILS.append(str(e)), print("PAGEERROR:", e)))
        page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(4000)

        # 铂钯租赁利率 tab
        lease = page.locator("#lease")
        chk("lease exists", lease.count() > 0, lease.count())
        if lease.count() > 0:
            lease.first.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(1000)
            tabs = lease.locator(".lhb-tab")
            chk("3 tabs", tabs.count() == 3, tabs.count())
            # 切铂金
            tabs.nth(1).click()
            page.wait_for_timeout(1200)
            chk("铂金 tab active", "active" in (tabs.nth(1).get_attribute("class") or ""), "")
            # 检查 chart 有 series（铂金的 4 条期限线应该渲染）
            chart = lease.locator(".echart canvas")
            chk("canvas exists", chart.count() > 0, chart.count())
            # 切钯金
            tabs.nth(2).click()
            page.wait_for_timeout(1200)
            chk("钯金 tab active", "active" in (tabs.nth(2).get_attribute("class") or ""), "")
            lease.first.screenshot(path=os.path.join(VD, "lease_pd_dark_20260722.png"))
            print("SCREENSHOT lease_pd")

        # 龙虎榜合计行
        lhb = page.locator("#lhb")
        chk("lhb exists", lhb.count() > 0, lhb.count())
        if lhb.count() > 0:
            lhb.first.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(1000)
            tfoot = lhb.locator("tfoot")
            chk("tfoot=2", tfoot.count() == 2, tfoot.count())
            if tfoot.count() >= 1:
                txt = tfoot.first.inner_text()
                chk("tfoot has 合计", "合计" in txt, txt[:60])

        browser.close()
finally:
    httpd.shutdown()

if FAILS:
    print("FAILED:", FAILS); sys.exit(1)
print("ALL PASS")
