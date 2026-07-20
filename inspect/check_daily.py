import json
d = json.load(open(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\public\data\daily.json", encoding="utf-8"))
print(f"dates: {len(d['dates'])}, range: {d['dates'][0]} → {d['dates'][-1]}")
print(f"series keys: {sorted(d['series'].keys())}")
# check how many non-null in agtdClose
nn = sum(1 for v in d['series']['agtdClose'] if v is not None)
print(f"agtdClose non-null: {nn}/{len(d['dates'])}")
