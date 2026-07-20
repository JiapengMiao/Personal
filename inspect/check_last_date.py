import pandas as pd
df = pd.read_excel(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\data\010源数据\白银所有数据.xlsx", sheet_name="白银数据", header=None, usecols=[0])
dates = pd.to_datetime(df.iloc[2:, 0], errors="coerce").dropna()
print(f"Last date in main table: {dates.iloc[-1]}")
print(f"Max date: {dates.max()}")
