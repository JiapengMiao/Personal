# Project-002 monitoring.json 数据源清单

> 用途：说明白银监测看板 `docs/data/monitoring.json` 里每一项数据从哪来、现在怎么更新、以后能不能自动化。
> 整理日期：2026-07-22（对应 monitoring.json asOfDate = 2026-07-21，17 项指标）。  
> 同日补丁：原 C 类 7 项待接入已按最优公开源写入（见第三节 C；脚本 `src/fill_monitoring_b_class.py`）。

---

## 一、更新链路（数据是怎么到网站上的）

```
006 项目（Project-006-白银客户搜集）
  ├─ web/data/monitoring-source.json   ← 人工维护的底稿（17 项指标 + 来源标注）
  ├─ web/data/market-data.json         ← Wind 日频数据（脚本自动拉取）
  │      ↑ web/scripts/fetch-market-data.mjs（经 wind 插件取数）
  │      ↑ 备用：web/scripts/sync-inventory-from-project002.mjs（从 002 daily.json 同步库存）
  │
  └─ node web/scripts/build-monitoring-data.mjs   ← 运行后编译两个输入
         ↓ 生成
      web/app/monitoring-data.json

002 项目（本项目）
  └─ src/build_dashboard_data.py 的 step_copy_static()（约 458 行）
         ↓ 直接复制 006 的生成物（本地另有灾备副本）
      docs/data/monitoring.json  →  GitHub Pages 上线
```

**要点**：网站上的 monitoring.json 不是在本项目算的，是 006 项目编译好后整体复制过来的。要改内容，改 006 的 `web/data/monitoring-source.json`（人工指标）或跑 `fetch-market-data.mjs`（Wind 指标），再跑 build 脚本，最后回 002 跑 publish。

---

## 二、数据源总表

monitoring.json 里登记了 12 个来源（sources 字段）：

| 来源 | 性质 | 更新方式 |
|---|---|---|
| World Silver Survey 2026（WSS，Silver Institute 年报） | 年度 PDF 报告，每年 4 月发布 | 人工读报告填底稿 |
| The Silver Institute 2025 market release | 官网新闻稿 | 人工 |
| Silver: The Next Generation Metal（Silver Institute 专题报告） | 专题 PDF | 人工 |
| IEA · Energy and AI | 专题报告（网页） | 人工 |
| IEA · Renewables 2025 | 年度报告（网页） | 人工 |
| Wind 万得 | 日频行情与库存 | **已自动**（脚本拉取） |
| ITRPV 17th Edition（VDMA） | 光伏技术年度路线图 | 人工读报告 |
| Yole Group · Power SiC | 功率半导体公开稿/代理口径 | 人工，保留模型标记 |
| TrendForce · AI server outlook | AI 服务器公开新闻稿 | 人工 |
| Silver sintering die-attach paste market | 第三方市场研究/代理口径 | 人工，保留模型标记 |
| Project-010 租借利率主表 | 本地 `lease_rates.json` | **已接入** |
| Wind / LBMA / SLV · 全球可用库存代理 | `LBMA + COMEX + 上期所 + 上金所 − SLV` | **已接入并自动重算** |

---

## 三、17 项指标逐项清单

### A 类：已自动接入（1 项）

| # | 主题 | 指标 | 频率 | 来源 | 更新方式 |
|---|---|---|---|---|---|
| 16 | 供应与投资 | 全球可用白银库存（扣除SLV） | 日度（LBMA月度滚动） | Wind / 彭博 / LBMA / 交易所 | ✅ 自动：`LBMA + COMEX + 上期所 + 上金所 − SLV`；保留各组成项真实截止日 |

### B 类：年度报告，人工维护（9 项）

