#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_lhb.py — 龙虎榜（上期所成交持仓排名）数据管道

读 010 每日已抓好的 SHFE_PM xlsx，复刻 get_lhb_tot_fig9.py 的加工逻辑：
  买卖 outer merge → 净持仓=买−卖 → 多头净持仓降序 TOP20 / 空头净持仓升序 TOP20
输出 web/public/data/lhb.json

用法: python src/build_lhb.py
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
SHFE_DIR = Path(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-010-日度会议数据整理\output\SHFE_PM")
OUT = ROOT / "web" / "public" / "data" / "lhb.json"


def find_latest_xlsx() -> Path:
    """找 SHFE_PM 目录下日期最新的 xlsx。"""
    cands = sorted(SHFE_DIR.glob("*成交持仓排名.xlsx"))
    if not cands:
        raise FileNotFoundError(f"未找到龙虎榜 xlsx：{SHFE_DIR}")
    return cands[-1]


def extract_date(path: Path) -> str:
    """从文件名提取日期 YYYY-MM-DD。"""
    m = re.search(r"(\d{8})", path.stem)
    if not m:
        return datetime.now().strftime("%Y-%m-%d")
    d = m.group(1)
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}"


def process_contract_sheet(df: pd.DataFrame) -> dict:
    """复刻 process_sheet_for_dragon_tiger：买卖 outer merge → 净持仓 → 排序 TOP20。"""
    # 提取买方
    buy_cols = ["持买单量会员简称", "持买单量", "持买单量比上交易日增减"]
    buy_df = df[buy_cols].dropna(subset=["持买单量会员简称", "持买单量"])
    buy_df = buy_df.copy()
    buy_df.columns = ["会员", "买量", "买增"]
    buy_df["买量"] = pd.to_numeric(buy_df["买量"], errors="coerce").fillna(0).astype(int)
    buy_df["买增"] = pd.to_numeric(buy_df["买增"], errors="coerce").fillna(0).astype(int)
    buy_agg = buy_df.groupby("会员").agg({"买量": "sum", "买增": "sum"}).reset_index()

    # 提取卖方
    sell_cols = ["持卖单量会员简称", "持卖单量", "持卖单量比上交易日增减"]
    sell_df = df[sell_cols].dropna(subset=["持卖单量会员简称", "持卖单量"])
    sell_df = sell_df.copy()
    sell_df.columns = ["会员", "卖量", "卖增"]
    sell_df["卖量"] = pd.to_numeric(sell_df["卖量"], errors="coerce").fillna(0).astype(int)
    sell_df["卖增"] = pd.to_numeric(sell_df["卖增"], errors="coerce").fillna(0).astype(int)
    sell_agg = sell_df.groupby("会员").agg({"卖量": "sum", "卖增": "sum"}).reset_index()

    # outer merge
    merged = pd.merge(buy_agg, sell_agg, on="会员", how="outer").fillna(0)
    merged["净持仓"] = (merged["买量"] - merged["卖量"]).astype(int)
    merged["买增"] = merged["买增"].astype(int)
    merged["卖增"] = merged["卖增"].astype(int)

    # 多头榜：买量>0，按净持仓降序，TOP20
    long_df = merged[merged["买量"] > 0].sort_values("净持仓", ascending=False).head(20)
    long_list = [
        {"rank": i + 1, "member": row["会员"], "position": int(row["买量"]),
         "change": int(row["买增"]), "net": int(row["净持仓"])}
        for i, (_, row) in enumerate(long_df.iterrows())
    ]

    # 空头榜：卖量>0，按净持仓升序，TOP20
    short_df = merged[merged["卖量"] > 0].sort_values("净持仓", ascending=True).head(20)
    short_list = [
        {"rank": i + 1, "member": row["会员"], "position": int(row["卖量"]),
         "change": int(row["卖增"]), "net": int(row["净持仓"])}
        for i, (_, row) in enumerate(short_df.iterrows())
    ]

    return {"long": long_list, "short": short_list}


def main():
    xlsx = find_latest_xlsx()
    date_str = extract_date(xlsx)
    print(f"[lhb] 读取 {xlsx.name} (date={date_str})")

    xl = pd.ExcelFile(xlsx)
    # 只取合约 sheet（AG 开头+含数字），排除"品种汇总"
    contract_sheets = [s for s in xl.sheet_names if re.match(r"AG\d", s, re.I)]
    contract_sheets.sort(key=lambda s: re.sub(r"\D", "", s))
    print(f"[lhb] 合约 sheets: {contract_sheets}")

    contracts = []
    for sn in contract_sheets:
        df = xl.parse(sn)
        code = sn.lower()  # ag2608
        result = process_contract_sheet(df)
        contracts.append({"code": code, **result})
        print(f"  {code}: long={len(result['long'])} short={len(result['short'])}")

    out = {
        "date": date_str,
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "contracts": contracts,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=None), encoding="utf-8")
    print(f"[lhb] OK → {OUT} ({OUT.stat().st_size} bytes, {len(contracts)} 合约)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
