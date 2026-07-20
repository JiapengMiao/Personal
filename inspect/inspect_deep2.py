# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-010-日度会议数据整理")
MASTER = BASE / "data/白银所有数据.xlsx"
pd.set_option('display.max_columns', None); pd.set_option('display.width', 250); pd.set_option('display.max_colwidth', 30)

def wind_ts(path, sheet, label):
    # data starts at excel row 7 (0-indexed 6)
    d = pd.read_excel(path, sheet_name=sheet, engine='openpyxl', header=None, skiprows=6)
    t = pd.to_datetime(d.iloc[:,0], errors='coerce')
    print(f"[{label}] rows={len(d)} time {t.min()} -> {t.max()} cols={d.shape[1]}")
    print("  first:", d.iloc[0,0], d.iloc[0,1], "| last:", d.iloc[-1,0], d.iloc[-1,1])
    return d

wind_ts(MASTER, 'AG（T+D）', 'AG(T+D) master')
wind_ts(MASTER, 'AG所有合约数据', 'AG所有合约 master')
wind_ts(MASTER, 'SPTAGUSDOZ_IDZ', 'SPTAGUSDOZ master')
wind_ts(MASTER, '外汇价格', '外汇 master')

print("\n### AG所有合约数据 列头（第3行证券代码）")
hdr = pd.read_excel(MASTER, sheet_name='AG所有合约数据', engine='openpyxl', header=None, nrows=4)
codes = hdr.iloc[2].tolist()
print("证券代码 row:", codes)

print("\n### 虚实比数据 前10行")
raw = pd.read_excel(MASTER, sheet_name='虚实比数据', engine='openpyxl', header=None, nrows=10)
print(raw.to_string())
d = pd.read_excel(MASTER, sheet_name='虚实比数据', engine='openpyxl', header=None, skiprows=5)
t = pd.to_datetime(d.iloc[:,0], errors='coerce')
print("data rows:", len(d), "range:", t.min(), "->", t.max())
print("sample rows (first 4 cols + col15-17):")
print(d.iloc[:3, [0,1,2,3,15,16,17]].to_string())
# non-null counts per column
nn = d.notna().sum()
print("non-null counts:", nn.tolist())

print("\n### 铂钯 前10行")
raw = pd.read_excel(MASTER, sheet_name='铂钯', engine='openpyxl', header=None, nrows=10)
print(raw.to_string())
d = pd.read_excel(MASTER, sheet_name='铂钯', engine='openpyxl', header=None, skiprows=5)
print("rows:", len(d))
for c in range(d.shape[1]):
    s = pd.to_datetime(d.iloc[:,c], errors='coerce')
    if s.notna().sum()>50:
        print(f"  date col {c}: {s.min()} -> {s.max()} valid={s.notna().sum()}")

print("\n### 季节图表 前6行")
raw = pd.read_excel(MASTER, sheet_name='季节图表', engine='openpyxl', header=None, nrows=6)
print(raw.to_string())

print("\n### 租借利率 前12行 + 尾部")
lr = BASE / "data/20260719租借利率.xlsx"
raw = pd.read_excel(lr, sheet_name=0, engine='openpyxl', header=None, nrows=12)
print(raw.iloc[:, :6].to_string())
full = pd.read_excel(lr, sheet_name=0, engine='openpyxl', header=None)
print("tail rows:"); print(full.tail(3).iloc[:, :6].to_string())
print("shape:", full.shape)
