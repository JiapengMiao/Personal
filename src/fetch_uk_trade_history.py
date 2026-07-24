#!/usr/bin/env python3
"""Download and compile the full HMRC monthly HS71069100 history.

HMRC's UK Trade Info bulk-data archive provides revised replacement files from
2016 onward.  This collector downloads the official archive files, parses the
fixed-width BDS records, and builds a continuous monthly series for unwrought
silver (CN8 71069100).  It never allocates annual totals to months and never
interpolates missing observations.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import urllib.request
import zipfile
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent
UK_DIR = ROOT / "data" / "uk"
CACHE_DIR = UK_DIR / "hmrc_bulk"
OUT_CSV = UK_DIR / "uk_silver_trade_compiled.csv"
OUT_JSON = ROOT / "web" / "public" / "data" / "uk_trade.json"
OUT_MD = UK_DIR / "uk_silver_trade_notes.md"
OUT_MANIFEST = CACHE_DIR / "hmrc_archive_manifest.json"

ARCHIVE_PAGE = (
    "https://www.uktradeinfo.com/trade-data/latest-bulk-data-sets/"
    "bulk-data-sets-archive/"
)
BASE = "https://www.uktradeinfo.com"
SOURCE = "HMRC UK Trade Info bulk data archive (BDS) HS71069100"
SERIES = "hmrc_bds_hs71069100"
CN8 = "71069100"

# HMRC BDS fixed-width layout (zero indexed).
PERIOD_S, PERIOD_L = 0, 6
CN8_S, CN8_L = 13, 8
NETMASS_S, NETMASS_L = 56, 12


@dataclass(frozen=True)
class ArchiveSpec:
    key: str
    flow: str
    url_path: str
    filename: str
    aliases: tuple[Path, ...] = ()

    @property
    def url(self) -> str:
        return BASE + self.url_path

    @property
    def cache_path(self) -> Path:
        return CACHE_DIR / self.filename


ARCHIVES = [
    ArchiveSpec(
        "exp-2026",
        "export",
        "/media/xm1jtft5/bdsexp_26archive.zip",
        "bdsexp_26archive.zip",
        (UK_DIR / "_exp_26.zip",),
    ),
    ArchiveSpec(
        "exp-2026-05",
        "export",
        "/media/m4wpixkm/bdsexp2605.zip",
        "bdsexp2605.zip",
        (UK_DIR / "_bdsexp2605.zip",),
    ),
    ArchiveSpec(
        "exp-2025",
        "export",
        "/media/ye2mtvjj/bdsexp_25archive.zip",
        "bdsexp_25archive.zip",
        (UK_DIR / "_exp_25.zip",),
    ),
    ArchiveSpec("exp-2024", "export", "/media/gjmhgw2g/bdsexp_24archive.zip", "bdsexp_24archive.zip"),
    ArchiveSpec("exp-2023", "export", "/media/br3dcbef/bdsexp_23archive.zip", "bdsexp_23archive.zip"),
    ArchiveSpec("exp-2022", "export", "/media/0e1b11zq/bdsexp_22archive.zip", "bdsexp_22archive.zip"),
    ArchiveSpec("exp-2021", "export", "/media/ifsljkie/bdsexp_21archive.zip", "bdsexp_21archive.zip"),
    ArchiveSpec("exp-2020", "export", "/media/gw2oqtjj/bdsexp_20archive.zip", "bdsexp_20archive.zip"),
    ArchiveSpec("exp-2019", "export", "/media/p0fjm54d/bdsexp_19archive.zip", "bdsexp_19archive.zip"),
    ArchiveSpec("exp-2018", "export", "/media/lvwa0fbz/bdsexp_18archive.zip", "bdsexp_18archive.zip"),
    ArchiveSpec("exp-2017", "export", "/media/y11fd51z/bdsexp_17archive.zip", "bdsexp_17archive.zip"),
    ArchiveSpec("exp-2016", "export", "/media/bkdhi1lr/bdsexp_16archive.zip", "bdsexp_16archive.zip"),
    ArchiveSpec(
        "imp-2026-h1",
        "import",
        "/media/4d1dpb4r/bdsimp_jan-jun26archive.zip",
        "bdsimp_jan-jun26archive.zip",
        (UK_DIR / "_imp_jan_jun26.zip",),
    ),
    ArchiveSpec(
        "imp-2026-05",
        "import",
        "/media/cjilp2jp/bdsimp2605.zip",
        "bdsimp2605.zip",
        (UK_DIR / "_bdsimp2605.zip",),
    ),
    ArchiveSpec(
        "imp-2025-h1",
        "import",
        "/media/rzloztvw/bdsimp_jan-jun25archive.zip",
        "bdsimp_jan-jun25archive.zip",
        (UK_DIR / "_imp_jan_jun25.zip",),
    ),
    ArchiveSpec(
        "imp-2025-h2",
        "import",
        "/media/utwhkjjx/bdsimp_jul-dec25archive.zip",
        "bdsimp_jul-dec25archive.zip",
        (UK_DIR / "_imp_jul_dec25.zip",),
    ),
    ArchiveSpec("imp-2024-h1", "import", "/media/c1rlakyp/bdsimp_jan-jun24archive.zip", "bdsimp_jan-jun24archive.zip"),
    ArchiveSpec("imp-2024-h2", "import", "/media/sgyhxio1/bdsimp_jul-dec24archive.zip", "bdsimp_jul-dec24archive.zip"),
    ArchiveSpec("imp-2023-h1", "import", "/media/zf1kevsi/bdsimp_jan-jun23archive.zip", "bdsimp_jan-jun23archive.zip"),
    ArchiveSpec("imp-2023-h2", "import", "/media/cykmlmkf/bdsimp_jul-dec23archive.zip", "bdsimp_jul-dec23archive.zip"),
    ArchiveSpec("imp-2022-h1", "import", "/media/sp5jfckt/bdsimp_jan-jun22archive.zip", "bdsimp_jan-jun22archive.zip"),
    ArchiveSpec("imp-2022-h2", "import", "/media/guaigoer/bdsimp_jul-dec22archive.zip", "bdsimp_jul-dec22archive.zip"),
    ArchiveSpec("imp-2021", "import", "/media/05ofpp4l/bdsimp_21archive.zip", "bdsimp_21archive.zip"),
    ArchiveSpec("imp-2020", "import", "/media/cw2bkhvh/bdsimp_20archive.zip", "bdsimp_20archive.zip"),
    ArchiveSpec("imp-2019", "import", "/media/batgkl2p/bdsimp_19archive.zip", "bdsimp_19archive.zip"),
    ArchiveSpec("imp-2018", "import", "/media/ndupigqy/bdsimp_18archive.zip", "bdsimp_18archive.zip"),
    ArchiveSpec("imp-2017", "import", "/media/y4rk5l3v/bdsimp_17archive.zip", "bdsimp_17archive.zip"),
    ArchiveSpec("imp-2016", "import", "/media/5qudm0sw/bdsimp_16archive.zip", "bdsimp_16archive.zip"),
]


def valid_zip(path: Path) -> bool:
    return path.is_file() and zipfile.is_zipfile(path)


def local_archive(spec: ArchiveSpec) -> Path | None:
    for candidate in spec.aliases + (spec.cache_path,):
        if valid_zip(candidate):
            return candidate
    return None


def download_archive(spec: ArchiveSpec) -> Path:
    existing = local_archive(spec)
    if existing is not None:
        return existing

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    target = spec.cache_path
    part = target.with_suffix(target.suffix + ".part")
    request = urllib.request.Request(
        spec.url,
        headers={"User-Agent": "Project-002-UK-silver-history/1.0"},
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            with part.open("wb") as handle:
                shutil.copyfileobj(response, handle, length=1024 * 1024)
        if not valid_zip(part):
            raise zipfile.BadZipFile(f"Downloaded file is not a valid ZIP: {spec.url}")
        part.replace(target)
        return target
    except Exception:
        part.unlink(missing_ok=True)
        raise


def prepare_archives(download: bool, workers: int) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    missing: list[ArchiveSpec] = []
    for spec in ARCHIVES:
        path = local_archive(spec)
        if path is None:
            missing.append(spec)
        else:
            resolved[spec.key] = path
            print(f"  [CACHE] {spec.key}: {path.name}", flush=True)

    if missing and not download:
        names = ", ".join(spec.key for spec in missing)
        raise RuntimeError(f"Missing HMRC archives with --no-download: {names}")
    if missing:
        print(
            f"  [DOWNLOAD] {len(missing)} official archives with {workers} workers",
            flush=True,
        )
        with ThreadPoolExecutor(max_workers=workers) as pool:
            jobs = {pool.submit(download_archive, spec): spec for spec in missing}
            for future in as_completed(jobs):
                spec = jobs[future]
                path = future.result()
                resolved[spec.key] = path
                print(
                    f"  [OK] {spec.key}: {path.stat().st_size / 1024 / 1024:,.1f} MB",
                    flush=True,
                )
    return resolved


def parse_archives(
    specs: Iterable[ArchiveSpec],
    resolved: dict[str, Path],
) -> tuple[dict[str, int], set[str], dict[str, int]]:
    monthly_kg: dict[str, int] = defaultdict(int)
    coverage: set[str] = set()
    record_counts: dict[str, int] = {}

    for spec in specs:
        path = resolved[spec.key]
        silver_records = 0
        archive_periods: set[str] = set()
        with zipfile.ZipFile(path) as archive:
            text_members = [
                name for name in archive.namelist() if name.lower().endswith(".txt")
            ]
            if not text_members:
                raise RuntimeError(f"No TXT member in HMRC archive: {path}")
            for name in text_members:
                with archive.open(name) as handle:
                    for raw in handle:
                        line = raw.decode("latin-1", errors="ignore").rstrip("\r\n")
                        if len(line) < NETMASS_S + NETMASS_L:
                            continue
                        period = line[PERIOD_S : PERIOD_S + PERIOD_L]
                        if (
                            len(period) != 6
                            or not period.isdigit()
                            or not 1 <= int(period[4:6]) <= 12
                        ):
                            continue
                        archive_periods.add(period)
                        if line[CN8_S : CN8_S + CN8_L] != CN8:
                            continue
                        try:
                            kg = int(line[NETMASS_S : NETMASS_S + NETMASS_L].strip())
                        except ValueError:
                            continue
                        monthly_kg[period] += kg
                        silver_records += 1
        if not archive_periods:
            raise RuntimeError(f"No monthly periods parsed from HMRC archive: {path}")
        overlap = coverage & archive_periods
        if overlap:
            raise RuntimeError(
                f"Overlapping HMRC archive periods would double count {spec.flow}: "
                f"{', '.join(sorted(overlap))}"
            )
        coverage.update(archive_periods)
        record_counts[spec.key] = silver_records
        print(
            f"  {spec.key}: {min(archive_periods)}-{max(archive_periods)}, "
            f"{silver_records} silver records",
            flush=True,
        )
    return dict(monthly_kg), coverage, record_counts


def yyyymm_range(start: str, end: str) -> list[str]:
    year, month = int(start[:4]), int(start[4:6])
    end_year, end_month = int(end[:4]), int(end[4:6])
    out: list[str] = []
    while (year, month) <= (end_year, end_month):
        out.append(f"{year}{month:02d}")
        month += 1
        if month == 13:
            year += 1
            month = 1
    return out


def write_csv(rows: list[dict[str, object]]) -> None:
    fields = [
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
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    print(f"[OK] {OUT_CSV.relative_to(ROOT)} ({len(rows)} rows)", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-download",
        action="store_true",
        help="Only use existing valid ZIP archives",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Concurrent HMRC archive downloads (default: 4)",
    )
    parser.add_argument(
        "--requested-through",
        default="2026-06",
        help="Requested end month shown in release metadata (default: 2026-06)",
    )
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 8:
        raise SystemExit("--workers must be between 1 and 8")

    print("[1/5] Resolving official HMRC BDS archives", flush=True)
    resolved = prepare_archives(not args.no_download, args.workers)

    print("[2/5] Parsing imports", flush=True)
    import_specs = [spec for spec in ARCHIVES if spec.flow == "import"]
    imports, import_coverage, import_counts = parse_archives(import_specs, resolved)

    print("[3/5] Parsing exports", flush=True)
    export_specs = [spec for spec in ARCHIVES if spec.flow == "export"]
    exports, export_coverage, export_counts = parse_archives(export_specs, resolved)

    common_coverage = import_coverage & export_coverage
    if not common_coverage:
        raise RuntimeError("HMRC import/export archives have no overlapping periods")
    first = min(common_coverage)
    latest = max(common_coverage)
    expected = yyyymm_range(first, latest)
    missing_import = [period for period in expected if period not in import_coverage]
    missing_export = [period for period in expected if period not in export_coverage]
    if missing_import or missing_export:
        raise RuntimeError(
            "HMRC archive coverage is discontinuous: "
            f"imports missing={missing_import}; exports missing={missing_export}"
        )

    print(
        f"[4/5] Building continuous monthly series {first}-{latest} "
        f"({len(expected)} months)",
        flush=True,
    )
    monthly: list[dict[str, object]] = []
    for period in expected:
        import_tonnes = round(imports.get(period, 0) / 1000, 3)
        export_tonnes = round(exports.get(period, 0) / 1000, 3)
        monthly.append(
            {
                "period_type": "month",
                "period": f"{period[:4]}-{period[4:6]}",
                "flow": "both",
                "import_tonnes": import_tonnes,
                "export_tonnes": export_tonnes,
                "net_import_tonnes": round(import_tonnes - export_tonnes, 3),
                "source": SOURCE,
                "notes": "CN8 71069100 unwrought silver; net mass kg -> tonnes",
                "confidence": "high",
                "series": SERIES,
            }
        )
    write_csv(monthly)

    annual: dict[int, dict[str, float]] = defaultdict(
        lambda: {"import_tonnes": 0.0, "export_tonnes": 0.0}
    )
    for row in monthly:
        year = int(str(row["period"])[:4])
        annual[year]["import_tonnes"] += float(row["import_tonnes"])
        annual[year]["export_tonnes"] += float(row["export_tonnes"])
    for values in annual.values():
        values["import_tonnes"] = round(values["import_tonnes"], 3)
        values["export_tonnes"] = round(values["export_tonnes"], 3)
        values["net_import_tonnes"] = round(
            values["import_tonnes"] - values["export_tonnes"], 3
        )

    years = sorted(annual)
    latest_year = int(latest[:4])
    latest_month = int(latest[4:6])
    complete_years = [
        year
        for year in years
        if sum(str(row["period"]).startswith(f"{year}-") for row in monthly) == 12
    ]
    full_imports = [annual[year]["import_tonnes"] for year in complete_years]
    full_nets = [annual[year]["net_import_tonnes"] for year in complete_years]
    requested_gap = (
        [args.requested_through]
        if args.requested_through > f"{latest_year}-{latest_month:02d}"
        else []
    )

    print("[5/5] Writing web JSON, notes, and archive manifest", flush=True)
    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "country": "UK",
        "source": SOURCE,
        "unit": "吨",
        "basis": "net_import",
        "netImportFormula": "进口 − 出口（正值=净流入英国；负值=净流出/再出口）",
        "primarySeries": SERIES,
        "asOf": f"{latest_year}-{latest_month:02d}",
        "requestedThrough": args.requested_through,
        "latestPublished": f"{latest_year}-{latest_month:02d}",
        "unavailablePeriods": requested_gap,
        "years": [str(year) for year in years],
        "imports": [annual[year]["import_tonnes"] for year in years],
        "exports": [annual[year]["export_tonnes"] for year in years],
        "netImport": [annual[year]["net_import_tonnes"] for year in years],
        "monthlyAvailable": True,
        "monthlyCount": len(monthly),
        "monthlySeriesComplete": True,
        "months": [row["period"] for row in monthly],
        "monthlyImports": [row["import_tonnes"] for row in monthly],
        "monthlyExports": [row["export_tonnes"] for row in monthly],
        "monthlyNetImport": [row["net_import_tonnes"] for row in monthly],
        "monthlyNote": (
            "HMRC BDS CN8 71069100 官方月度净重；连续覆盖 "
            f"{monthly[0]['period']} 至 {monthly[-1]['period']}，"
            "不做年度拆月或插值。"
            + (
                f" {args.requested_through} 尚未发布，图中保留空档。"
                if requested_gap
                else ""
            )
        ),
        "latestMonth": f"{latest_year}-{latest_month:02d}",
        "partialYears": {
            str(latest_year): (
                f"截至 {latest_month} 月 · HMRC BDS 月度加总，不可当全年"
            )
        },
        "stats": {
            "latestCompleteYear": max(complete_years),
            "latestYearImport": annual[latest_year]["import_tonnes"],
            "latestYearExport": annual[latest_year]["export_tonnes"],
            "latestYearNetImport": annual[latest_year]["net_import_tonnes"],
            "peakImport": max(full_imports),
            "peakImportYear": complete_years[full_imports.index(max(full_imports))],
            "peakNetImport": max(full_nets),
            "peakNetImportYear": complete_years[full_nets.index(max(full_nets))],
            "minNetImport": min(full_nets),
            "minNetImportYear": complete_years[full_nets.index(min(full_nets))],
        },
        "partners": "全部贸易伙伴与地区合计；伦敦枢纽贸易含转口/再出口",
        "sourceUrls": {
            "archive": ARCHIVE_PAGE,
            "ukTradeInfo": "https://www.uktradeinfo.com/",
        },
        "disclaimer": (
            "英国是 LBMA 全球枢纽，贸易含大量转口/再出口，净进口可为负。"
            f"本序列全部来自 HMRC BDS CN8 71069100 官方月度净重，覆盖 "
            f"{monthly[0]['period']} 至 {monthly[-1]['period']}；"
            "不含其他 HS7106 形态，也不做年度拆月或插值。"
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] {OUT_JSON.relative_to(ROOT)}", flush=True)

    manifest = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "archivePage": ARCHIVE_PAGE,
        "archives": [
            {
                "key": spec.key,
                "flow": spec.flow,
                "url": spec.url,
                "localPath": str(resolved[spec.key].relative_to(ROOT)),
                "sizeBytes": resolved[spec.key].stat().st_size,
                "silverRecordCount": (
                    import_counts.get(spec.key, export_counts.get(spec.key, 0))
                ),
            }
            for spec in ARCHIVES
        ],
    }
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    OUT_MANIFEST.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"[OK] {OUT_MANIFEST.relative_to(ROOT)}", flush=True)

    annual_table = "\n".join(
        f"| {year}{'*' if year == latest_year else ''} "
        f"| {annual[year]['import_tonnes']:,.3f} "
        f"| {annual[year]['export_tonnes']:,.3f} "
        f"| {annual[year]['net_import_tonnes']:,.3f} |"
        for year in years
    )
    notes = f"""# 英国白银进出口数据整理

