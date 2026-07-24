#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
美国 / 英国白银进出口数据汇编 + 与印度对比预览图

口径统一：净进口 = 进口 − 出口（正值 = 净流入该国）
- 美国主序列：USGS 银含量（进口 for consumption / 出口），含矿石精矿+精炼/多雷等
- 英国主序列：2015–2019 用 WSS 金条贸易；2020–2024 用 Comtrade HS710691（未锻造，7106 主体）
- 印度：沿用 data/india 已整理序列

输出：
- data/us/us_silver_trade_compiled.csv
- data/us/us_silver_trade_notes.md
- data/uk/uk_silver_trade_compiled.csv
- data/uk/uk_silver_trade_notes.md
- web/public/data/us_trade.json
- web/public/data/uk_trade.json
- output/us_uk_india_silver_trade_preview.png
"""
from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT_US_CSV = ROOT / "data" / "us" / "us_silver_trade_compiled.csv"
OUT_US_MD = ROOT / "data" / "us" / "us_silver_trade_notes.md"
OUT_UK_CSV = ROOT / "data" / "uk" / "uk_silver_trade_compiled.csv"
OUT_UK_MD = ROOT / "data" / "uk" / "uk_silver_trade_notes.md"
OUT_US_JSON = ROOT / "web" / "public" / "data" / "us_trade.json"
OUT_UK_JSON = ROOT / "web" / "public" / "data" / "uk_trade.json"
OUT_PNG = ROOT / "output" / "us_uk_india_silver_trade_preview.png"

C = {
    "bg": "#0a101b",
    "panel": "#0e1524",
    "raised": "#121a2b",
    "hairline": "#1c2a3d",
    "text": "#e8eef6",
    "sub": "#9fb0c3",
    "weak": "#64748b",
    "imp": "#56c8dc",
    "exp": "#8a9bb5",
    "net": "#d9a441",
    "us": "#56c8dc",
    "uk": "#d9a441",
    "in": "#f26d6d",
    "event": "#f26d6d",
    "down": "#3ecf8e",
}

# ——— 美国 USGS 银含量（吨）———
# 来源：USGS Historical Statistics + MCS 2024–2026；2025 为 MCS 2026 初估 (e)
US_USGS = {
    # year: (import_t, export_t, note)
    2015: (5930, 817, "USGS hist"),
    2016: (6160, 289, "USGS hist"),
    2017: (5040, 157, "USGS hist"),
    2018: (4840, 604, "USGS hist"),
    2019: (4760, 220, "USGS hist"),
    2020: (6730, 141, "USGS MCS"),
    2021: (6160, 137, "USGS MCS"),
    2022: (4490, 276, "USGS MCS revised"),
    2023: (4950, 73, "USGS MCS revised"),
    2024: (4430, 113, "USGS MCS 2026"),
    2025: (7600, 300, "USGS MCS 2026 estimate e"),
}

# 美国 Comtrade HS7106 毛重（吨）— 交叉验证，与 USGS 银含量口径不同
US_COMTRADE_7106 = {
    2020: (8918.5, 2622.0),
    2021: (8216.3, 3236.2),
    2022: (7389.0, 2333.6),
    2023: (7740.0, 1730.8),
    2024: (5812.8, 1464.4),
}

# WSS 美国金条（吨）— Metals Focus
US_WSS_BULLION = {
    2024: (4636, 445, "WSS 2025: imp -12% to 15y low; exp -34%"),
}

# ——— 英国 ———
# 2015–2019：WSS 金条贸易（吨）
UK_WSS = {
    2015: (3752, 3747, "WSS bullion"),
    2016: (3903, 1358, "WSS bullion"),
    2017: (4559, 1338, "WSS bullion"),
    2018: (3313, 2690, "WSS bullion"),
    2019: (2877, 2081, "WSS bullion"),
}

# 2020–2024：Comtrade HS710691 未锻造（吨，WITS 伙伴加总/世界总量）
UK_COMTRADE_710691 = {
    2020: (3546, 4890, "WITS 710691 World/sum"),
    2021: (6290, 3790, "WITS 710691 sum ~6270–6300"),
    2022: (2340, 11270, "WITS 710691; export spike to India"),
    2023: (4094, 3681, "WITS 710691"),
    2024: (4500, 4129, "WITS 710691 sum/est"),
}

# 印度（与 india 汇编一致，完整年）
IN_IMPORTS = {
    2015: 8093, 2016: 3000, 2017: 5133, 2018: 6942, 2019: 5969,
    2020: 2218, 2021: 2773, 2022: 9450, 2023: 3574, 2024: 7695, 2025: 7222,
}
IN_EXPORTS = {
    2020: 217.9, 2021: 440.0, 2022: 94.7, 2023: 170.4, 2024: 524.9, 2025: 130.8,
}


def net_imp(imp, exp):
    if imp is None:
        return None
    if exp is None:
        return round(float(imp), 1)
    return round(float(imp) - float(exp), 1)


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"[OK] CSV {path} ({len(rows)} rows)")


def build_us() -> dict:
    # 若 us_trade.json 已由 fetch_us_trade_data.py（Census HS7106 月度明细）生成，
    # 直接沿用其结果，避免 update_all.py 用旧 USGS 年度硬编码覆盖月度数据。
    if OUT_US_JSON.exists():
        try:
            existing = json.loads(OUT_US_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = None
        if isinstance(existing, dict) and existing.get("primarySeries") in {
            "us_hs7106_census_comtrade",
            "us_dataweb_census_hs7106",
        }:
            print(
                "[SKIP] US 使用 fetch_us_trade_data.py 已生成的官方月度数据"
                f"（asOf={existing.get('asOf')}），硬编码不再覆盖"
            )
            return existing

    rows = []
    years, imps, exps, nets = [], [], [], []
    for y in sorted(US_USGS):
        imp, exp, note = US_USGS[y]
        ni = net_imp(imp, exp)
        years.append(str(y))
        imps.append(imp)
        exps.append(exp)
        nets.append(ni)
        conf = "medium" if "estimate" in note else "high"
        rows.append(
            {
                "period_type": "calendar_year",
                "period": str(y),
                "flow": "both",
                "import_tonnes": imp,
                "export_tonnes": exp,
                "net_import_tonnes": ni,
                "source": "USGS MCS / Historical Statistics",
                "notes": note,
                "confidence": conf,
                "series": "usgs_silver_content",
            }
        )
    for y, (imp, exp) in US_COMTRADE_7106.items():
        rows.append(
            {
                "period_type": "calendar_year",
                "period": str(y),
                "flow": "both",
                "import_tonnes": imp,
                "export_tonnes": exp,
                "net_import_tonnes": net_imp(imp, exp),
                "source": "WITS/UN Comtrade HS7106",
                "notes": "gross weight; different scope vs USGS content",
                "confidence": "high",
                "series": "comtrade_hs7106",
            }
        )
    for y, (imp, exp, note) in US_WSS_BULLION.items():
        rows.append(
            {
                "period_type": "calendar_year",
                "period": str(y),
                "flow": "both",
                "import_tonnes": imp,
                "export_tonnes": exp,
                "net_import_tonnes": net_imp(imp, exp),
                "source": "Metals Focus / WSS",
                "notes": note,
                "confidence": "high",
                "series": "wss_bullion",
            }
        )

    write_csv(
        OUT_US_CSV,
        rows,
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

    # 峰值（完整年，排除 estimate 年也可保留 2025e）
    peak_i = int(np.argmax(imps))
    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "country": "US",
        "source": "USGS silver content (primary) · Comtrade HS7106 / WSS bullion cross-check",
        "unit": "吨",
        "basis": "net_import",
        "netImportFormula": "进口 − 出口（正值 = 净流入美国）",
        "primarySeries": "usgs_silver_content",
        "asOf": years[-1],
        "years": years,
        "imports": imps,
        "exports": exps,
        "netImport": nets,
        "partialYears": {"2025": "USGS MCS 2026 preliminary estimate"},
        "stats": {
            "latestCompleteYear": 2024,
            "latestImport": US_USGS[2024][0],
            "latestExport": US_USGS[2024][1],
            "latestNetImport": net_imp(*US_USGS[2024][:2]),
            "ytdYear": 2025,
            "ytdImport": US_USGS[2025][0],
            "ytdExport": US_USGS[2025][1],
            "ytdNetImport": net_imp(*US_USGS[2025][:2]),
            "ytdNote": "全年初估 e，非 YTD",
            "peakImport": imps[peak_i],
            "peakImportYear": int(years[peak_i]),
            "peakNetImport": max(nets),
            "peakNetImportYear": int(years[int(np.argmax(nets))]),
        },
        "partners": "进口主源：墨西哥、加拿大等",
        "disclaimer": (
            "主序列为 USGS 银含量（含矿石/精矿/精炼/多雷等，不含硬币与废料）。"
            "与纯 HS7106 毛重、WSS 金条口径不同，不可直接横向加总。"
            "2025 为 MCS 2026 初估，可修订。"
        ),
    }
    OUT_US_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_US_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON {OUT_US_JSON}")

    OUT_US_MD.write_text(
        f"""# 美国白银进出口数据整理

