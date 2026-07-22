#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""增量更新广期所铂钯仓单，并输出完整历史 CSV。"""
from __future__ import annotations

import csv
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "gfex"
WAREHOUSE_API = "http://www.gfex.com.cn/u/interfacesWebTdWbillWeeklyQuotes/loadList"
VARIETIES = [("pt", "铂"), ("pd", "钯")]
FIELDS = ["品种", "日期", "仓库代码", "仓库名称", "昨日仓单", "今日注册", "今日注销", "今日仓单", "增减"]


def weekdays(start: datetime, end: datetime):
    current = start
    while current.date() <= end.date():
        if current.weekday() < 5:
            yield current.strftime("%Y%m%d")
        current += timedelta(days=1)


def fetch(session: requests.Session, date8: str, code: str, name: str) -> list[dict]:
    response = session.post(WAREHOUSE_API, data={"gen_date": date8, "variety": code}, timeout=20)
    response.raise_for_status()
    result = response.json()
    records = []
    for item in result.get("data") or []:
        if item.get("variety") in {"总计", "小计"} or not item.get("genDate"):
            continue
        records.append({
            "品种": name,
            "日期": item.get("genDate", ""),
            "仓库代码": item.get("whCodeOrder", ""),
            "仓库名称": item.get("whAbbr", ""),
            "昨日仓单": item.get("lastWbillQty", 0),
            "今日注册": item.get("regWbillQty", 0),
            "今日注销": item.get("logoutWbillQty", 0),
            "今日仓单": item.get("wbillQty", 0),
            "增减": item.get("diff", 0),
        })
    return records


def main() -> int:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    candidates = sorted(DATA_DIR.glob("铂钯仓单数据_*.csv"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        print("未找到历史完整 CSV，请先运行 gfex_batch_fetch.py", file=sys.stderr)
        return 1
    source = candidates[-1]
    with source.open(encoding="utf-8-sig") as fh:
        existing = list(csv.DictReader(fh))
    if not existing:
        print(f"历史 CSV 为空: {source}", file=sys.stderr)
        return 1

    first_date = min(row["日期"] for row in existing)
    last_date = max(row["日期"] for row in existing)
    start = datetime.strptime(last_date, "%Y%m%d") + timedelta(days=1)
    end = datetime.now()
    dates = list(weekdays(start, end))
    if not dates:
        print(f"已是最新：{last_date}")
        return 0

    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    session.get("http://www.gfex.com.cn", timeout=20)
    new_rows: list[dict] = []
    for date8 in dates:
        day_rows = []
        for code, name in VARIETIES:
            day_rows.extend(fetch(session, date8, code, name))
        new_rows.extend(day_rows)
        print(f"{date8}: {len(day_rows)} 条")
        time.sleep(0.3)

    if not new_rows:
        print("交易所尚未发布新仓单数据；保留现有完整 CSV")
        return 0

    combined = existing + new_rows
    unique = {}
    for row in combined:
        key = (row["品种"], row["日期"], row["仓库代码"], row["仓库名称"])
        unique[key] = row
    combined = sorted(unique.values(), key=lambda r: (r["日期"], r["品种"], r["仓库代码"], r["仓库名称"]))
    latest_date = max(row["日期"] for row in combined)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    target = DATA_DIR / f"铂钯仓单数据_{first_date}_{latest_date}_{timestamp}.csv"
    with target.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(combined)
    print(f"[OK] 新增 {len(new_rows)} 条，完整历史截止 {latest_date}: {target.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

