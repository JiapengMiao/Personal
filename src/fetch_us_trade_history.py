#!/usr/bin/env python3
"""Fetch the full official U.S. monthly HS/HTS 7106 quantity history.

USITC DataWeb republishes the official U.S. Census merchandise-trade
statistics and exposes public, reproducible report queries.  The electronic
series starts in 1989.  This collector requests:

* general imports, first unit of quantity;
* total exports, first unit of quantity;
* world total, all districts, HS/HTS heading 7106;
* monthly frequency.

DataWeb returns gram (GM) and component-gram (CGM) rows separately.  Both are
silver mass/content measures, so the two rows are converted to grams, summed,
and divided by 1,000,000 to obtain tonnes.  No annual-to-month allocation,
interpolation, or other estimated filling is performed.
"""
from __future__ import annotations

import argparse
import copy
import csv
import http.cookiejar
import json
import re
import urllib.error
import urllib.request
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
US_DIR = ROOT / "data" / "us"
CACHE_DIR = US_DIR / "dataweb_cache"
OUT_COMPILED = US_DIR / "us_silver_trade_compiled.csv"
OUT_MONTHLY = US_DIR / "us_silver_trade_monthly.csv"
OUT_CODES = US_DIR / "us_silver_trade_by_code.csv"
OUT_NOTES = US_DIR / "us_silver_trade_notes.md"
OUT_JSON = ROOT / "web" / "public" / "data" / "us_trade.json"

DATAWEB_BASE = "https://datawebws.usitc.gov/dataweb"
DATAWEB_SITE = "https://dataweb.usitc.gov/"
SYSTEM_QUERIES_URL = f"{DATAWEB_BASE}/api/v2/savedQuery/getAllSystemSavedQueries"
RUN_REPORT_URL = f"{DATAWEB_BASE}/api/v2/report2/runReport"
GLOBAL_VARS_URL = f"{DATAWEB_BASE}/api/v2/query/getGlobalVars"
CENSUS_PRODUCTS_URL = "https://www.census.gov/foreign-trade/data/dataproducts.html"
CENSUS_RELEASE_URL = "https://www.census.gov/foreign-trade/schedule.html"
SOURCE = "USITC DataWeb · official U.S. Census trade statistics"
SERIES = "us_dataweb_census_hs7106"

MONTH_LABELS = [
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]

UNIT_TO_GRAMS = {
    "gram": Decimal("1"),
    "grams": Decimal("1"),
    "component gram": Decimal("1"),
    "component grams": Decimal("1"),
    "kilogram": Decimal("1000"),
    "kilograms": Decimal("1000"),
    "component kilogram": Decimal("1000"),
    "component kilograms": Decimal("1000"),
    "metric ton": Decimal("1000000"),
    "metric tons": Decimal("1000000"),
    "metric tonne": Decimal("1000000"),
    "metric tonnes": Decimal("1000000"),
    "component metric ton": Decimal("1000000"),
    "component metric tons": Decimal("1000000"),
}


def parse_period(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if not match:
        raise argparse.ArgumentTypeError("Use YYYY-MM, for example 2026-06")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise argparse.ArgumentTypeError("Month must be 01-12")
    return year, month


def month_range(start_year: int, end_year: int, end_month: int) -> list[str]:
    return [
        f"{year}-{month:02d}"
        for year in range(start_year, end_year + 1)
        for month in range(1, (end_month if year == end_year else 12) + 1)
    ]


class DataWebClient:
    """Small cookie-aware client for the public DataWeb report endpoint."""

    def __init__(self) -> None:
        self.cookie_jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cookie_jar)
        )
        self.base_headers = {
            "User-Agent": "Project-002-US-silver-history/1.0",
            "Origin": DATAWEB_SITE.rstrip("/"),
            "Referer": DATAWEB_SITE,
        }

    def _xsrf_header(self) -> dict[str, str]:
        for cookie in self.cookie_jar:
            if cookie.name == "XSRF-TOKEN":
                return {"X-XSRF-TOKEN": cookie.value}
        return {}

    def get_json(self, url: str, timeout: int = 60) -> Any:
        request = urllib.request.Request(url, headers=self.base_headers)
        with self.opener.open(request, timeout=timeout) as response:
            return json.load(response)

    def post_json(self, url: str, payload: Any, timeout: int = 300) -> Any:
        headers = {
            **self.base_headers,
            **self._xsrf_header(),
            "Content-Type": "application/json; charset=utf-8",
        }
        request = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        with self.opener.open(request, timeout=timeout) as response:
            return json.load(response)


