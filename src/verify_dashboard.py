# -*- coding: utf-8 -*-
"""看板视觉验证：真实 Edge 截图各区块与交互态。用法: py -3.14 src/verify_dashboard.py <port>"""
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4491"
BASE = f"http://127.0.0.1:{PORT}"
OUT = Path(__file__).resolve().parent.parent / "output" / "verify"
OUT.mkdir(parents=True, exist_ok=True)

SECTIONS = ["hero", "signals", "trends", "market", "daily", "positions", "basis", "season", "dynamics", "indicators"]

with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1000}, device_scale_factor=1.5)
    errors = []
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE, wait_until="networkidle", timeout=60000)
    page.wait_for_timeout(3500)

    # 全页总览（顶部）
    page.screenshot(path=str(OUT / "00_top.png"))

    # 逐区块截图
    for sid in SECTIONS:
        try:
            el = page.locator(f"#{sid}")
            if el.count() == 0:
                el = page.locator(f"[id='{sid}']")
            el.first.scroll_into_view_if_needed(timeout=5000)
            page.wait_for_timeout(1200)
            page.screenshot(path=str(OUT / f"sec_{sid}.png"))
            print(f"ok {sid}")
        except Exception as e:
            print(f"miss {sid}: {e}")

    # 交互1：基差切到第3个pair tab（触发懒加载）
    try:
        page.locator("#basis").first.scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(800)
        tabs = page.locator("#basis button, #basis [role='tab']")
        n = tabs.count()
        print(f"basis tabs found: {n}")
        if n >= 3:
            tabs.nth(2).click()
            page.wait_for_timeout(2500)
            page.screenshot(path=str(OUT / "act_basis_tab3.png"))
            print("ok basis tab3")
    except Exception as e:
        print(f"miss basis interaction: {e}")

    # 交互2：打开指标库详情抽屉
    try:
        page.locator("#indicators").first.scroll_into_view_if_needed(timeout=5000)
        page.wait_for_timeout(800)
        rows = page.locator("#indicators table tbody tr, #indicators tr")
        n = rows.count()
        print(f"indicator rows found: {n}")
        if n >= 1:
            rows.nth(0).click()
            page.wait_for_timeout(2000)
            page.screenshot(path=str(OUT / "act_drawer.png"))
            print("ok drawer")
    except Exception as e:
        print(f"miss drawer interaction: {e}")

    # 浅色模式
    try:
        page.keyboard.press("Escape")
        tgl = page.locator("button[aria-label*='主题'], button[title*='主题'], button[aria-label*='theme'], button[title*='theme']")
        if tgl.count() > 0:
            tgl.first.click()
            page.wait_for_timeout(1500)
            page.evaluate("window.scrollTo(0,0)")
            page.wait_for_timeout(800)
            page.screenshot(path=str(OUT / "act_light_mode.png"))
            print("ok light mode")
        else:
            print("miss theme toggle button")
    except Exception as e:
        print(f"miss light mode: {e}")

    print("CONSOLE_ERRORS:", len(errors))
    for e in errors[:10]:
        print("  ERR:", e[:200])
    browser.close()
print("done ->", OUT)
