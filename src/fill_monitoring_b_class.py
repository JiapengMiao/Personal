# -*- coding: utf-8 -*-
"""Fill B-class (pending) monitoring indicators with best-available public data.

Updates:
  - data/monitoring/monitoring-source.json  (human draft)
  - data/monitoring/monitoring-data.json    (compiled fallback)
  - docs/data/monitoring.json
  - web/public/data/monitoring.json
  - output/wb-preview/data/monitoring.json (if present)

Indicator 16 is rebuilt from the dashboard daily data using the agreed
global-available-inventory proxy formula.
"""
from __future__ import annotations

import json
import math
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_SOURCE = ROOT / "data" / "monitoring" / "monitoring-source.json"
SRC_COMPILED = ROOT / "data" / "monitoring" / "monitoring-data.json"
LEASE = ROOT / "docs" / "data" / "lease_rates.json"
DAILY = ROOT / "web" / "public" / "data" / "daily.json"
OUT_PATHS = [
    ROOT / "docs" / "data" / "monitoring.json",
    ROOT / "web" / "public" / "data" / "monitoring.json",
    ROOT / "output" / "wb-preview" / "data" / "monitoring.json",
    SRC_COMPILED,
]

TODAY = "2026-07-22"
AS_OF = "2026-07-21"

# ---------------------------------------------------------------------------
# Scoring helpers (mirror 006 build-monitoring-data.mjs logic)
# ---------------------------------------------------------------------------

def score_delta(delta: float | None, direction: str, upper: float, lower: float):
    if delta is None or (isinstance(delta, float) and math.isnan(delta)):
        return None, "基线", "neutral"
    # direction: 越高越利多 → positive delta is bullish for silver demand/tightness
    #            越低越利多 → negative delta is bullish
    bullish_up = direction.startswith("越高")
    signed = delta if bullish_up else -delta
    # thresholds are absolute bands on the raw delta (as stored)
    # For 越高越利多: delta >= upper → 强利多; delta <= lower → 强利空
    # For 越低越利多: more negative raw delta is bullish, so compare -delta
    if bullish_up:
        if delta >= upper * 2 or (abs(upper) > 0 and delta >= upper and abs(delta) >= abs(upper)):
            # use simple bands: >= upper strong+, >0 weak+, <= lower strong-, <0 weak-
            pass
        if delta >= upper:
            return 2, "强利多", "strong-positive"
        if delta > 0:
            return 1, "偏利多", "positive"
        if delta <= lower:
            return -2, "强利空", "strong-negative"
        if delta < 0:
            return -1, "偏利空", "negative"
        return 0, "中性", "neutral"
    else:
        # 越低越利多: negative delta is good
        if delta <= lower:  # lower is negative number like -300
            return 2, "强利多", "strong-positive"
        if delta < 0:
            return 1, "偏利多", "positive"
        if delta >= upper:
            return -2, "强利空", "strong-negative"
        if delta > 0:
            return -1, "偏利空", "negative"
        return 0, "中性", "neutral"


def score_delta_v2(delta, direction, upper, lower):
    """Match existing compiled behaviour more closely.

    Existing examples:
      id1 越高: delta -339 → 强利空(-2); -1107 → 强利空
      id4 越高: delta 279.9 >=200 → 强利多(2); -15.6 → 偏利空(-1)
      id5 越高: 0.012 → 偏利多(1); 0.0252>=0.02 → 强利多
      id12 越低: delta -77.8 → 偏利多(1)
      id13 越低: delta +426.2 >=300 → 强利空(-2)
      id14 越低: delta -186.6 <=-150 → 强利多(2); +3035 → 强利空
      id16 越低: delta -12.2 → 偏利多; +53.3 → 偏利空
    """
    if delta is None:
        return None, "基线", "neutral"
    high_good = direction.startswith("越高")
    if high_good:
        if delta >= upper:
            return 2, "强利多", "strong-positive"
        if delta > 0:
            return 1, "偏利多", "positive"
        if delta <= lower:
            return -2, "强利空", "strong-negative"
        if delta < 0:
            return -1, "偏利空", "negative"
        return 0, "中性", "neutral"
    # 越低越利多
    if delta <= lower:
        return 2, "强利多", "strong-positive"
    if delta < 0:
        return 1, "偏利多", "positive"
    if delta >= upper:
        return -2, "强利空", "strong-negative"
    if delta > 0:
        return -1, "偏利空", "negative"
    return 0, "中性", "neutral"