> 整理日期：2026-07-23  
> **表达基准：净进口 = 进口 − 出口（正值 = 净流入美国）**  
> 主序列：**USGS 银含量**（Mineral Commodity Summaries / Historical Statistics）

## 1. 主序列（USGS，吨银含量）

| 年 | 进口 | 出口 | 净进口 | 备注 |
|---:|---:|---:|---:|---|
"""
        + "\n".join(
            f"| {y} | {US_USGS[y][0]:,} | {US_USGS[y][1]:,} | {net_imp(*US_USGS[y][:2]):,} | {US_USGS[y][2]} |"
            for y in sorted(US_USGS)
        )
        + """

- 美国长期**净进口**；净进口依赖度近年约表观消费的 60–80%。
- 进口主源：墨西哥（约 44–50%）、加拿大（约 17–29%）等。
- 2025 初估进口跳升至约 **7,600 吨**（关税/EFP 担忧下 CME 入库等因素，见 WSS 2026）。

## 2. 交叉验证

### Comtrade HS7106 毛重（吨）
| 年 | 进口 | 出口 | 净进口 |
|---:|---:|---:|---:|
"""
        + "\n".join(
            f"| {y} | {a:,.1f} | {b:,.1f} | {net_imp(a,b):,.1f} |"
            for y, (a, b) in sorted(US_COMTRADE_7106.items())
        )
        + """

