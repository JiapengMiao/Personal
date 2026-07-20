# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
from pathlib import Path
BASE = Path(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-010-日度会议数据整理")
lr = BASE / "data/20260719租借利率.xlsx"
hdr = pd.read_excel(lr, sheet_name=0, engine='openpyxl', header=None, nrows=8)
names = hdr.iloc[7].tolist()
print("all column names (row idx 7):", names)
d = pd.read_excel(lr, sheet_name=0, engine='openpyxl', header=None, skiprows=8)
t = pd.to_datetime(d.iloc[:,0], errors='coerce')
print("date range:", t.min(), "->", t.max(), "rows:", len(d))
# find silver columns
for i, n in enumerate(names):
    if isinstance(n, str) and ('银' in n or '金' in n):
        s = pd.to_numeric(d.iloc[:, i], errors='coerce')
        print(f"  col{i} {n}: valid={s.notna().sum()}, latest={d.iloc[0,i]}")