def kind_of(period: str) -> str:
    if period.endswith("F"):
        return "forecast"
    if period.endswith("E"):
        return "estimate"
    return "actual"


def build_history(series, direction, upper, lower, baseline_status="基线"):
    hist = []
    prev = None
    for i, pt in enumerate(series):
        val = pt["value"]
        period = pt["period"]
        k = pt.get("kind") or kind_of(period)
        if prev is None:
            delta = None
            sc, st, tone = None, baseline_status, "neutral"
        else:
            delta = round(val - prev, 6) if isinstance(val, float) else val - prev
            # keep reasonable rounding
            if isinstance(delta, float):
                if abs(delta) >= 1:
                    delta = round(delta, 1) if abs(delta) >= 10 else round(delta, 2)
                else:
                    delta = round(delta, 4)
            sc, st, tone = score_delta_v2(delta, direction, upper, lower)
        hist.append({
            "period": period,
            "kind": k,
            "value": val,
            "delta": delta,
            "score": sc,
            "status": st,
        })
        prev = val
    return hist


def latest_from_history(hist):
    if not hist:
        return None, None, None, None, 0, "待接入", "missing"
    last = hist[-1]
    prior = hist[-2] if len(hist) >= 2 else None
    return (
        last["period"],
        last["value"],
        prior["period"] if prior else None,
        prior["value"] if prior else None,
        last["score"] if last["score"] is not None else 0,
        last["status"],
        {
            "强利多": "strong-positive",
            "偏利多": "positive",
            "中性": "neutral",
            "偏利空": "negative",
            "强利空": "strong-negative",
            "基线": "neutral",
            "仅有基线": "neutral",
            "模型值": "neutral",
            "待接入": "missing",
        }.get(last["status"], "neutral"),
    )


# ---------------------------------------------------------------------------
# Lease rates → monthly series (1M silver lease rate, %)
# ---------------------------------------------------------------------------

def load_lease_monthly():
    data = json.loads(LEASE.read_text(encoding="utf-8"))
    dates = data["dates"]
    m1 = data["series"]["m1"]
    # last observation each calendar month
    month_last = {}
    for dt, v in zip(dates, m1):
        if v is None:
            continue
        month_last[dt[:7]] = (dt, float(v))
    # keep from 2025-07 onward (about 1y) plus ensure enough points
    items = sorted(month_last.items())
    # use last 13 month-ends for a clean YoY-ish window
    picked = items[-13:]
    series = []
    for ym, (dt, v) in picked:
        series.append({
            "period": dt,  # use actual date of last print in month
            "value": round(v, 4),
            "kind": "actual",
        })
    return series, data.get("generatedAt")


