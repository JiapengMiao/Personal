#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_hk_trade.py

读取 data/hk_silver_trade.csv（政府统计处 HS7106 白银月度进出口，吨），
输出 web/public/data/hk_trade.json 供 07 香港进出口区块使用。

用法:  python src/build_hk_trade.py
"""
import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "data" / "hk_silver_trade.csv"
OUT = ROOT / "web" / "public" / "data" / "hk_trade.json"


def main() -> None:
    with open(SRC, encoding="utf-8-sig") as fh:
        rows = sorted(csv.DictReader(fh), key=lambda r: r["月份"])

    out = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "政府统计处对外商品贸易统计 · HS7106",
        "unit": "吨",
        "asOf": rows[-1]["月份"],
        "months": [r["月份"] for r in rows],
        "imports": [float(r["进口数量(吨)"]) for r in rows],
        "exports": [float(r["出口总额数量(吨)"]) for r in rows],
        "reexports": [float(r["转口数量(吨)"]) for r in rows],
        "net": [float(r["净流入数量(吨)"]) for r in rows],  # 进口-出口（净流入）
        "importsUsdM": [float(r["进口货值(亿美元)"]) for r in rows],
        "exportsUsdM": [float(r["出口总额货值(亿美元)"]) for r in rows],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[OK] hk_trade.json: {len(rows)} 个月（{rows[0]['月份']}~{rows[-1]['月份']}），{OUT.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
