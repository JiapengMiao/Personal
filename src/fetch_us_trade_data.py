#!/usr/bin/env python3
"""Fetch and compile official U.S. Census HS/HTS 7106 silver trade data.

The Census merchandise ZIPs contain large country/district detail files.  This
collector uses HTTP range requests and reads only EXP_COMM.TXT / IMP_COMM.TXT,
which are the national commodity summaries.  A complete local ZIP is reused
when present.

Quantity basis:
* imports: general imports, first reported quantity (GEN_QY1)
* exports: domestic + foreign/re-export, first reported quantity (QTY_1)
* GM and CGM are both gram-based units; CGM means content grams
* net imports = imports - total exports
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import urllib.error
import urllib.request
import zipfile
from collections import OrderedDict
from datetime import date, datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
US_DIR = ROOT / "data" / "us"
BULK_DIR = US_DIR / "census_bulk"
OUT_COMPILED = US_DIR / "us_silver_trade_compiled.csv"
OUT_MONTHLY = US_DIR / "us_silver_trade_monthly.csv"
OUT_CODES = US_DIR / "us_silver_trade_by_code.csv"
OUT_NOTES = US_DIR / "us_silver_trade_notes.md"
OUT_JSON = ROOT / "web" / "public" / "data" / "us_trade.json"

SOURCE_NAME = "U.S. Census Merchandise Trade files · HS/HTS 7106"
PRIMARY_SERIES = "us_hs7106_census_comtrade"
DATA_PRODUCTS_URL = "https://www.census.gov/foreign-trade/data/dataproducts.html"
EXPORT_LAYOUT_URL = "https://www.census.gov/foreign-trade/reference/products/layouts/exdb.html"
IMPORT_LAYOUT_URL = "https://www.census.gov/foreign-trade/reference/products/layouts/imdb.html"
RELEASE_SCHEDULE_URL = "https://www.census.gov/foreign-trade/schedule.html"
USA_TRADE_ONLINE_URL = "https://usatradeonline.census.gov/"
WITS_IMPORT_2025_URL = (
    "https://wits.worldbank.org/trade/comtrade/en/country/USA/year/2025/"
    "tradeflow/Imports/partner/ALL/product/7106"
)
WITS_EXPORT_2025_URL = (
    "https://wits.worldbank.org/trade/comtrade/en/country/USA/year/2025/"
    "tradeflow/Exports/partner/ALL/product/7106"
)

# Annual HS7106 reference. 2020-2024 were already used by the project; 2025 was
# checked against the World row on WITS/UN Comtrade on 2026-07-23.
ANNUAL_HS7106 = {
    2020: (8918.5, 2622.0, "WITS/UN Comtrade HS7106"),
    2021: (8216.3, 3236.2, "WITS/UN Comtrade HS7106"),
    2022: (7389.0, 2333.6, "WITS/UN Comtrade HS7106"),
    2023: (7740.0, 1730.8, "WITS/UN Comtrade HS7106"),
    2024: (5812.8, 1464.4, "WITS/UN Comtrade HS7106"),
    2025: (7435.87, 5783.12, "WITS/UN Comtrade HS7106 · World"),
}

# Kept as a clearly separated cross-check in the compiled CSV and notes.
USGS_REFERENCE = {
    2015: (5930.0, 817.0, "USGS historical"),
    2016: (6160.0, 289.0, "USGS historical"),
    2017: (5040.0, 157.0, "USGS historical"),
    2018: (4840.0, 604.0, "USGS historical"),
    2019: (4760.0, 220.0, "USGS historical"),
    2020: (6730.0, 141.0, "USGS MCS"),
    2021: (6160.0, 137.0, "USGS MCS"),
    2022: (4490.0, 276.0, "USGS MCS revised"),
    2023: (4950.0, 73.0, "USGS MCS revised"),
    2024: (4430.0, 113.0, "USGS MCS 2026"),
    2025: (7600.0, 300.0, "USGS MCS 2026 estimate"),
}

# Official USA Trade Online Reimagined report, queried on 2026-07-23:
# Harmonized System / District Level / World Total / individual months /
# Quantity 1 (Gen) for imports and Quantity 1 / Total Exports for exports.
# Values are exact grams summed across the applicable 10-digit HS/HTS 7106
# codes. May is also present in the local IMDB/EXDB files and is validated
# against this independent official report below.
USA_TRADE_ONLINE_MONTHLY_2026 = {
    "2026-01": {"import_grams": 326_889_984, "export_grams": 1_666_389_145},
    "2026-02": {"import_grams": 336_223_444, "export_grams": 1_786_716_885},
    "2026-03": {"import_grams": 374_566_482, "export_grams": 1_251_041_821},
    "2026-04": {"import_grams": 360_442_956, "export_grams": 643_519_933},
    "2026-05": {"import_grams": 416_094_156, "export_grams": 255_717_055},
}


class PublishedFileMissing(RuntimeError):
    """The requested Census monthly file is not published."""


class HTTPRangeReader(io.RawIOBase):
    """Seekable, cached reader backed by HTTP byte-range requests."""

    def __init__(
        self,
        url: str,
        *,
        block_size: int = 4 * 1024 * 1024,
        max_blocks: int = 6,
        timeout: int = 120,
    ) -> None:
        super().__init__()
        self.url = url
        self.block_size = block_size
        self.max_blocks = max_blocks
        self.timeout = timeout
        self._pos = 0
        self._cache: OrderedDict[int, bytes] = OrderedDict()
        self._size = self._probe_size()

    @staticmethod
    def _headers(start: int, end: int) -> dict[str, str]:
        return {
            "Range": f"bytes={start}-{end}",
            "Accept-Encoding": "identity",
            "User-Agent": "Project-002-US-silver-trade-updater/1.0",
        }

    def _probe_size(self) -> int:
        req = urllib.request.Request(self.url, headers=self._headers(0, 0))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status = getattr(response, "status", response.getcode())
                content_range = response.headers.get("Content-Range", "")
                if status != 206:
                    raise RuntimeError(
                        f"Server does not support byte ranges for {self.url} "
                        f"(HTTP {status}); refusing a full multi-hundred-MB download"
                    )
                match = re.search(r"/(\d+)$", content_range)
                if not match:
                    raise RuntimeError(f"Missing file size in Content-Range: {content_range!r}")
                response.read(1)
                return int(match.group(1))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise PublishedFileMissing(self.url) from exc
            raise

    def _get_block(self, block_index: int) -> bytes:
        cached = self._cache.get(block_index)
        if cached is not None:
            self._cache.move_to_end(block_index)
            return cached

        start = block_index * self.block_size
        end = min(self._size - 1, start + self.block_size - 1)
        req = urllib.request.Request(self.url, headers=self._headers(start, end))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                status = getattr(response, "status", response.getcode())
                if status != 206:
                    raise RuntimeError(
                        f"Expected HTTP 206 for {self.url}, got {status}; "
                        "refusing a full download"
                    )
                data = response.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                raise PublishedFileMissing(self.url) from exc
            raise

        expected = end - start + 1
        if len(data) != expected:
            raise IOError(
                f"Short HTTP range read for {self.url}: "
                f"{start}-{end}, expected {expected}, got {len(data)}"
            )
        self._cache[block_index] = data
        self._cache.move_to_end(block_index)
        while len(self._cache) > self.max_blocks:
            self._cache.popitem(last=False)
        return data

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        if whence == io.SEEK_SET:
            new_pos = offset
        elif whence == io.SEEK_CUR:
            new_pos = self._pos + offset
        elif whence == io.SEEK_END:
            new_pos = self._size + offset
        else:
            raise ValueError(f"Unsupported whence: {whence}")
        if new_pos < 0:
            raise ValueError("Negative seek position")
        self._pos = min(new_pos, self._size)
        return self._pos

    def read(self, size: int = -1) -> bytes:
        if self._pos >= self._size:
            return b""
        if size is None or size < 0:
            size = self._size - self._pos
        if size == 0:
            return b""
        end_pos = min(self._size, self._pos + size)
        parts: list[bytes] = []
        while self._pos < end_pos:
            block_index = self._pos // self.block_size
            block = self._get_block(block_index)
            block_start = block_index * self.block_size
            inner_start = self._pos - block_start
            take = min(end_pos - self._pos, len(block) - inner_start)
            parts.append(block[inner_start : inner_start + take])
            self._pos += take
        return b"".join(parts)

    def readinto(self, buffer: bytearray) -> int:
        data = self.read(len(buffer))
        buffer[: len(data)] = data
        return len(data)


def census_url(year: int, month: int, flow: str) -> str:
    yy = str(year)[-2:]
    mm = f"{month:02d}"
    if flow == "export":
        return (
            f"https://www.census.gov/trade/downloads/{year}/Merch/"
            f"ex_m/EXDB{yy}{mm}.ZIP"
        )
    if flow == "import":
        return (
            f"https://www.census.gov/trade/downloads/{year}/Merch/"
            f"im_m/IMDB{yy}{mm}.ZIP"
        )
    raise ValueError(flow)


def local_zip_path(year: int, month: int, flow: str) -> Path:
    prefix = "EXDB" if flow == "export" else "IMDB"
    return BULK_DIR / f"{prefix}{str(year)[-2:]}{month:02d}.ZIP"


def read_summary_entry(year: int, month: int, flow: str) -> tuple[bytes, str]:
    entry_name = "EXP_COMM.TXT" if flow == "export" else "IMP_COMM.TXT"
    local_path = local_zip_path(year, month, flow)
    if local_path.exists():
        try:
            with zipfile.ZipFile(local_path) as archive:
                return archive.read(entry_name), census_url(year, month, flow)
        except (zipfile.BadZipFile, KeyError):
            print(f"  [WARN] ignoring invalid local archive: {local_path.name}", flush=True)

    url = census_url(year, month, flow)
    print(f"  [RANGE] {url}", flush=True)
    remote = HTTPRangeReader(url)
    with zipfile.ZipFile(remote) as archive:
        return archive.read(entry_name), url


def parse_int(text: str) -> int:
    value = text.strip()
    return int(value) if value else 0


def quantity_to_grams(quantity: int, unit: str) -> int:
    unit = unit.strip().upper()
    if unit in {"GM", "CGM"}:
        return quantity
    if unit in {"KG", "KGM", "CKG"}:
        return quantity * 1000
    if unit in {"T", "TON", "CTN"}:
        return quantity * 1_000_000
    raise ValueError(f"Unsupported HS7106 quantity unit: {unit!r}")


def parse_export(data: bytes, period: str, source_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in data.decode("latin-1").splitlines():
        if len(line) < 373 or line[1:5] != "7106":
            continue
        unit = line[61:64].strip()
        quantity_mo = parse_int(line[88:103])
        quantity_ytd = parse_int(line[238:253])
        rows.append(
            {
                "period": period,
                "flow": "domestic_export" if line[0] == "1" else "reexport",
                "code": line[1:11],
                "description": line[11:61].strip(),
                "unit": unit,
                "quantity_mo_reported": quantity_mo,
                "quantity_ytd_reported": quantity_ytd,
                "quantity_mo_grams": quantity_to_grams(quantity_mo, unit),
                "quantity_ytd_grams": quantity_to_grams(quantity_ytd, unit),
                "value_mo_usd": parse_int(line[118:133]),
                "value_ytd_usd": parse_int(line[268:283]),
                "source_url": source_url,
            }
        )
    if not rows:
        raise ValueError(f"No export HS7106 rows found for {period}")
    return rows


def parse_import(data: bytes, period: str, source_url: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in data.decode("latin-1").splitlines():
        if len(line) < 732 or not line.startswith("7106"):
            continue
        unit = line[60:63].strip()
        quantity_mo = parse_int(line[192:207])
        quantity_ytd = parse_int(line[522:537])
        rows.append(
            {
                "period": period,
                "flow": "general_import",
                "code": line[0:10],
                "description": line[10:60].strip(),
                "unit": unit,
                "quantity_mo_reported": quantity_mo,
                "quantity_ytd_reported": quantity_ytd,
                "quantity_mo_grams": quantity_to_grams(quantity_mo, unit),
                "quantity_ytd_grams": quantity_to_grams(quantity_ytd, unit),
                "value_mo_usd": parse_int(line[222:237]),
                "value_ytd_usd": parse_int(line[552:567]),
                "source_url": source_url,
            }
        )
    if not rows:
        raise ValueError(f"No import HS7106 rows found for {period}")
    return rows


def tonnes(grams: int) -> float:
    # One gram is 0.000001 tonne; retain six decimals so monthly rows sum
    # exactly to the official year-to-date quantity.
    return round(grams / 1_000_000, 6)


def summarize_usa_trade_online(period: str) -> dict[str, Any]:
    """Build a monthly quantity row from the official USA Trade Online report."""
    current = USA_TRADE_ONLINE_MONTHLY_2026[period]
    periods = [
        key
        for key in sorted(USA_TRADE_ONLINE_MONTHLY_2026)
        if key[:4] == period[:4] and key <= period
    ]
    ytd_import = sum(
        USA_TRADE_ONLINE_MONTHLY_2026[key]["import_grams"] for key in periods
    )
    ytd_export = sum(
        USA_TRADE_ONLINE_MONTHLY_2026[key]["export_grams"] for key in periods
    )
    import_grams = current["import_grams"]
    export_grams = current["export_grams"]
    return {
        "period": period,
        "import_tonnes": tonnes(import_grams),
        "domestic_export_tonnes": None,
        "reexport_tonnes": None,
        "export_tonnes": tonnes(export_grams),
        "net_import_tonnes": tonnes(import_grams - export_grams),
        "import_value_usd": None,
        "export_value_usd": None,
        "ytd_import_tonnes": tonnes(ytd_import),
        "ytd_domestic_export_tonnes": None,
        "ytd_reexport_tonnes": None,
        "ytd_export_tonnes": tonnes(ytd_export),
        "ytd_net_import_tonnes": tonnes(ytd_import - ytd_export),
        "ytd_import_value_usd": None,
        "ytd_export_value_usd": None,
        "_source": "U.S. Census USA Trade Online Reimagined",
    }


def summarize_period(
    period: str,
    import_rows: list[dict[str, Any]],
    export_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    domestic = [row for row in export_rows if row["flow"] == "domestic_export"]
    reexports = [row for row in export_rows if row["flow"] == "reexport"]

    def sum_field(rows: list[dict[str, Any]], field: str) -> int:
        return sum(int(row[field]) for row in rows)

    import_mo = sum_field(import_rows, "quantity_mo_grams")
    domestic_mo = sum_field(domestic, "quantity_mo_grams")
    reexport_mo = sum_field(reexports, "quantity_mo_grams")
    export_mo = domestic_mo + reexport_mo

    import_ytd = sum_field(import_rows, "quantity_ytd_grams")
    domestic_ytd = sum_field(domestic, "quantity_ytd_grams")
    reexport_ytd = sum_field(reexports, "quantity_ytd_grams")
    export_ytd = domestic_ytd + reexport_ytd

    return {
        "period": period,
        "import_tonnes": tonnes(import_mo),
        "domestic_export_tonnes": tonnes(domestic_mo),
        "reexport_tonnes": tonnes(reexport_mo),
        "export_tonnes": tonnes(export_mo),
        "net_import_tonnes": tonnes(import_mo - export_mo),
        "import_value_usd": sum_field(import_rows, "value_mo_usd"),
        "export_value_usd": sum_field(export_rows, "value_mo_usd"),
        "ytd_import_tonnes": tonnes(import_ytd),
        "ytd_domestic_export_tonnes": tonnes(domestic_ytd),
        "ytd_reexport_tonnes": tonnes(reexport_ytd),
        "ytd_export_tonnes": tonnes(export_ytd),
        "ytd_net_import_tonnes": tonnes(import_ytd - export_ytd),
        "ytd_import_value_usd": sum_field(import_rows, "value_ytd_usd"),
        "ytd_export_value_usd": sum_field(export_rows, "value_ytd_usd"),
    }


def fetch_period(year: int, month: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    period = f"{year}-{month:02d}"
    print(f"[FETCH] {period}", flush=True)
    export_data, export_url = read_summary_entry(year, month, "export")
    import_data, import_url = read_summary_entry(year, month, "import")
    export_rows = parse_export(export_data, period, export_url)
    import_rows = parse_import(import_data, period, import_url)
    summary = summarize_period(period, import_rows, export_rows)
    print(
        "  "
        f"import={summary['import_tonnes']:,.3f} t, "
        f"export={summary['export_tonnes']:,.3f} t, "
        f"net={summary['net_import_tonnes']:,.3f} t",
        flush=True,
    )
    return summary, import_rows + export_rows


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] {path.relative_to(ROOT)} ({len(rows)} rows)")


def build_outputs(
    annual_summaries: dict[int, dict[str, Any]],
    monthly_summaries: list[dict[str, Any]],
    code_rows: list[dict[str, Any]],
    requested_through: str,
    unavailable_periods: list[str],
    not_cached_periods: list[str],
) -> None:
    if not monthly_summaries:
        raise RuntimeError("No current-year monthly data were available")

    latest = monthly_summaries[-1]
    latest_period = latest["period"]
    current_year = int(latest_period[:4])
    latest_month = int(latest_period[-2:])
    expected_published = {
        f"{current_year}-{month:02d}" for month in range(1, latest_month + 1)
    }
    observed_published = {row["period"] for row in monthly_summaries}
    published_months_complete = expected_published.issubset(observed_published)

    annual_rows: list[dict[str, Any]] = []
    for year in sorted(annual_summaries):
        row = annual_summaries[year]
        annual_rows.append(
            {
                "year": year,
                "import_tonnes": row["ytd_import_tonnes"],
                "export_tonnes": row["ytd_export_tonnes"],
                "net_import_tonnes": row["ytd_net_import_tonnes"],
            }
        )
    annual_rows.append(
        {
            "year": current_year,
            "import_tonnes": latest["ytd_import_tonnes"],
            "export_tonnes": latest["ytd_export_tonnes"],
            "net_import_tonnes": latest["ytd_net_import_tonnes"],
        }
    )

    compiled: list[dict[str, Any]] = []
    for row in annual_rows[:-1]:
        compiled.append(
            {
                "period_type": "calendar_year",
                "period": str(row["year"]),
                "flow": "both",
                "import_tonnes": row["import_tonnes"],
                "export_tonnes": row["export_tonnes"],
                "net_import_tonnes": row["net_import_tonnes"],
                "source": annual_summaries[row["year"]].get("_source", SOURCE_NAME),
                "notes": annual_summaries[row["year"]].get(
                    "_notes",
                    "general imports; domestic exports + reexports; GM/CGM -> t",
                ),
                "confidence": "high",
                "series": PRIMARY_SERIES,
            }
        )
    for row in monthly_summaries:
        compiled.append(
            {
                "period_type": "month",
                "period": row["period"],
                "flow": "both",
                "import_tonnes": row["import_tonnes"],
                "export_tonnes": row["export_tonnes"],
                "net_import_tonnes": row["net_import_tonnes"],
                "source": row.get("_source", SOURCE_NAME),
                "notes": (
                    "general imports; total exports; GM/CGM -> t"
                    if row.get("_source")
                    else "general imports; domestic exports + reexports; GM/CGM -> t"
                ),
                "confidence": "high",
                "series": PRIMARY_SERIES,
            }
        )
    compiled.append(
        {
            "period_type": "year_to_date",
            "period": latest_period,
            "flow": "both",
            "import_tonnes": latest["ytd_import_tonnes"],
            "export_tonnes": latest["ytd_export_tonnes"],
            "net_import_tonnes": latest["ytd_net_import_tonnes"],
            "source": SOURCE_NAME,
            "notes": f"{current_year} YTD through month {latest_month:02d}; not full year",
            "confidence": "high",
            "series": PRIMARY_SERIES,
        }
    )
    for year, (imports, exports, note) in USGS_REFERENCE.items():
        compiled.append(
            {
                "period_type": "calendar_year",
                "period": str(year),
                "flow": "both",
                "import_tonnes": imports,
                "export_tonnes": exports,
                "net_import_tonnes": round(imports - exports, 1),
                "source": "USGS MCS / Historical Statistics",
                "notes": note,
                "confidence": "medium" if "estimate" in note else "high",
                "series": "usgs_silver_content",
            }
        )

    compiled_fields = [
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
    ]
    write_csv(OUT_COMPILED, compiled, compiled_fields)

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
    write_csv(OUT_MONTHLY, monthly_summaries, monthly_fields)

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
    ]
    write_csv(OUT_CODES, code_rows, code_fields)

    years = [str(row["year"]) for row in annual_rows]
    imports = [row["import_tonnes"] for row in annual_rows]
    exports = [row["export_tonnes"] for row in annual_rows]
    net_imports = [row["net_import_tonnes"] for row in annual_rows]
    latest_complete = annual_rows[-2]
    complete_nets = [row["net_import_tonnes"] for row in annual_rows[:-1]]
    complete_imports = [row["import_tonnes"] for row in annual_rows[:-1]]

    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "country": "US",
        "source": (
            "WITS/UN Comtrade HS7106 (2020-2025) · "
            "U.S. Census USA Trade Online / Merchandise Trade "
            "HS/HTS 7106 (2026 monthly)"
        ),
        "unit": "吨",
        "basis": "net_import",
        "netImportFormula": "进口 − 出口（正值 = 净流入美国；负值 = 净流出/再出口）",
        "primarySeries": PRIMARY_SERIES,
        "asOf": latest_period,
        "requestedThrough": requested_through,
        "latestPublished": latest_period,
        "unavailablePeriods": unavailable_periods,
        "publishedButMonthlyFileNotCached": not_cached_periods,
        "years": years,
        "imports": imports,
        "exports": exports,
        "netImport": net_imports,
        "partialYears": {
            str(current_year): (
                f"截至 {latest_month} 月 · Census HS7106 月度累计，非全年"
            )
        },
        "monthlyAvailable": True,
        "monthlySeriesComplete": published_months_complete,
        "months": [row["period"] for row in monthly_summaries],
        "monthlyImports": [row["import_tonnes"] for row in monthly_summaries],
        "monthlyDomesticExports": [
            row["domestic_export_tonnes"] for row in monthly_summaries
        ],
        "monthlyReexports": [row["reexport_tonnes"] for row in monthly_summaries],
        "monthlyExports": [row["export_tonnes"] for row in monthly_summaries],
        "monthlyNetImport": [row["net_import_tonnes"] for row in monthly_summaries],
        "monthlyNote": (
            "2026 年 1—5 月为 Census 官方月度数量：1—4 月取自 USA Trade "
            "Online Reimagined，5 月由 IMDB/EXDB 原始文件复核；2026-06 "
            "商品明细尚未发布，图中保留空档。"
        ),
        "stats": {
            "latestCompleteYear": latest_complete["year"],
            "latestImport": latest_complete["import_tonnes"],
            "latestExport": latest_complete["export_tonnes"],
            "latestNetImport": latest_complete["net_import_tonnes"],
            "ytdYear": current_year,
            "ytdMonth": latest_month,
            "ytdImport": latest["ytd_import_tonnes"],
            "ytdExport": latest["ytd_export_tonnes"],
            "ytdNetImport": latest["ytd_net_import_tonnes"],
            "ytdDomesticExport": latest["ytd_domestic_export_tonnes"],
            "ytdReexport": latest["ytd_reexport_tonnes"],
            "ytdNote": f"截至 {latest_month} 月，非全年",
            "peakImport": max(complete_imports),
            "peakImportYear": annual_rows[
                complete_imports.index(max(complete_imports))
            ]["year"],
            "peakNetImport": max(complete_nets),
            "peakNetImportYear": annual_rows[
                complete_nets.index(max(complete_nets))
            ]["year"],
        },
        "partners": "世界合计；国别伙伴明细不在本次商品总表口径内",
        "releaseStatus": {
            "requested": requested_through,
            "availableThrough": latest_period,
            "detailJune2026Scheduled": "2026-08-04",
        },
        "sourceUrls": {
            "dataProducts": DATA_PRODUCTS_URL,
            "exportLayout": EXPORT_LAYOUT_URL,
            "importLayout": IMPORT_LAYOUT_URL,
            "releaseSchedule": RELEASE_SCHEDULE_URL,
            "usaTradeOnline": USA_TRADE_ONLINE_URL,
            "witsImport2025": WITS_IMPORT_2025_URL,
            "witsExport2025": WITS_EXPORT_2025_URL,
        },
        "disclaimer": (
            "2020-2025 年为 WITS/UN Comtrade HS7106；2026 月度为 "
            "U.S. Census USA Trade Online / Merchandise Trade HS/HTS 7106："
            "一般进口与总出口。"
            "数量采用商品记录第一计量单位，GM（克）与 CGM（含量克）统一换算为吨。"
            "不含银矿砂/精矿、废料、硬币。"
            f"{current_year} 为截至 {latest_month} 月累计，不能当作全年。"
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] {OUT_JSON.relative_to(ROOT)}")

    annual_table = "\n".join(
        f"| {row['year']}{'*' if row['year'] == current_year else ''} "
        f"| {row['import_tonnes']:,.1f} | {row['export_tonnes']:,.1f} "
        f"| {row['net_import_tonnes']:,.1f} |"
        for row in annual_rows
    )
    def fmt_optional(value: Any) -> str:
        return "—" if value is None else f"{value:,.1f}"

    monthly_table = "\n".join(
        f"| {row['period']} | {fmt_optional(row['import_tonnes'])} "
        f"| {fmt_optional(row['domestic_export_tonnes'])} "
        f"| {fmt_optional(row['reexport_tonnes'])} "
        f"| {fmt_optional(row['export_tonnes'])} "
        f"| {fmt_optional(row['net_import_tonnes'])} |"
        for row in monthly_summaries
    )
    missing_note = (
        "、".join(unavailable_periods) + " 尚未发布。"
        if unavailable_periods
        else "请求范围内月份均已发布。"
    )
    cache_note = (
        "、".join(not_cached_periods) + " 未缓存 EXDB/IMDB 压缩包，"
        "月度数量已由 Census USA Trade Online 官方报告补齐。"
        if not_cached_periods
        else "已发布月份的本地逐月文件齐全。"
    )
    notes = f"""# 美国白银进出口数据整理