def choose_template(system_queries: dict[str, Any]) -> dict[str, Any]:
    for query in system_queries.get("list", []):
        settings = query.get("searchOptions", {}).get("componentSettings", {})
        options = query.get("reportOptions", {})
        if (
            options.get("classificationSystem") == "HTS"
            and settings.get("yearsTimeline") == "Monthly"
        ):
            return query
    raise RuntimeError("No public monthly HTS DataWeb query template was available")


def build_query(
    template: dict[str, Any],
    *,
    years: list[int],
    trade_type: str,
    measure: str,
) -> dict[str, Any]:
    query = copy.deepcopy(template)
    query.update(
        {
            "savedQueryDatabaseId": None,
            "savedQueryID": None,
            "savedQueryName": "Project-002 U.S. silver monthly history",
            "savedQueryDesc": "Official monthly HS/HTS 7106 quantity history",
            "savedQueryType": "",
            "isOwner": False,
            "apiToken": "",
            "captchaResponse": "",
            "captchaValid": False,
            "queryJSON": "",
        }
    )
    query["reportOptions"] = {
        "tradeType": trade_type,
        "classificationSystem": "HTS",
    }

    settings = query["searchOptions"]["componentSettings"]
    settings.update(
        {
            "dataToReport": [measure],
            "scale": "1",
            "timeframeSelectType": "fullYears",
            "years": [str(year) for year in years],
            "startDate": None,
            "endDate": None,
            "startMonth": None,
            "endMonth": None,
            "yearsTimeline": "Monthly",
        }
    )

    commodities = query["searchOptions"]["commodities"]
    commodities.update(
        {
            "commodities": ["7106"],
            "commoditiesExpanded": [
                {
                    "name": (
                        "SILVER (INCLUDING SILVER PLATED WITH GOLD OR PLATINUM), "
                        "UNWROUGHT OR IN SEMIMANUFACTURED FORMS, OR IN POWDER FORM"
                    ),
                    "value": "7106",
                    "hasChildren": True,
                }
            ],
            "commoditiesManual": "7106",
            "granularity": "4",
            "aggregation": "Aggregate Commodities",
            "codeDisplayFormat": "NO",
            "commoditySelectType": "list",
            "showHTSValidDetails": True,
        }
    )

    countries = query["searchOptions"]["countries"]
    countries.update(
        {
            "countries": [],
            "countriesExpanded": [],
            "aggregation": "Aggregate countries",
            "countriesSelectType": "all",
        }
    )
    districts = query["searchOptions"]["MiscGroup"]["districts"]
    districts.update(
        {
            "districts": [],
            "districtsExpanded": [],
            "aggregation": "Aggregate District",
            "districtsSelectType": "all",
        }
    )

    data_sort = query["sortingAndDataFormat"]["DataSort"]
    data_sort.update({"sortOrder": [], "columnOrder": ["UNITS"], "sortYear": None})
    custom = query["sortingAndDataFormat"]["reportCustomizations"]
    custom.update(
        {
            "totalRecords": "20000",
            "exportCombineTables": False,
            "exportRawData": False,
            "suppressZeroValues": False,
            "removeDuplicateValues": False,
        }
    )
    query["unitConversion"] = "0"
    query["manualConversions"] = []
    return query


def parse_number(value: Any) -> tuple[Decimal | None, bool]:
    if value is None:
        return None, False
    text = str(value).strip()
    if text in {"", "-", "—", "N/A", "NA", "null", "None"}:
        return None, False
    suppressed = "*" in text
    text = text.replace(",", "").replace("*", "").strip()
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    if not text:
        return None, suppressed
    try:
        number = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"Unexpected DataWeb quantity: {value!r}") from exc
    return (-number if negative else number), suppressed


def flatten_columns(table: dict[str, Any]) -> list[str]:
    return [
        str(column.get("label") or "")
        for group in table.get("column_groups", [])
        for column in group.get("columns", [])
    ]


