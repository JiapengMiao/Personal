import pandas as pd
sheets = pd.read_excel(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\data\010源数据\白银所有数据.xlsx", sheet_name=["虚实比数据"], header=None)
raw_v = sheets["虚实比数据"]
hdr = raw_v.iloc[5].tolist()
body = raw_v.iloc[6:]
oi_date = pd.to_datetime(body.iloc[:, 2], errors="coerce")
print(f"OI date range: {oi_date.min()} → {oi_date.max()}")
print(f"OI date count: {oi_date.notna().sum()}")
# Find AG2608 column
for j in range(3, body.shape[1]):
    col_code = hdr[j]
    if isinstance(col_code, str) and "AG2608" in col_code:
        vals = pd.to_numeric(body.iloc[:, j], errors="coerce")
        d = pd.DataFrame({"date": oi_date, "oi": vals}).dropna()
        d = d.sort_values("date")
        print(f"\nAG2608 OI: {len(d)} rows, {d['date'].min()} → {d['date'].max()}")
        print(f"Last 5 rows:")
        print(d.tail(5).to_string())
        break