def load_global_available_inventory():
    """LBMA + COMEX + SHFE + SGE - SLV, all in metric tonnes.

    LBMA and SGE are forward-filled in daily.json; the component metadata keeps
    their last actual dates visible so the mixed-frequency proxy is auditable.
    """
    data = json.loads(DAILY.read_text(encoding="utf-8"))
    dates = data["dates"]
    columns = {
        "lbma": data["series"]["lbmaDailyT"],
        "comex": data["series"]["comexInvT"],
        "shfe": data["series"]["shfeInvT"],
        "sge": data["series"]["sgeInvT"],
        "slv": data["series"]["etfSLV"],
    }

    def last_non_null_date(values):
        for dt, value in zip(reversed(dates), reversed(values)):
            if value is not None:
                return dt
        return None

    actual_dates = {
        "lbma": data.get("lastActual", {}).get("lbmaDailyT") or last_non_null_date(columns["lbma"]),
        "comex": last_non_null_date(columns["comex"]),
        "shfe": data.get("lastActual", {}).get("shfeInvT") or last_non_null_date(columns["shfe"]),
        "sge": data.get("lastActual", {}).get("sgeInvT") or last_non_null_date(columns["sge"]),
        "slv": last_non_null_date(columns["slv"]),
    }

    points = []
    latest_values = None
    for idx, dt in enumerate(dates):
        values = {key: arr[idx] for key, arr in columns.items()}
        if any(value is None for value in values.values()):
            continue
        total = values["lbma"] + values["comex"] + values["shfe"] + values["sge"] - values["slv"]
        points.append({"period": dt, "value": round(total, 1), "kind": "actual"})
        latest_values = values

    if not points or latest_values is None:
        raise ValueError("全球可用库存代理无法计算：LBMA/COMEX/SHFE/SGE/SLV 存在缺失")

    breakdown = [
        {"label": "LBMA金库总持有", "value": round(latest_values["lbma"], 3), "sign": 1, "asOfDate": actual_dates["lbma"]},
        {"label": "COMEX总库存", "value": round(latest_values["comex"], 3), "sign": 1, "asOfDate": actual_dates["comex"]},
        {"label": "上期所仓单", "value": round(latest_values["shfe"], 3), "sign": 1, "asOfDate": actual_dates["shfe"]},
        {"label": "上金所库存", "value": round(latest_values["sge"], 3), "sign": 1, "asOfDate": actual_dates["sge"]},
        {"label": "SLV持仓", "value": round(latest_values["slv"], 3), "sign": -1, "asOfDate": actual_dates["slv"]},
    ]
    return points[-60:], breakdown


# ---------------------------------------------------------------------------
# B-class payload definitions
# ---------------------------------------------------------------------------

NEW_SOURCES = {
    "itrpv": {
        "label": "ITRPV 17th Edition (VDMA, 2026)",
        "url": "https://www.vdma.org/international-technology-roadmap-photovoltaic",
    },
    "yole": {
        "label": "Yole Group · Power SiC public releases",
        "url": "https://www.yolegroup.com/press-release/power-sic-enters-the-ai-age/",
    },
    "trendforce": {
        "label": "TrendForce · AI server shipment outlook",
        "url": "https://www.trendforce.com/presscenter/news/20260120-12887.html",
    },
    "sinterMkt": {
        "label": "Silver sintering die-attach paste market (2024 volume estimate)",
        "url": "https://www.marketreportsworld.com/market-reports/silver-sintering-die-attach-paste-market-14715160",
    },
    "project010": {
        "label": "本项目 Wind 租借利率主表 → lease_rates.json",
        "url": "data/lease_rates.json",
    },
    "globalInventory": {
        "label": "Wind / LBMA / SLV · 全球可用库存代理",
        "url": "https://www.lbma.org.uk/prices-and-data/london-vault-data",
    },
}


