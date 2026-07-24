#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考 web/src/components/HkTrade.tsx 的视觉结构，但口径按印度国情调整：

- 印度长期以净进口为主 → 折线/指标一律用「净进口」
- 净进口 = 进口 − 出口（正值 = 净流入国内）
- 进口/出口柱状 + 净进口折线
- 深色主题配色（与看板 dark palette 对齐）

输出：
- web/public/data/india_trade.json
- output/india_silver_trade_preview.png
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
MONTHLY_CSV = ROOT / "data" / "india" / "india_silver_trade_monthly.csv"
OUT_JSON = ROOT / "web" / "public" / "data" / "india_trade.json"
OUT_PNG = ROOT / "output" / "india_silver_trade_preview.png"
IMPORT_URL = "https://tradestat.commerce.gov.in/meidb/commoditywise_import"
EXPORT_URL = "https://tradestat.commerce.gov.in/meidb/commoditywise_export"

# 与看板 dark palette 对齐
C = {
    "bg": "#0a101b",
    "panel": "#0e1524",
    "raised": "#121a2b",
    "hairline": "#1c2a3d",
    "text": "#e8eef6",
    "sub": "#9fb0c3",
    "weak": "#64748b",
    "imp": "#56c8dc",  # live 青 = 进口
    "exp": "#8a9bb5",  # series[7] = 出口
    "net": "#d9a441",  # gold = 净进口
    "up": "#f26d6d",
    "down": "#3ecf8e",
    "mark": "#f0c264",
    "event": "#f26d6d",
}

# 日历年历史参考。2018 年起会在 build_json() 中由官方月度 HS7106 汇总覆盖。
ANNUAL_IMPORTS = {
    2015: 8093,
    2016: 3000,
    2017: 5133,
    2018: 6942,
    2019: 5969,
    2020: 2218,
    2021: 2773,
    2022: 9450,
    2023: 3574,
    2024: 7695,
    2025: 7222,
}

# 出口历史参考。2018 年起会在 build_json() 中由官方月度 HS7106 汇总覆盖。
ANNUAL_EXPORTS = {
    2015: None,
    2016: None,
    2017: None,
    2018: None,
    2019: None,
    2020: 217.9,
    2021: 440.0,
    2022: 94.7,
    2023: 170.4,
    2024: 524.9,
    2025: 130.8,
}


def load_monthly_series() -> list[dict[str, float | str]]:
    if not MONTHLY_CSV.exists():
        raise FileNotFoundError(
            f"印度官方月度数据不存在，请先运行 src/fetch_india_trade_data.py: "
            f"{MONTHLY_CSV}"
        )

    rows: list[dict[str, float | str]] = []
    with MONTHLY_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for raw in csv.DictReader(handle):
            month = raw["month"]
            imports = float(raw["imports_tonnes"])
            exports = float(raw["exports_tonnes"])
            net_import = float(raw["net_import_tonnes"])
            if abs((imports - exports) - net_import) > 0.001:
                raise ValueError(f"{month}: 净进口不等于进口减出口")
            rows.append(
                {
                    "month": month,
                    "imports": imports,
                    "exports": exports,
                    "netImport": net_import,
                }
            )

    if not rows:
        raise ValueError(f"印度官方月度数据为空: {MONTHLY_CSV}")
    months = [str(row["month"]) for row in rows]
    if months != sorted(months) or len(months) != len(set(months)):
        raise ValueError("印度官方月度数据的月份未排序或存在重复")
    for previous, current in zip(months, months[1:]):
        year, month = map(int, previous.split("-"))
        expected = (
            f"{year + 1:04d}-01"
            if month == 12
            else f"{year:04d}-{month + 1:02d}"
        )
        if current != expected:
            raise ValueError(f"印度官方月度数据缺月: {previous} 后应为 {expected}")
    return rows


