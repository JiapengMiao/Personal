# 验证第5条反馈：基差/进出口盈亏的时间轴缩放后，区间统计是否联动
# 方法：1) 鼠标滚轮在图上缩放（inside dataZoom）2) 拖动 slider 选区主体
# 断言：区间均值/百分位文本在缩放与拖动后发生变化
import sys
from playwright.sync_api import sync_playwright

PORT = sys.argv[1] if len(sys.argv) > 1 else "4496"
URL = f"http://127.0.0.1:{PORT}/"
OUT = "output/verify"


def read_stats(page, idx):
    """读取第 idx 个 stat-cards 组的所有卡片文本"""
    cards = page.locator("#basis .stat-cards").nth(idx).locator(".stat-card")
    out = []
    for i in range(cards.count()):
        small = cards.nth(i).locator("small").inner_text()
        strong = cards.nth(i).locator("strong").inner_text()
        out.append(f"{small}={strong}")
    return " | ".join(out)


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1920, "height": 1080})
    page.goto(URL, wait_until="networkidle")
    page.wait_for_selector("#basis canvas", timeout=20000)
    page.locator("#basis").scroll_into_view_if_needed()
    page.wait_for_timeout(1500)

    canvas = page.locator("#basis canvas").first
    box = canvas.bounding_box()
    print(f"[INFO] basis canvas box: {box}")

    print(f"[初始] 基差: {read_stats(page, 0)}")
    print(f"[初始] 盈亏: {read_stats(page, 1)}")

    # --- 1) 滚轮缩放基差图（inside zoom）---
    cx, cy = box["x"] + box["width"] * 0.5, box["y"] + box["height"] * 0.45
    page.mouse.move(cx, cy)
    for _ in range(4):
        page.mouse.wheel(0, -400)
        page.wait_for_timeout(120)
    page.wait_for_timeout(600)
    print(f"[滚轮缩放后] 基差: {read_stats(page, 0)}")
    page.screenshot(path=f"{OUT}/stats_basis_wheel.png")

    # --- 2) 拖动基差图 slider 选区主体（pan 窗口）---
    box2 = canvas.bounding_box()
    slider_y = box2["y"] + box2["height"] - 8 - 9  # bottom:8 height:18 → 中线
    sx = box2["x"] + box2["width"] * 0.5
    page.mouse.move(sx, slider_y)
    page.mouse.down()
    page.mouse.move(sx + box2["width"] * 0.25, slider_y, steps=12)
    page.mouse.up()
    page.wait_for_timeout(600)
    print(f"[slider拖动后] 基差: {read_stats(page, 0)}")
    page.screenshot(path=f"{OUT}/stats_basis_drag.png")

    # --- 3) 滚轮缩放进出口盈亏图 ---
    profit_canvas = page.locator("#basis canvas").nth(1)
    pbox = profit_canvas.bounding_box()
    pcx, pcy = pbox["x"] + pbox["width"] * 0.5, pbox["y"] + pbox["height"] * 0.45
    page.mouse.move(pcx, pcy)
    for _ in range(4):
        page.mouse.wheel(0, -400)
        page.wait_for_timeout(120)
    page.wait_for_timeout(600)
    print(f"[滚轮缩放后] 盈亏: {read_stats(page, 1)}")
    page.screenshot(path=f"{OUT}/stats_profit_wheel.png")

    # --- 4) 拖动盈亏图 slider ---
    pbox2 = profit_canvas.bounding_box()
    psy = pbox2["y"] + pbox2["height"] - 8 - 9
    psx = pbox2["x"] + pbox2["width"] * 0.5
    page.mouse.move(psx, psy)
    page.mouse.down()
    page.mouse.move(psx - pbox2["width"] * 0.2, psy, steps=12)
    page.mouse.up()
    page.wait_for_timeout(600)
    print(f"[slider拖动后] 盈亏: {read_stats(page, 1)}")
    page.screenshot(path=f"{OUT}/stats_profit_drag.png")

    browser.close()
print("DONE")
