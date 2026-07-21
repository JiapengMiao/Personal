# -*- coding: utf-8 -*-
from pathlib import Path

agent = Path(r"C:/Users/56558/Nutstore/1/我的坚果云/agent")
pit = (agent / "【全局复盘与踩坑日志】.md").read_text(encoding="utf-8", errors="replace")
wb = (agent / "【全局工作台】.md").read_text(encoding="utf-8", errors="replace")

p002 = next(agent.glob("Project-002*"))
logs = []
for f in sorted((p002 / "conversation_logs").glob("*.md")):
    logs.append((f.name, f.read_text(encoding="utf-8", errors="replace")))

# keywords / phrases to search in global pit log
checks = [
    ("LTTB × connectNulls", ["LTTB", "connectNulls"]),
    ("ECharts sampling/LTTB 与 dataZoom", ["LTTB", "dataZoom", "sampling"]),
    ("周频数据 connectNulls 虚线感", ["connectNulls", "虚线"]),
    ("RangePicker max 取 max(数据末,今天)", ["RangePicker", "数据末日期"]),
    ("vite base ./ 与相对路径 fetch", ["base:", 'base: "./"', "相对路径"]),
    ("GitHub Contents API 大文件损坏", ["Contents API", "大 JS", "API 上传"]),
    ("git reset --hard 丢未推送修改", ["reset --hard"]),
    ("git remote set-url 覆盖 PAT", ["remote set-url", "旧 token", "旧 PAT"]),
    ("对话记录/PAT 不进 git/docs", ["conversation_logs", "对话记录", "PAT", "publish.bat"]),
    ("git filter-repo 清 token", ["filter-repo"]),
    ("CSS zoom 命中偏移 / patchZoomHit", ["zoom", "patchZoomHit", "defineProperty", "命中"]),
    ("devicePixelRatio × zoom 防模糊", ["devicePixelRatio", "模糊"]),
    ("克隆事件重派发不可靠", ["克隆", "defineProperty"]),
    ("zrender 只听 pointer 事件", ["pointer", "zrender"]),
    ("国内库存 = 上期+上金 ffill", ["domesticInvT", "上金所", "ffill"]),
    ("偶数月合约过滤", ["偶数"]),
    ("金银比单位 ×1000", ["金银比", "1000"]),
    ("EdgeOne 自定义域名/免备案", ["EdgeOne", "silverdaily"]),
    ("WebBridge CSS selector click", ["WebBridge", "selector", "IIFE"]),
    ("evaluate IIFE", ["IIFE"]),
    ("vite build wb-clean / 旧 hash", ["wb-clean", "旧 hash", "safe-delete"]),
    ("本地远端分叉用 API 部署", ["分叉", "Contents API", "Git Data API"]),
    ("CDN 硬刷新", ["硬刷新", "CDN"]),
    ("startsWith空串恒true", ["startsWith", "METAL_KEYS"]),
    ("CSS replace_all 涨跌色陷阱", ["replace_all", "涨红", "跌绿"]),
    ("Playwright evaluate 单参数", ["evaluate", "Playwright"]),
    ("Git Bash 反斜杠 vite 路径", ["反斜杠", "正斜杠", "vite.js"]),
    ("npx 不在 PATH / http.server", ["npx", "http.server"]),
    ("006 table-row 是 button", ["table-row"]),
    ("租赁利率自动发现", ["租赁利率", "自动发现"]),
    ("pageerror 验证而非 curl 200", ["pageerror", "curl 200"]),
    ("坚果云 *冲突* 文件", ["冲突"]),
    ("域名误读 .top vs .cfd", ["silverdaily", ".top", ".cfd"]),
]

print("=== GLOBAL PIT LOG length", len(pit))
print("=== WORKBENCH section 9 present", "高频踩坑自检清单" in wb)
print()
print("=== Keyword presence in 全局复盘与踩坑日志 ===")
for title, kws in checks:
    hits = [k for k in kws if k in pit]
    miss = [k for k in kws if k not in pit]
    status = "FULL" if not miss else ("PARTIAL" if hits else "MISSING")
    print(f"[{status}] {title}")
    if hits:
        print("  hit:", ", ".join(hits))
    if miss:
        print("  miss:", ", ".join(miss))

print()
print("=== Keyword presence in 全局工作台 §9 ===")
for title, kws in checks:
    hits = [k for k in kws if k in wb]
    miss = [k for k in kws if k not in wb]
    status = "FULL" if not miss else ("PARTIAL" if hits else "MISSING")
    if status != "MISSING":
        print(f"[{status}] {title} | hit={hits} miss={miss}")

# Extract dated entries mentioning 002 / 白银看板 / silverdaily / zoom / LTTB from pit log
print()
print("=== Pit log headings/lines related to 002 topics (sample) ===")
keys = ["002", "白银", "LTTB", "zoom", "EdgeOne", "silverdaily", "PAT", "WebBridge", "connectNulls", "龙虎", "patchZoom", "Pages", "Contents API", "filter-repo"]
for i, line in enumerate(pit.splitlines()):
    if any(k in line for k in keys) and (line.startswith("#") or line.startswith("###") or line.startswith("- **")):
        print(f"{i+1}: {line[:120]}")
