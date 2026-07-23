#!/usr/bin/env python3
"""Parse UK HS71069100 (unwrought silver) monthly trade from HMRC bulk data archives."""
import csv
import json
import zipfile
from collections import defaultdict
from datetime import datetime, date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BULK = ROOT / "data" / "uk"
OUT_CSV = BULK / "uk_silver_trade_compiled.csv"
OUT_JSON = ROOT / "web" / "public" / "data" / "uk_trade.json"
OUT_MD = BULK / "uk_silver_trade_notes.md"

# HMRC BDS fixed-width layout (0-indexed):
PERIOD_S, PERIOD_L = 0, 6      # YYYYMM
CN8_S, CN8_L = 13, 8           # 8-digit commodity
NETMASS_S, NETMASS_L = 56, 12  # kg

IMP_ZIPS = [BULK / "_imp_jan_jun25.zip", BULK / "_imp_jul_dec25.zip",
            BULK / "_imp_jan_jun26.zip", BULK / "_bdsimp2605.zip"]
EXP_ZIPS = [BULK / "_exp_25.zip", BULK / "_exp_26.zip",
            BULK / "_bdsexp2605.zip"]

HISTORICAL = {
    2015: (3752, 3747, "WSS bullion"),
    2016: (3903, 1358, "WSS bullion"),
    2017: (4559, 1338, "WSS bullion"),
    2018: (3313, 2690, "WSS bullion"),
    2019: (2877, 2081, "WSS bullion"),
    2020: (3546, 4890, "WITS/Comtrade HS710691"),
    2021: (6290, 3790, "WITS/Comtrade HS710691"),
    2022: (2340, 11270, "WITS/Comtrade HS710691"),
    2023: (4094, 3681, "WITS/Comtrade HS710691"),
    2024: (4500, 4129, "WITS/Comtrade HS710691"),
}


def parse_zips(zips, cn8="71069100"):
    monthly = defaultdict(int)
    for zp in zips:
        if not zp.exists():
            continue
        n = 0
        with zipfile.ZipFile(zp) as zf:
            for name in zf.namelist():
                if not name.lower().endswith(".txt"):
                    continue
                with zf.open(name) as f:
                    for raw in f:
                        ln = raw.decode("utf-8", errors="ignore").rstrip("\r\n")
                        if len(ln) < NETMASS_S + NETMASS_L:
                            continue
                        if ln[CN8_S:CN8_S+CN8_L] != cn8:
                            continue
                        period = ln[PERIOD_S:PERIOD_S+PERIOD_L]
                        try:
                            kg = int(ln[NETMASS_S:NETMASS_S+NETMASS_L])
                        except ValueError:
                            continue
                        monthly[period] += kg
                        n += 1
        print(f"  {zp.name}: {n} records")
    return dict(monthly)