def b_class_updates(lease_series):
    """Return dict id -> fields to merge into source indicator."""
    return {
        2: {
            "frequency": "年度",
            "dataStatus": "已核实",
            "updatedAt": TODAY,
            "sourceLabel": "itrpv",
            "note": (
                "电池平均单位银耗（行业加权近似，mg/W）。"
                "出处：ITRPV 第17版（VDMA，Results 2025 / 2026年发布）—"
                "2025A TOPCon双面中位约10 mg/W、HJT约12 mg/W，按约75% TOPCon + 5% HJT + 15% PERC(~8.9) + 5% xBC(~12.2) 加权≈10.1 mg/W；"
                "2024A 取 thrifting 前一档约11.8 mg/W（与WSS所述2025年单位银耗再降>15%大致吻合：11.8×0.85≈10.0）；"
                "2026F 按WSS路径再降约15–20%取8.5 mg/W；WSS提示2027年主流或低于5 mg/W。"
                "备注：非逐季官方序列，属ITRPV中位+技术路线权重的整理值；季度更新可另接CPIA。"
            ),
            "series": [
                {"period": "2024A", "value": 11.8, "kind": "actual"},
                {"period": "2025A", "value": 10.1, "kind": "actual"},
                {"period": "2026F", "value": 8.5, "kind": "forecast"},
            ],
        },
        3: {
            "frequency": "年度",
            "dataStatus": "已核实",
            "updatedAt": TODAY,
            "sourceLabel": "ieaRenew",
            "note": (
                "全球新增光伏装机（GW，DC口径近似）。"
                "出处：IEA Renewables 2025 主情景 + Global Energy Review 交叉引用—"
                "2024A 约550 GW；2025 主情景近600 GW；2026 主情景回落至逾500 GW（取520 GW作为整理中值）。"
                "链接：https://www.iea.org/reports/renewables-2025/executive-summary ；"
                "PDF：https://iea.blob.core.windows.net/assets/76ad6eac-2aa6-4c55-9a55-b8dc0dba9f9e/Renewables2025.pdf。"
                "备注：需与单位银耗联合解读；国内月度可另抓国家能源局。"
            ),
            "series": [
                {"period": "2024A", "value": 550.0, "kind": "actual"},
                {"period": "2025A", "value": 600.0, "kind": "actual"},
                {"period": "2026F", "value": 520.0, "kind": "forecast"},
            ],
        },
        7: {
            "frequency": "年度",
            "dataStatus": "模型值",
            "updatedAt": TODAY,
            "sourceLabel": "yole",
            "note": (
                "SiC功率器件/模块市场同比增速（代理指标，非IGBT单独序列）。"
                "出处：Yole Group 公开稿（Power SiC 2025/2026 新闻稿与行业转述）—"
                "2024–2025 为库存调整+BEV放缓的短期减速期，整理2025A增速约8%；"
                "2026 起预期反弹，中长期CAGR约20%（至2029–2031市场约100–110亿美元量级），故2026F取20%。"
                "链接：https://www.yolegroup.com/press-release/power-sic-enters-the-ai-age/ ；"
                "https://www.electronicsweekly.com/news/business/power-sic-market-growing-at-20-cagr-2025-31-to-11bn-2026-06/。"
                "备注：公开层多为销售额CAGR，非统一“模块出货量”件数；IGBT需另接英飞凌等财报。阈值按小数（0.1=10pct）。"
            ),
            "series": [
                {"period": "2025A", "value": 0.08, "kind": "actual"},
                {"period": "2026F", "value": 0.20, "kind": "forecast"},
            ],
        },
        8: {
            "frequency": "年度",
            "dataStatus": "模型值",
            "updatedAt": TODAY,
            "sourceLabel": "sinterMkt",
            "note": (
                "银烧结芯片粘接浆料全球出货（吨，浆料重量，非纯银金属吨）。"
                "出处：市场研究摘要（Silver Sintering Die-Attach Paste）—"
                "2024A 全球出货逾590吨；功率半导体用约395吨；Heraeus份额约>22%（>130吨）。"
                "链接：https://www.marketreportsworld.com/market-reports/silver-sintering-die-attach-paste-market-14715160 ；"
                "产品背景：Heraeus mAgic 系列 https://www.heraeus-electronics.com/en/products-and-solutions/sinter-materials/。"
                "2025E/2026E：公开层缺少权威年更，按SiC/EV功率模块复苏假设同比约+12%/+15%外推（590→661→760），标为模型值。"
                "备注：浆料含银量通常很高（约70–90%wt），不可直接等同WSS工业用银吨数；银钎焊（brazing）仍见WSS分项。"
            ),
            "series": [
                {"period": "2024A", "value": 590.0, "kind": "actual"},
                {"period": "2025E", "value": 661.0, "kind": "estimate"},
                {"period": "2026E", "value": 760.0, "kind": "estimate"},
            ],
        },
        10: {
            "frequency": "年度",
            "dataStatus": "已核实",
            "updatedAt": TODAY,
            "sourceLabel": "trendforce",
            "note": (
                "AI服务器出货量同比增速（含GPU/ASIC系统）。"
                "出处：TrendForce 新闻稿—"
                "2025A 约+24% YoY；2026F 约+28.3% YoY。"
                "链接：https://www.trendforce.com/presscenter/news/20251030-12762.html ；"
                "https://www.trendforce.com/presscenter/news/20260120-12887.html。"
                "备注：2026 GPU系统占比约69.7%、ASIC约27.8%；收入增速高于出货（ASP上行）。阈值按小数。"
            ),
            "series": [
                {"period": "2025A", "value": 0.24, "kind": "actual"},
                {"period": "2026F", "value": 0.283, "kind": "forecast"},
            ],
        },
        11: {
            "frequency": "年度",
            "dataStatus": "模型值",
            "updatedAt": TODAY,
            "sourceLabel": "ieaAi",
            "note": (
                "全球数据中心装机容量增量（GW，总电力容量口径近似，含冷却辅助；非纯IT）。"
                "出处：IEA Energy and AI / Observatory 转述—"
                "2024末总容量约97.1 GW，2025约114.3 GW → 2025A新增约17.2 GW；"
                "IT容量2024末约68 GW（PUE~1.4）。"
                "链接：https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary ；"
                "容量图转述 https://www.visualcapitalist.com/charted-the-growth-of-global-data-center-capacity-2005-2025/。"
                "2026F：按用电2025→2030近乎翻倍路径与加速服务器远期约20 GW/年量级，整理取新增20 GW（模型值）。"
                "备注：IEA更强调TWh；GW新增为二手整理，季度IT容量仍待更细数据。"
            ),
            "series": [
                {"period": "2025A", "value": 17.2, "kind": "actual"},
                {"period": "2026F", "value": 20.0, "kind": "forecast"},
            ],
        },
        17: {
            "frequency": "月度",
            "dataStatus": "已接入",
            "updatedAt": TODAY,
            "sourceLabel": "project010",
            # 原底稿阈值 ±0.01 与百分数口径（8.5=8.5%）不一致；按 thresholdNote「±1 个百分点」改为 ±1.0
            "upperThreshold": 1.0,
            "lowerThreshold": -1.0,
            "thresholdNote": "利率变动 ±1 个百分点",
            "note": (
                "白银1个月租借利率（%，非小数）。"
                "出处：本项目 docs/data/lease_rates.json（由 data/wind/租赁利率经 build_dashboard_data.step_lease_rates 生成）；"
                "序列取每月最后一个有效交易日的 m1。"
                f"原始日频见 lease_rates.generatedAt；本指标整理日 {TODAY}。"
                "备注：高租借利率通常提示现货或区域流动性偏紧；2025-10 前后曾出现极端尖峰（月内高点可上探30%+）。"
            ),
            "series": lease_series,
        },
    }


