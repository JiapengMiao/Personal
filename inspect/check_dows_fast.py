import pandas as pd
from collections import Counter
df = pd.read_excel(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\data\010源数据\白银所有数据.xlsx", sheet_name="白银数据", header=None, usecols=[0])
dates = pd.to_datetime(df.iloc[2:, 0], errors="coerce").dropna()
print(f"Total dates: {len(dates)}")
print(f"Range: {dates.min()} → {dates.max()}")
dows = Counter(dates.dt.weekday)
print(f"Weekday dist (0=Mon..6=Sun): {dict(sorted(dows.items()))}")
# Check 2025 only
d25 = dates[dates.dt.year == 2025]
print(f"\n2025 dates: {len(d25)}")
print(f"2025 weekday dist: {dict(sorted(Counter(d25.dt.weekday).items()))}")
# Check 2026
d26 = dates[dates.dt.year == 2026]
print(f"\n2026 dates: {len(d26)}")
print(f"2026 weekday dist: {dict(sorted(Counter(d26.dt.weekday).items()))}")
# Check if any Saturday/Sunday in 2025+
weekends = dates[(dates.dt.year >= 2025) & (dates.dt.weekday >= 5)]
print(f"\nWeekends in 2025+: {len(weekends)}")
if len(weekends) > 0:
    print(weekends.head(10).tolist())
