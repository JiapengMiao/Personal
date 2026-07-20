path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\src\build_dashboard_data.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# Fix lines 707-708 (0-indexed: 706-707)
lines[706] = '        check(b["times"][0] >= "2026-01-01" and len(b["times"]) > 100,\n'
lines[707] = '            f"{name} 时间范围 {b[\'times\'][0]} → {b[\'times\'][-1]} ({len(b[\'times\'])} 条)")\n'

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Indentation fixed for basis check")
