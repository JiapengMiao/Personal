#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_lhb.py — 龙虎榜（上期所成交持仓排名）数据管道

读 data/shfe/lhb/ 中每日已抓好的全部 SHFE_PM xlsx，复刻原加工逻辑：
  买卖 outer merge → 净持仓=买−卖 → 多头净持仓降序 TOP20 / 空头净持仓升序 TOP20
输出含全部可用交易日的 web/public/data/lhb.json，最新日期仍保留在顶层兼容旧前端。

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
SHFE_DIR = ROOT / "data" / "shfe" / "lhb"
RANKING_DIR = ROOT / "data" / "shfe" / "ranking"
OUT = ROOT / "web" / "public" / "data" / "lhb.json"


def find_all_snapshots() -> list[tuple[str, Path, str]]:
    """按交易日汇总龙虎榜源文件。

    历史数据使用已归档的 xlsx；当日数据优先从 SHFE 增量采集器的原始排名 JSON
    直接重建。两者字段来自同一份上期所 pmYYYYMMDD.dat，避免网页更新时龙虎榜
    仍停留在旧的 xlsx 文件。
    """
    by_date: dict[str, tuple[Path, str]] = {}
    for xlsx in SHFE_DIR.glob("*成交持仓排名.xlsx"):
        by_date[extract_date(xlsx)] = (xlsx, "xlsx")
    for raw_json in RANKING_DIR.glob("*/silver_ranking_*.json"):
        # 已有历史 xlsx 时保持其既有口径；最新增量日通常只有 JSON。
        by_date.setdefault(extract_date(raw_json), (raw_json, "json"))
    if not by_date:
        raise FileNotFoundError(f"未找到龙虎榜源文件：{SHFE_DIR} 或 {RANKING_DIR}")
    return [(day, *by_date[day]) for day in sorted(by_date)]


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


def process_workbook(xlsx: Path) -> dict:
    """解析单个交易日工作簿。"""
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

    return {"date": date_str, "contracts": contracts}


def process_ranking_json(raw_json: Path) -> dict:
    """把 SHFE 增量采集器保存的原始排名 JSON 转为龙虎榜结构。"""
    date_str = extract_date(raw_json)
    print(f"[lhb] 读取 SHFE 原始排名 {raw_json.name} (date={date_str})")
    records = json.loads(raw_json.read_text(encoding="utf-8"))
    raw_df = pd.DataFrame(records)
    if raw_df.empty:
        raise ValueError(f"SHFE 原始排名为空：{raw_json}")

    raw_df["INSTRUMENTID"] = raw_df["INSTRUMENTID"].astype(str).str.strip().str.lower()
    raw_df["RANK"] = pd.to_numeric(raw_df["RANK"], errors="coerce")
    # 仅保留实际合约的前 20 名，排除 agall 汇总及 rank=999 总计行。
    raw_df = raw_df[
        raw_df["INSTRUMENTID"].str.fullmatch(r"ag\d+")
        & raw_df["RANK"].between(1, 20)
    ].copy()
    if raw_df.empty:
        raise ValueError(f"SHFE 原始排名未找到 AG 合约前 20 名：{raw_json}")

    contracts = []
    for code, frame in raw_df.groupby("INSTRUMENTID", sort=True):
        normalized = pd.DataFrame({
            "持买单量会员简称": frame.get("PARTICIPANTABBR2"),
            "持买单量": frame.get("CJ2"),
            "持买单量比上交易日增减": frame.get("CJ2_CHG"),
            "持卖单量会员简称": frame.get("PARTICIPANTABBR3"),
            "持卖单量": frame.get("CJ3"),
            "持卖单量比上交易日增减": frame.get("CJ3_CHG"),
        }).replace("", pd.NA)
        result = process_contract_sheet(normalized)
        contracts.append({"code": code, **result})
        print(f"  {code}: long={len(result['long'])} short={len(result['short'])}")
    return {"date": date_str, "contracts": contracts}


def main():
    snapshots = [
        process_workbook(path) if source_kind == "xlsx" else process_ranking_json(path)
        for _, path, source_kind in find_all_snapshots()
    ]
    latest = snapshots[-1]
    out = {
        "date": latest["date"],
        "generatedAt": datetime.now().isoformat(timespec="seconds"),
        "contracts": latest["contracts"],
        "dates": snapshots,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=None), encoding="utf-8")
    print(
        f"[lhb] OK → {OUT} ({OUT.stat().st_size} bytes, "
        f"{len(snapshots)} 个交易日, 最新 {len(latest['contracts'])} 合约)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
