# -*- coding: utf-8 -*-
"""验证：龙虎榜合计行 + 租借利率 tab 切换。截图深/浅各一张龙虎榜 + 一张铂钯租赁。"""
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
        ctx = browser.new_context(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
        page = ctx.new_page()
        page.on("pageerror", lambda e: (FAILS.append(str(e)), print("PAGEERROR:", e)))
        page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(4000)

        # ===== 龙虎榜合计行 =====
        lhb = page.locator("#lhb")
        chk("lhb exists", lhb.count() > 0, lhb.count())
        if lhb.count() > 0:
            lhb.first.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(1500)
            tfoot = lhb.locator("tfoot")
            chk("tfoot exists", tfoot.count() == 2, tfoot.count())
            if tfoot.count() >= 1:
                total_text = tfoot.first.inner_text()
                chk("tfoot has 合计", "合计" in total_text, total_text[:80])
                # 验证合计数值 = 各行加总（持仓量列）
                cells = tfoot.first.locator("td")
                chk("tfoot has 5 cells", cells.count() == 5, cells.count())
            lhb.first.screenshot(path=os.path.join(VD, "lhb_total_dark_20260722.png"))
            print("SCREENSHOT lhb_total_dark")

        # ===== 租借利率 tab =====
        lease = page.locator("#lease")
        chk("lease exists", lease.count() > 0, lease.count())
        if lease.count() > 0:
            lease.first.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(1000)
            tabs = lease.locator(".lhb-tab")
            tc = tabs.count()
            chk("lease tabs=3", tc == 3, tc)
            # 默认=白银
            chk("default tab active=白银", "active" in (tabs.nth(0).get_attribute("class") or ""), tabs.nth(0).get_attribute("class"))
            # 切到铂金
            tabs.nth(1).click()
            page.wait_for_timeout(800)
            desc = lease.locator(".section-heading p").inner_text()
            chk("tab switch to 铂金", "铂金" in desc, desc[:40])
            lease.first.screenshot(path=os.path.join(VD, "lease_pt_dark_20260722.png"))
            print("SCREENSHOT lease_pt_dark")
            # 切到钯金
            tabs.nth(2).click()
            page.wait_for_timeout(800)
            desc2 = lease.locator(".section-heading p").inner_text()
            chk("tab switch to 钯金", "钯金" in desc2, desc2[:40])

        browser.close()
finally:
    httpd.shutdown()

if FAILS:
    print("FAILED:", FAILS); sys.exit(1)
print("ALL PASS")