def build_json() -> dict:
    monthly_rows = load_monthly_series()
    monthly_labels = [str(row["month"]) for row in monthly_rows]
    monthly_imp = [float(row["imports"]) for row in monthly_rows]
    monthly_exp = [float(row["exports"]) for row in monthly_rows]
    monthly_net = [float(row["netImport"]) for row in monthly_rows]

    latest_year = int(monthly_labels[-1][:4])
    latest_month_number = int(monthly_labels[-1][5:7])
    current_year_rows = [
        row for row in monthly_rows if str(row["month"]).startswith(f"{latest_year}-")
    ]
    current_import = round(
        sum(float(row["imports"]) for row in current_year_rows), 3
    )
    current_export = round(
        sum(float(row["exports"]) for row in current_year_rows), 3
    )

    annual_imports = dict(ANNUAL_IMPORTS)
    annual_exports = dict(ANNUAL_EXPORTS)
    monthly_years = sorted({int(str(row["month"])[:4]) for row in monthly_rows})
    for year in monthly_years:
        year_rows = [
            row
            for row in monthly_rows
            if str(row["month"]).startswith(f"{year}-")
        ]
        annual_imports[year] = round(
            sum(float(row["imports"]) for row in year_rows), 3
        )
        annual_exports[year] = round(
            sum(float(row["exports"]) for row in year_rows), 3
        )
    partial_years = {
        latest_year: f"至{monthly_labels[-1]} · TradeStat 官方月度累计"
    }

    years = sorted(annual_imports)
    imports = [annual_imports[y] for y in years]
    exports = [annual_exports.get(y) for y in years]

    # 净进口 = 进口 − 出口（正值 = 净流入印度）
    # 缺出口年份：出口按 0 计，并在 netImportNote 标注（出口量级通常很小）
    net_import = []
    for imp, exp in zip(imports, exports):
        if exp is None:
            net_import.append(round(float(imp), 1))
        else:
            net_import.append(round(float(imp) - float(exp), 1))

    # 仅在有出口数据的年份上算峰值净进口，避免缺出口年被当成“出口=0”虚高
    net_with_exp = [
        (y, ni)
        for y, exp, ni in zip(years, exports, net_import)
        if exp is not None
    ]
    if net_with_exp:
        peak_y, peak_ni = max(net_with_exp, key=lambda t: t[1])
    else:
        peak_y, peak_ni = years[int(np.argmax(imports))], max(net_import)

    # 完整年 vs 不完整年：指标卡默认展示最近完整年；2026 YTD 单独列出
    complete_years = [y for y in years if y not in partial_years]
    last_complete = complete_years[-1]
    idx_c = years.index(last_complete)
    ytd_year = max(partial_years) if partial_years else None
    idx_ytd = years.index(ytd_year) if ytd_year in years else None

    # 峰值只在完整年里算（避免 YTD 干扰）
    complete_imps = [(y, annual_imports[y]) for y in complete_years]
    peak_imp_y, peak_imp = max(complete_imps, key=lambda t: t[1])
    net_with_exp_complete = [
        (y, ni)
        for y, exp, ni in zip(years, exports, net_import)
        if exp is not None and y not in partial_years
    ]
    if net_with_exp_complete:
        peak_y, peak_ni = max(net_with_exp_complete, key=lambda t: t[1])
    else:
        peak_y, peak_ni = peak_imp_y, float(peak_imp)

    payload = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "country": "India",
        "source": "印度商务部 TradeStat / DGCI&S · HS7106 月度数量",
        "sourceUrl": IMPORT_URL,
        "sourceUrls": {
            "imports": IMPORT_URL,
            "exports": EXPORT_URL,
        },
        "primarySeries": "india_tradestat_hs7106_monthly",
        "unit": "吨",
        "asOf": monthly_labels[-1],
        "frequency": "monthly",
        "basis": "net_import",
        "netImportFormula": "进口 − 出口（正值 = 白银净流入印度）",
        "years": [str(y) for y in years],
        "imports": imports,
        "exports": exports,
        "netImport": net_import,
        "partialYears": {str(k): v for k, v in partial_years.items()},
        "monthly": {
            "months": monthly_labels,
            "imports": monthly_imp,
            "exports": monthly_exp,
            "netImport": monthly_net,
            "note": (
                "印度商务部 TradeStat / DGCI&S 官方月度数量；"
                "HS7106，千克换算为吨。"
            ),
        },
        "monthlyAvailable": True,
        "monthlySeriesComplete": True,
        "months": monthly_labels,
        "monthlyImports": monthly_imp,
        "monthlyExports": monthly_exp,
        "monthlyNetImport": monthly_net,
        "monthlyNote": (
            f"官方连续月度序列：{monthly_labels[0]}—{monthly_labels[-1]}，"
            "进口、出口均无缺月；净进口=进口−出口。"
        ),
        "requestedThrough": monthly_labels[-1],
        "latestPublished": monthly_labels[-1],
        "unavailablePeriods": [],
        "events": [
            {"date": "2024-07-24", "label": "关税 15%→6%", "kind": "cut"},
            {"date": "2026-05-13", "label": "关税 6%→15% + 进口限制", "kind": "hike"},
        ],
        "stats": {
            "latestCompleteYear": last_complete,
            "latestImport": imports[idx_c],
            "latestExport": exports[idx_c],
            "latestNetImport": net_import[idx_c],
            "ytdYear": ytd_year,
            "ytdImport": imports[idx_ytd] if idx_ytd is not None else None,
            "ytdExport": exports[idx_ytd] if idx_ytd is not None else None,
            "ytdNetImport": net_import[idx_ytd] if idx_ytd is not None else None,
            "ytdNote": partial_years.get(ytd_year, "") if ytd_year else "",
            "ytdVsPriorYearImportPct": (
                round(
                    (
                        current_import
                        / sum(
                            float(row["imports"])
                            for row in monthly_rows
                            if str(row["month"]).startswith(f"{latest_year - 1}-")
                            and int(str(row["month"])[5:7]) <= latest_month_number
                        )
                        - 1.0
                    )
                    * 100.0,
                    1,
                )
                if idx_ytd is not None
                else None
            ),
            "peakNetImport": peak_ni,
            "peakNetImportYear": peak_y,
            "peakImport": peak_imp,
            "peakImportYear": peak_imp_y,
            "fy2025_26_import_t": 7335,
            "fy2025_26_import_usd_bn": 12.0,
            "may2026_import_t": monthly_imp[-1],
        },
        "disclaimer": (
            "口径以净进口为基准：净进口=进口−出口。"
            f"月度主序列为印度商务部 TradeStat / DGCI&S HS7106 官方数量，"
            f"覆盖 {monthly_labels[0]}—{monthly_labels[-1]}，千克换算为吨。"
            "2018 年起的年频值由同一官方月度序列汇总；"
            "2015—2017 仅保留行业历史参考，口径不可直接拼接。"
        ),
    }
    return payload