### WSS 金条 2024
- 进口 4,636 吨（−12%，15 年低点）；出口 445 吨（−34%）

## 3. 一手源
- USGS Silver：https://www.usgs.gov/centers/national-minerals-information-center/silver-statistics-and-information
- MCS 2026 PDF：https://pubs.usgs.gov/periodicals/mcs2026/mcs2026-silver.pdf
- Historical ds140：USGS Data Series 140 silver xlsx
- Census / USITC DataWeb（HS/HTS 明细）
- WSS 2025/2026（Metals Focus）

## 4. 文件
- `data/us/us_silver_trade_compiled.csv`
- `web/public/data/us_trade.json`
""",
        encoding="utf-8",
    )
    print(f"[OK] MD {OUT_US_MD}")
    return payload


def build_uk() -> dict:
    # 若 uk_trade.json 已由 fetch_uk_trade_data.py（HMRC BDS 月度明细）生成，
    # 直接沿用其结果，不再用内置硬编码（2015-2024）覆盖，避免数据回退。
    if OUT_UK_JSON.exists():
        try:
            existing = json.loads(OUT_UK_JSON.read_text(encoding="utf-8"))
        except Exception:
            existing = None
        if isinstance(existing, dict) and existing.get("primarySeries") in {
            "hmrc_ots_hs71069100",
            "hmrc_bds_hs71069100",
        }:
            print(f"[SKIP] UK 使用 fetch_uk_trade_data.py 已生成的 BDS 数据（asOf={existing.get('asOf')}），硬编码不再覆盖")
            return existing

    rows = []
    # 合并主展示序列：WSS 2015-19 + Comtrade 2020-24
    primary = {}
    for y, (imp, exp, note) in UK_WSS.items():
        primary[y] = (imp, exp, note, "wss_bullion", "high")
    for y, (imp, exp, note) in UK_COMTRADE_710691.items():
        primary[y] = (imp, exp, note, "comtrade_hs710691", "medium")

    years, imps, exps, nets = [], [], [], []
    for y in sorted(primary):
        imp, exp, note, series, conf = primary[y]
        ni = net_imp(imp, exp)
        years.append(str(y))
        imps.append(imp)
        exps.append(exp)
        nets.append(ni)
        rows.append(
            {
                "period_type": "calendar_year",
                "period": str(y),
                "flow": "both",
                "import_tonnes": imp,
                "export_tonnes": exp,
                "net_import_tonnes": ni,
                "source": "WSS bullion" if series.startswith("wss") else "WITS/Comtrade HS710691",
                "notes": note,
                "confidence": conf,
                "series": series,
            }
        )

    write_csv(
        OUT_UK_CSV,
        rows,
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

    peak_i = int(np.argmax(imps))
    # 英国常作枢纽：净进口可正可负（再出口）
    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "country": "UK",
        "source": "WSS bullion 2015–2019 + WITS/Comtrade HS710691 2020–2024",
        "unit": "吨",
        "basis": "net_import",
        "netImportFormula": "进口 − 出口（正值 = 净流入英国；负值 = 净流出/再出口）",
        "primarySeries": "mixed_wss_comtrade",
        "asOf": years[-1],
        "years": years,
        "imports": imps,
        "exports": exps,
        "netImport": nets,
        "partialYears": {},
        "stats": {
            "latestCompleteYear": 2024,
            "latestImport": imps[-1],
            "latestExport": exps[-1],
            "latestNetImport": nets[-1],
            "peakImport": imps[peak_i],
            "peakImportYear": int(years[peak_i]),
            "peakNetImport": max(nets),
            "peakNetImportYear": int(years[int(np.argmax(nets))]),
            "minNetImport": min(nets),
            "minNetImportYear": int(years[int(np.argmin(nets))]),
            "exportSpike2022": UK_COMTRADE_710691[2022][1],
        },
        "partners": "进口：中/港/哈萨克/德/波等；出口：印度、加拿大、瑞士、阿联酋、美国等（伦敦枢纽再出口）",
        "disclaimer": (
            "英国是 LBMA 全球枢纽，贸易含大量转口/再出口，净进口波动大甚至为负。"
            "2015–2019 与 2020–2024 来源不同（WSS 金条 vs Comtrade 710691），衔接处勿过度解读微小差异。"
            "2025 全年数量公开源尚不完整。"
        ),
    }
    OUT_UK_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_UK_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON {OUT_UK_JSON}")

    OUT_UK_MD.write_text(
        f"""# 英国白银进出口数据整理