| # | 主题 | 指标 | 频率 | 来源 | 数据状态 |
|---|---|---|---|---|---|
| 1 | 光伏银耗 | 全球光伏用银量 | 年度 | World Silver Survey 2026 | 已核实 |
| 4 | 非光伏电气电子 | 非光伏电气电子用银 | 年度 | World Silver Survey 2026 | 已核实 |
| 5 | 非光伏电气电子 | 占工业需求比重 | 年度 | World Silver Survey 2026 | 已核实 |
| 6 | 非光伏电气电子 | 全球汽车行业用银 | 年度 | Silver: The Next Generation Metal | 模型值 |
| 9 | AI物理基础设施 | 全球数据中心用电 | 年度 | IEA · Energy and AI（2025A = 485 TWh 基线） | 仅有基线 |
| 12 | 供应与投资 | 全球矿山产量 | 年度 | World Silver Survey 2026 | 已核实 |
| 13 | 供应与投资 | 全球再生银供应 | 年度 | World Silver Survey 2026 | 已核实 |
| 14 | 供应与投资 | 全球市场平衡 | 年度 | World Silver Survey 2026 | 已核实 |
| 15 | 供应与投资 | ETP净流入 | 月度/年度 | Silver Institute 2025 market release | 仅有基线 |

更新方式：每年 4 月 WSS 新报告发布后，人工把新数字填进 006 的 `monitoring-source.json`，跑 build 脚本。IEA / 专题报告同理（不定期）。

### C 类：原待接入 → 2026-07-22 已按最优公开源补齐（7 项）

> 由 `src/fill_monitoring_b_class.py` 写入 `monitoring-source.json` 并重编译 `monitoring.json`。  
> 每条 `note` 字段内含**出处链接与口径说明**；模型外推项 `dataStatus=模型值`。

| # | 主题 | 指标 | 频率 | 采用来源 | 整理值（摘要） | 数据状态 |
|---|---|---|---|---|---|---|
| 2 | 光伏银耗 | 电池平均单位银耗 | 年度 | **ITRPV 17th（VDMA）** + WSS thrifting 路径 | 2024A 11.8 / 2025A 10.1 / 2026F 8.5 mg/W（TOPCon/HJT/PERC/xBC 加权） | 已核实（整理值） |
| 3 | 光伏银耗 | 全球新增光伏装机 | 年度 | **IEA Renewables 2025** | 2024A 550 / 2025A 600 / 2026F 520 GW | 已核实 |
| 7 | 高功率封装 | SiC/IGBT功率模块出货增速 | 年度 | **Yole Group** 公开稿（SiC 市场 CAGR） | 2025A 8% / 2026F 20%（小数 0.08 / 0.20） | 模型值（销售额代理，非模块件数） |
| 8 | 高功率封装 | 银烧结/银钎焊材料出货 | 年度 | **银烧结 die-attach 浆料市场研究**（2024 吨数）+ 外推 | 2024A 590 / 2025E 661 / 2026E 760 吨（浆料重，非纯银） | 模型值 |
| 10 | AI物理基础设施 | AI服务器/GPU系统出货增速 | 年度 | **TrendForce** 新闻稿 | 2025A +24% / 2026F +28.3% | 已核实 |
| 11 | AI物理基础设施 | 数据中心新增IT容量 | 年度 | **IEA Energy and AI** 容量转述 | 2025A +17.2 GW / 2026F +20 GW（总电力容量口径） | 模型值 |
| 17 | 供应与投资 | 白银租借利率 | 月度 | **Project-010 → `data/lease_rates.json` m1** | 每月末值，最新 2026-07-21 = -0.12% | 已接入 |

**出处 URL（写入 sources 字段）**

| key | label | url |
|---|---|---|
| itrpv | ITRPV 17th Edition (VDMA, 2026) | https://www.vdma.org/international-technology-roadmap-photovoltaic |
| yole | Yole Group · Power SiC public releases | https://www.yolegroup.com/press-release/power-sic-enters-the-ai-age/ |
| trendforce | TrendForce · AI server shipment outlook | https://www.trendforce.com/presscenter/news/20260120-12887.html |
| sinterMkt | Silver sintering die-attach paste market | https://www.marketreportsworld.com/market-reports/silver-sintering-die-attach-paste-market-14715160 |
| project010 | Project-010 租借利率主表 | （本地 `lease_rates.json`） |

**口径注意**

- #2 阈值原为「季度 ±0.3 mg/W」，现为年度点，年度降幅 >1 mg/W 会显示强利空（与降银利空逻辑一致）。
- #7/#10 增速以**小数**存储（0.20 = 20%），与 #5 比重字段同一约定。
- #8 是**浆料吨数**，不可直接加总进 WSS 工业用银。
- #11 更接近设施总电力容量增量，不是纯 IT 负载；IEA 主口径仍是 TWh（见指标 9）。
- #17 阈值已校正为 ±1.0 个百分点（原底稿 ±0.01 与百分数口径不符）。
- #16 为全球可流通库存的代理口径；LBMA总持有可能还包含其他ETF或已分配金属，减去SLV后仍不能解释为严格自由库存。

