import pandas as pd
from datetime import datetime

# Reproduce the exact logic
sheets = pd.read_excel(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\data\010源数据\白银所有数据.xlsx", sheet_name=["白银数据", "虚实比数据", "白银合约参数"], header=None)

# Main table
raw = sheets["白银数据"]
header = raw.iloc[1].tolist()
df = raw.iloc[2:].copy()
df.columns = header
df = df.rename(columns={header[0]: "date"})
df["date"] = pd.to_datetime(df["date"], errors="coerce")
df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
hist_cal = pd.DatetimeIndex(df["date"])
print(f"hist_cal: {len(hist_cal)} days, {hist_cal[0]} → {hist_cal[-1]}")

# Expiry
def parse_yyyymmdd(v):
    if v is None: return None
    s = str(v).strip()
    if len(s) == 8 and s.isdigit():
        return datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))
    try: return pd.Timestamp(v).to_pydatetime()
    except: return None

raw_p = sheets["白银合约参数"]
expiry = {}
for _, row in raw_p.iloc[1:].iterrows():
    code = str(row.iloc[0]).strip().lower()
    exp = parse_yyyymmdd(row.iloc[2])
    if exp: expiry[code] = exp

# Trading calendar
wd = hist_cal.weekday
biz = hist_cal[wd < 5]
exp_dates = pd.DatetimeIndex(list(expiry.values()))
trading_cal = biz.union(exp_dates).sort_values()
print(f"trading_cal: {len(trading_cal)} days, {trading_cal[0]} → {trading_cal[-1]}")

# Check AG2608
exp_ts = pd.Timestamp(expiry["ag2608"])
exp_pos = int(trading_cal.searchsorted(exp_ts))
print(f"\nAG2608 expiry={exp_ts}, exp_pos={exp_pos}")
print(f"trading_cal[exp_pos] = {trading_cal[exp_pos]}")

# OI data
raw_v = sheets["虚实比数据"]
hdr = raw_v.iloc[5].tolist()
body = raw_v.iloc[6:]
oi_date = pd.to_datetime(body.iloc[:, 2], errors="coerce")
for j in range(3, body.shape[1]):
    col_code = hdr[j]
    if isinstance(col_code, str) and "AG2608" in col_code.strip():
        vals = pd.to_numeric(body.iloc[:, j], errors="coerce")
        d = pd.DataFrame({"date": oi_date, "oi": vals}).dropna().sort_values("date").reset_index(drop=True)
        print(f"\nAG2608 OI: {len(d)} rows")
        # Check last 5
        for _, row in d.tail(5).iterrows():
            dt = pd.Timestamp(row["date"])
            di = int(trading_cal.searchsorted(dt))
            x = di - exp_pos
            print(f"  date={dt.date()} di={di} x={x} oi={row['oi']}")
        # Check extension condition
        last_daily = df["date"].iloc[-1]
        print(f"\nExtension check: exp_ts={exp_ts} <= last_daily={last_daily} ? {exp_ts <= pd.Timestamp(last_daily)}")
        break