> 整理日期：2026-07-23  
> **表达基准：净进口 = 进口 − 出口**（正=净流入；**负=净流出/再出口**，伦敦枢纽常见）  
> 主序列：2015–2019 **WSS 金条**；2020–2024 **Comtrade HS710691**（未锻造，占 7106 主体）

## 1. 主序列（吨）

| 年 | 进口 | 出口 | 净进口 | 来源 |
|---:|---:|---:|---:|---|
"""
        + "\n".join(
            f"| {y} | {primary[y][0]:,} | {primary[y][1]:,} | {net_imp(primary[y][0], primary[y][1]):,} | {primary[y][3]} |"
            for y in sorted(primary)
        )
        + """

### 要点
- **2022 出口异常高**（约 11,270 吨，大量对印等），净进口大幅为负。
- 英国矿山产量可忽略；贸易反映 **LBMA 清算/金库/再出口** 功能。
- 对印出口是长期关键流出方向（与印度进口关税政策联动）。
- 2025 全年数量公开源尚不完整；OEC 等有金额数据但数量待补。

## 2. 一手源
- HMRC UK Trade Info：https://www.uktradeinfo.com/
- WITS/Comtrade HS 7106 / 710691
- LBMA vault / clearing：https://www.lbma.org.uk/prices-and-data/london-vault-data
- Silver Institute World Silver Survey（历史金条贸易章）

