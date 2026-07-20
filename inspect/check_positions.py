import json
d = json.load(open(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\public\data\positions_curve.json", encoding="utf-8"))
for c in d["contracts"]:
    pts = c["points"]
    last = pts[-1] if pts else None
    first = pts[0] if pts else None
    print(f"{c['code']} expiry={c['expiry']} pts={len(pts)} x=[{first['x'] if first else '?'}..{last['x'] if last else '?'}] last_y={last['y'] if last else '?'}")
