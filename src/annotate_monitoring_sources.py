# -*- coding: utf-8 -*-
"""为 monitoring 观测指标统一补全出处备注，便于后续更新。

写入：
  - data/monitoring/monitoring-source.json
  - data/monitoring/monitoring-data.json
  - docs/data/monitoring.json
  - web/public/data/monitoring.json
  - output/wb-preview/data/monitoring.json（若存在）

备注统一结构：
  【出处】...
  【链接】...
  【更新】...
  【口径】...
"""
from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "monitoring" / "monitoring-source.json"
OUTS = [
    ROOT / "docs" / "data" / "monitoring.json",
    ROOT / "web" / "public" / "data" / "monitoring.json",
    ROOT / "output" / "wb-preview" / "data" / "monitoring.json",
    ROOT / "data" / "monitoring" / "monitoring-data.json",
]

WSS_PDF = "https://silverinstitute.org/wp-content/uploads/2026/04/World-Silver-Survey-2026.pdf"
WSS_RELEASE = "https://silverinstitute.org/elevated-lease-rates-regional-liquidity-tightness-and-robust-investor-interest-resulted-in-record-silver-prices-in-2025/"
NEXT_GEN = "https://silverinstitute.org/wp-content/uploads/2025/12/Silver_The-Next-Generation-Metal_DECEMBER-Release.pdf"
IEA_AI = "https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary"
IEA_RENEW = "https://www.iea.org/reports/renewables-2025/executive-summary"
IEA_RENEW_PDF = "https://iea.blob.core.windows.net/assets/76ad6eac-2aa6-4c55-9a55-b8dc0dba9f9e/Renewables2025.pdf"
ITRPV = "https://www.vdma.org/international-technology-roadmap-photovoltaic"
YOLE = "https://www.yolegroup.com/press-release/power-sic-enters-the-ai-age/"
YOLE2 = "https://www.electronicsweekly.com/news/business/power-sic-market-growing-at-20-cagr-2025-31-to-11bn-2026-06/"
TF1 = "https://www.trendforce.com/presscenter/news/20251030-12762.html"
TF2 = "https://www.trendforce.com/presscenter/news/20260120-12887.html"
SINTER = "https://www.marketreportsworld.com/market-reports/silver-sintering-die-attach-paste-market-14715160"
HERAEUS = "https://www.heraeus-electronics.com/en/products-and-solutions/sinter-materials/"
WIND = "https://www.wind.com.cn/"
VC_DC = "https://www.visualcapitalist.com/charted-the-growth-of-global-data-center-capacity-2005-2025/"

# Moz → 吨：×31.1035（金衡）
MOZ = "1 Moz × 31.1035 = 吨"


def note(*parts: str) -> str:
    return "".join(parts)