> 整理日期：{date.today().isoformat()}  
> 主序列：**U.S. Census Merchandise Trade HS/HTS 7106**  
> 表达基准：**净进口 = 一般进口 −（国内出口 + 再出口）**

## 1. 官方主序列（吨）

| 年 | 进口 | 出口 | 净进口 |
|---:|---:|---:|---:|
{annual_table}

\\* {current_year} 为截至 **{latest_month} 月**累计，不是全年。

## 2. {current_year} 月度（吨）

| 月份 | 一般进口 | 国内出口 | 再出口 | 总出口 | 净进口 |
|---|---:|---:|---:|---:|---:|
{monthly_table}

截至本次运行，用户请求到 {requested_through}；{missing_note}
{cache_note}
美国 Census 的 2026 年 6 月完整商品明细计划于 **2026-08-04** 发布。

## 3. 口径

- 商品范围：10 位 HTS / Schedule B 编码以 `7106` 开头。
- 进口：`IMP_COMM.TXT` 的一般进口第一数量 `GEN_QY1`。
- 出口：`EXP_COMM.TXT` 的国内出口与外国货物再出口第一数量之和。
- 单位：`GM` 为克，`CGM` 为含量克；均除以 1,000,000 换算为吨。
- HS7106 不含银矿砂/精矿、废料和硬币；不能与 USGS 更宽口径银含量直接加总。

