# -*- coding: utf-8 -*-
from pathlib import Path

agent = Path(r"C:/Users/56558/Nutstore/1/我的坚果云/agent")
pit = (agent / "【全局复盘与踩坑日志】.md").read_text(encoding="utf-8", errors="replace")
lines = pit.splitlines()

# print all ### headings from 2026-07-19 onward
print("=== ALL ### headings from line 390 ===")
for i, line in enumerate(lines):
    if i + 1 >= 390 and line.startswith("### "):
        print(f"{i+1}: {line}")

print()
print("=== Search missing topics context ===")
for kw in ["filter-repo", "偶数", "startsWith", "涨红", "跌绿", "replace_all", "反斜杠", "npx", "table-row", "租赁", "Git Data API", "deploy_git", "conversation_logs", "publish.bat", "上金所", "domesticInv", "METAL", "铂钯", "龙虎"]:
    found = [f"{i+1}:{lines[i][:100]}" for i in range(len(lines)) if kw in lines[i]]
    print(f"\nKW [{kw}] count={len(found)}")
    for x in found[:5]:
        print(" ", x)