def style_ax(ax) -> None:
    ax.set_facecolor(C["panel"])
    ax.tick_params(colors=C["sub"], labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(C["hairline"])
    ax.yaxis.grid(True, color=C["hairline"], linewidth=0.8, alpha=0.9)
    ax.xaxis.grid(False)
    ax.set_axisbelow(True)


def fmt_ton(v: float, digits: int = 0) -> str:
    if digits <= 0:
        return f"{v:,.0f}"
    return f"{v:,.{digits}f}"


def draw_chart(data: dict) -> None:
    plt.rcParams["font.sans-serif"] = [
        "Microsoft YaHei",
        "SimHei",
        "Arial Unicode MS",
        "DejaVu Sans",
    ]
    plt.rcParams["axes.unicode_minus"] = False

    years = [int(y) for y in data["years"]]
    imports = np.array(data["imports"], dtype=float)
    exports = np.array(
        [np.nan if v is None else v for v in data["exports"]], dtype=float
    )
    net_import = np.array(data["netImport"], dtype=float)

    fig = plt.figure(figsize=(14.5, 10.2), facecolor=C["bg"])
    gs = GridSpec(
        3,
        4,
        figure=fig,
        height_ratios=[0.72, 2.35, 1.85],
        hspace=0.38,
        wspace=0.28,
        left=0.06,
        right=0.98,
        top=0.92,
        bottom=0.07,
    )

    # ——— 标题 ———
    fig.text(
        0.06,
        0.965,
        "07′  印度白银进出口 · 年频参考 + 官方月度",
        color=C["text"],
        fontsize=16,
        fontweight="600",
        va="top",
    )
    fig.text(
        0.06,
        0.935,
        "2018 年起：印度商务部 TradeStat / DGCI&S HS7106 官方月度汇总（吨）· 净进口 = 进口 − 出口",
        color=C["sub"],
        fontsize=10,
        va="top",
    )

    # ——— 指标卡（以净进口为基准） ———
    st = data["stats"]
    y_complete = st["latestCompleteYear"]
    ytd_y = st.get("ytdYear")
    ytd_imp = st.get("ytdImport")
    ytd_pct = st.get("ytdVsPriorYearImportPct")
    ytd_note = st.get("ytdNote") or "不完整年"
    pct_txt = (
        f"约{ytd_pct:+.0f}% vs {y_complete}全年"
        if ytd_pct is not None
        else "不完整年 · 仅供对比"
    )
    cards = [
        (
            f"{y_complete} 进口（完整年）",
            f"{fmt_ton(st['latestImport'])} 吨",
            "日历年 · TradeStat HS7106",
            C["imp"],
        ),
        (
            f"{y_complete} 净进口",
            f"{fmt_ton(st['latestNetImport'])} 吨",
            "进口 − 出口 · 净流入",
            C["net"],
        ),
        (
            f"{ytd_y} YTD 进口*" if ytd_y else "YTD 进口*",
            f"{fmt_ton(ytd_imp)} 吨" if ytd_imp is not None else "—",
            f"{ytd_note} · {pct_txt}",
            C["event"],
        ),
        (
            "2026-05 进口",
            f"{fmt_ton(st['may2026_import_t'])} 吨",
            "加税+限制后 · -94% YoY",
            C["event"],
        ),
    ]
    for i, (title, value, note, color) in enumerate(cards):
        ax = fig.add_subplot(gs[0, i])
        ax.set_facecolor(C["raised"])
        for spine in ax.spines.values():
            spine.set_color(C["hairline"])
        ax.set_xticks([])
        ax.set_yticks([])
        ax.text(0.06, 0.72, title, transform=ax.transAxes, color=C["sub"], fontsize=10, va="center")
        ax.text(
            0.06,
            0.38,
            value,
            transform=ax.transAxes,
            color=color,
            fontsize=18,
            fontweight="600",
            va="center",
        )
        ax.text(0.06, 0.12, note, transform=ax.transAxes, color=C["weak"], fontsize=8.5, va="center")

    # ——— 主图：年频 ———
    ax1 = fig.add_subplot(gs[1, :])
    style_ax(ax1)
    ax1.set_title(
        "年频进出口与净进口（吨）· 2026* 为不完整年 YTD",
        color=C["text"],
        fontsize=12,
        loc="left",
        pad=10,
    )

    x = np.arange(len(years))
    w = 0.36
    partial_set = {int(k) for k in data.get("partialYears", {})}
    complete_mask = np.array([y not in partial_set for y in years])
    partial_mask = ~complete_mask

    # 完整年：实心柱
    ax1.bar(
        x[complete_mask] - w / 2,
        imports[complete_mask],
        width=w,
        color=C["imp"],
        alpha=0.75,
        label="进口",
        zorder=3,
    )
    ax1.bar(
        x[complete_mask] + w / 2,
        np.nan_to_num(exports[complete_mask], nan=0.0),
        width=w,
        color=C["exp"],
        alpha=0.65,
        label="出口",
        zorder=3,
    )
    # 不完整年：斜线填充 + 描边，避免被当成全年
    if partial_mask.any():
        ax1.bar(
            x[partial_mask] - w / 2,
            imports[partial_mask],
            width=w,
            facecolor=C["imp"],
            edgecolor=C["event"],
            linewidth=1.4,
            alpha=0.45,
            hatch="///",
            label="进口（YTD*）",
            zorder=3,
        )
        ax1.bar(
            x[partial_mask] + w / 2,
            np.nan_to_num(exports[partial_mask], nan=0.0),
            width=w,
            facecolor=C["exp"],
            edgecolor=C["event"],
            linewidth=1.2,
            alpha=0.4,
            hatch="///",
            label="出口（YTD*）",
            zorder=3,
        )

    # 净进口折线：完整年实线，连到 YTD 用虚线
    if partial_mask.any():
        last_c = int(np.where(complete_mask)[0][-1])
        ax1.plot(
            x[: last_c + 1],
            net_import[: last_c + 1],
            color=C["net"],
            linewidth=2.4,
            marker="o",
            markersize=5,
            label="净进口",
            zorder=5,
        )
        ax1.plot(
            x[last_c:],
            net_import[last_c:],
            color=C["net"],
            linewidth=2.2,
            linestyle="--",
            marker="o",
            markersize=6,
            markerfacecolor=C["event"],
            markeredgecolor=C["net"],
            label="净进口（YTD*）",
            zorder=5,
        )
    else:
        ax1.plot(
            x,
            net_import,
            color=C["net"],
            linewidth=2.4,
            marker="o",
            markersize=5,
            label="净进口",
            zorder=5,
        )
    ax1.axhline(0, color=C["weak"], linestyle="--", linewidth=1, zorder=2)

    # 政策事件
    ax1.annotate(
        "2024-07 关税15%→6%",
        xy=(years.index(2024), imports[years.index(2024)]),
        xytext=(years.index(2024) - 1.8, imports[years.index(2024)] + 1400),
        color=C["down"],
        fontsize=9,
        arrowprops=dict(arrowstyle="->", color=C["down"], lw=1),
        zorder=6,
    )

    # 峰值净进口（完整年）
    peak_y = int(st["peakNetImportYear"])
    if peak_y in years:
        peak_i = years.index(peak_y)
        ax1.annotate(
            f"峰值净进口 {fmt_ton(st['peakNetImport'])}",
            xy=(peak_i, net_import[peak_i]),
            xytext=(peak_i, net_import[peak_i] + 900),
            ha="center",
            color=C["net"],
            fontsize=9,
            arrowprops=dict(arrowstyle="-", color=C["net"], lw=0.8),
        )

    # 最近完整年净进口标注
    idx_c = years.index(int(y_complete))
    ax1.annotate(
        f"+{fmt_ton(float(net_import[idx_c]))}",
        xy=(idx_c, float(net_import[idx_c])),
        xytext=(idx_c, float(net_import[idx_c]) + 700),
        ha="center",
        color=C["net"],
        fontsize=10,
        fontweight="600",
    )

    # 最新不完整年 YTD 标注
    if ytd_y in years:
        i26 = years.index(ytd_y)
        ax1.annotate(
            f"{ytd_y} YTD\n{fmt_ton(float(imports[i26]))}吨*",
            xy=(i26, float(imports[i26])),
            xytext=(i26 - 0.15, float(imports[i26]) + 1100),
            ha="center",
            color=C["event"],
            fontsize=9,
            fontweight="600",
            arrowprops=dict(arrowstyle="->", color=C["event"], lw=1),
            zorder=6,
        )
        ax1.annotate(
            "2026-05 关税→15%+限制",
            xy=(i26, float(imports[i26]) * 0.35),
            xytext=(i26 - 2.2, float(imports[i26]) + 2800),
            color=C["event"],
            fontsize=9,
            arrowprops=dict(arrowstyle="->", color=C["event"], lw=1),
            zorder=6,
        )

    xticklabels = [f"{y}*" if y in partial_set else str(y) for y in years]
    ax1.set_xticks(x)
    ax1.set_xticklabels(xticklabels, color=C["sub"])
    # 不完整年 x 标签标红
    for tick, y in zip(ax1.get_xticklabels(), years):
        if y in partial_set:
            tick.set_color(C["event"])
    ax1.set_ylabel("吨", color=C["sub"])
    y_max = max(float(np.nanmax(imports)), float(np.nanmax(net_import))) * 1.28
    ax1.set_ylim(0, y_max)

    leg = ax1.legend(loc="upper left", frameon=True, fontsize=8, ncol=2)
    leg.get_frame().set_facecolor(C["raised"])
    leg.get_frame().set_edgecolor(C["hairline"])
    for t in leg.get_texts():
        t.set_color(C["text"])

    ax1.text(
        0.01,
        0.02,
        "注：印度长期净进口；出口量级远小于进口。* = 不完整年（不可当全年）。2015–2019 缺出口时净进口暂按进口计。",
        transform=ax1.transAxes,
        color=C["weak"],
        fontsize=8,
        va="bottom",
    )

    # ——— 副图：官方近期月度进出口与净进口 ———
    ax2 = fig.add_subplot(gs[2, :])
    style_ax(ax2)
    ax2.set_title(
        "官方月度进出口与净进口（吨）· 最近24个月",
        color=C["text"],
        fontsize=12,
        loc="left",
        pad=10,
    )

    m_labels = data["monthly"]["months"][-24:]
    m_imports = np.array(data["monthly"]["imports"][-24:], dtype=float)
    m_exports = np.array(data["monthly"]["exports"][-24:], dtype=float)
    m_net = np.array(data["monthly"]["netImport"][-24:], dtype=float)
    mx = np.arange(len(m_labels))
    width = 0.34
    ax2.bar(
        mx - width / 2,
        m_imports,
        width=width,
        color=C["imp"],
        alpha=0.75,
        zorder=3,
        label="进口",
    )
    ax2.bar(
        mx + width / 2,
        m_exports,
        width=width,
        color=C["exp"],
        alpha=0.65,
        zorder=3,
        label="出口",
    )
    ax2.plot(
        mx,
        m_net,
        color=C["net"],
        linewidth=2.0,
        marker="o",
        markersize=3.5,
        zorder=4,
        label="净进口",
    )
    ax2.axhline(0, color=C["weak"], linestyle="--", linewidth=1, zorder=2)

    if "2026-05" in m_labels:
        idx = m_labels.index("2026-05")
        ax2.axvline(idx - 0.5, color=C["event"], linestyle="--", linewidth=1.2, alpha=0.9, zorder=2)
        ax2.text(
            idx - 0.45,
            max(m_imports) * 0.92,
            "2026-05-13\n关税→15%+限制",
            color=C["event"],
            fontsize=9,
            va="top",
        )

    ax2.set_xticks(mx)
    ax2.set_xticklabels(m_labels, color=C["sub"], rotation=45, ha="right")
    ax2.set_ylabel("吨", color=C["sub"])
    legend = ax2.legend(loc="upper left", frameon=True, fontsize=8, ncol=3)
    legend.get_frame().set_facecolor(C["raised"])
    legend.get_frame().set_edgecolor(C["hairline"])
    for text in legend.get_texts():
        text.set_color(C["text"])

    fig.text(
        0.06,
        0.015,
        "月度主序列：印度商务部 TradeStat / DGCI&S HS7106 官方数量，千克换算为吨；"
        f"连续覆盖 {data['monthly']['months'][0]}—{data['monthly']['months'][-1]}，"
        "净进口=进口−出口；2018 年起年频值由同一月度序列汇总。 生成：" + data["generatedAt"],
        color=C["weak"],
        fontsize=8,
    )

    OUT_PNG.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=160, facecolor=C["bg"])
    plt.close(fig)
    print(f"[OK] PNG -> {OUT_PNG}")


def main() -> None:
    data = build_json()
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] JSON -> {OUT_JSON}")
    draw_chart(data)
    print(
        f"[OK] basis=net_import  years={data['years'][0]}~{data['years'][-1]}  "
        f"complete={data['stats']['latestCompleteYear']} netImport={data['stats']['latestNetImport']}  "
        f"ytd{data['stats']['ytdYear']}={data['stats']['ytdImport']}"
    )


if __name__ == "__main__":
    main()
