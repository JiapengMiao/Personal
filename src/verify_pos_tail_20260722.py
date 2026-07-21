# -*- coding: utf-8 -*-
"""验证 05 持仓量与虚实比：未到期合约尾端浮签卡片标注（markPoint）— 深/浅双主题。

自包含：内置 http.server 临时静态服务（端口 OS 分配、daemon、跑完即退，无残留进程）。
主题持久化在 localStorage['ag-monitor-theme']，故每个主题先 setItem 再 reload。
读 ECharts option 做客观断言（canvas 文字 DOM 查不到）+ 每主题截图验视觉。

断言（每主题）：
1. #positions 含两个 echart
2. 每图恰 2 条 series 带 markPoint（ag2608、ag2610），已到期 3 条无标
3. formatter 含 "距到期 20" 与 "距到期 63"；持仓含"手"、虚实比含"倍"
4. label 已升级为浮签卡片：backgroundColor / borderColor / borderRadius / padding 齐备
5. 无 pageerror
"""
import os
import sys
import json
import threading
import http.server
import socketserver
from playwright.sync_api import sync_playwright

TEMP = r"C:\Users\56558\AppData\Local\Temp\wb-pos-build"
ROOT = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化"
VERIFY_DIR = os.path.join(ROOT, "output", "verify")
os.makedirs(VERIFY_DIR, exist_ok=True)
THEME_KEY = "ag-monitor-theme"

assert os.path.isfile(os.path.join(TEMP, "index.html")), "temp build missing index.html (rebuild needed)"
assert os.path.isfile(os.path.join(TEMP, "data", "positions_curve.json")), "temp build missing data (re-copy needed)"


class _H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=TEMP, **k)

    def log_message(self, *a):
        pass


httpd = socketserver.TCPServer(("127.0.0.1", 0), _H)
PORT = httpd.server_address[1]
threading.Thread(target=httpd.serve_forever, daemon=True).start()
print("SERVER port =", PORT)

INFO_JS = """(el) => {
  const inst = window.__echarts && window.__echarts.getInstanceByDom(el);
  if (!inst) return {err: 'no instance'};
  const series = inst.getOption().series || [];
  const info = series.map(s => {
    const mp = s.markPoint;
    const has = !!(mp && mp.data && mp.data.length);
    const lab = mp && mp.label ? mp.label : {};
    return {name: s.name, has: has, fmt: has ? lab.formatter : null,
            bg: lab.backgroundColor, bc: lab.borderColor, br: lab.borderRadius, pad: lab.padding};
  });
  return {total: series.length, info: info, labeled: info.filter(x => x.has)};
}"""

FAILS = []


def check(name, ok, detail):
    print(("PASS " if ok else "FAIL ") + name + " | " + str(detail))
    if not ok:
        FAILS.append(name)


try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="msedge", headless=True)
        ctx = browser.new_context(viewport={"width": 1600, "height": 1200}, device_scale_factor=2)
        page = ctx.new_page()
        page.on("pageerror", lambda e: (FAILS.append("pageerror: " + str(e)), print("PAGEERROR:", e)))
        url = "http://127.0.0.1:%d/" % PORT

        for theme in ("dark", "light"):
            print("\n########## THEME =", theme, "##########")
            page.goto(url, wait_until="networkidle", timeout=90000)
            page.evaluate("(a)=>localStorage.setItem(a.k,a.v)", {"k": THEME_KEY, "v": theme})
            page.reload(wait_until="networkidle", timeout=90000)
            page.wait_for_timeout(3500)
            page.locator("#positions").first.scroll_into_view_if_needed(timeout=15000)
            page.wait_for_timeout(2000)

            charts = page.locator("#positions .echart")
            n = charts.count()
            check("[%s] 05 含两个 echart" % theme, n == 2, "count=%d" % n)

            labels = ["持仓", "虚实比"]
            expect_unit = ["手", "倍"]
            for i in range(min(n, 2)):
                info = charts.nth(i).evaluate(INFO_JS)
                lab = info.get("labeled", [])
                names = sorted(x["name"] for x in lab)
                fmts = " ".join(x["fmt"] or "" for x in lab)
                expired_labeled = [x["name"] for x in info.get("info", [])
                                   if x["name"] in ("ag2602", "ag2604", "ag2606") and x["has"]]
                # 浮签卡片属性（取第一个带标的 series 看 label 配置）
                card = lab[0] if lab else {}
                check("[%s] %s labeled==2" % (theme, labels[i]), len(lab) == 2, "names=%s" % names)
                check("[%s] %s 仅 ag2608/ag2610" % (theme, labels[i]), names == ["ag2608", "ag2610"], "names=%s" % names)
                check("[%s] %s 距到期20&63+单位%s" % (theme, labels[i], expect_unit[i]),
                      ("距到期 20" in fmts and "距到期 63" in fmts and expect_unit[i] in fmts),
                      fmts[:120].replace("\n", "\\n"))
                check("[%s] %s 已到期无标" % (theme, labels[i]), len(expired_labeled) == 0,
                      "expired=%s" % expired_labeled)
                check("[%s] %s 浮签卡:bg/border/radius/pad" % (theme, labels[i]),
                      bool(card.get("bg")) and bool(card.get("bc")) and card.get("br") == 5 and card.get("pad") is not None,
                      "bg=%s bc=%s br=%s pad=%s" % (card.get("bg"), card.get("bc"), card.get("br"), card.get("pad")))

            out = os.path.join(VERIFY_DIR, "pos_tail_%s_20260722.png" % theme)
            page.locator("#positions").first.screenshot(path=out)
            print("[%s] SCREENSHOT -> %s" % (theme, out))
        browser.close()
finally:
    httpd.shutdown()

print("\n===== 结果 =====")
if FAILS:
    print("FAILED:", json.dumps(FAILS, ensure_ascii=False))
    sys.exit(1)
print("ALL PASS")