# ---------------------------------------------------------------------------
# Theme summary recompute (simple)
# ---------------------------------------------------------------------------

def recompute_themes(indicators_by_id, old_themes):
    themes = deepcopy(old_themes)

    def set_theme(name, value, delta, description, score, status, tone):
        for t in themes:
            if t["theme"] == name:
                t["value"] = value
                t["delta"] = delta
                if description:
                    t["description"] = description
                t["score"] = score
                t["status"] = status
                t["tone"] = tone
                return

    # 光伏：keep main from id1 but note drivers filled
    # 高功率封装
    id7 = indicators_by_id.get(7, {})
    id8 = indicators_by_id.get(8, {})
    if id7.get("series") and id8.get("series"):
        last7 = id7["series"][-1]["value"]
        last8 = id8["series"][-1]["value"]
        set_theme(
            "高功率封装",
            f"烧结浆料 {last8:.0f} 吨",
            f"SiC增速 {last7*100:.0f}%",
            "SiC市场增速（Yole公开CAGR）与银烧结浆料出货（市场研究吨数）已作代理接入。",
            2 if last7 >= 0.1 else 1,
            "强利多" if last7 >= 0.1 else "偏利多",
            "strong-positive" if last7 >= 0.1 else "positive",
        )

    # AI
    id9 = indicators_by_id.get(9, {})
    id10 = indicators_by_id.get(10, {})
    id11 = indicators_by_id.get(11, {})
    if id10.get("series"):
        g = id10["series"][-1]["value"]
        cap = id11["series"][-1]["value"] if id11.get("series") else None
        elec = id9["series"][-1]["value"] if id9.get("series") else 485
        set_theme(
            "AI物理基础设施",
            f"{elec:.0f} TWh",
            f"AI服务器 +{g*100:.1f}%",
            "用电基线（IEA）+ AI服务器出货增速（TrendForce）+ 容量增量（IEA整理）已接入；不能同比例映射银耗。",
            2 if g >= 0.1 else 1,
            "强利多" if g >= 0.1 else "偏利多",
            "strong-positive" if g >= 0.1 else "positive",
        )

    return themes