> 整理日期：{date.today().isoformat()}  
> 主序列：**HMRC UK Trade Info BDS CN8 71069100（月度净重）**  
> 表达基准：**净进口 = 进口 − 出口**

## 1. 覆盖与口径

- 官方真实月度覆盖：**{monthly[0]['period']} 至 {monthly[-1]['period']}**，共 **{len(monthly)}** 个月。
- 商品：CN8 `71069100`，未锻造白银。
- 数量：BDS `Net Mass`，千克除以 1,000 换算为吨。
- 年度拆月/插值：**未使用**。
- 2026 年 replacement archive 当前覆盖 1—4 月；另接入只含 5 月的 `2605` 文件，并通过月份覆盖检查确认没有重复计数。

## 2. 年度校验汇总（吨）

| 年 | 进口 | 出口 | 净进口 |
|---:|---:|---:|---:|
{annual_table}

\\* {latest_year} 为截至 {latest_month} 月累计，不是全年。

## 3. 官方来源

- HMRC BDS archive：{ARCHIVE_PAGE}
- UK Trade Info：https://www.uktradeinfo.com/

## 4. 文件

- `data/uk/uk_silver_trade_compiled.csv`
- `data/uk/hmrc_bulk/`
- `web/public/data/uk_trade.json`
"""
    OUT_MD.write_text(notes, encoding="utf-8")
    print(f"[OK] {OUT_MD.relative_to(ROOT)}", flush=True)
    print(
        f"[DONE] UK official monthly history {monthly[0]['period']}~"
        f"{monthly[-1]['period']} ({len(monthly)} rows)",
        flush=True,
    )


if __name__ == "__main__":
    main()
