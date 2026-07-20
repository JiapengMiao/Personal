# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-010-日度会议数据整理")
MASTER = BASE / "data/白银所有数据.xlsx"

pd.set_option('display.max_columns', None)
pd.set_option('display.width', 250)
pd.set_option('display.max_colwidth', 30)

def raw_rows(path, sheet, n=10, usecols=None):
    df = pd.read_excel(path, sheet_name=sheet, engine='openpyxl', header=None, nrows=n, usecols=usecols)
    return df

print("### 1) 白银数据 sheet: 第1列前10行 + 日期范围")
df = pd.read_excel(MASTER, sheet_name='白银数据', engine='openpyxl', header=None, usecols=[0])
print(df.head(10).to_string())
dates = pd.to_datetime(df.iloc[2:, 0], errors='coerce')
print("date range:", dates.min(), "->", dates.max(), "valid:", dates.notna().sum())

print("\n### 2) AG（T+D）sheet: 前8行原始")
print(raw_rows(MASTER, 'AG（T+D）', 8).to_string())
d = pd.read_excel(MASTER, sheet_name='AG（T+D）', engine='openpyxl', header=None, skiprows=5)
d.columns = ['time','close']
print("data rows:", len(d), "range:", d['time'].min(), "->", d['time'].max())
print(d.head(2).to_string())

print("\n### 3) AG所有合约数据 sheet: 前7行(前6列)")
print(raw_rows(MASTER, 'AG所有合约数据', 7, usecols=list(range(6))).to_string())
d = pd.read_excel(MASTER, sheet_name='AG所有合约数据', engine='openpyxl', header=None, skiprows=5)
print("data rows:", len(d), "range:", pd.to_datetime(d.iloc[:,0], errors='coerce').min(), "->", pd.to_datetime(d.iloc[:,0], errors='coerce').max())
print("tail(2):"); print(d.tail(2).iloc[:, :6].to_string())

print("\n### 4) SPTAGUSDOZ_IDZ sheet: 前8行")
print(raw_rows(MASTER, 'SPTAGUSDOZ_IDZ', 8).to_string())
d = pd.read_excel(MASTER, sheet_name='SPTAGUSDOZ_IDZ', engine='openpyxl', header=None, skiprows=5)
print("data rows:", len(d), "range:", d.iloc[:,0].min(), "->", d.iloc[:,0].max())

print("\n### 5) 外汇价格 sheet: 前8行")
print(raw_rows(MASTER, '外汇价格', 8).to_string())
d = pd.read_excel(MASTER, sheet_name='外汇价格', engine='openpyxl', header=None, skiprows=5)
print("data rows:", len(d), "range:", d.iloc[:,0].min(), "->", d.iloc[:,0].max())

print("\n### 6) 虚实比数据 sheet: 前10行（全部列）")
print(raw_rows(MASTER, '虚实比数据', 10).to_string())

print("\n### 7) 铂钯 sheet: 前10行")
print(raw_rows(MASTER, '铂钯', 10).to_string())

print("\n### 8) 季节图表 sheet: 前6行")
print(raw_rows(MASTER, '季节图表', 6).to_string())

print("\n### 9) 租借利率 xlsx: 前10行 + 日期范围")
lr = BASE / "data/20260719租借利率.xlsx"
df = pd.read_excel(lr, sheet_name=0, engine='openpyxl', header=None, nrows=10)
print(df.to_string())
full = pd.read_excel(lr, sheet_name=0, engine='openpyxl', header=None, usecols=[0])
print("col0 tail:"); print(full.tail(3).to_string())