def parse_report(
    response: dict[str, Any],
    *,
    flow: str,
    latest_period: str,
) -> tuple[dict[str, Decimal], list[dict[str, Any]], set[str]]:
    tables = response.get("dto", {}).get("tables", [])
    if not tables:
        raise RuntimeError(f"DataWeb returned no table for {flow}")
    table = tables[0]
    columns = flatten_columns(table)
    if "Year" not in columns or "Quantity Description" not in columns:
        raise RuntimeError(f"Unexpected DataWeb columns for {flow}: {columns}")

    totals: dict[str, Decimal] = defaultdict(Decimal)
    raw_rows: list[dict[str, Any]] = []
    suppressed_periods: set[str] = set()
    seen_units: set[str] = set()

    for group in table.get("row_groups", []):
        for row in group.get("rowsNew", []):
            values = [entry.get("value") for entry in row.get("rowEntries", [])]
            record = dict(zip(columns, values))
            year_text = str(record.get("Year") or "").strip()
            unit = str(record.get("Quantity Description") or "").strip()
            if not re.fullmatch(r"\d{4}", year_text) or not unit:
                continue
            unit_key = unit.casefold()
            seen_units.add(unit_key)
            if unit_key not in UNIT_TO_GRAMS:
                raise ValueError(
                    f"Unsupported DataWeb first-quantity unit for HS7106: {unit!r}"
                )
            multiplier = UNIT_TO_GRAMS[unit_key]
            ytd_reported = Decimal(0)
            ytd_grams = Decimal(0)
            for month, label in enumerate(MONTH_LABELS, 1):
                period = f"{year_text}-{month:02d}"
                if period > latest_period:
                    continue
                quantity, suppressed = parse_number(record.get(label))
                if quantity is None:
                    continue
                grams = quantity * multiplier
                totals[period] += grams
                ytd_reported += quantity
                ytd_grams += grams
                if suppressed:
                    suppressed_periods.add(period)
                raw_rows.append(
                    {
                        "period": period,
                        "flow": flow,
                        "code": "7106",
                        "description": "Silver, unwrought/semimanufactured/powder",
                        "unit": unit,
                        "quantity_mo_reported": str(quantity),
                        "quantity_ytd_reported": str(ytd_reported),
                        "quantity_mo_grams": str(grams),
                        "quantity_ytd_grams": str(ytd_grams),
                        "value_mo_usd": "",
                        "value_ytd_usd": "",
                        "source_url": DATAWEB_SITE,
                        "quantity_suppressed": suppressed,
                    }
                )

    if not totals:
        raise RuntimeError(f"DataWeb returned no monthly quantities for {flow}")
    print(
        f"  {flow}: {len(totals)} months; units={', '.join(sorted(seen_units))}",
        flush=True,
    )
    return dict(totals), raw_rows, suppressed_periods


def decimal_tonnes(grams: Decimal) -> float:
    return float((grams / Decimal("1000000")).quantize(Decimal("0.000001")))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] {path.relative_to(ROOT)} ({len(rows)} rows)", flush=True)


