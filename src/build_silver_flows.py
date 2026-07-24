#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_silver_flows.py

生成 web/public/data/silver_flows.json 供 07C「全球银条流向」卡片使用。

两类数据：
A. WSS 报告组（6 组）：World Silver Survey 2026（Silver Institute）
   Appendix 23-30 银条流向示意图，2025 年银条流向，1 Moz = 31.1035 吨。
   配对数值已核验（output/wss2026_fabrication_trade_tonnes.md，坐标就近算法
   客观生成并校验量集合），此处以常量形式嵌入，不解析 md。
B. 官方海关组（4 组）：2025 全年按伙伴国/地区拆分，由
   src/fetch_partner_flows.py 采集（美国 USITC DataWeb / Census、
   印度 TradeStat、香港政府统计处 IDDS），本脚本读取其 CSV，
   取 Top 伙伴（累计占比 ≥95%）+ 合并「其他」。

自洽校验：
- WSS 组：partners 求和 ÷ sharePct 反推总量 vs impliedTotalTonnes（容忍 1%）；
- 官方组：Top 伙伴 + 其他 = 全年合计（恒等），并打印 Top 覆盖率。
任一失败则不写文件并以非零码退出。

用法:  python src/build_silver_flows.py
"""
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "web" / "public" / "data" / "silver_flows.json"
CSV_US = ROOT / "data" / "us" / "us_silver_trade_partners_2025.csv"
CSV_IN = ROOT / "data" / "india" / "india_silver_export_partners_2025.csv"
CSV_HK = ROOT / "data" / "hk_silver_import_partners_2025.csv"

T_PER_MOZ = 31.1035  # 1 Moz = 31.1035 吨
TOLERANCE = 0.01     # WSS 组反推总量自洽容忍 1%
TOP_COVERAGE = 0.95  # 官方组 Top 伙伴累计占比目标
TOP_CAP = 14         # 官方组 Top 伙伴数量上限

# ——— 伙伴中文名映射（未命中会告警并保留原名）———
PARTNER_ZH = {
    # 通用
    "United Kingdom": "英国", "U K": "英国", "UK": "英国",
    "United States": "美国", "U S A": "美国", "USA": "美国",
    "United Arab Emirates": "阿联酋", "U ARAB EMTS": "阿联酋",
    "Switzerland": "瑞士", "SWITZERLAND": "瑞士",
    "Canada": "加拿大", "CANADA": "加拿大",
    "Mexico": "墨西哥", "Germany": "德国", "GERMANY": "德国",
    "France": "法国", "FRANCE": "法国",
    "Italy": "意大利", "ITALY": "意大利",
    "Spain": "西班牙", "SPAIN": "西班牙",
    "India": "印度", "China": "中国", "CHINESE MAINLAND": "中国内地",
    "Hong Kong": "香港", "HONG KONG": "香港",
    "Taiwan": "台湾", "TAIWAN": "台湾",
    "Japan": "日本", "JAPAN": "日本",
    "South Korea": "韩国", "KOREA": "韩国",
    "Turkey": "土耳其", "TURKEY": "土耳其",
    "Australia": "澳大利亚", "AUSTRALIA": "澳大利亚",
    "Russia": "俄罗斯", "RUSSIA": "俄罗斯",
    "Poland": "波兰", "Kazakhstan": "哈萨克斯坦", "Uzbekistan": "乌兹别克斯坦",
    "Chile": "智利", "Belgium": "比利时",
    "Brazil": "巴西", "BRAZIL": "巴西",
    "Denmark": "丹麦", "DENMARK": "丹麦",
    "Saudi Arabia": "沙特阿拉伯", "SAUDI ARAB": "沙特阿拉伯",
}

# ——— A. WSS 报告组（吨）：WSS 2026 Appendix 23-30，2025 年银条流向 ———
# 每组：hub 枢纽名 / direction 方向 / sharePct 展示部分占该枢纽总量比例 /
#       impliedTotalTonnes 占比反推的枢纽总量 / partners 主要伙伴（从大到小）
#
# 2026-07-24 v3 几何定稿 + 官方交叉验证（详见 output/wss2026_fabrication_trade_tonnes.md 第五节）：
#   配对依据 redo_wss_pairing.py（PDF 箭头矢量几何）；
#   官方验证 crosscheck_wss_flows.py（HMRC BDS / TradeStat / IDDS / USITC）。
#   - App24a 英国出口：HMRC 71069100 六伙伴全部吻合（≤14%），定稿。
#   - App25 香港出口：IDDS ttype=4（含转口）9/11 吻合（≤7.4%）；
#     8=Vietnam、4=Singapore 由 IDDS 裁定（248.2t≈8Moz / 138.9t≈4.5Moz）。
#   - App26 印度进口：TradeStat 8/9 吻合（≤5.6%）；韩国 3Moz vs 官方 4.5Moz 标低置信。
#   - App24b 英国进口：HMRC consignment 口径构成与 MF 图面口径系统性不同
#     （HMRC：美国 104Moz 主导；图面：中国 48Moz 主导，总量同量级），
#     图面配对忠实 MF 原图，保持几何结果并标注口径冲突。
#   - lowConfidence=True：几何证据较弱或与官方矛盾的小流量项。
FLOWS_WSS = [
    {
        "hub": "瑞士",
        "direction": "export",
        "sharePct": 89,
        "impliedTotalTonnes": 2691,
        "partners": [
            {"name": "英国", "tonnes": 746.5},
            {"name": "美国", "tonnes": 342.1},
            {"name": "土耳其", "tonnes": 311.0},
            {"name": "印度", "tonnes": 248.8},
            {"name": "德国", "tonnes": 186.6},
            {"name": "意大利", "tonnes": 155.5, "lowConfidence": True},
            {"name": "黎巴嫩", "tonnes": 124.4, "lowConfidence": True},
            {"name": "法国", "tonnes": 93.3},
            {"name": "阿联酋", "tonnes": 93.3, "lowConfidence": True},
            {"name": "泰国", "tonnes": 93.3},
        ],
    },
    {
        "hub": "瑞士",
        "direction": "import",
        "sharePct": 85,
        "impliedTotalTonnes": 1098,
        "partners": [
            {"name": "摩洛哥", "tonnes": 217.7},
            {"name": "意大利", "tonnes": 186.6},
            {"name": "中国", "tonnes": 155.5},
            {"name": "德国", "tonnes": 124.4},
            {"name": "美国", "tonnes": 93.3},
            {"name": "秘鲁", "tonnes": 62.2},
            {"name": "印尼", "tonnes": 31.1},
            {"name": "波兰", "tonnes": 31.1},
            {"name": "澳大利亚", "tonnes": 31.1},
        ],
    },
    {
        "hub": "英国",
        "direction": "export",
        "sharePct": 98,
        "impliedTotalTonnes": 7109,
        "partners": [
            {"name": "美国", "tonnes": 3981.2},
            {"name": "印度", "tonnes": 2052.8},
            {"name": "加拿大", "tonnes": 466.6},
            {"name": "瑞士", "tonnes": 248.8},
            {"name": "阿联酋", "tonnes": 124.4},
            {"name": "比利时", "tonnes": 93.3},
        ],
    },
    {
        "hub": "英国",
        "direction": "import",
        "sharePct": 92,
        "impliedTotalTonnes": 8351,
        "partners": [
            {"name": "中国", "tonnes": 1493.0},
            {"name": "哈萨克斯坦", "tonnes": 1181.9},
            {"name": "美国", "tonnes": 964.2},
            {"name": "西班牙", "tonnes": 839.8},
            {"name": "波兰", "tonnes": 715.4},
            {"name": "韩国", "tonnes": 684.3},
            {"name": "德国", "tonnes": 684.3},
            {"name": "加拿大", "tonnes": 528.8},
            {"name": "墨西哥", "tonnes": 373.2},
            {"name": "乌兹别克斯坦", "tonnes": 124.4},
            {"name": "瑞士", "tonnes": 93.3, "lowConfidence": True},
        ],
    },
    {
        "hub": "香港",
        "direction": "export",
        "sharePct": 96,
        "impliedTotalTonnes": 5184,
        "partners": [
            {"name": "印度", "tonnes": 2208.3},
            {"name": "英国", "tonnes": 1150.8},
            {"name": "泰国", "tonnes": 404.3},
            {"name": "越南", "tonnes": 248.8},
            {"name": "阿联酋", "tonnes": 186.6},
            {"name": "美国", "tonnes": 155.5},
            {"name": "瑞士", "tonnes": 155.5},
            {"name": "台湾", "tonnes": 155.5},
            {"name": "新加坡", "tonnes": 124.4},
            {"name": "中国", "tonnes": 93.3, "lowConfidence": True},
            {"name": "澳大利亚", "tonnes": 93.3},
        ],
    },
    {
        "hub": "印度",
        "direction": "import",
        "sharePct": 94,
        "impliedTotalTonnes": 7213,
        "partners": [
            {"name": "香港", "tonnes": 2923.7},
            {"name": "英国", "tonnes": 2208.3},
            {"name": "美国", "tonnes": 497.7},
            {"name": "瑞士", "tonnes": 342.1},
            {"name": "阿联酋", "tonnes": 279.9},
            {"name": "中国", "tonnes": 186.6},
            {"name": "新加坡", "tonnes": 155.5},
            {"name": "澳大利亚", "tonnes": 93.3},
            {"name": "韩国", "tonnes": 93.3, "lowConfidence": True},
        ],
    },
]

# ——— B. 官方海关组配置：fetch_partner_flows.py 产出的 CSV ———
OFFICIAL_SPECS = [
    {
        "hub": "香港",
        "direction": "import",
        "csv": CSV_HK,
        "flow": "import",
        "source": "香港政府统计处 IDDS · HKHS6 7106 按原产地 · 2025 全年",
    },
    {
        "hub": "美国",
        "direction": "export",
        "csv": CSV_US,
        "flow": "export",
        "source": "USITC DataWeb / U.S. Census · HS/HTS 7106 总出口 · 2025 全年",
    },
    {
        "hub": "美国",
        "direction": "import",
        "csv": CSV_US,
        "flow": "import",
        "source": "USITC DataWeb / U.S. Census · HS/HTS 7106 一般进口 · 2025 全年",
    },
    {
        "hub": "印度",
        "direction": "export",
        "csv": CSV_IN,
        "flow": "export",
        "source": "TradeStat 印度商务部 / DGCI&S · HS7106 · Calendar Year 2025",
    },
]

WSS_SOURCE = "World Silver Survey 2026（Silver Institute）· Appendix 23-30 银条流向"


def zh(name: str, unmapped: set[str]) -> str:
    if name in PARTNER_ZH:
        return PARTNER_ZH[name]
    unmapped.add(name)
    return name


def build_official_group(spec: dict, unmapped: set[str]) -> tuple[dict, float]:
    """读 CSV → Top 伙伴（累计 ≥95%）+ 其他；返回 (group, top_coverage)"""
    with spec["csv"].open(encoding="utf-8-sig", newline="") as fh:
        rows = [
            (r["partner_en"], float(r["tonnes"]))
            for r in csv.DictReader(fh)
            if r["flow"] == spec["flow"] and float(r["tonnes"]) > 0
        ]
    if not rows:
        raise RuntimeError(f"{spec['csv'].name}: no rows for flow={spec['flow']}")
    rows.sort(key=lambda kv: -kv[1])
    total = sum(t for _, t in rows)

    top: list[tuple[str, float]] = []
    acc = 0.0
    for name, tonnes in rows:
        if acc >= TOP_COVERAGE * total or len(top) >= TOP_CAP:
            break
        top.append((name, tonnes))
        acc += tonnes
    other = total - acc
    partners = [{"name": zh(n, unmapped), "tonnes": round(t, 1)} for n, t in top]
    if other > 0.05:
        partners.append({"name": "其他", "tonnes": round(other, 1)})

    group = {
        "hub": spec["hub"],
        "direction": spec["direction"],
        "kind": "official",
        "sharePct": 100,
        "impliedTotalTonnes": round(total, 1),
        "partners": partners,
        "source": spec["source"],
    }
    return group, acc / total


def validate_wss() -> bool:
    """WSS 组：partners 求和 ÷ sharePct 反推总量 vs impliedTotalTonnes（容忍 1%）。"""
    ok = True
    for f in FLOWS_WSS:
        shown = sum(p["tonnes"] for p in f["partners"])
        derived = shown / (f["sharePct"] / 100)
        implied = f["impliedTotalTonnes"]
        err = abs(derived - implied) / implied
        status = "OK " if err <= TOLERANCE else "FAIL"
        if err > TOLERANCE:
            ok = False
        direction = "出口" if f["direction"] == "export" else "进口"
        print(
            f"  [{status}] [WSS] {f['hub']}{direction} · 占 {f['sharePct']}%："
            f"伙伴合计 {shown:,.1f} 吨 → 反推 {derived:,.1f} 吨 vs "
            f"impliedTotal {implied:,} 吨（偏差 {err * 100:.2f}%）"
        )
    return ok


def main() -> None:
    print("[check] 银条流向自洽校验：")
    if not validate_wss():
        print("[ERR] WSS 组存在不自洽分组，已中止，未写文件。")
        sys.exit(1)

    unmapped: set[str] = set()
    official_groups: list[dict] = []
    for spec in OFFICIAL_SPECS:
        group, coverage = build_official_group(spec, unmapped)
        official_groups.append(group)
        direction = "出口" if group["direction"] == "export" else "进口"
        top_n = len(group["partners"]) - (1 if group["partners"][-1]["name"] == "其他" else 0)
        check = sum(p["tonnes"] for p in group["partners"])
        err = abs(check - group["impliedTotalTonnes"]) / group["impliedTotalTonnes"]
        status = "OK " if err <= 0.002 else "FAIL"
        if err > 0.002:
            print(f"[ERR] 官方组 {group['hub']}{direction} Top+其他≠合计（偏差 {err*100:.2f}%），已中止。")
            sys.exit(1)
        print(
            f"  [{status}] [海关] {group['hub']}{direction}：Top {top_n} + 其他 "
            f"（覆盖 {coverage * 100:.1f}%），合计 {group['impliedTotalTonnes']:,.1f} 吨"
        )
    if unmapped:
        print(f"  [WARN] 未映射中文名的伙伴（保留原名）：{sorted(unmapped)}")

    # 组排序：WSS 6 组在前，官方补充组按 香港进口 / 美国出口 / 美国进口 / 印度出口 插入。
    flows = [
        *FLOWS_WSS[:5],              # 瑞士出口/进口、英国出口/进口、香港出口
        official_groups[0],          # 香港进口（官方）
        official_groups[1],          # 美国出口（官方）
        official_groups[2],          # 美国进口（官方）
        FLOWS_WSS[5],                # 印度进口（WSS）
        official_groups[3],          # 印度出口（官方）
    ]
    wss_with_kind = []
    for f in flows:
        f = dict(f)
        f.setdefault("kind", "wss")
        f.setdefault("source", WSS_SOURCE)
        wss_with_kind.append(f)

    out = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "World Silver Survey 2026（Silver Institute）+ 官方海关（USITC/Census、TradeStat、香港政府统计处）",
        "asOf": "2025",
        "unit": "吨",
        "mozPerTonne": round(1 / T_PER_MOZ, 6),
        "note": "2025 年银条/白银（HS/HTS 7106）流向。kind=wss：WSS 2026 报告口径，"
                "每组展示为主要伙伴，sharePct 为展示部分占该枢纽总量比例，"
                "impliedTotalTonnes 由占比反推；kind=official：官方海关 2025 全年口径，"
                "Top 伙伴（累计 ≥95%）+ 其他，impliedTotalTonnes 为全年实际合计。"
                "1 Moz = 31.1035 吨。",
        "flows": wss_with_kind,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    partners = sum(len(f["partners"]) for f in wss_with_kind)
    print(
        f"[OK] silver_flows.json: {len(wss_with_kind)} 组流向 / {partners} 个伙伴，"
        f"{OUT.stat().st_size / 1024:.1f} KB"
    )


if __name__ == "__main__":
    main()