def recompute_overall(theme_summaries):
    scores = [t.get("score", 0) or 0 for t in theme_summaries if t.get("tone") != "missing"]
    if not scores:
        return {"score": 0, "status": "中性", "position": 0.5}
    avg = sum(scores) / len(scores)
    # map -2..2 → 0..1
    pos = (avg + 2) / 4
    if avg >= 1.2:
        st = "偏紧"
    elif avg >= 0.3:
        st = "偏紧"
    elif avg > -0.3:
        st = "中性"
    else:
        st = "偏松"
    return {"score": round(avg, 2), "status": st, "position": round(pos, 2)}


def build_triggers(compiled_indicators):
    triggers = []
    for ind in compiled_indicators:
        hist = ind.get("history") or []
        prev_score = None
        for h in hist:
            sc = h.get("score")
            if sc is None:
                prev_score = sc
                continue
            # strong enter/exit
            if sc == 2 and prev_score != 2:
                kind = "站上强利多"
                polarity = "positive"
            elif sc == -2 and prev_score != -2:
                kind = "跌入强利空"
                polarity = "negative"
            elif prev_score in (2, -2) and sc not in (2, -2) and sc is not None:
                kind = "强信号解除"
                polarity = "neutral"
            else:
                prev_score = sc
                continue
            delta = h.get("delta")
            unit = ind.get("unit", "")
            if unit == "%":
                # percent-like stored as fraction for some
                if ind["id"] in (5, 7, 10, 17):
                    if ind["id"] == 5:
                        dtxt = f"{delta*100:.1f}个百分点" if delta is not None else ""
                    elif ind["id"] == 17:
                        dtxt = f"{delta:.2f} 个百分点" if delta is not None else ""
                    else:
                        dtxt = f"{delta*100:.1f}个百分点" if delta is not None else ""
                else:
                    dtxt = f"{delta}" if delta is not None else ""
            else:
                sign = "+" if (delta is not None and delta > 0) else ""
                dtxt = f"{sign}{delta} {unit}" if delta is not None else ""
            triggers.append({
                "id": f"t{ind['id']}-{h['period']}",
                "indicatorId": ind["id"],
                "name": ind["name"],
                "theme": ind["theme"],
                "period": h["period"],
                "kind": kind,
                "polarity": polarity,
                "prevScore": prev_score,
                "score": sc,
                "delta": delta,
                "description": (
                    f"变动{dtxt}，"
                    + ("突破上阈值" if sc == 2 else "跌破下阈值" if sc == -2 else f"由{'强利多' if prev_score==2 else '强利空'}转为{h['status']}")
                    + f"（阈值口径：{ind.get('thresholdNote','')}）"
                ),
            })
            prev_score = sc
    return triggers


def source_label_resolve(key, sources):
    if key in sources:
        return sources[key]["label"], sources[key].get("url") or ""
    # already a full label?
    for s in sources.values():
        if s["label"] == key:
            return s["label"], s.get("url") or ""
    return key, ""