def build_monthly_rows(
    periods: list[str],
    imports: dict[str, Decimal],
    exports: dict[str, Decimal],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    missing: list[str] = []
    ytd_import = Decimal(0)
    ytd_export = Decimal(0)
    current_year = ""
    for period in periods:
        year = period[:4]
        if year != current_year:
            current_year = year
            ytd_import = Decimal(0)
            ytd_export = Decimal(0)
        import_grams = imports.get(period)
        export_grams = exports.get(period)
        if import_grams is None or export_grams is None:
            missing.append(period)
            continue
        ytd_import += import_grams
        ytd_export += export_grams
        rows.append(
            {
                "period": period,
                "import_tonnes": decimal_tonnes(import_grams),
                "domestic_export_tonnes": "",
                "reexport_tonnes": "",
                "export_tonnes": decimal_tonnes(export_grams),
                "net_import_tonnes": decimal_tonnes(import_grams - export_grams),
                "import_value_usd": "",
                "export_value_usd": "",
                "ytd_import_tonnes": decimal_tonnes(ytd_import),
                "ytd_domestic_export_tonnes": "",
                "ytd_reexport_tonnes": "",
                "ytd_export_tonnes": decimal_tonnes(ytd_export),
                "ytd_net_import_tonnes": decimal_tonnes(ytd_import - ytd_export),
                "ytd_import_value_usd": "",
                "ytd_export_value_usd": "",
            }
        )
    return rows, missing


def annualize(monthly: list[dict[str, Any]]) -> dict[int, dict[str, float]]:
    annual: dict[int, dict[str, float]] = defaultdict(
        lambda: {"import_tonnes": 0.0, "export_tonnes": 0.0}
    )
    for row in monthly:
        year = int(row["period"][:4])
        annual[year]["import_tonnes"] += float(row["import_tonnes"])
        annual[year]["export_tonnes"] += float(row["export_tonnes"])
    for year, values in annual.items():
        values["import_tonnes"] = round(values["import_tonnes"], 6)
        values["export_tonnes"] = round(values["export_tonnes"], 6)
        values["net_import_tonnes"] = round(
            values["import_tonnes"] - values["export_tonnes"], 6
        )
    return dict(annual)


def write_outputs(
    *,
    monthly: list[dict[str, Any]],
    raw_rows: list[dict[str, Any]],
    requested_through: str,
    published_through: str,
    start_year: int,
    missing_periods: list[str],
    suppressed_periods: set[str],
) -> None:
    annual = annualize(monthly)
    published_year, published_month = parse_period(published_through)
    complete_years = [
        year
        for year in sorted(annual)
        if sum(row["period"].startswith(f"{year}-") for row in monthly) == 12
    ]
    latest_complete_year = max(complete_years)
    latest = monthly[-1]

    monthly_fields = [
        "period",
        "import_tonnes",
        "domestic_export_tonnes",
        "reexport_tonnes",
        "export_tonnes",
        "net_import_tonnes",
        "import_value_usd",
        "export_value_usd",
        "ytd_import_tonnes",
        "ytd_domestic_export_tonnes",
        "ytd_reexport_tonnes",
        "ytd_export_tonnes",
        "ytd_net_import_tonnes",
        "ytd_import_value_usd",
        "ytd_export_value_usd",
    ]
    write_csv(OUT_MONTHLY, monthly, monthly_fields)

    code_fields = [
        "period",
        "flow",
        "code",
        "description",
        "unit",
        "quantity_mo_reported",
        "quantity_ytd_reported",
        "quantity_mo_grams",
        "quantity_ytd_grams",
        "value_mo_usd",
        "value_ytd_usd",
        "source_url",
        "quantity_suppressed",
    ]
    write_csv(OUT_CODES, raw_rows, code_fields)

    compiled: list[dict[str, Any]] = []
    for year in sorted(annual):
        compiled.append(
            {
                "period_type": (
                    "calendar_year" if year in complete_years else "year_to_date"
                ),
                "period": str(year) if year in complete_years else published_through,
                "flow": "both",
                **annual[year],
                "source": SOURCE,
                "notes": (
                    "General imports; total exports; GM + CGM -> tonnes"
                    if year in complete_years
                    else f"YTD through month {published_month:02d}; not a full year"
                ),
                "confidence": "high",
                "series": SERIES,
            }
        )
    for row in monthly:
        compiled.append(
            {
                "period_type": "month",
                "period": row["period"],
                "flow": "both",
                "import_tonnes": row["import_tonnes"],
                "export_tonnes": row["export_tonnes"],
                "net_import_tonnes": row["net_import_tonnes"],
                "source": SOURCE,
                "notes": "General imports; total exports; GM + CGM -> tonnes",
                "confidence": "high",
                "series": SERIES,
            }
        )
    write_csv(
        OUT_COMPILED,
        compiled,
        [
            "period_type",
            "period",
            "flow",
            "import_tonnes",
            "export_tonnes",
            "net_import_tonnes",
            "source",
            "notes",
            "confidence",
            "series",
        ],
    )

    years = sorted(annual)
    full_imports = [annual[year]["import_tonnes"] for year in complete_years]
    full_nets = [annual[year]["net_import_tonnes"] for year in complete_years]
    unavailable = (
        [requested_through] if requested_through > published_through else []
    )
    monthly_note = (
        f"USITC DataWeb（美国 Census 官方贸易统计）HS/HTS 7106 月度第一数量；"
        f"GM（克）与 CGM（含量克）相加后换算为吨。连续覆盖 "
        f"{monthly[0]['period']} 至 {monthly[-1]['period']}，不做拆月或插值。"
    )
    if unavailable:
        monthly_note += f" {requested_through} 尚未发布，图中保留空档。"
    if suppressed_periods:
        monthly_note += (
            f" {len(suppressed_periods)} 个月含 DataWeb 数量抑制标记，"
            "保留其已披露聚合值。"
        )

    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "country": "US",
        "source": SOURCE + " · HS/HTS 7106",
        "unit": "吨",
        "basis": "net_import",
        "netImportFormula": "进口 − 出口（正值 = 净流入美国；负值 = 净流出/再出口）",
        "primarySeries": SERIES,
        "asOf": published_through,
        "requestedThrough": requested_through,
        "latestPublished": published_through,
        "unavailablePeriods": unavailable,
        "publishedButMonthlyFileNotCached": [],
        "years": [str(year) for year in years],
        "imports": [annual[year]["import_tonnes"] for year in years],
        "exports": [annual[year]["export_tonnes"] for year in years],
        "netImport": [annual[year]["net_import_tonnes"] for year in years],
        "partialYears": {
            str(published_year): (
                f"截至 {published_month} 月 · DataWeb/Census HS7106 月度累计，非全年"
            )
        },
        "monthlyAvailable": True,
        "monthlyCount": len(monthly),
        "monthlySeriesComplete": not missing_periods,
        "months": [row["period"] for row in monthly],
        "monthlyImports": [row["import_tonnes"] for row in monthly],
        "monthlyExports": [row["export_tonnes"] for row in monthly],
        "monthlyNetImport": [row["net_import_tonnes"] for row in monthly],
        "monthlyNote": monthly_note,
        "stats": {
            "latestCompleteYear": latest_complete_year,
            "latestImport": annual[latest_complete_year]["import_tonnes"],
            "latestExport": annual[latest_complete_year]["export_tonnes"],
            "latestNetImport": annual[latest_complete_year]["net_import_tonnes"],
            "ytdYear": published_year,
            "ytdMonth": published_month,
            "ytdImport": latest["ytd_import_tonnes"],
            "ytdExport": latest["ytd_export_tonnes"],
            "ytdNetImport": latest["ytd_net_import_tonnes"],
            "ytdDomesticExport": None,
            "ytdReexport": None,
            "ytdNote": f"截至 {published_month} 月，非全年",
            "peakImport": max(full_imports),
            "peakImportYear": complete_years[full_imports.index(max(full_imports))],
            "peakNetImport": max(full_nets),
            "peakNetImportYear": complete_years[full_nets.index(max(full_nets))],
        },
        "partners": "世界合计；DataWeb 查询聚合全部贸易伙伴与关区",
        "releaseStatus": {
            "requested": requested_through,
            "availableThrough": published_through,
            "detailJune2026Scheduled": "2026-08-04",
        },
        "sourceUrls": {
            "dataWeb": DATAWEB_SITE,
            "censusDataProducts": CENSUS_PRODUCTS_URL,
            "censusReleaseSchedule": CENSUS_RELEASE_URL,
        },
        "disclaimer": (
            f"{start_year}-{published_year} 月度均取自 USITC DataWeb 所载美国 "
            "Census 官方商品贸易统计。进口为一般进口，出口为总出口；商品范围为 "
            "HS/HTS 7106。第一数量中的 GM（克）与 CGM（含量克）统一换算并相加。"
            "不含银矿砂/精矿、废料和硬币；不做年度拆月或插值。"
            f"{published_year} 仅截至 {published_month} 月。"
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] {OUT_JSON.relative_to(ROOT)}", flush=True)

    annual_table = "\n".join(
        f"| {year}{'*' if year == published_year else ''} "
        f"| {annual[year]['import_tonnes']:,.3f} "
        f"| {annual[year]['export_tonnes']:,.3f} "
        f"| {annual[year]['net_import_tonnes']:,.3f} |"
        for year in years
    )
    missing_text = "无" if not missing_periods else "、".join(missing_periods)
    suppression_text = (
        "无"
        if not suppressed_periods
        else f"{len(suppressed_periods)} 个月（详见原始 DataWeb 报告缓存）"
    )
    notes = f"""# 美国白银进出口数据整理

> 整理日期：{date.today().isoformat()}  
> 主序列：**USITC DataWeb / U.S. Census HS/HTS 7106 月度第一数量**  
> 表达基准：**净进口 = 一般进口 − 总出口**

## 1. 覆盖与口径

- 真实月度覆盖：**{monthly[0]['period']} 至 {monthly[-1]['period']}**，共 **{len(monthly)}** 个月。
- 进口：General Imports；出口：Total Exports；伙伴与关区均聚合。
- DataWeb 分列返回 GM（克）和 CGM（含量克）；本项目先相加，再除以 1,000,000 换算为吨。
- 年度拆月/插值：**未使用**。
- 公开范围内缺失月份：{missing_text}。
- DataWeb 数量抑制标记：{suppression_text}。
- 用户请求到 {requested_through}；当前官方发布到 {published_through}。

## 2. 年度校验汇总（吨）

| 年 | 一般进口 | 总出口 | 净进口 |
|---:|---:|---:|---:|
{annual_table}

\\* {published_year} 为截至 {published_month} 月累计，不是全年。

## 3. 官方来源

- USITC DataWeb：{DATAWEB_SITE}
- Census 数据产品：{CENSUS_PRODUCTS_URL}
- Census 发布日程：{CENSUS_RELEASE_URL}

## 4. 文件

- `data/us/us_silver_trade_monthly.csv`
- `data/us/us_silver_trade_compiled.csv`
- `data/us/us_silver_trade_by_code.csv`
- `data/us/dataweb_cache/`
- `web/public/data/us_trade.json`
"""
    OUT_NOTES.write_text(notes, encoding="utf-8")
    print(f"[OK] {OUT_NOTES.relative_to(ROOT)}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start-year",
        type=int,
        default=1989,
        help="First DataWeb electronic year (default: 1989)",
    )
    parser.add_argument(
        "--through",
        default="2026-06",
        help="Requested coverage in YYYY-MM (default: 2026-06)",
    )
    args = parser.parse_args()
    requested_year, requested_month = parse_period(args.through)
    if args.start_year < 1989:
        raise SystemExit("USITC DataWeb electronic trade data start in 1989")
    if args.start_year > requested_year:
        raise SystemExit("--start-year cannot be later than --through")

    client = DataWebClient()
    print("[1/5] Reading DataWeb release metadata and public query template", flush=True)
    global_vars = client.get_json(GLOBAL_VARS_URL)
    current_year = int(global_vars["currentYear"])
    current_month = int(global_vars["currentMonth"])
    published = min((requested_year, requested_month), (current_year, current_month))
    published_year, published_month = published
    published_through = f"{published_year}-{published_month:02d}"
    years = list(range(args.start_year, published_year + 1))
    template = choose_template(client.get_json(SYSTEM_QUERIES_URL))
    print(
        f"  requested={args.through}; DataWeb published={current_year}-{current_month:02d}; "
        f"using through={published_through}",
        flush=True,
    )

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    reports: dict[str, dict[str, Any]] = {}
    specs = [
        ("general_import", "GenImp", "GEN_FIR_UNIT_QUANTITY"),
        ("total_export", "TotExp", "FIRST_UNIT_QUANTITY"),
    ]
    for index, (flow, trade_type, measure) in enumerate(specs, 2):
        print(f"[{index}/5] Querying {flow}, {years[0]}-{years[-1]} monthly", flush=True)
        query = build_query(
            template,
            years=years,
            trade_type=trade_type,
            measure=measure,
        )
        response = client.post_json(RUN_REPORT_URL, query)
        reports[flow] = response
        cache_path = CACHE_DIR / (
            f"{flow}_{years[0]}_{published_year}_monthly_hs7106.json"
        )
        cache_path.write_text(
            json.dumps(
                {"query": query, "response": response},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        print(f"  [CACHE] {cache_path.relative_to(ROOT)}", flush=True)

    print("[4/5] Parsing and validating monthly quantities", flush=True)
    imports, import_raw, import_suppressed = parse_report(
        reports["general_import"],
        flow="general_import",
        latest_period=published_through,
    )
    exports, export_raw, export_suppressed = parse_report(
        reports["total_export"],
        flow="total_export",
        latest_period=published_through,
    )
    expected_periods = month_range(args.start_year, published_year, published_month)
    monthly, missing = build_monthly_rows(expected_periods, imports, exports)
    if not monthly:
        raise RuntimeError("No overlapping import/export months were returned")
    if missing:
        print(
            f"  [WARN] {len(missing)} published-range months lacked one or both flows",
            flush=True,
        )
    else:
        print(
            f"  [VALIDATED] continuous {monthly[0]['period']}~{monthly[-1]['period']} "
            f"({len(monthly)} months)",
            flush=True,
        )

    print("[5/5] Writing project data and web JSON", flush=True)
    write_outputs(
        monthly=monthly,
        raw_rows=sorted(
            import_raw + export_raw,
            key=lambda row: (row["period"], row["flow"], row["unit"]),
        ),
        requested_through=args.through,
        published_through=published_through,
        start_year=args.start_year,
        missing_periods=missing,
        suppressed_periods=import_suppressed | export_suppressed,
    )
    print(
        f"[DONE] U.S. official monthly history {monthly[0]['period']}~"
        f"{monthly[-1]['period']} ({len(monthly)} rows)",
        flush=True,
    )


if __name__ == "__main__":
    main()