# id -> full attribution note
NOTES: dict[int, str] = {
    1: note(
        "【出处】World Silver Survey 2026（Metals Focus / The Silver Institute）光伏用银分项；",
        f"原始约 2024=197.5 / 2025=186.6 / 2026F=151.0 Moz，换算吨后写入本序列（{MOZ}）。",
        f"【链接】{WSS_PDF}",
        "【更新】每年约 4 月 WSS 新版发布后，人工改 monitoring-source.json 指标1 series，再跑编译。",
        "【口径】装机增长与单位降银/银包铜/铜电镀的合成结果；2026F 同比约-19.1%。非季度序列。",
    ),
    2: note(
        "【出处】ITRPV 第17版（VDMA，Results 2025）电池金属化银耗中位值 + WSS 2026 thrifting 路径；",
        "2025A：TOPCon双面≈10、HJT≈12、PERC≈8.9、xBC≈12.2 mg/W，按约75%/5%/15%/5%权重≈10.1；",
        "2024A≈11.8（与 WSS「2025 单位银耗再降>15%」粗吻合）；2026F≈8.5（再降约15–20%）；WSS 提示 2027 主流或<5 mg/W。",
        f"【链接】ITRPV {ITRPV} ；WSS对照 {WSS_PDF}",
        "【更新】ITRPV 通常年更；季度可另摘 CPIA/企业技术会。改 source 指标2 series 后重编译。",
        "【口径】行业加权整理值，非单一厂商 BOM；单位 mg/W。",
    ),
    3: note(
        "【出处】IEA Renewables 2025 主情景（全球光伏新增装机，DC 口径近似）",
        "及 Global Energy Review 交叉引用：2024A≈550 GW，2025≈近600 GW，2026 回落至逾500 GW（整理中值520）。",
        f"【链接】摘要 {IEA_RENEW} ；PDF {IEA_RENEW_PDF}",
        "【更新】IEA 年报；国内月度可抓国家能源局装机新闻作补充，勿与全球口径混用。",
        "【口径】需与指标2单位银耗联合解读，不能单独外推白银吨数。",
    ),
    4: note(
        "【出处】World Silver Survey 2026：电气电子用银总量 − 光伏用银；",
        "含汽车、AI/数据中心、电网、半导体、通信与消费电子等非光伏电气电子。",
        f"示例：2025 电气电子约449.5 Moz − PV186.6 Moz ≈262.9 Moz → 约8177 吨（{MOZ}）。",
        f"【链接】{WSS_PDF}",
        "【更新】随 WSS 年报与指标1同步改 series（2024A/2025A/2026F）。",
        "【口径】WSS 工业需求分项推导，不是海关或企业出货直接加总。",
    ),
    5: note(
        "【出处】由指标4 ÷ WSS 全球工业用银总需求 计算（World Silver Survey 2026）。",
        "序列以小数存储：0.3999 = 39.99%。",
        f"【链接】{WSS_PDF}",
        "【更新】WSS 更新工业总需求或非光伏电气电子后重算三项年份。",
        "【口径】守门指标：判断电气化增量是否足以抵消光伏降银；阈值按百分点小数（±0.02=±2pct）。",
    ),
    6: note(
        "【出处】Silver Institute《Silver: The Next Generation Metal》（2025-12，Oxford Economics 合作）；",
        "报告给出 2031 年全球汽车用银约94 Moz≈2923.7 吨、2025–2031 CAGR 3.4%；",
        "本序列由终点与 CAGR 反推：2025E≈2392.3、2026E≈2473.6 吨（全汽车口径，含 ICE/混合/BEV）。",
        f"【链接】{NEXT_GEN}",
        "【更新】专题报告不定期；有新版终点/CAGR 时重算，或改用 WSS 若日后单列汽车分项。",
        "【口径】模型反推值（dataStatus=模型值），非 WSS 供需主表直接数。",
    ),
    7: note(
        "【出处】Yole Group Power SiC 公开新闻稿/行业转述（销售额口径 CAGR，作模块出货代理）；",
        "2024–2025 为库存调整+BEV 放缓的减速期，整理 2025A≈+8%；",
        "中长期至 2029–2031 约20% CAGR、市场约100–110 亿美元，故 2026F=20%。",
        f"【链接】{YOLE} ；{YOLE2}",
        "【更新】Yole 年报/季监（多为付费）或英飞凌/安森美/意法财报 SiC 收入增速；改 series 后重编译。",
        "【口径】代理指标：公开层多为 $ 增速而非统一模块件数；IGBT 需另接；值用小数 0.20=20%。",
    ),
    8: note(
        "【出处】银烧结芯片粘接浆料（die-attach paste）市场研究摘要：2024A 全球出货逾590 吨浆料；",
        "功率半导体用约395 吨；Heraeus 份额约>22%（>130 吨）。",
        "2025E/2026E 按 SiC/EV 功率模块复苏假设 +12%/+15% 外推至 661/760 吨（模型值）。",
        f"【链接】市场摘要 {SINTER} ；Heraeus mAgic 产品 {HERAEUS}",
        "【更新】缺权威年更时保持模型外推并标注；有 IDTechEx/供应商吨数则替换 actual。",
        "【口径】浆料重量，不是纯银金属吨，不可直接加进 WSS 工业用银；银钎焊另见 WSS brazing 分项（industrialMix）。",
    ),
    9: note(
        "【出处】IEA《Energy and AI》及后续 Key Questions on Energy and AI：",
        "2025A 全球数据中心用电约485 TWh；展望 2030 约950 TWh。",
        f"【链接】{IEA_AI}",
        "【更新】IEA 专题/更新稿发布后改 series；目前仅有 2025A 基线。",
        "【口径】用电是硬件扩张的代理，不能同比例映射白银吨数；与指标10/11 联合看。",
    ),
    10: note(
        "【出处】TrendForce AI 服务器出货展望新闻稿：",
        "2025A 出货量约+24% YoY；2026F 约+28.3% YoY（含 GPU/ASIC 系统）。",
        f"【链接】{TF1} ；{TF2}",
        "【更新】TrendForce 新闻稿/付费库季度更新；也可对照 CSP 资本开支与 NVIDIA 数据中心收入。",
        "【口径】出货量增速（小数存储）；收入增速通常更高。2026 GPU 系统占比约69.7%、ASIC 约27.8%。",
    ),
    11: note(
        "【出处】IEA Energy and AI / Observatory 容量口径转述：",
        "2024 末全球数据中心总电力容量约97.1 GW，2025 约114.3 GW → 2025A 新增约17.2 GW；",
        "IT 容量 2024 末约68 GW（PUE~1.4）。2026F 新增 20 GW 为按用电翻倍路径与加速服务器量级整理的模型值。",
        f"【链接】{IEA_AI} ；容量图转述 {VC_DC}",
        "【更新】IEA 图表/Observatory 更新后替换；第三方（DC Byte 等）可作季度交叉。",
        "【口径】偏设施总电力容量增量，不是纯 IT 负载 GW；IEA 主叙事仍是 TWh（指标9）。",
    ),
    12: note(
        "【出处】World Silver Survey 2026 矿山产量：2025A≈846.6 Moz、2026F≈844.1 Moz，",
        f"换算为 26332.2 / 26254.4 吨（{MOZ}）。",
        f"【链接】{WSS_PDF}",
        "【更新】每年 WSS；也可对照 GFMS/各大矿企产量指引作预览，最终以 WSS 为准。",
        "【口径】白银多为铜/铅锌/金副产品，供给弹性受主金属资本开支制约。",
    ),
    13: note(
        "【出处】World Silver Survey 2026 再生银（回收）供应：",
        f"2025A≈197.6 Moz、2026F≈211.3 Moz → 6146.0 / 6572.2 吨（{MOZ}）。",
        f"【链接】{WSS_PDF}",
        "【更新】WSS 年报；高银价年份关注珠宝/工业废料回收与精炼瓶颈新闻。",
        "【口径】高价推动回收；再生增加对价格偏利空（方向：越低越利多）。",
    ),
    14: note(
        "【出处】World Silver Survey 2026 全球市场平衡（供应−需求，不含 ETP）：",
        "2025A 缺口约−40.3 Moz、2026F 约−46.3 Moz → −1253.5 / −1440.1 吨；",
        f"2017–2024 历史序列同表换算（{MOZ}）。与顶层 marketBalance 字段同源。",
        f"【链接】{WSS_PDF}",
        "【更新】WSS 主表；改 series 时同步改 marketBalance 数组。",
        "【口径】负值=缺口；不包含 ETP 资金流（见指标15）。",
    ),
    15: note(
        "【出处】The Silver Institute 市场新闻稿 + WSS 2026 投资/ETP 章节整理；",
        "当前仅写入 2026F 净流入基线 933.1 吨≈30 Moz。",
        "对照：WSS 称 2025 全球银 ETP 净流入约273 Moz（未写入本序列，可后续补 2025A）。",
        f"【链接】新闻稿 {WSS_RELEASE} ；年报 {WSS_PDF}",
        "【更新】WSS/协会月度投资新闻；半自动可用 SLV/PSLV 等持仓日频（Wind/iFinD）估算。",
        "【口径】资金流影响可流通金属紧张度；与供需缺口（指标14）分开记录。",
    ),
    16: note(
        "【出处】本项目 daily.json 的 LBMA金库总持有、COMEX总库存、上期所仓单、上金所库存与SLV持仓；",
        "原始数据来自 Wind/彭博及交易所、LBMA公开库存链路，统一换算为吨。",
        "【链接】https://www.lbma.org.uk/prices-and-data/london-vault-data",
        "【更新】日度重算；LBMA按月公布并沿用至下一期，上金所休市或未更新日沿用最后实际值。",
        "【口径】全球可用库存代理 = LBMA + COMEX + 上期所 + 上金所 − SLV；LBMA总持有仍可能包含其他ETF或已分配金属，因此这是近似可流通口径，不是严格自由库存。",
    ),
    17: note(
        "【出处】本项目 data/wind/租赁利率 → docs/data/lease_rates.json 的 series.m1；",
        "监测序列取每月最后一个有效交易日的白银 1 个月租借利率（%，非小数）。",
        "生成脚本：src/build_dashboard_data.py → step_lease_rates()；",
        "监测填充：src/fill_monitoring_b_class.py / annotate 流程。",
        "【链接】本地文件 docs/data/lease_rates.json（无外网 URL）；原始 xlsx 见 data/wind/租赁利率/。",
        "【更新】010 更新租借利率表后跑 build_dashboard_data，再刷新本指标月末序列。",
        "【口径】高租借利率提示现货/区域流动性偏紧；2025-10 前后曾出现极端尖峰。阈值 ±1.0 个百分点。",
    ),
}

