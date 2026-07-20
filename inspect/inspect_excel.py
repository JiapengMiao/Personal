# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import pandas as pd
from pathlib import Path

BASE = Path(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-010-日度会议数据整理")

FILES = [
    "data/白银所有数据.xlsx",
    "data/季节图表.xlsx",
    "data/20260719租借利率.xlsx",
    "data/AG/AG(T+D).xlsx",
    "data/AG/AG所有合约数据.xlsx",
    "data/AG/虚实比数据.xlsx",
    "data/AG/合约参数.xlsx",
    "data/AG/外汇价格.xlsx",
    "data/AG/SPTAGUSDOZ_IDC.xlsx",
    "data/AG/Fig6_现货基差_数据统计_20260713_174644.xlsx",
]

def try_date_range(df):
    """Try to find a date-like column and report min/max."""
    for col in df.columns:
        c = str(col).lower()
        if any(k in c for k in ['date','time','日期','时间']):
            s = pd.to_datetime(df[col], errors='coerce')
            if s.notna().sum() > 0:
                return col, s.min(), s.max(), s.notna().sum()
    return None

for rel in FILES:
    p = BASE / rel
    print("="*100)
    print(f"FILE: {rel}")
    if not p.exists():
        print("  [MISSING]")
        continue
    try:
        xf = pd.ExcelFile(p, engine='openpyxl')
        print(f"  sheets ({len(xf.sheet_names)}): {xf.sheet_names}")
        for sh in xf.sheet_names:
            print(f"  ---- sheet: {sh}")
            try:
                # read limited rows for structure
                df = pd.read_excel(p, sheet_name=sh, engine='openpyxl', nrows=5)
                # total rows: read only first column
                col0 = pd.read_excel(p, sheet_name=sh, engine='openpyxl', usecols=[0])
                nrows = len(col0)
                print(f"    rows: {nrows}")
                print(f"    columns ({len(df.columns)}): {list(df.columns)}")
                # date range from full first read of the date col
                full = pd.read_excel(p, sheet_name=sh, engine='openpyxl')
                dr = try_date_range(full)
                if dr:
                    print(f"    date col: '{dr[0]}'  min={dr[1]}  max={dr[2]}  valid={dr[3]}/{len(full)}")
                else:
                    print("    date col: none detected")
                print("    head(3):")
                with pd.option_context('display.max_columns', None, 'display.width', 220, 'display.max_colwidth', 28):
                    print(df.head(3).to_string(index=False))
            except Exception as e:
                print(f"    [sheet error] {type(e).__name__}: {e}")
    except Exception as e:
        print(f"  [file error] {type(e).__name__}: {e}")
