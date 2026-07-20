import pandas as pd
from datetime import datetime

# Check what parse_yyyymmdd returns
def parse_yyyymmdd(v):
    if v is None:
        return None
    s = str(v).strip()
    if len(s) == 8 and s.isdigit():
        return datetime(int(s[:4]), int(s[4:6]), int(s[6:8]))
    try:
        return pd.Timestamp(v).to_pydatetime()
    except Exception:
        return None

# Read contract params
raw_p = pd.read_excel(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\data\010源数据\白银所有数据.xlsx", sheet_name="白银合约参数", header=None)
for _, row in raw_p.iloc[1:].iterrows():
    code = str(row.iloc[0]).strip().lower()
    exp_raw = row.iloc[2]
    exp = parse_yyyymmdd(exp_raw)
    print(f"{code}: raw={exp_raw!r} type={type(exp_raw).__name__} parsed={exp}")