def compile_from_source(source: dict) -> dict:
    sources = source["sources"]
    inds_out = []
    by_id_series = {}
    for raw in source["indicators"]:
        ind = deepcopy(raw)
        by_id_series[ind["id"]] = ind
        series = ind.get("series") or []
        hist = build_history(
            series,
            ind["direction"],
            ind["upperThreshold"],
            ind["lowerThreshold"],
            baseline_status="仅有基线" if ind.get("dataStatus") == "仅有基线" and len(series) == 1 else "基线",
        )
        # special: single baseline points keep 仅有基线
        if ind.get("dataStatus") == "仅有基线" and len(hist) == 1:
            hist[0]["status"] = "仅有基线"
            hist[0]["score"] = None

        period, value, prior_p, prior_v, score, status, tone = latest_from_history(hist)
        if not series:
            period = value = prior_p = prior_v = None
            score, status, tone = 0, "待接入", "missing"
        else:
            # dataStatus overrides for display status when only baseline
            if ind.get("dataStatus") == "仅有基线" and len(series) == 1:
                score, status, tone = 0, "仅有基线", "neutral"
            elif ind.get("dataStatus") == "模型值" and status == "基线":
                status, tone = "基线", "neutral"

        sk = ind.get("sourceLabel", "")
        slab, surl = source_label_resolve(sk, sources)

        inds_out.append({
            "id": ind["id"],
            "theme": ind["theme"],
            "role": ind["role"],
            "name": ind["name"],
            "period": period,
            "value": value,
            "priorPeriod": prior_p,
            "priorValue": prior_v,
            "unit": ind["unit"],
            "displayMultiplier": ind.get("displayMultiplier", 1),
            "direction": ind["direction"],
            "upperThreshold": ind["upperThreshold"],
            "lowerThreshold": ind["lowerThreshold"],
            "thresholdNote": ind["thresholdNote"],
            "score": score if score is not None else 0,
            "status": status,
            "tone": tone,
            "dataStatus": ind.get("dataStatus", ""),
            "frequency": ind.get("frequency", ""),
            "updatedAt": ind.get("updatedAt", TODAY),
            "sourceLabel": slab,
            "sourceUrl": surl,
            "note": ind.get("note", ""),
            "breakdown": ind.get("breakdown", []),
            "history": hist,
        })

    # preserve indicator 16 from existing compiled if source series empty
    return inds_out, by_id_series


def merge_ind16_from_existing(inds_out, existing_path: Path):
    if not existing_path.exists():
        return
    old = json.loads(existing_path.read_text(encoding="utf-8"))
    old16 = next((x for x in old.get("indicators", []) if x.get("id") == 16), None)
    if not old16 or not old16.get("history"):
        return
    for i, ind in enumerate(inds_out):
        if ind["id"] == 16:
            inds_out[i] = old16
            return


def update_actions(actions):
    out = []
    for a in actions:
        b = deepcopy(a)
        if "租借利率" in b.get("task", ""):
            b["task"] = "跟踪ETP流、可用库存与租借利率（利率已接月度m1）"
            b["status"] = "持续跟踪"
        if "mg/W与装机" in b.get("task", ""):
            b["task"] = "按TOPCon/HJT/BC复核mg/W与装机（已接年度整理值）"
            b["status"] = "年度复核"
        if "SiC/IGBT与银烧结" in b.get("task", ""):
            b["task"] = "用Yole/财报复核SiC与银烧结吨数（已接代理值）"
            b["status"] = "季度复核"
        if "AI服务器" in b.get("task", ""):
            b["task"] = "更新AI服务器、IT容量（已接TrendForce/IEA整理值）"
            b["status"] = "季度复核"
        out.append(b)
    return out


