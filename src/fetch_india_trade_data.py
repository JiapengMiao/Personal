#!/usr/bin/env python3
"""Fetch official India monthly HS 7106 silver import/export quantities.

Source:
    Government of India, Department of Commerce, TradeStat / DGCI&S.

The TradeStat commodity-wise report returns the selected calendar month's
quantity for both the requested year and the prior year.  This collector pairs
adjacent years to reduce the number of requests, preserves the official integer
kilogram observations, and derives tonnes/net imports without interpolation.
"""
from __future__ import annotations

import argparse
import csv
import http.cookiejar
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
INDIA_DIR = ROOT / "data" / "india"
OUT_MONTHLY = INDIA_DIR / "india_silver_trade_monthly.csv"

IMPORT_URL = "https://tradestat.commerce.gov.in/meidb/commoditywise_import"
EXPORT_URL = "https://tradestat.commerce.gov.in/meidb/commoditywise_export"
SOURCE_NAME = "India Department of Commerce TradeStat / DGCI&S · HS7106"
FIRST_MONTH = "2018-01"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)

MONTH_NAMES = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}


@dataclass(frozen=True)
class FlowConfig:
    name: str
    url: str
    month_field: str
    year_field: str
    level_field: str
    report_value_field: str
    report_year_field: str


FLOWS = {
    "imports": FlowConfig(
        name="imports",
        url=IMPORT_URL,
        month_field="imddMonth",
        year_field="imddYear",
        level_field="imddCommodityLevel",
        report_value_field="imddReportVal",
        report_year_field="imddReportYear",
    ),
    "exports": FlowConfig(
        name="exports",
        url=EXPORT_URL,
        month_field="ddMonth",
        year_field="ddYear",
        level_field="ddCommodityLevel",
        report_value_field="ddReportVal",
        report_year_field="ddReportYear",
    ),
}


