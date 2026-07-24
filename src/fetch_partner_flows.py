#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_partner_flows.py

拉取 2025 全年官方海关白银（HS/HTS 7106）按伙伴国/地区拆分，供
「全球银条流向」卡片的官方补充组使用：

1. 美国进口/出口：USITC DataWeb（美国 Census 官方），General Imports /
   Total Exports，Break Out Countries；GM（克）与 CGM（含量克）加总 ÷1e6 得吨，
   与 fetch_us_trade_history.py 口径一致。
2. 印度出口：TradeStat 印度商务部 commodity_wise_all_countries_export，
   Calendar Year 2025 的 Jan-Dec 累计列，千克 ÷1000 得吨，
   并与 india_silver_trade_monthly.csv 的 2025 合计交叉校验。
3. 香港进口：政府统计处 IDDS（QCy 年度数量），进口按原产地
   （coclass=C, co=ALL），千克 ÷1000 得吨，
   并与 hk_silver_trade.csv 的 2025 进口合计交叉校验。

用法:  python src/fetch_partner_flows.py
"""
from __future__ import annotations

import csv
import http.cookiejar
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from fetch_us_trade_history import (  # noqa: E402
    DataWebClient,
    MONTH_LABELS,
    RUN_REPORT_URL,
    SYSTEM_QUERIES_URL,
    UNIT_TO_GRAMS,
    build_query,
    choose_template,
    parse_number,
)

YEAR = 2025

OUT_US = ROOT / "data" / "us" / f"us_silver_trade_partners_{YEAR}.csv"
OUT_IN = ROOT / "data" / "india" / f"india_silver_export_partners_{YEAR}.csv"
OUT_HK = ROOT / "data" / f"hk_silver_import_partners_{YEAR}.csv"
CACHE_US = ROOT / "data" / "us" / "dataweb_cache"
CACHE_IN = ROOT / "data" / "india" / f"india_export_partners_cy{YEAR}.html"
CACHE_HK = ROOT / "data" / f"hk_silver_import_partners_{YEAR}.json"

IN_URL = "https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_export"
HK_API = "https://tradeidds.censtatd.gov.hk/api/get"
UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)


# ——— 美国：USITC DataWeb Break Out Countries ———
def fetch_us() -> dict[str, dict[str, float]]:
    """返回 {flow: {partner_en: tonnes}}，flow ∈ general_import / total_export"""
    client = DataWebClient()
    template = choose_template(client.get_json(SYSTEM_QUERIES_URL))
    specs = [
        ("general_import", "GenImp", "GEN_FIR_UNIT_QUANTITY"),
        ("total_export", "TotExp", "FIRST_UNIT_QUANTITY"),
    ]
    result: dict[str, dict[str, float]] = {}
    CACHE_US.mkdir(parents=True, exist_ok=True)
    for flow, trade_type, measure in specs:
        print(f"[US] {flow} {YEAR} Break Out Countries ...", flush=True)
        query = build_query(template, years=[YEAR], trade_type=trade_type, measure=measure)
        query["searchOptions"]["countries"]["aggregation"] = "Break Out Countries"
        response = client.post_json(RUN_REPORT_URL, query)
        cache = CACHE_US / f"partner_{flow}_{YEAR}_hs7106.json"
        cache.write_text(
            json.dumps({"query": query, "response": response}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  [CACHE] {cache.relative_to(ROOT)}", flush=True)

        tables = response.get("dto", {}).get("tables", [])
        if not tables:
            raise RuntimeError(f"DataWeb returned no table for partner {flow}")
        table = tables[0]
        columns = [
            str(c.get("label") or "")
            for g in table.get("column_groups", [])
            for c in g.get("columns", [])
        ]
        if "Country" not in columns or "Quantity Description" not in columns:
            raise RuntimeError(f"Unexpected partner columns for {flow}: {columns}")

        grams_by_partner: dict[str, Decimal] = defaultdict(Decimal)
        for group in table.get("row_groups", []):
            for row in group.get("rowsNew", []):
                values = [e.get("value") for e in row.get("rowEntries", [])]
                record = dict(zip(columns, values))
                partner = str(record.get("Country") or "").strip()
                year_text = str(record.get("Year") or "").strip()
                unit = str(record.get("Quantity Description") or "").strip()
                if not partner or year_text != str(YEAR) or not unit:
                    continue
                multiplier = UNIT_TO_GRAMS.get(unit.casefold())
                if multiplier is None:
                    raise ValueError(f"Unsupported unit: {unit!r}")
                for label in MONTH_LABELS:
                    quantity, _ = parse_number(record.get(label))
                    if quantity is not None:
                        grams_by_partner[partner] += quantity * multiplier

        tonnes = {
            p: float((g / Decimal("1000000")).quantize(Decimal("0.000001")))
            for p, g in grams_by_partner.items()
            if g > 0
        }
        result[flow] = dict(sorted(tonnes.items(), key=lambda kv: -kv[1]))
        print(f"  {flow}: {len(result[flow])} 个伙伴，合计 {sum(result[flow].values()):,.3f} 吨", flush=True)
        time.sleep(1)
    return result


# ——— 印度：TradeStat commodity_wise_all_countries_export ———
class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag, attrs) -> None:  # noqa: ANN001
        tag = tag.lower()
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._row is not None and self._cell is not None:
            self._row.append(" ".join("".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None


def fetch_india() -> dict[str, float]:
    """返回 {partner_en: tonnes}（印度出口，Calendar Year 2025）"""
    print(f"[IN] exports by partner CY{YEAR} ...", flush=True)
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
    html = opener.open(
        urllib.request.Request(IN_URL, headers={"User-Agent": UA}), timeout=60
    ).read().decode("utf-8", "replace")
    token = re.search(r'name="_token"\s+value="([^"]+)"', html)
    if not token:
        raise RuntimeError("TradeStat CSRF token not found (all-countries export)")
    fields = {
        "_token": token.group(1),
        "cwacexHSCODE": "7106",
        "hscode_value": "",
        "description_value": "",
        "cwacexMonth": "12",
        "cwacexYear": str(YEAR),
        "cwacexReportVal": "2",  # Quantity
        "cwacexReportYear": "2",  # Calendar Year
    }
    request = urllib.request.Request(
        IN_URL,
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={
            "User-Agent": UA,
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": IN_URL,
        },
        method="POST",
    )
    resp = opener.open(request, timeout=60).read().decode("utf-8", "replace")
    CACHE_IN.parent.mkdir(parents=True, exist_ok=True)
    CACHE_IN.write_text(resp, encoding="utf-8")
    print(f"  [CACHE] {CACHE_IN.relative_to(ROOT)}", flush=True)

    parser = _TableParser()
    parser.feed(resp)
    header = next((r for r in parser.rows if r and "Country" in r), None)
    if not header:
        raise RuntimeError("TradeStat partner table header not found")
    cy_col = next(
        (i for i, h in enumerate(header) if h.replace(" ", "").startswith(f"Jan-Dec{YEAR}")),
        None,
    )
    if cy_col is None:
        raise RuntimeError(f"Jan-Dec{YEAR} column not found in {header}")

    kg_by_partner: dict[str, int] = {}
    official_total = None
    for row in parser.rows:
        if len(row) <= cy_col:
            continue
        if row[0].isdigit():
            kg = int(round(float(row[cy_col].replace(",", "") or 0)))
            if kg > 0:
                kg_by_partner[row[1].strip()] = kg
        elif "Total" in row:
            official_total = int(round(float(row[cy_col].replace(",", "") or 0)))

    summed = sum(kg_by_partner.values())
    print(f"  伙伴合计 {summed:,} kg vs 报表 Total {official_total:,} kg", flush=True)
    if official_total is not None and summed != official_total:
        raise RuntimeError("TradeStat partner sum does not match the report total row")

    # 与月度 CSV 的 2025 出口合计交叉校验
    with (ROOT / "data" / "india" / "india_silver_trade_monthly.csv").open(
        encoding="utf-8-sig", newline=""
    ) as fh:
        monthly_total = sum(
            int(r["exports_kg"]) for r in csv.DictReader(fh) if r["month"].startswith(str(YEAR))
        )
    print(f"  与月度 CSV {YEAR} 出口合计 {monthly_total:,} kg 交叉校验", flush=True)
    if summed != monthly_total:
        raise RuntimeError(f"Partner total {summed} != monthly CSV total {monthly_total}")

    tonnes = {p: round(kg / 1000.0, 6) for p, kg in kg_by_partner.items()}
    out = dict(sorted(tonnes.items(), key=lambda kv: -kv[1]))
    print(f"  {len(out)} 个伙伴，合计 {sum(out.values()):,.3f} 吨", flush=True)
    return out


# ——— 香港：政府统计处 IDDS 进口按原产地 ———
def fetch_hk() -> dict[str, float]:
    """返回 {partner_en: tonnes}（香港进口按原产地，2025 年度）"""
    print(f"[HK] imports by origin {YEAR} ...", flush=True)
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    def get(params: dict[str, str]) -> dict:
        url = HK_API + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
        return json.loads(opener.open(req, timeout=60).read().decode())

    kg_by_partner: dict[str, int] = defaultdict(int)
    raw_rows: list[dict] = []
    for code in ["710610", "710691", "710692"]:
        data = get({
            "lang": "EN", "sv": "QCy", "freq": "A",
            "period": f"{YEAR},{YEAR}", "ttype": "1",
            "codeclass": "HKHS6", "code": code,
            "coclass": "C", "co": "ALL",
        })
        status = data.get("header", {}).get("status", {})
        if status.get("code") != 0:
            raise RuntimeError(f"HK IDDS {code}: {status.get('name')}")
        rows = data.get("dataSet", [])
        print(f"  QCy {code}: {len(rows)} 个原产地", flush=True)
        for r in rows:
            name = str(r.get("coDescEN") or r.get("co") or "").strip()
            if name:
                kg_by_partner[name] += int(r["figure"])
                raw_rows.append(r)
        time.sleep(0.5)

    CACHE_HK.write_text(
        json.dumps({"year": YEAR, "rows": raw_rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  [CACHE] {CACHE_HK.relative_to(ROOT)}", flush=True)

    # 与 hk_silver_trade.csv 的 2025 进口合计交叉校验（容忍 0.5%，口径/修订差异）
    summed_t = sum(kg_by_partner.values()) / 1000.0
    with (ROOT / "data" / "hk_silver_trade.csv").open(encoding="utf-8-sig", newline="") as fh:
        monthly_total = sum(
            float(r["进口数量(吨)"]) for r in csv.DictReader(fh) if r["月份"].startswith(str(YEAR))
        )
    diff = abs(summed_t - monthly_total) / monthly_total if monthly_total else 1
    print(
        f"  伙伴合计 {summed_t:,.1f} 吨 vs 月度 CSV {YEAR} 进口 {monthly_total:,.1f} 吨（偏差 {diff*100:.2f}%）",
        flush=True,
    )
    if diff > 0.005:
        raise RuntimeError("HK partner total deviates from monthly CSV by >0.5%")

    tonnes = {p: round(kg / 1000.0, 6) for p, kg in kg_by_partner.items()}
    out = dict(sorted(tonnes.items(), key=lambda kv: -kv[1]))
    print(f"  {len(out)} 个原产地，合计 {sum(out.values()):,.3f} 吨", flush=True)
    return out


def write_csv(path: Path, rows: list[tuple[str, str, float]], source: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["flow", "partner_en", "tonnes", "year", "source"])
        writer.writerows(rows)
    print(f"[OK] {path.relative_to(ROOT)} ({len(rows)} rows)", flush=True)


def main() -> None:
    us = fetch_us()
    india = fetch_india()
    hk = fetch_hk()

    src_us = "USITC DataWeb / U.S. Census · HS/HTS 7106 · GM+CGM→吨"
    src_in = "India DoC TradeStat / DGCI&S · HS7106 · CY2025 Jan-Dec"
    src_hk = "香港政府统计处 IDDS · HKHS6 7106 · QCy 原产地"
    us_rows = [("export", p, t) for p, t in us["total_export"].items()] + [
        ("import", p, t) for p, t in us["general_import"].items()
    ]
    write_csv(OUT_US, us_rows, src_us)
    write_csv(OUT_IN, [("export", p, t) for p, t in india.items()], src_in)
    write_csv(OUT_HK, [("import", p, t) for p, t in hk.items()], src_hk)
    print("[DONE] partner flows fetched")


if __name__ == "__main__":
    main()
