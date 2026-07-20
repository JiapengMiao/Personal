import json
d = json.load(open(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\public\data\positions_curve.json", encoding="utf-8"))
for c in d["contracts"]:
    if c["code"] == "ag2608":
        pts = c["points"]
        print(f"AG2608 last 5 points:")
        for p in pts[-5:]:
            print(f"  x={p['x']}, y={p['y']}")
        print(f"AG2608 first 3 points:")
        for p in pts[:3]:
            print(f"  x={p['x']}, y={p['y']}")