def main():
    print("[1/5] Parsing imports...")
    imp = parse_zips(IMP_ZIPS)
    print(f"  -> {len(imp)} months")

    print("[2/5] Parsing exports...")
    exp = parse_zips(EXP_ZIPS)
    print(f"  -> {len(exp)} months")

    bulk_months = sorted(set(list(imp) + list(exp)))
    print(f"[3/5] Bulk months: {len(bulk_months)} ({bulk_months[0]}~{bulk_months[-1]})")

    # Monthly CSV rows
    monthly = []
    for m in bulk_months:
        yr, mo = int(m[:4]), int(m[4:6])
        monthly.append({
            "period_type": "month", "period": f"{yr}-{mo:02d}", "flow": "both",
            "import_tonnes": round(imp.get(m, 0) / 1000, 1),
            "export_tonnes": round(exp.get(m, 0) / 1000, 1),
            "net_import_tonnes": round((imp.get(m, 0) - exp.get(m, 0)) / 1000, 1),
            "source": "HMRC UK Trade Info bulk data (BDS)",
            "notes": "HS71069100 unwrought silver; kg->t",
            "confidence": "high", "series": "hmrc_ots_hs71069100",
        })

    # Annual aggregation
    bulk_annual = defaultdict(lambda: [0.0, 0.0])
    for m in bulk_months:
        y = int(m[:4])
        bulk_annual[y][0] += imp.get(m, 0) / 1000
        bulk_annual[y][1] += exp.get(m, 0) / 1000

    annual = {}
    for y, (i, e, s) in HISTORICAL.items():
        if y in bulk_annual:
            annual[y] = (round(bulk_annual[y][0], 1), round(bulk_annual[y][1], 1), "HMRC BDS")
        else:
            annual[y] = (float(i), float(e), s)
    for y in sorted(bulk_annual):
        if y not in annual:
            annual[y] = (round(bulk_annual[y][0], 1), round(bulk_annual[y][1], 1), "HMRC BDS")

    years = sorted(annual)
    latest_m = bulk_months[-1]
    ly, lm = int(latest_m[:4]), int(latest_m[4:6])
    print(f"[4/5] Annual coverage: {years[0]}~{years[-1]}, latest {ly}-{lm:02d}")

    # Write CSV
    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    flds = ["period_type","period","flow","import_tonnes","export_tonnes",
            "net_import_tonnes","source","notes","confidence","series"]
    with OUT_CSV.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=flds, extrasaction="ignore")
        w.writeheader()
        w.writerows(monthly)
    print(f"[OK] CSV ({len(monthly)} rows)")

    # Write JSON
    imps = [annual[y][0] for y in years]
    exps = [annual[y][1] for y in years]
    nets = [round(annual[y][0] - annual[y][1], 1) for y in years]
    pi = max(range(len(imps)), key=lambda i: imps[i])
    ni = min(range(len(nets)), key=lambda i: nets[i])
    complete_yrs = [y for y in years if sum(1 for r in monthly if r["period"].startswith(str(y))) == 12]
    # 不完整年（有月度记录但不足12个月）标记为 partialYears，前端淡化显示
    partial_years = {}
    for y in years:
        cnt = sum(1 for r in monthly if r["period"].startswith(str(y)))
        if 0 < cnt < 12:
            partial_years[str(y)] = f"截至 {lm} 月 · BDS 月度加总，不可当全年"

    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "country": "UK",
        "source": "HMRC UK Trade Info bulk data (BDS) HS71069100",
        "unit": "\u5428",
        "basis": "net_import",
        "netImportFormula": "\u8fdb\u53e3 \u2212 \u51fa\u53e3\uff08\u6b63\u503c=\u51c0\u6d41\u5165\u82f1\u56fd\uff1b\u8d1f\u503c=\u51c0\u6d41\u51fa/\u518d\u51fa\u53e3\uff09",
        "primarySeries": "hmrc_ots_hs71069100",
        "asOf": f"{ly}-{lm:02d}",
        "years": [str(y) for y in years],
        "imports": [round(annual[y][0], 1) for y in years],
        "exports": [round(annual[y][1], 1) for y in years],
        "netImport": nets,
        "monthlyAvailable": True,
        "monthlyCount": len(monthly),
        "latestMonth": f"{ly}-{lm:02d}",
        "partialYears": partial_years,
        "stats": {
            "latestCompleteYear": max(complete_yrs) if complete_yrs else years[-1],
            "latestYearImport": imps[-1],
            "latestYearExport": exps[-1],
            "latestYearNetImport": nets[-1],
            "peakImport": imps[pi], "peakImportYear": years[pi],
            "peakNetImport": max(nets), "peakNetImportYear": years[nets.index(max(nets))],
            "minNetImport": nets[ni], "minNetImportYear": years[ni],
        },
        "partners": "\u8fdb\u53e3\uff1a\u4e2d/\u6e2f/\u54c8\u8428\u514b/\u5fb7/\u6ce2\u7b49\uff1b\u51fa\u53e3\uff1a\u5370\u5ea6\u3001\u52a0\u62ff\u5927\u3001\u745e\u58eb\u3001\u963f\u8054\u914b\u3001\u7f8e\u56fd\u7b49\uff08\u4f26\u6566\u67a2\u7ebd\u518d\u51fa\u53e3\uff09",
        "disclaimer": (
            "\u82f1\u56fd\u662f LBMA \u5168\u7403\u67a2\u7ebd\uff0c\u8d38\u6613\u542b\u5927\u91cf\u8f6c\u53e3/\u518d\u51fa\u53e3\uff0c\u51c0\u8fdb\u53e3\u6ce2\u52a8\u5927\u751a\u81f3\u4e3a\u8d1f\u3002"
            f"\u6570\u636e\u6765\u81ea HMRC UK Trade Info bulk data\uff0c\u622a\u81f3 {ly}-{lm:02d}\u3002"
            "2015-2024 \u4e3a WSS/Comtrade \u5e74\u5ea6\u6570\u636e\uff0c2025+ \u4e3a BDS \u6708\u5ea6\u660e\u7ec6\u3002"
        ),
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON")

    # Write notes MD
    md = [
        "# \u82f1\u56fd\u767d\u94f6\u8fdb\u51fa\u53e3\u6570\u636e\u6574\u7406", "",
        f"> \u6574\u7406\u65e5\u671f\uff1a{date.today().isoformat()}  ",
        "> **\u8868\u8fbe\u57fa\u51c6\uff1a\u51c0\u8fdb\u53e3 = \u8fdb\u53e3 \u2212 \u51fa\u53e3**\uff08\u6b63=\u51c0\u6d41\u5165\uff1b\u8d1f=\u51c0\u6d41\u51fa/\u518d\u51fa\u53e3\uff0c\u4f26\u6566\u67a2\u7ebd\u5e38\u89c1\uff09  ",
        "> \u4e3b\u5e8f\u5217\uff1a**HMRC UK Trade Info BDS HS71069100**\uff08\u672a\u953b\u9020\u767d\u94f6\uff09", "",
        "## 1. \u5e74\u5ea6\u6c47\u603b\uff08\u5428\uff09", "", "| \u5e74 | \u8fdb\u53e3 | \u51fa\u53e3 | \u51c0\u8fdb\u53e3 |", "|---:|---:|---:|---:|",
    ]
    for y in years:
        md.append(f"| {y} | {annual[y][0]:,.1f} | {annual[y][1]:,.1f} | {annual[y][0]-annual[y][1]:,.1f} |")
    md += ["", "### \u8981\u70b9",
        f"- \u6570\u636e\u8986\u76d6 {years[0]}-{years[-1]}\uff0c\u622a\u81f3 **{ly}-{lm:02d}** \u6708\u5ea6\u660e\u7ec6",
        f"- \u6708\u5ea6\u8bb0\u5f55\u5171 **{len(monthly)}** \u6761",
        f"- **{years[pi]} \u5e74\u8fdb\u53e3\u5cf0\u503c**\uff1a{imps[pi]:,.0f} \u5428",
        f"- **{years[ni]} \u5e74\u51c0\u8fdb\u53e3\u6700\u4f4e**\uff1a{nets[ni]:,.0f} \u5428",
        "- \u82f1\u56fd\u77ff\u5c71\u4ea7\u91cf\u53ef\u5ffd\u7565\uff1b\u8d38\u6613\u53cd\u6620 **LBMA \u6e05\u7b97/\u91d1\u5e93/\u518d\u51fa\u53e3** \u529f\u80fd",
        "- \u5bf9\u5370\u51fa\u53e3\u662f\u957f\u671f\u5173\u952e\u6d41\u51fa\u65b9\u5411\uff08\u4e0e\u5370\u5ea6\u8fdb\u53e3\u5173\u7a0e\u653f\u7b56\u8054\u52a8\uff09", "",
        "## 2. \u4e00\u624b\u6e90", "- HMRC UK Trade Info\uff1ahttps://www.uktradeinfo.com/",
        "- LBMA vault\uff1ahttps://www.lbma.org.uk/prices-and-data/london-vault-data", "",
        "## 3. \u6587\u4ef6", "- `data/uk/uk_silver_trade_compiled.csv`", "- `web/public/data/uk_trade.json`",
    ]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"[OK] MD")
    print(f"\n[DONE] UK {years[0]}~{ly}-{lm:02d}, {len(monthly)} monthly records")


if __name__ == "__main__":
    main()