## 4. 官方来源

- Census 免费贸易数据产品：{DATA_PRODUCTS_URL}
- Census USA Trade Online：{USA_TRADE_ONLINE_URL}
- 出口总表布局：{EXPORT_LAYOUT_URL}
- 进口总表布局：{IMPORT_LAYOUT_URL}
- 发布日程：{RELEASE_SCHEDULE_URL}
- WITS/UN Comtrade 2025 进口：{WITS_IMPORT_2025_URL}
- WITS/UN Comtrade 2025 出口：{WITS_EXPORT_2025_URL}

## 5. 文件

- `data/us/us_silver_trade_compiled.csv`
- `data/us/us_silver_trade_monthly.csv`
- `data/us/us_silver_trade_by_code.csv`
- `web/public/data/us_trade.json`
"""
    OUT_NOTES.write_text(notes, encoding="utf-8")
    print(f"[OK] {OUT_NOTES.relative_to(ROOT)}")


def parse_through(value: str) -> tuple[int, int]:
    match = re.fullmatch(r"(\d{4})-(\d{2})", value)
    if not match:
        raise argparse.ArgumentTypeError("Use YYYY-MM, for example 2026-06")
    year, month = int(match.group(1)), int(match.group(2))
    if not 1 <= month <= 12:
        raise argparse.ArgumentTypeError("Month must be 01-12")
    return year, month


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--through",
        default="2026-06",
        help="Requested current-year coverage in YYYY-MM (default: 2026-06)",
    )
    parser.add_argument(
        "--annual-start",
        type=int,
        default=2020,
        help="First complete annual HS7106 year to include (default: 2020)",
    )
    parser.add_argument(
        "--available-through",
        default="2026-05",
        help="Latest officially published Census commodity month (default: 2026-05)",
    )
    args = parser.parse_args()
    through_year, through_month = parse_through(args.through)
    available_year, available_month = parse_through(args.available_through)
    if through_year <= args.annual_start:
        raise SystemExit("--through year must be later than --annual-start")
    if available_year != through_year:
        raise SystemExit("--available-through and --through must use the same year")
    if available_month > through_month:
        raise SystemExit("--available-through cannot be later than --through")

    BULK_DIR.mkdir(parents=True, exist_ok=True)
    annual_summaries: dict[int, dict[str, Any]] = {}
    monthly_summaries: list[dict[str, Any]] = []
    all_code_rows: list[dict[str, Any]] = []
    unavailable: list[str] = []
    not_cached: list[str] = []

    print(
        f"[1/3] Complete years {args.annual_start}-{through_year - 1}",
        flush=True,
    )
    for year in range(args.annual_start, through_year):
        if year not in ANNUAL_HS7106:
            raise RuntimeError(f"No annual HS7106 reference configured for {year}")
        imports, exports, source = ANNUAL_HS7106[year]
        annual_summaries[year] = {
            "period": f"{year}-12",
            "ytd_import_tonnes": imports,
            "ytd_export_tonnes": exports,
            "ytd_net_import_tonnes": round(imports - exports, 3),
            "_source": source,
            "_notes": "HS7106 World total; kilograms -> tonnes",
        }

    print(f"[2/3] Current year through {args.through}", flush=True)
    for month in range(1, through_month + 1):
        period = f"{through_year}-{month:02d}"
        if month > available_month:
            print(f"  [NOT PUBLISHED] {period}", flush=True)
            unavailable.append(period)
            continue
        export_local = local_zip_path(through_year, month, "export")
        import_local = local_zip_path(through_year, month, "import")
        if not (export_local.exists() and import_local.exists()):
            if period in USA_TRADE_ONLINE_MONTHLY_2026:
                summary = summarize_usa_trade_online(period)
                monthly_summaries.append(summary)
                print(
                    "  [USA TRADE ONLINE] "
                    f"import={summary['import_tonnes']:,.3f} t, "
                    f"export={summary['export_tonnes']:,.3f} t, "
                    f"net={summary['net_import_tonnes']:,.3f} t",
                    flush=True,
                )
            else:
                print(f"  [NOT CACHED] {period}", flush=True)
            not_cached.append(period)
            continue
        summary, code_rows = fetch_period(through_year, month)
        if period in USA_TRADE_ONLINE_MONTHLY_2026:
            official = summarize_usa_trade_online(period)
            for field in ("import_tonnes", "export_tonnes", "net_import_tonnes"):
                if summary[field] != official[field]:
                    raise RuntimeError(
                        f"{period} Census bulk / USA Trade Online mismatch for "
                        f"{field}: {summary[field]} != {official[field]}"
                    )
            print("  [VALIDATED] bulk totals match USA Trade Online", flush=True)
        monthly_summaries.append(summary)
        all_code_rows.extend(code_rows)

    print("[3/3] Writing outputs", flush=True)
    build_outputs(
        annual_summaries,
        monthly_summaries,
        all_code_rows,
        args.through,
        unavailable,
        not_cached,
    )
    print(
        f"[DONE] requested={args.through}, "
        f"available={monthly_summaries[-1]['period']}",
        flush=True,
    )


if __name__ == "__main__":
    # The public USITC DataWeb route exposes the complete official Census
    # monthly history (1989-present) in two small report calls.  Keep the
    # EXDB/IMDB helpers above for raw-file checks, while making the complete
    # history collector the normal command-line entry point.
    from fetch_us_trade_history import main as history_main

    history_main()