# 衍生块出处（写入顶层 dataLineage，供更新人员阅读）
DATA_LINEAGE = {
    "marketBalance": {
        "label": "全球市场平衡十年序列",
        "sourceKey": "wss",
        "note": note(
            "【出处】与指标14相同，World Silver Survey 2026 供需平衡表换算为吨；",
            "type=实际/预测 对应 A/F。【链接】",
            WSS_PDF,
            "【更新】改指标14 series 时必须同步本数组，避免图卡不一致。",
        ),
    },
    "industrialMix": {
        "label": "工业用银结构（光伏/非光伏/钎焊/其他）",
        "sourceKey": "wss",
        "note": note(
            "【出处】World Silver Survey 2026 工业需求分项吨数；",
            "photovoltaic 与指标1一致，nonPv 与指标4一致，brazing/other 为 WSS 其余工业分项。",
            f"【链接】{WSS_PDF}",
            "【更新】WSS 年报后四列一并改；单位吨。",
        ),
    },
    "triggers": {
        "label": "强信号触发记录",
        "sourceKey": None,
        "note": "【出处】无独立外源；由编译脚本按各指标阈值比较 history 自动生成。【更新】无需手维。",
    },
    "themeSummaries": {
        "label": "主题汇总卡",
        "sourceKey": None,
        "note": "【出处】主指标/已接入代理值汇总（光伏看1、电气电子看4、功率看7/8、AI看9/10、供应看14）；【更新】编译时重算。",
    },
    "overallPulse": {
        "label": "综合脉冲",
        "sourceKey": None,
        "note": "【出处】主题分数汇总；【更新】编译时重算，勿手改 unless 校准。",
    },
    "actions": {
        "label": "行动建议",
        "sourceKey": None,
        "note": "【出处】人工维护于 monitoring-source.json；【更新】随接入状态改 task/status 文案。",
    },
}


