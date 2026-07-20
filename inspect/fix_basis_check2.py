path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\src\build_dashboard_data.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    if "2026-07-18 03:00" in line:
        print(f"Line {i+1}: {line.rstrip()}")
        # Replace this line and the next
        lines[i] = '          check(b["times"][0] >= "2026-01-01" and len(b["times"]) > 100,\n'
        lines[i+1] = '              f"{name} 时间范围 {b[\'times\'][0]} → {b[\'times\'][-1]} ({len(b[\'times\'])} 条)")\n'
        print(f"  -> replaced lines {i+1}-{i+2}")

with open(path, "w", encoding="utf-8") as f:
    f.writelines(lines)
print("Done")
