# Project-002 monitoring.json 数据源清单

> 用途：说明白银监测看板 `docs/data/monitoring.json` 里每一项数据从哪来、现在怎么更新、以后能不能自动化。
> 整理日期：2026-07-22（对应 monitoring.json asOfDate = 2026-07-21，17 项指标）。

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

monitoring.json 里登记了 6 个来源（sources 字段）：

| 来源 | 性质 | 更新方式 |
|---|---|---|
| World Silver Survey 2026（WSS，Silver Institute 年报） | 年度 PDF 报告，每年 4 月发布 | 人工读报告填底稿 |
| The Silver Institute 2025 market release | 官网新闻稿 | 人工 |
| Silver: The Next Generation Metal（Silver Institute 专题报告） | 专题 PDF | 人工 |
| IEA · Energy and AI | 专题报告（网页） | 人工 |
| IEA · Renewables 2025 | 年度报告（网页） | 人工 |
| Wind 万得 | 日频行情与库存 | **已自动**（脚本拉取） |

---

## 三、17 项指标逐项清单

### A 类：已自动接入（1 项）

| # | 主题 | 指标 | 频率 | 来源 | 更新方式 |
|---|---|---|---|---|---|
| 16 | 供应与投资 | 交易所及伦敦可用库存 | 日度 | Wind 万得 | ✅ 自动：006 跑 `fetch-market-data.mjs`，当前更新到 2026-07-20 |

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

### C 类：待接入（7 项）

| # | 主题 | 指标 | 频率 | 拟定来源 | 备注 |
|---|---|---|---|---|---|
| 2 | 光伏银耗 | 电池平均单位银耗 | 季度 | WSS（mg/W） | WSS 一年只有一期，季度数据可另找 CPIA（中国光伏行业协会） |
| 3 | 光伏银耗 | 全球新增光伏装机 | 季度/年度 | IEA Renewables 2025（GW） | 国内月度装机可看国家能源局，可网页抓取 |
| 7 | 高功率封装 | SiC/IGBT功率模块出货增速 | 季度 | 待确定 | 候选：英飞凌/安森美/意法财报、Yole 报告 |
| 8 | 高功率封装 | 银烧结/银钎焊材料出货 | 季度 | 待确定 | 候选：贺利氏等材料商财报，公开数据少 |
| 10 | AI物理基础设施 | AI服务器/GPU系统出货增速 | 季度 | 待确定 | 候选：TrendForce / IDC 季度新闻稿 |
| 11 | AI物理基础设施 | 数据中心新增IT容量 | 季度 | IEA · Energy and AI | IEA 不定期更新，暂只能人工 |
| 17 | 供应与投资 | 白银租借利率 | 周度/月度 | 待确定 | **本项目已有现成数据：`docs/data/lease_rates.json`（周度，源自 010 主表租赁利率 sheet），可直接接入** |

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

| 指标 | 能否自动 | 可行路径 |
|---|---|---|
| 16 库存 | 已自动 | Wind 插件日频拉取，维持现状 |
| 17 租借利率 | **最容易接** | 002 的 `lease_rates.json` 已是周度序列，006 生成器加一个读取步骤即可 |
| 3 光伏装机 | 半自动 | 国家能源局月度新闻可网页抓取；IEA 年度仍需人工 |
| 15 ETP净流入 | 半自动 | 可用 SLV / PSLV 等白银 ETF 持仓日频数据估算（Wind / iFinD 可查），替代官网月报 |
| 2 单位银耗 | 难自动 | WSS 年度 + CPIA 报告，都是 PDF，需人工读数 |
| 7 / 8 / 10 出货类 | 难自动 | 依赖财报或付费报告（Yole / TrendForce），只能人工摘录 |
| WSS 系（1/4/5/12/13/14） | 一年一次人工 | 每年 4 月新报告发布后统一更新一次即可，频率低、量不大 |

---

## 六、备注

- 17 项指标的 `updatedAt` 多为 2026-07-19，那是人工底稿的最后编辑日期，不是同步失败；文件整体 asOfDate = 2026-07-21。
- 002 侧校验逻辑在 `build_dashboard_data.py` 约 1480 行：会检查 asOfDate 新鲜度和指标 16 的接入状态。
- 本文档放项目根目录，不进 `docs/`（docs 由 publish.bat 全清重建，只放线上产物）。