## 3. 文件
- `data/uk/uk_silver_trade_compiled.csv`
- `web/public/data/uk_trade.json`
""",
        encoding="utf-8",
    )
    print(f"[OK] MD {OUT_UK_MD}")
    return payload


def india_series():
    years = sorted(IN_IMPORTS)
    imps = [IN_IMPORTS[y] for y in years]
    exps = [IN_EXPORTS.get(y) for y in years]
    nets = [net_imp(i, e) for i, e in zip(imps, exps)]
    return years, imps, exps, nets


def draw_compare(us: dict, uk: dict) -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
    plt.rcParams["axes.unicode_minus"] = False

    in_years, in_imp, in_exp, in_net = india_series()
    us_years = [int(y) for y in us["years"]]
    uk_years = [int(y) for y in uk["years"]]

    fig = plt.figure(figsize=(15.2, 11.2), facecolor=C["bg"])
    gs = GridSpec(
        3, 3, figure=fig, height_ratios=[0.7, 2.2, 2.0], hspace=0.42, wspace=0.28,
        left=0.06, right=0.98, top=0.91, bottom=0.06,
    )

    fig.text(0.06, 0.965, "美 / 英 / 印 白银贸易对比 · 净进口口径", color=C["text"], fontsize=16, fontweight="600", va="top")
    fig.text(
        0.06, 0.935,
        "净进口 = 进口 − 出口（正=净流入）。美=USGS银含量；英=WSS/Comtrade；印=WSS/Comtrade。口径不同，比趋势不比绝对水平硬加总。",
        color=C["sub"], fontsize=9.5, va="top",
    )

    # 指标卡（兼容 fetch_uk_trade_data.py 生成的 BDS schema 与内置硬编码 schema）
    uk_stats = uk.get("stats", {})
    uk_latest_net = uk_stats.get("latestNetImport", uk_stats.get("latestYearNetImport", 0.0))
    uk_complete_y = uk_stats.get("latestCompleteYear", 2024)
    if "exportSpike2022" in uk_stats:
        uk_exp22 = uk_stats["exportSpike2022"]
    else:
        uk_exp22 = uk["exports"][uk["years"].index("2022")] if "2022" in uk["years"] else 0.0
    cards = [
        ("美国 2024 净进口", f"{us['stats']['latestNetImport']:,.0f} 吨", "USGS · 完整年", C["us"]),
        ("美国 2025e 进口", f"{us['stats']['ytdImport']:,.0f} 吨", "MCS 初估 · 跳升", C["event"]),
        (f"英国 {uk_complete_y} 净进口", f"{uk_latest_net:,.0f} 吨", "枢纽 · 可正可负", C["uk"]),
        ("英国 2022 出口峰值", f"{uk_exp22:,.0f} 吨", "再出口高峰", C["exp"]),
        ("印度 2025 净进口", f"{in_net[-1]:,.0f} 吨", "长期净进口国", C["in"]),
        ("印度 2026-05 进口", "33 吨", "加税+限制后", C["event"]),
    ]
    # 用 2 行不好排，改顶部 6 小卡用 3 列不够——改为 3 张宽卡 + 说明
    # 实际用 gs[0,:] 拆 3 卡
    top_cards = [
        ("美国 USGS", f"2024 净进口 {us['stats']['latestNetImport']:,.0f} t", f"2025e 进口 {us['stats']['ytdImport']:,.0f} t（初估）", C["us"]),
        ("英国 枢纽", f"{uk_complete_y} 净进口 {uk_latest_net:,.0f} t", f"2022 出口峰值 {uk_exp22:,.0f} t", C["uk"]),
        ("印度 消费国", f"2025 净进口 {in_net[-1]:,.0f} t", "2026-05 进口 33 t（加税后）", C["in"]),
    ]
    for i, (title, v1, v2, color) in enumerate(top_cards):
        ax = fig.add_subplot(gs[0, i])
        ax.set_facecolor(C["raised"])
        for sp in ax.spines.values():
            sp.set_color(C["hairline"])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.06, 0.72, title, transform=ax.transAxes, color=C["sub"], fontsize=11, va="center")
        ax.text(0.06, 0.40, v1, transform=ax.transAxes, color=color, fontsize=15, fontweight="600", va="center")
        ax.text(0.06, 0.14, v2, transform=ax.transAxes, color=C["weak"], fontsize=10, va="center")

    def style(ax):
        ax.set_facecolor(C["panel"])
        ax.tick_params(colors=C["sub"], labelsize=8)
        for sp in ax.spines.values():
            sp.set_color(C["hairline"])
        ax.yaxis.grid(True, color=C["hairline"], lw=0.8)
        ax.set_axisbelow(True)

    # ——— 中图：三国净进口折线 ———
    axn = fig.add_subplot(gs[1, :])
    style(axn)
    axn.set_title("三国净进口对比（吨）", color=C["text"], fontsize=12, loc="left", pad=8)

    axn.plot(us_years, us["netImport"], color=C["us"], lw=2.3, marker="o", ms=4.5, label="美国净进口（USGS）")
    axn.plot(uk_years, uk["netImport"], color=C["uk"], lw=2.3, marker="s", ms=4.5, label="英国净进口（WSS/Comtrade）")
    axn.plot(in_years, in_net, color=C["in"], lw=2.3, marker="^", ms=4.5, label="印度净进口（WSS/Comtrade）")
    axn.axhline(0, color=C["weak"], ls="--", lw=1)
    # 2025e 美国
    if 2025 in us_years:
        i = us_years.index(2025)
        axn.plot(us_years[i], us["netImport"][i], "o", color=C["event"], ms=8, zorder=6)
        axn.annotate("US 2025e", xy=(2025, us["netImport"][i]), xytext=(2024.2, us["netImport"][i] + 800),
                     color=C["event"], fontsize=8, arrowprops=dict(arrowstyle="->", color=C["event"], lw=0.8))
    # 英国 2022 深坑
    if 2022 in uk_years:
        i = uk_years.index(2022)
        axn.annotate("UK 2022 再出口高峰\n净进口大幅为负", xy=(2022, uk["netImport"][i]),
                     xytext=(2019.5, uk["netImport"][i] - 1500), color=C["uk"], fontsize=8,
                     arrowprops=dict(arrowstyle="->", color=C["uk"], lw=0.8))
    # 印度 2022 峰值
    if 2022 in in_years:
        i = in_years.index(2022)
        axn.annotate("IN 2022 峰值", xy=(2022, in_net[i]), xytext=(2022.3, in_net[i] + 600),
                     color=C["in"], fontsize=8)

    axn.set_ylabel("吨", color=C["sub"])
    axn.set_xlim(2014.5, 2025.5)
    leg = axn.legend(loc="upper left", fontsize=8, frameon=True, ncol=3)
    leg.get_frame().set_facecolor(C["raised"])
    leg.get_frame().set_edgecolor(C["hairline"])
    for t in leg.get_texts():
        t.set_color(C["text"])

    # ——— 底图：美、英各自进出口柱 ———
    ax_us = fig.add_subplot(gs[2, 0:2])
    style(ax_us)
    ax_us.set_title("美国进出口（USGS 银含量，吨）", color=C["text"], fontsize=11, loc="left", pad=8)
    x = np.arange(len(us_years))
    w = 0.36
    imp_us = np.array(us["imports"], float)
    exp_us = np.array(us["exports"], float)
    # 2025e 半透明
    colors_imp = [C["event"] if y == 2025 else C["imp"] for y in us_years]
    ax_us.bar(x - w / 2, imp_us, width=w, color=colors_imp, alpha=0.75, label="进口")
    ax_us.bar(x + w / 2, exp_us, width=w, color=C["exp"], alpha=0.65, label="出口")
    ax_us.plot(x, us["netImport"], color=C["net"], lw=2, marker="o", ms=4, label="净进口")
    ax_us.set_xticks(x)
    ax_us.set_xticklabels([f"{y}e" if y == 2025 else str(y) for y in us_years], color=C["sub"], fontsize=8)
    ax_us.set_ylabel("吨", color=C["sub"])
    leg = ax_us.legend(loc="upper left", fontsize=8, frameon=True)
    leg.get_frame().set_facecolor(C["raised"])
    leg.get_frame().set_edgecolor(C["hairline"])
    for t in leg.get_texts():
        t.set_color(C["text"])

    ax_uk = fig.add_subplot(gs[2, 2])
    style(ax_uk)
    ax_uk.set_title("英国进出口（吨）", color=C["text"], fontsize=11, loc="left", pad=8)
    x2 = np.arange(len(uk_years))
    ax_uk.bar(x2 - w / 2, uk["imports"], width=w, color=C["imp"], alpha=0.75, label="进口")
    ax_uk.bar(x2 + w / 2, uk["exports"], width=w, color=C["exp"], alpha=0.65, label="出口")
    ax_uk.plot(x2, uk["netImport"], color=C["net"], lw=2, marker="o", ms=3.5, label="净进口")
    ax_uk.axhline(0, color=C["weak"], ls="--", lw=0.8)
    ax_uk.set_xticks(x2)
    ax_uk.set_xticklabels([str(y)[2:] for y in uk_years], color=C["sub"], fontsize=7)
    ax_uk.set_ylabel("吨", color=C["sub"])
    leg = ax_uk.legend(loc="upper left", fontsize=7, frameon=True)
    leg.get_frame().set_facecolor(C["raised"])
    leg.get_frame().set_edgecolor(C["hairline"])
    for t in leg.get_texts():
        t.set_color(C["text"])

    fig.text(
        0.06, 0.012,
        "口径提示：三国序列来源不同（USGS含量 / 英枢纽贸易 / 印消费进口），适合比方向与节奏，不适合简单加总。"
        f"  生成：{datetime.now().astimezone().isoformat(timespec='seconds')}",
        color=C["weak"], fontsize=8,
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=160, facecolor=C["bg"])
    plt.close(fig)
    print(f"[OK] PNG {OUT_PNG}")


def main() -> None:
    us = build_us()
    uk = build_uk()
    draw_compare(us, uk)
    print("[DONE] US/UK silver trade compiled + compare chart")


if __name__ == "__main__":
    main()