def main():
    source = json.loads(SRC.read_text(encoding="utf-8"))

    # 线上页面以站点根目录为基准，可直接打开同目录下的租借利率 JSON。
    if "project010" in source.get("sources", {}):
        source["sources"]["project010"]["url"] = "data/lease_rates.json"
        source["sources"]["project010"]["label"] = (
            "本项目 Wind 租借利率主表 → lease_rates.json"
        )

    # annotate each indicator in draft
    for ind in source["indicators"]:
        nid = ind["id"]
        ind["displayMultiplier"] = 100 if nid in (5, 7, 10) else 1
        if nid == 16:
            ind["name"] = "全球可用白银库存（扣除SLV）"
            ind["sourceLabel"] = "globalInventory"
        if nid in NOTES:
            ind["note"] = NOTES[nid]
            # keep sourceLabel keys as-is; fix 16 if still 待确定
            if nid == 16 and ind.get("sourceLabel") in ("待确定", "", None):
                ind["sourceLabel"] = "wind"
            if nid == 17:
                ind["sourceLabel"] = "project010"
                ind["upperThreshold"] = 1.0
                ind["lowerThreshold"] = -1.0
                ind["thresholdNote"] = "利率变动 ±1 个百分点"

    source["dataLineage"] = DATA_LINEAGE
    source["attributionUpdatedAt"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    SRC.write_text(json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {SRC}")

    # patch all compiled outputs: refresh notes, source urls, dataLineage
    src_by_id = {i["id"]: i for i in source["indicators"]}
    sources_map = source["sources"]

    def resolve(label_key: str):
        if label_key in sources_map:
            return sources_map[label_key]["label"], sources_map[label_key].get("url") or ""
        # already resolved full label
        for s in sources_map.values():
            if s["label"] == label_key:
                return s["label"], s.get("url") or ""
        return label_key, ""

    for path in OUTS:
        if not path.exists():
            print(f"skip missing {path}")
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["sources"] = deepcopy(sources_map)
        doc["dataLineage"] = deepcopy(DATA_LINEAGE)
        doc["attributionUpdatedAt"] = source["attributionUpdatedAt"]
        for ind in doc.get("indicators", []):
            raw = src_by_id.get(ind["id"])
            if not raw:
                continue
            ind["note"] = raw["note"]
            ind["name"] = raw.get("name", ind.get("name", ""))
            ind["displayMultiplier"] = raw.get("displayMultiplier", 1)
            # refresh source label/url from key if draft still uses key
            key = raw.get("sourceLabel", "")
            slab, surl = resolve(key)
            # if compiled already has full label matching, still refresh url
            if key in sources_map:
                ind["sourceLabel"] = slab
                ind["sourceUrl"] = surl
            else:
                # draft had key resolved already in previous compile — map by id defaults
                defaults = {
                    1: "wss", 2: "itrpv", 3: "ieaRenew", 4: "wss", 5: "wss", 6: "nextGen",
                    7: "yole", 8: "sinterMkt", 9: "ieaAi", 10: "trendforce", 11: "ieaAi",
                    12: "wss", 13: "wss", 14: "wss", 15: "wssRelease", 16: "globalInventory", 17: "project010",
                }
                k2 = defaults.get(ind["id"])
                if k2:
                    ind["sourceLabel"], ind["sourceUrl"] = resolve(k2)
            if ind["id"] == 17:
                ind["upperThreshold"] = 1.0
                ind["lowerThreshold"] = -1.0
                ind["thresholdNote"] = "利率变动 ±1 个百分点"
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {path}")

    # verify all notes contain 出处
    bad = []
    doc = json.loads((ROOT / "docs" / "data" / "monitoring.json").read_text(encoding="utf-8"))
    for ind in doc["indicators"]:
        if "【出处】" not in (ind.get("note") or ""):
            bad.append(ind["id"])
        if not ind.get("sourceLabel"):
            bad.append(f"label-{ind['id']}")
    print("missing attribution ids:", bad or "none")
    print("dataLineage keys:", list(doc.get("dataLineage", {})))


if __name__ == "__main__":
    main()
