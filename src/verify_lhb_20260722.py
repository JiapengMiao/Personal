# -*- coding: utf-8 -*-
"""验证龙虎榜区块渲染：深色主题截图 #lhb section。"""
import os, sys, threading, http.server, socketserver
from playwright.sync_api import sync_playwright

TEMP = r"C:\Users\56558\AppData\Local\Temp\wb-pos-build"
ROOT = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化"
OUT = os.path.join(ROOT, "output", "verify", "lhb_dark_20260722.png")

class _H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k): super().__init__(*a, directory=TEMP, **k)
    def log_message(self, *a): pass

httpd = socketserver.TCPServer(("127.0.0.1", 0), _H)
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print("PORT =", PORT)

FAILS = []
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        page = browser.new_page(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
        page.on("pageerror", lambda e: (FAILS.append(str(e)), print("PAGEERROR:", e)))
        page.goto(f"http://127.0.0.1:{PORT}/", wait_until="networkidle", timeout=90000)
        page.wait_for_timeout(4000)

        # 检查 #lhb 存在
        lhb = page.locator("#lhb")
        if lhb.count() == 0:
            print("FAIL: #lhb section not found")
            FAILS.append("no #lhb")
        else:
            lhb.first.scroll_into_view_if_needed(timeout=10000)
            page.wait_for_timeout(1500)

            # 检查 tab 按钮
            tabs = lhb.locator(".lhb-tab")
            tc = tabs.count()
            print(f"tabs: {tc}")
            if tc < 1: FAILS.append("no tabs")

            # 检查表格行
            rows = lhb.locator(".lhb-table tbody tr")
            rc = rows.count()
            print(f"table rows: {rc}")
            if rc < 10: FAILS.append(f"too few rows: {rc}")

            # 检查导航含"龙虎"
            nav_text = page.locator(".topbar nav").inner_text()
            has_nav = "龙虎" in nav_text
            print(f"nav has 龙虎: {has_nav}")
            if not has_nav: FAILS.append("nav missing 龙虎")

            lhb.first.screenshot(path=OUT)
            print("SCREENSHOT ->", OUT)
        browser.close()
finally:
    httpd.shutdown()

if FAILS:
    print("FAILED:", FAILS); sys.exit(1)
print("ALL PASS")