class ReportTableParser(HTMLParser):
    """Collect cells from all HTML table rows while preserving empty cells."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
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
            value = " ".join("".join(self._cell).split())
            self._row.append(value)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
            self._cell = None


def month_iter(start: str, end: str) -> Iterable[str]:
    year, month = map(int, start.split("-"))
    end_year, end_month = map(int, end.split("-"))
    while (year, month) <= (end_year, end_month):
        yield f"{year:04d}-{month:02d}"
        month += 1
        if month == 13:
            month = 1
            year += 1


def shift_month(value: str, delta: int) -> str:
    year, month = map(int, value.split("-"))
    serial = year * 12 + month - 1 + delta
    return f"{serial // 12:04d}-{serial % 12 + 1:02d}"


def open_text(opener: urllib.request.OpenerDirector, request: urllib.request.Request) -> str:
    with opener.open(request, timeout=60) as response:
        return response.read().decode("utf-8", errors="replace")


def new_session(config: FlowConfig) -> tuple[urllib.request.OpenerDirector, str]:
    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(cookie_jar)
    )
    request = urllib.request.Request(
        config.url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
    )
    html = open_text(opener, request)
    token_match = re.search(r'name="_token"\s+value="([^"]+)"', html)
    if not token_match:
        raise RuntimeError(f"{config.name}: TradeStat CSRF token not found")
    return opener, token_match.group(1)


def discover_latest_month() -> str:
    opener = urllib.request.build_opener()
    request = urllib.request.Request(
        IMPORT_URL,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
    )
    html = open_text(opener, request)
    match = re.search(
        r"Data available:\s*Jan\s+2018\s+to\s+([A-Za-z]+)\s+(\d{4})",
        html,
        flags=re.IGNORECASE,
    )
    if not match:
        raise RuntimeError("Could not discover latest TradeStat publication month")
    month_name = match.group(1).capitalize()
    if month_name not in MONTH_NAMES:
        raise RuntimeError(f"Unknown month name in TradeStat banner: {month_name}")
    return f"{int(match.group(2)):04d}-{MONTH_NAMES[month_name]:02d}"


def parse_quantity(value: str) -> int | None:
    normalized = (
        value.replace(",", "")
        .replace("\u2212", "-")
        .replace("\xa0", "")
        .strip()
    )
    if not normalized or normalized in {"—", "-", "NA", "N/A"}:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", normalized)
    if not match:
        return None
    return int(round(float(match.group(0))))


def parse_report(html: str, query_year: int, month: int) -> dict[str, int | None]:
    parser = ReportTableParser()
    parser.feed(html)
    for row in parser.rows:
        if "7106" not in row:
            continue
        code_index = row.index("7106")
        # Row layout after HS code:
        # description, unit, prior-year month, current-year month, growth, ...
        if len(row) <= code_index + 4:
            continue
        prior_value = parse_quantity(row[code_index + 3])
        current_value = parse_quantity(row[code_index + 4])
        suffix = f"{month:02d}"
        return {
            f"{query_year - 1:04d}-{suffix}": prior_value,
            f"{query_year:04d}-{suffix}": current_value,
        }
    raise RuntimeError(
        f"HS7106 row not found in TradeStat response for {query_year}-{month:02d}"
    )


def post_report(
    opener: urllib.request.OpenerDirector,
    token: str,
    config: FlowConfig,
    query_year: int,
    month: int,
) -> dict[str, int | None]:
    fields = {
        "_token": token,
        config.month_field: str(month),
        config.year_field: str(query_year),
        "comlev": "specific",
        config.level_field: "4",
        "comval": "7106",
        config.report_value_field: "2",  # Quantity
        config.report_year_field: "2",  # Calendar year
    }
    request = urllib.request.Request(
        config.url,
        data=urllib.parse.urlencode(fields).encode("utf-8"),
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": config.url,
        },
        method="POST",
    )
    return parse_report(open_text(opener, request), query_year, month)


def build_query_tasks(target_months: set[str], latest_month: str) -> list[tuple[int, int]]:
    """Pair adjacent years because each report includes current + prior year."""

    latest_year, latest_number = map(int, latest_month.split("-"))
    tasks: set[tuple[int, int]] = set()
    by_month_number: dict[int, set[int]] = {month: set() for month in range(1, 13)}
    for value in target_months:
        year, month = map(int, value.split("-"))
        by_month_number[month].add(year)

    for month, years in by_month_number.items():
        remaining = set(years)
        while remaining:
            year = min(remaining)
            next_year = year + 1
            next_is_published = (
                next_year < latest_year
                or (next_year == latest_year and month <= latest_number)
            )
            if next_year in remaining and next_is_published:
                tasks.add((next_year, month))
                remaining.remove(year)
                remaining.remove(next_year)
            else:
                tasks.add((year, month))
                remaining.remove(year)
    return sorted(tasks)


def fetch_chunk(
    config: FlowConfig,
    tasks: list[tuple[int, int]],
) -> dict[str, int | None]:
    if not tasks:
        return {}
    opener, token = new_session(config)
    values: dict[str, int | None] = {}
    for query_year, month in tasks:
        for attempt in range(1, 4):
            try:
                values.update(post_report(opener, token, config, query_year, month))
                break
            except (OSError, urllib.error.HTTPError, RuntimeError) as exc:
                if attempt == 3:
                    raise RuntimeError(
                        f"{config.name} {query_year}-{month:02d} failed after "
                        f"{attempt} attempts: {exc}"
                    ) from exc
                time.sleep(float(attempt))
                opener, token = new_session(config)
    return values


def fetch_flow(
    config: FlowConfig,
    target_months: set[str],
    latest_month: str,
    workers: int,
) -> dict[str, int]:
    tasks = build_query_tasks(target_months, latest_month)
    if not tasks:
        return {}
    worker_count = max(1, min(workers, len(tasks)))
    chunks = [tasks[index::worker_count] for index in range(worker_count)]
    combined: dict[str, int | None] = {}
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = [
            executor.submit(fetch_chunk, config, chunk)
            for chunk in chunks
            if chunk
        ]
        for future in as_completed(futures):
            combined.update(future.result())

    result: dict[str, int] = {}
    for month in sorted(target_months):
        value = combined.get(month)
        if value is None:
            raise RuntimeError(f"{config.name}: missing official quantity for {month}")
        result[month] = value
    print(
        f"[OK] {config.name}: {len(result)} months from "
        f"{len(tasks)} TradeStat reports"
    )
    return result


def load_existing() -> dict[str, dict[str, str]]:
    if not OUT_MONTHLY.exists():
        return {}
    with OUT_MONTHLY.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["month"]: row for row in csv.DictReader(handle)}


def write_monthly(
    months: list[str],
    existing: dict[str, dict[str, str]],
    imports: dict[str, int],
    exports: dict[str, int],
    fetched_at: str,
) -> None:
    rows: list[dict[str, object]] = []
    for month in months:
        old = existing.get(month, {})
        import_kg = imports.get(month)
        export_kg = exports.get(month)
        if import_kg is None and old.get("imports_kg"):
            import_kg = int(old["imports_kg"])
        if export_kg is None and old.get("exports_kg"):
            export_kg = int(old["exports_kg"])
        if import_kg is None or export_kg is None:
            raise RuntimeError(f"Cannot write incomplete India month: {month}")
        net_kg = import_kg - export_kg
        rows.append(
            {
                "month": month,
                "imports_kg": import_kg,
                "exports_kg": export_kg,
                "net_import_kg": net_kg,
                "imports_tonnes": f"{import_kg / 1000.0:.3f}",
                "exports_tonnes": f"{export_kg / 1000.0:.3f}",
                "net_import_tonnes": f"{net_kg / 1000.0:.3f}",
                "source": SOURCE_NAME,
                "import_source_url": IMPORT_URL,
                "export_source_url": EXPORT_URL,
                "fetched_at": fetched_at,
            }
        )

    fieldnames = list(rows[0])
    OUT_MONTHLY.parent.mkdir(parents=True, exist_ok=True)
    temp_path = OUT_MONTHLY.with_suffix(".csv.tmp")
    with temp_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    temp_path.replace(OUT_MONTHLY)
    print(f"[OK] CSV -> {OUT_MONTHLY} ({len(rows)} months)")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fetch official India TradeStat HS7106 monthly quantities"
    )
    parser.add_argument("--start", default=FIRST_MONTH)
    parser.add_argument("--end", help="YYYY-MM; default: latest published month")
    parser.add_argument(
        "--refresh-months",
        type=int,
        default=18,
        help="Re-fetch this many latest months on incremental runs (default: 18)",
    )
    parser.add_argument(
        "--refresh-all",
        action="store_true",
        help="Re-fetch the complete requested range",
    )
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()

    latest_month = discover_latest_month()
    end_month = args.end or latest_month
    if end_month > latest_month:
        raise ValueError(
            f"Requested {end_month}, but TradeStat is only published through "
            f"{latest_month}"
        )
    if args.start < FIRST_MONTH or args.start > end_month:
        raise ValueError(f"Invalid range: {args.start} to {end_month}")

    months = list(month_iter(args.start, end_month))
    existing = load_existing()
    missing = {
        month
        for month in months
        if month not in existing
        or not existing[month].get("imports_kg")
        or not existing[month].get("exports_kg")
    }
    if args.refresh_all or not existing:
        target_months = set(months)
    else:
        refresh_start = shift_month(
            end_month, -max(0, args.refresh_months - 1)
        )
        recent = {month for month in months if month >= refresh_start}
        target_months = missing | recent

    print(
        f"[INFO] TradeStat available through {latest_month}; "
        f"range={args.start}..{end_month}; refresh={len(target_months)} months"
    )
    imports = fetch_flow(
        FLOWS["imports"], target_months, latest_month, args.workers
    )
    exports = fetch_flow(
        FLOWS["exports"], target_months, latest_month, args.workers
    )
    fetched_at = datetime.now().astimezone().isoformat(timespec="seconds")
    write_monthly(months, existing, imports, exports, fetched_at)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
