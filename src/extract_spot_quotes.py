# -*- coding: utf-8 -*-
"""从白银每日报价 Excel 提取最新日期报价块，输出 spot_quotes.json。"""
import json
from datetime import datetime
from pathlib import Path
from openpyxl import load_workbook

XLSX = Path(r"C:\Users\56558\Nutstore\1\金属投研小组\MJP-苗嘉鹏\数据计算\白银报价\白银每日报价.xlsx")
OUT = Path(__file__).resolve().parent.parent / "web" / "public" / "data" / "spot_quotes.json"

def main():
    wb = load_workbook(str(XLSX), read_only=True, data_only=True)
    ws = wb[wb.sheetnames[0]]
    rows = list(ws.iter_rows(min_row=3, values_only=True))
    wb.close()

    # 找最新日期
    last_date = None
    last_idx = None
    for i in range(len(rows) - 1, -1, -1):
        if rows[i][0] is not None:
            last_date = rows[i][0]
            last_idx = i
            break
    if last_date is None:
        print("无数据"); return

    date_str = last_date.strftime("%Y-%m-%d") if isinstance(last_date, datetime) else str(last_date)[:10]

    # 收集该日期块
    block = []
    for i in range(last_idx, len(rows)):
        r = rows[i]
        if i > last_idx and r[0] is not None:
            break
        block.append(r)

    # 第一行的 J 列是 TD-沪银价差
    td_spread = block[0][9] if len(block[0]) > 9 else None

    quotes = []
    for r in block:
        name = r[1]
        if not name:
            continue
        quotes.append({
            "name": name,
            "factorySh": str(r[2]) if r[2] else None,
            "factoryGd": str(r[3]) if r[3] else None,
            "factoryCt": str(r[4]) if r[4] else None,
            "stdSh": str(r[5]) if r[5] else None,
            "stdGd": str(r[6]) if r[6] else None,
            "stdCt": str(r[7]) if r[7] else None,
            "note": str(r[8]) if r[8] else None,
        })

    result = {
        "date": date_str,
        "tdFuturesSpread": str(td_spread) if td_spread else None,
        "count": len(quotes),
        "quotedCount": sum(1 for q in quotes if any([q["factorySh"], q["factoryGd"], q["factoryCt"], q["stdSh"], q["stdGd"], q["stdCt"]])),
        "quotes": quotes,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"[OK] spot_quotes.json ({date_str}, {len(quotes)} 家, {result['quotedCount']} 家有报价)")

if __name__ == "__main__":
    main()