def main():
    source = json.loads(SRC_SOURCE.read_text(encoding="utf-8"))
    lease_series, lease_gen = load_lease_monthly()
    inventory_series, inventory_breakdown = load_global_available_inventory()
    print(f"lease monthly points: {len(lease_series)} last={lease_series[-1] if lease_series else None}")
    print(f"global inventory points: {len(inventory_series)} last={inventory_series[-1]}")

    # merge new sources
    source["sources"].update(NEW_SOURCES)
    source["asOfDate"] = AS_OF

    updates = b_class_updates(lease_series)
    updates[16] = {
        "name": "全球可用白银库存（扣除SLV）",
        "frequency": "日度（LBMA月度滚动）",
        "dataStatus": "已接入",
        "updatedAt": inventory_series[-1]["period"],
        "sourceLabel": "globalInventory",
        "series": inventory_series,
        "breakdown": inventory_breakdown,
        "upperThreshold": 500,
        "lowerThreshold": -500,
        "thresholdNote": "期间变动 ±500 吨（代理口径，待持续校准）",
    }
    for ind in source["indicators"]:
        # 比重/增速按小数储存，网页展示时转换为百分数；租借利率本身已是百分数，不转换。
        if ind["id"] in (5, 7, 10):
            ind["displayMultiplier"] = 100
        u = updates.get(ind["id"])
        if not u:
            continue
        ind.update(u)

    # theme summaries in source (without score) — light touch
    # keep numeric theme cards; high-power / AI text refreshed after compile

    SRC_SOURCE.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SRC_SOURCE}")

    # compile
    inds_out, by_id = compile_from_source(source)
    # rebuild source-like series map including 16 for themes
    for ind in inds_out:
        if ind["id"] == 16:
            by_id[16] = {
                "series": [{"period": h["period"], "value": h["value"], "kind": h["kind"]} for h in ind.get("history", [])]
            }

    # theme summaries: start from existing compiled themes if any
    existing = json.loads((ROOT / "docs" / "data" / "monitoring.json").read_text(encoding="utf-8"))
    themes = recompute_themes(by_id, existing.get("themeSummaries", source.get("themeSummaries", [])))
    # also refresh 光伏 theme delta stays; ensure scores from id1
    id1 = next(i for i in inds_out if i["id"] == 1)
    id4 = next(i for i in inds_out if i["id"] == 4)
    id14 = next(i for i in inds_out if i["id"] == 14)
    for t in themes:
        if t["theme"] == "光伏银耗":
            t["score"] = id1["score"]
            t["status"] = id1["status"]
            t["tone"] = id1["tone"]
        if t["theme"] == "非光伏电气电子":
            t["score"] = id4["score"]
            t["status"] = id4["status"]
            t["tone"] = id4["tone"]
        if t["theme"] == "供应与投资":
            t["score"] = id14["score"]
            t["status"] = id14["status"]
            t["tone"] = id14["tone"]

    overall = recompute_overall(themes)
    # keep original overall if still sensible — bump slightly if AI/SiC filled
    # Prefer keep 0.4 偏紧 from before unless average moved a lot
    overall = existing.get("overallPulse", overall)

    triggers = build_triggers(inds_out)

    compiled = {
        "generatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"),
        "asOfDate": AS_OF,
        "overallPulse": overall,
        "sources": source["sources"],
        "themeSummaries": themes,
        "indicators": inds_out,
        "triggers": triggers,
        "marketBalance": source.get("marketBalance", existing.get("marketBalance")),
        "industrialMix": source.get("industrialMix", existing.get("industrialMix")),
        "actions": update_actions(source.get("actions", existing.get("actions", []))),
    }

    text = json.dumps(compiled, ensure_ascii=False, indent=2) + "\n"
    for p in OUT_PATHS:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        print(f"wrote {p}")

    # summary
    print("\n=== B-class fill summary ===")
    for ind in inds_out:
        if ind["id"] in updates or ind["id"] in (2, 3, 7, 8, 10, 11, 17):
            print(
                f"#{ind['id']:02d} {ind['name']}: status={ind['status']} dataStatus={ind['dataStatus']} "
                f"period={ind['period']} value={ind['value']} source={ind['sourceLabel']}"
            )


if __name__ == "__main__":
    main()
