#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
crosscheck_wss_flows.py

WSS 2026 六张白银流向图「几何配对」的官方数据交叉验证。

四路证据：
  A. UK HMRC BDS（本地缓存 zip，固定宽文本，伙伴国代码 offset 29:31，NETMASS 56:68 单位 0.1kg）
     → 直接验证 App24a 英国出口、App24b 英国进口全员。
  B. 印度 TradeStat commodity_wise_all_countries_import（cwacim 表单 POST）
     → 直接验证 App26 印度进口全员；镜像验证 23a→India、24a→India、25→India。
  C. 香港 IDDS API 出口按目的地（ttype 2/3/4 探测，ccclass=C&cc=ALL）
     → 直接验证 App25 香港出口全员，并裁定 Vietnam/Singapore 的 8/4 归属。
  D. USITC DataWeb 缓存 CSV（fetch_partner_flows.py 产物）
     → 镜像验证 23a→USA、24a→USA、25→USA、26←USA 及 24b←USA（美国出口侧）。

输出：output/_wss_official_crosscheck.json + 控制台对照表（Moz ↔ 吨，1 Moz = 0.0311034768 t）。
用法:  python src/crosscheck_wss_flows.py
"""
from __future__ import annotations

import csv
import http.cookiejar
import io
import json
import re
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
YEAR = 2025
T_PER_MOZ = 31.1034768  # 1 Moz = 31.1034768 t

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
)

UK_ZIPS = {
    "import": [ROOT / "data/uk/_imp_jan_jun25.zip", ROOT / "data/uk/_imp_jul_dec25.zip"],
    "export": [ROOT / "data/uk/_exp_25.zip"],
}
IN_IMPORT_URL = "https://tradestat.commerce.gov.in/meidb/commodity_wise_all_countries_import"
CACHE_IN = ROOT / "data" / "india" / f"india_import_partners_cy{YEAR}.html"
HK_API = "https://tradeidds.censtatd.gov.hk/api/get"
CACHE_HK = ROOT / "data" / f"hk_silver_export_partners_{YEAR}.json"
US_CSV = ROOT / "data" / "us" / f"us_silver_trade_partners_{YEAR}.csv"

OUT_JSON = ROOT / "output" / "_wss_official_crosscheck.json"

ISO2_NAME = {
    "AE": "UAE", "AU": "Australia", "BE": "Belgium", "CA": "Canada", "CH": "Switzerland",
    "CN": "China", "DE": "Germany", "ES": "Spain", "FR": "France", "GB": "UK",
    "HK": "Hong Kong", "ID": "Indonesia", "IN": "India", "IT": "Italy", "KR": "South Korea",
    "KZ": "Kazakhstan", "LB": "Lebanon", "MA": "Morocco", "MX": "Mexico", "PE": "Peru",
    "PL": "Poland", "SG": "Singapore", "TH": "Thailand", "TR": "Turkey", "TW": "Taiwan",
    "US": "USA", "UZ": "Uzbekistan", "VN": "Vietnam", "JP": "Japan", "NL": "Netherlands",
    "ZA": "South Africa", "RU": "Russia", "AT": "Austria", "SE": "Sweden", "NO": "Norway",
    "KG": "Kyrgyzstan", "AR": "Argentina", "BR": "Brazil", "CL": "Chile", "CO": "Colombia",
    "IE": "Ireland", "IL": "Israel", "MY": "Malaysia", "PT": "Portugal", "EG": "Egypt",
}

# ——— 几何配对锚点（Moz，来自 redo_wss_pairing.py 定稿）———
GEOM = {
    "23a_swiss_export": {"UK": 24, "USA": 11, "Turkey": 10, "India": 8, "Germany": 6,
                         "Italy": 5, "Lebanon": 4, "France": 3, "UAE": 3, "Thailand": 3},
    "23b_swiss_import": {"Morocco": 7, "Italy": 6, "China": 5, "Germany": 4, "USA": 3,
                         "Peru": 2, "Indonesia": 1, "Poland": 1, "Australia": 1},
    "24a_uk_export": {"USA": 128, "India": 66, "Canada": 15, "Switzerland": 8, "UAE": 4,
                      "Belgium": 3},
    "24b_uk_import": {"China": 48, "Kazakhstan": 38, "USA": 31, "Spain": 27, "Poland": 23,
                      "South Korea": 22, "Germany": 22, "Canada": 17, "Mexico": 12,
                      "Uzbekistan": 4, "Switzerland": 3},
    "25_hk_export": {"India": 71, "UK": 37, "Thailand": 13, "VN_or_SG_8": 8, "UAE": 6,
                     "USA": 5, "Switzerland": 5, "Taiwan": 5, "VN_or_SG_4": 4,
                     "China": 3, "Australia": 3},
    "26_india_import": {"Hong Kong": 94, "UK": 71, "USA": 16, "Switzerland": 11, "UAE": 9,
                        "China": 6, "Singapore": 5, "Australia": 3, "South Korea": 3},
}


def norm_name(raw: str) -> str:
    """规范化官方国名（印度 TradeStat 拼写、IDDS、USITC）到 GEOM 用名。"""
    s = re.sub(r"\s+", " ", raw.replace(".", " ")).strip().upper()
    table = {
        "U K": "UK", "UNITED KINGDOM": "UK", "U S A": "USA", "UNITED STATES": "USA",
        "U ARAB EMTS": "UAE", "UNITED ARAB EMIRATES": "UAE",
        "CHINA P RP": "China", "CHINA": "China", "HONG KONG": "Hong Kong",
        "SWITZERLAND": "Switzerland", "SINGAPORE": "Singapore", "AUSTRALIA": "Australia",
        "KOREA RP": "South Korea", "KOREA, REPUBLIC OF": "South Korea", "SOUTH KOREA": "South Korea",
        "GERMANY": "Germany", "CANADA": "Canada", "MEXICO": "Mexico", "SPAIN": "Spain",
        "POLAND": "Poland", "KAZAKHSTAN": "Kazakhstan", "UZBEKISTAN": "Uzbekistan",
        "VIETNAM": "Vietnam", "VIET NAM": "Vietnam", "TAIWAN": "Taiwan",
        "THAILAND": "Thailand", "TURKEY": "Turkey", "TURKIYE": "Turkey", "ITALY": "Italy",
        "FRANCE": "France", "BELGIUM": "Belgium", "LEBANON": "Lebanon",
        "MOROCCO": "Morocco", "PERU": "Peru", "INDONESIA": "Indonesia", "INDIA": "India",
        "JAPAN": "Japan", "NETHERLANDS": "Netherlands", "RUSSIA": "Russia",
    }
    return table.get(s, raw.strip())


# ——— A. UK HMRC BDS by partner ———
def uk_bds_by_partner() -> dict:
    """{flow: {commodity: {partner: tonnes}}}，NETMASS(56:68) 单位 kg → t（÷1000）。
    实证：BDSimp 行 43:56 为 SUPP(克，含银量)，56:68 为 NETMASS(kg，总重)，
    kg 口径下 UK 出口六伙伴与 WSS 几何值及印度镜像全部吻合。"""
    out: dict[str, dict[str, dict[str, float]]] = {}
    for flow, zips in UK_ZIPS.items():
        agg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        months = 0
        for zp in zips:
            zf = zipfile.ZipFile(zp)
            for name in zf.namelist():
                if not re.match(r"BDS\w+\d{4}\.txt", Path(name).name):
                    continue
                months += 1
                for raw in io.TextIOWrapper(zf.open(name), encoding="latin-1"):
                    commodity = raw[13:21].strip()
                    if not commodity.startswith("7106"):
                        continue
                    iso2 = raw[29:31].strip()
                    try:
                        kg = int(raw[56:68])
                    except ValueError:
                        continue
                    if iso2:
                        agg[commodity][iso2] += kg
        out[flow] = {
            c: {ISO2_NAME.get(k, k): round(v / 1000.0, 3) for k, v in sorted(d.items(), key=lambda kv: -kv[1])}
            for c, d in agg.items()
        }
        print(f"[UK] {flow}: {months} 个月, 商品 {list(out[flow])}", flush=True)
        for c, d in out[flow].items():
            print(f"  {c}: {len(d)} 伙伴, 合计 {sum(d.values()):,.1f} t", flush=True)
    return out


# ——— B. 印度进口 by partner ———
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


def fetch_india_imports() -> dict[str, float]:
    print(f"[IN] imports by partner CY{YEAR} ...", flush=True)
    if CACHE_IN.exists():
        print(f"  [CACHE] 复用 {CACHE_IN.relative_to(ROOT)}", flush=True)
        resp = CACHE_IN.read_text(encoding="utf-8")
    else:
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))
        html = opener.open(
            urllib.request.Request(IN_IMPORT_URL, headers={"User-Agent": UA}), timeout=60
        ).read().decode("utf-8", "replace")
        token = re.search(r'name="_token"\s+value="([^"]+)"', html)
        if not token:
            raise RuntimeError("TradeStat CSRF token not found (all-countries import)")
        fields = {
            "_token": token.group(1),
            "cwacimHSCODE": "7106",
            "hscode_value": "",
            "description_value": "",
            "cwacimMonth": "12",
            "cwacimYear": str(YEAR),
            "cwacimReportVal": "2",   # Quantity
            "cwacimReportYear": "2",  # Calendar Year
        }
        req = urllib.request.Request(
            IN_IMPORT_URL,
            data=urllib.parse.urlencode(fields).encode("utf-8"),
            headers={
                "User-Agent": UA,
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": IN_IMPORT_URL,
            },
            method="POST",
        )
        resp = opener.open(req, timeout=60).read().decode("utf-8", "replace")
        CACHE_IN.parent.mkdir(parents=True, exist_ok=True)
        CACHE_IN.write_text(resp, encoding="utf-8")
        print(f"  [CACHE] {CACHE_IN.relative_to(ROOT)}", flush=True)

    parser = _TableParser()
    parser.feed(resp)
    header = next((r for r in parser.rows if r and "Country" in r), None)
    if not header:
        raise RuntimeError("TradeStat import partner table header not found")
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
                kg_by_partner[norm_name(row[1])] = kg
        elif "Total" in row:
            official_total = int(round(float(row[cy_col].replace(",", "") or 0)))

    summed = sum(kg_by_partner.values())
    print(f"  伙伴合计 {summed:,} kg vs 报表 Total {official_total:,} kg", flush=True)

    with (ROOT / "data" / "india" / "india_silver_trade_monthly.csv").open(
        encoding="utf-8-sig", newline=""
    ) as fh:
        monthly_total = sum(
            int(r["imports_kg"]) for r in csv.DictReader(fh) if r["month"].startswith(str(YEAR))
        )
    print(f"  与月度 CSV {YEAR} 进口合计 {monthly_total:,} kg 交叉校验", flush=True)
    ok = (official_total == summed) and (summed == monthly_total)
    print(f"  一致性: {'OK' if ok else 'MISMATCH'}", flush=True)

    tonnes = {p: round(kg / 1000.0, 3) for p, kg in kg_by_partner.items()}
    return dict(sorted(tonnes.items(), key=lambda kv: -kv[1]))


# ——— C. HK IDDS 出口按目的地 ———
def fetch_hk_exports() -> dict[str, float]:
    print(f"[HK] exports by destination {YEAR} ...", flush=True)
    if CACHE_HK.exists():
        print(f"  [CACHE] 复用 {CACHE_HK.relative_to(ROOT)}", flush=True)
        raw = json.loads(CACHE_HK.read_text(encoding="utf-8"))
        return {r["partner"]: r["tonnes"] for r in raw["partners"]}

    cookie_jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

    def get(params: dict[str, str]) -> dict:
        url = HK_API + "?" + "&".join(f"{k}={v}" for k, v in params.items())
        req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": UA})
        return json.loads(opener.open(req, timeout=60).read().decode())

    kg_by_partner: dict[str, int] = defaultdict(int)
    raw_rows: list[dict] = []
    # 全量探测 ttype=1..4，打印量级，选出口类中合计最大者（转口才是 HK 银贸易主体）
    probes: dict[str, tuple[int, int]] = {}
    for ttype in ["1", "2", "3", "4"]:
        probe = get({
            "lang": "EN", "sv": "QCy", "freq": "A",
            "period": f"{YEAR},{YEAR}", "ttype": ttype,
            "codeclass": "HKHS6", "code": "710691",
            "ccclass": "C", "cc": "ALL",
        })
        status = probe.get("header", {}).get("status", {})
        rows = probe.get("dataSet", []) or []
        total_kg = sum(int(r["figure"]) for r in rows) if status.get("code") == 0 else 0
        probes[ttype] = (len(rows), total_kg)
        print(f"  探测 ttype={ttype}: status={status.get('code')} rows={len(rows)} 合计={total_kg/1000:,.1f} t", flush=True)
        time.sleep(0.4)
    # 出口候选（排除 ttype=1 进口）：选合计最大的
    export_probes = {k: v for k, v in probes.items() if k != "1" and v[0] > 0}
    if not export_probes:
        raise RuntimeError("HK IDDS export: no working ttype among 2/3/4")
    used_ttype = max(export_probes, key=lambda k: export_probes[k][1])
    print(f"  采用 ttype={used_ttype}（{export_probes[used_ttype][1]/1000:,.1f} t）", flush=True)

    for code in ["710610", "710691", "710692"]:
        data = get({
            "lang": "EN", "sv": "QCy", "freq": "A",
            "period": f"{YEAR},{YEAR}", "ttype": used_ttype,
            "codeclass": "HKHS6", "code": code,
            "ccclass": "C", "cc": "ALL",
        })
        rows = data.get("dataSet", []) or []
        print(f"  QCy {code} ttype={used_ttype}: {len(rows)} 个目的地", flush=True)
        for r in rows:
            name = str(r.get("ccDescEN") or r.get("cc") or "").strip()
            if name:
                kg_by_partner[norm_name(name)] += int(r["figure"])
                raw_rows.append(r)
        time.sleep(0.5)

    tonnes = {p: round(kg / 1000.0, 3) for p, kg in kg_by_partner.items()}
    out = dict(sorted(tonnes.items(), key=lambda kv: -kv[1]))
    CACHE_HK.write_text(
        json.dumps({"year": YEAR, "ttype": used_ttype,
                    "partners": [{"partner": p, "tonnes": t} for p, t in out.items()],
                    "rows": raw_rows}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"  [CACHE] {CACHE_HK.relative_to(ROOT)}", flush=True)
    print(f"  {len(out)} 个目的地，合计 {sum(out.values()):,.1f} 吨", flush=True)
    return out


# ——— D. USITC 缓存镜像 ———
def us_mirror() -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {"import": {}, "export": {}}
    if not US_CSV.exists():
        print(f"[US] {US_CSV} 不存在，跳过镜像", flush=True)
        return out
    with US_CSV.open(encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            out[r["flow"]][norm_name(r["partner_en"])] = float(r["tonnes"])
    print(f"[US] import {len(out['import'])} 伙伴 / export {len(out['export'])} 伙伴", flush=True)
    return out


# ——— 对照表 ———
def compare(title: str, geom: dict[str, float], official: dict[str, float],
            official_label: str, mirror: dict[str, float] | None = None,
            mirror_label: str = "") -> list[dict]:
    print(f"\n=== {title} ===")
    print(f"{'partner':<16}{'geom Moz':>9}{'geom t':>9}{official_label + ' t':>16}" +
          (f"{mirror_label + ' t':>16}" if mirror is not None else "") + f"{'Δoff %':>9}")
    rows = []
    for partner, moz in geom.items():
        gt = moz * T_PER_MOZ
        ot = official.get(partner)
        mt = mirror.get(partner) if mirror else None
        delta = (ot - gt) / gt * 100 if ot is not None and gt else None
        line = f"{partner:<16}{moz:>9.0f}{gt:>9.1f}" + (f"{ot:>16.1f}" if ot is not None else f"{'—':>16}")
        if mirror is not None:
            line += f"{mt:>16.1f}" if mt is not None else f"{'—':>16}"
        line += f"{delta:>8.1f}%" if delta is not None else f"{'':>9}"
        print(line)
        rows.append({"partner": partner, "geom_moz": moz, "geom_t": round(gt, 2),
                     "official_t": ot, "mirror_t": mt,
                     "delta_off_pct": round(delta, 1) if delta is not None else None})
    return rows


def main() -> None:
    result: dict = {"year": YEAR}

    uk = uk_bds_by_partner()
    result["uk_bds"] = uk

    india_imp = fetch_india_imports()
    result["india_import_partners"] = india_imp

    try:
        hk_exp = fetch_hk_exports()
    except Exception as exc:  # noqa: BLE001
        print(f"[HK] 出口拉取失败: {exc}", flush=True)
        hk_exp = {}
    result["hk_export_partners"] = hk_exp

    us = us_mirror()
    result["us_mirror"] = us

    # 汇总对照
    uk_imp_691 = uk.get("import", {}).get("71069100", {})
    uk_exp_691 = uk.get("export", {}).get("71069100", {})
    uk_imp_all = dict(uk_imp_691)
    for c, d in uk.get("import", {}).items():
        if c == "71069100":
            continue
        for p, t in d.items():
            uk_imp_all[p] = round(uk_imp_all.get(p, 0) + t, 3)
    uk_exp_all = dict(uk_exp_691)
    for c, d in uk.get("export", {}).items():
        if c == "71069100":
            continue
        for p, t in d.items():
            uk_exp_all[p] = round(uk_exp_all.get(p, 0) + t, 3)

    result["comparisons"] = {}
    result["comparisons"]["24b_uk_import"] = compare(
        "App24b 英国进口 ← HMRC BDS 71069100", GEOM["24b_uk_import"], uk_imp_691, "HMRC691")
    result["comparisons"]["24b_uk_import_all7106"] = compare(
        "App24b 英国进口 ← HMRC BDS 7106全口径", GEOM["24b_uk_import"], uk_imp_all, "HMRCall")
    result["comparisons"]["24a_uk_export"] = compare(
        "App24a 英国出口 ← HMRC BDS 71069100", GEOM["24a_uk_export"], uk_exp_691, "HMRC691")
    result["comparisons"]["26_india_import"] = compare(
        "App26 印度进口 ← TradeStat cwacim 7106", GEOM["26_india_import"], india_imp, "IN-off")
    result["comparisons"]["25_hk_export"] = compare(
        "App25 香港出口 ← IDDS QCy 7106", GEOM["25_hk_export"], hk_exp, "HK-off")
    # 镜像
    us_imp, us_exp = us["import"], us["export"]
    result["comparisons"]["23a_swiss_export_mirrors"] = compare(
        "App23a 瑞士出口（镜像：US/IN/UK 从瑞士进口）", GEOM["23a_swiss_export"],
        {"USA": us_imp.get("Switzerland", 0) or 0, "India": india_imp.get("Switzerland", 0) or 0,
         "UK": uk_imp_all.get("Switzerland", 0) or 0}, "mirror")
    result["comparisons"]["24a_uk_export_mirrors"] = compare(
        "App24a 英国出口（镜像：US/IN 从 UK 进口）", GEOM["24a_uk_export"],
        {"USA": us_imp.get("UK", 0) or 0, "India": india_imp.get("UK", 0) or 0}, "mirror")
    result["comparisons"]["25_hk_export_mirrors"] = compare(
        "App25 香港出口（镜像：US/IN 从 HK 进口）", GEOM["25_hk_export"],
        {"USA": us_imp.get("Hong Kong", 0) or 0, "India": india_imp.get("Hong Kong", 0) or 0}, "mirror")
    result["comparisons"]["26_india_import_mirrors"] = compare(
        "App26 印度进口（镜像：US 出口到印度）", GEOM["26_india_import"],
        {"USA": us_exp.get("India", 0) or 0}, "mirror")
    result["comparisons"]["24b_uk_import_mirrors"] = compare(
        "App24b 英国进口（镜像：US 出口到 UK）", GEOM["24b_uk_import"],
        {"USA": us_exp.get("UK", 0) or 0}, "mirror")

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n[OK] {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