---

## 四、monitoring.json 里的衍生数据（不是独立来源，由上面算出来）

| 字段 | 内容 | 来源 |
|---|---|---|
| marketBalance | 2017–2026 十年全球市场平衡序列（吨），2026F = -1440.1（预测） | WSS，随指标 14 一起人工维护 |
| industrialMix | 2024 / 2025 / 2026F 光伏、非光伏、钎焊、其他用银吨数 | WSS，人工维护 |
| triggers | 强信号触发记录 | build 脚本按阈值规则**自动计算**，无需维护 |
| themeSummaries / overallPulse | 主题汇总卡、综合脉冲分 | build 脚本自动汇总 |
| actions | 行动建议 | 人工写在底稿里 |

---

## 五、自动化潜力评估（找"其他更新方式"用）

| 指标 | 能否自动 | 可行路径 | 2026-07-22 状态 |
|---|---|---|---|
| 16 库存 | 已自动 | Wind 插件日频拉取，维持现状 | 已接入 |
| 17 租借利率 | **已接月度** | 读 `lease_rates.json` m1 月末值；可再升周度 | 已接入 |
| 3 光伏装机 | 半自动 | 国家能源局月度新闻可网页抓取；IEA 年度仍需人工 | 已接 IEA 年度 |
| 15 ETP净流入 | 半自动 | 可用 SLV / PSLV 等白银 ETF 持仓日频数据估算（Wind / iFinD 可查），替代官网月报 | 仍仅有 2026F 基线 |
| 2 单位银耗 | 难自动 | ITRPV/WSS/CPIA 都是 PDF，需人工读数 | 已接 ITRPV 整理值 |
| 7 / 8 / 10 出货类 | 难自动 | 依赖财报或付费报告（Yole / TrendForce），只能人工摘录 | 已接公开稿/模型值 |
| 11 IT容量 | 半自动 | IEA 不定期；第三方容量数据库 | 已接 IEA 整理值 |
| WSS 系（1/4/5/12/13/14） | 一年一次人工 | 每年 4 月新报告发布后统一更新一次即可，频率低、量不大 | 已核实 |

---

## 六、出处备注规范（观测部门更新用）

每条指标的 `note` 必须包含四段标签（由 `src/annotate_monitoring_sources.py` 统一写入）：

| 标签 | 含义 |
|---|---|
| `【出处】` | 报告/数据库/本地表名称与关键原始数 |
| `【链接】` | 可点击 URL 或本地路径 |
| `【更新】` | 下次怎么改、改哪个文件、多久一次 |
| `【口径】` | 单位、是否模型值、勿与其它指标混加等 |

衍生块出处写在顶层 `dataLineage`（`marketBalance` / `industrialMix` / `triggers` / `themeSummaries` / `overallPulse` / `actions`），不单独占 indicators。

**改数流程建议**

1. 改 `data/006源数据/monitoring-source.json` 的 `indicators[].series`（或跑 006 Wind 拉取）。
2. 若只改备注模板：`py -3 src/annotate_monitoring_sources.py`。
3. 若重填 B 类公开整理值：`py -3 src/fill_monitoring_b_class.py`，再跑 annotate 以免备注被旧逻辑覆盖。
4. 发布前确认 `docs/data/monitoring.json` 与 `web/public/data/monitoring.json` 已同步。

---

## 七、备注

- 17 项指标的 `updatedAt`：A 类多为 2026-07-19（底稿），B 类补数/出处标注为 2026-07-22；文件整体 asOfDate = 2026-07-21。
- 顶层 `attributionUpdatedAt` 记录最近一次全量出处标注时间。
- 002 侧校验逻辑在 `build_dashboard_data.py` 约 1480 行：会检查 asOfDate 新鲜度和指标 16 的接入状态。
- 本文档放项目根目录，不进 `docs/`（docs 由 publish.bat 全清重建，只放线上产物）。
