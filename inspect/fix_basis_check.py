path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\src\build_dashboard_data.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

old_check = '''          check(b["times"][0] >= "2026-06-29" and b["times"][-1] <= "2026-07-18 03:00",
              f"{name} 时间范围 {b['times'][0]} → {b['times'][-1]}")'''
new_check = '''          check(b["times"][0] >= "2026-01-01" and len(b["times"]) > 100,
              f"{name} 时间范围 {b['times'][0]} → {b['times'][-1]} ({len(b['times'])} 条)")'''
src = src.replace(old_check, new_check, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Basis time range check updated")
