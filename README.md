# Project-002-白银数据网页可视化

> 贵金属数据终端：白银 / 铂钯 / 监测中心
> 创建时间：2026-07-19
> 最近更新：2026-07-24

## 项目概述

本项目使用 Vite、React、TypeScript 和 ECharts 构建交互式贵金属数据终端。网页按数据用途拆分为白银、铂钯和监测中心三个静态入口，仍共用一套采集、JSON 生成、构建和发布管道。

原 Project-004、Project-005、Project-006 的监测模块及 Project-010 的相关数据管道已统一并入本项目：

- Project-004：SHFE、SGE 数据和采集器
- Project-005：GFEX 铂钯仓单数据和采集器
- Project-006：仅迁入监测模块；客户池、客户分析、报告、PDF 和工作簿仍保留在 Project-006
- Project-010：Wind 主工作簿、租赁利率、龙虎榜及必要刷新逻辑

正式网站：<https://silverdaily.cfd/>

## 页面结构

| 页面 | 正式地址 | 归属内容 |
|---|---|---|
| 白银数据终端 | <https://silverdaily.cfd/silver/> | 01—08：行情、库存、白银持仓与虚实比、COMEX、上期所持仓、龙虎榜、贸易基差、租借利率 |
| 铂钯数据终端 | <https://silverdaily.cfd/platinum-palladium/> | 01—08 中归属铂钯的广期所仓单、仓库明细与铂金/钯金虚实比 |
| 白银监测中心 | <https://silverdaily.cfd/monitoring/> | 09—12：五项固定监测、趋势与结构、信号动态、十七项指标库 |

根地址会自动进入白银数据终端。三页顶栏均提供“白银｜铂钯｜监测中心”切换；静态页面从同一根目录读取 data JSON，避免重复维护数据。

部署链路：GitHub `main` 分支 → EdgeOne Pages 国际站项目 `silverdaily-global` 自动部署。

## 当前状态

- 最近一次全量基础数据更新：2026-07-24 17:40—17:43（14/14 环节成功）
- 2026-07-24 页面结构：已完成三静态页面拆分；白银页只保留 01—08 的白银模块，铂钯页展示 GFEX 仓单与铂钯虚实比，监测中心承接原 09—12 模块。三个页面均已在本地实际加载验证，无控制台错误。
- 2026-07-24 定向更新：香港贸易卡片补回可见国别标题；印度、美国、英国均改用官方连续月度数据
- 2026-07-24 研究记录：已完成秘鲁 HS7106 与镜像口径核验，但因量级较小且出口结构无法形成完整同口径表，原始研究保留于 `data/peru/`、`output/`，不在 07C 网页展示。
- 更新结果：印度、美国、英国官方月度历史数据全部拉取并通过连续性、重复月份和净进口公式校验；本轮 `update_all.py` 已先自动拉取交易所数据，再完成统一更新、TypeScript 校验、Vite 生产构建和 `docs/` 同步。
- 当前本地数据与功能：
  - Wind 主工作簿与租赁利率、SHFE 会员持仓与龙虎榜、SGE Ag(T+D)、GFEX 铂钯仓单均已更新至 2026-07-24
  - 产业监测底稿最新为 2026-07-22，香港贸易原始表最新为 2026-07-21；页面已按现有底稿全量重建
  - 美、英、印三国白银贸易区块已接入 Part 07
  - 全球银条流向已展示瑞士、英国、香港、美国、印度的 2025 年进出口伙伴结构（10 组、100 个伙伴记录）；同国进口固定左侧、出口固定右侧；秘鲁不在网页展示
  - 美国 USITC DataWeb / Census HS/HTS 7106 真实月度数据连续覆盖 1989-01 至 2026-05，共 449 个月；2026-06 尚未发布，页面保留空档
  - 英国 HMRC BDS CN8 71069100 真实月度数据连续覆盖 2016-01 至 2026-05，共 125 个月；2026-06 尚未发布，页面保留空档
  - 印度 TradeStat / DGCI&S HS 7106 月度进口、出口及净进口连续覆盖 2018-01 至 2026-05，共 101 个月、无缺月
  - 前端数据请求使用构建版本参数和 `no-store`，降低旧数据缓存风险

线上正式站点仍以最近一次 `docs/`、Git 与 EdgeOne 发布结果为准。

不同数据源的发布频率并不一致，页面应以各指标标注的真实截止日期为准。

## 目录结构

```text
Project-002-白银数据网页可视化/
├── README.md
├── src/
│   ├── update_all.py               # 统一更新入口
│   ├── collectors/                 # 交易所和 Wind 采集器
│   └── pipelines/                  # 辅助数据管道
├── data/
│   ├── wind/                       # Wind 主表、租赁利率
│   ├── shfe/                       # 上期所会员持仓、龙虎榜
│   ├── sge/                        # Ag(T+D) 日行情
│   ├── gfex/                       # 广期所铂钯仓单
│   ├── monitoring/                 # 产业监测底稿
│   ├── us/                         # 美国白银贸易
│   ├── uk/                         # 英国白银贸易
│   ├── india/                      # 印度白银贸易
│   └── peru/                       # 秘鲁伙伴结构：SUNAT 进口表与出口镜像样本
├── web/                            # Vite + React 前端
│   ├── silver/                     # 白银静态入口
│   ├── platinum-palladium/         # 铂钯静态入口
│   ├── monitoring/                 # 监测中心静态入口
│   ├── src/pages/                  # 三页应用与共享顶栏
│   └── public/data/                # 三页共用读取的 JSON
├── docs/                           # Pages 发布目录，仅放构建产物
├── output/
│   ├── update_runs/latest.json     # 最近一次统一更新报告
│   ├── verify/                     # 验证截图
│   └── 对话记录/                   # 持久项目对话记录（避免被 docs 构建同步覆盖）
├── conversation_logs/              # 本地对话记录，不进入 Git
├── Project-002-monitoring数据源清单.md
└── publish.bat                     # 更新、提交并推送的一键脚本
```

## 日常更新流程

### 1. 更新外部源数据

`src/update_all.py` 默认会先增量拉取可直连交易所的数据，再重建看板。Wind 主工作簿和租赁利率仍以 Project-010 为准；其余交易所采集器也可在排障或单独补数时直接运行：

| 采集器 | 数据 | 输出 |
|---|---|---|
| `shfe_incremental_fetch.py` | 上期所会员持仓、龙虎榜原始排名 | `data/shfe/ranking/` |
| `sge_ag_td_fetch.py` | 上金所 Ag(T+D) 日行情 | `data/sge/` |
| `gfex_incremental_fetch.py` | 广期所铂钯仓单 | `data/gfex/` |
| `wind_refresh_xls.py` | Wind 主工作簿 | `data/wind/` |

完整说明见 [数据采集器说明](src/collectors/README.md)。

注意：Ag(T+D) 日行情不等同于上金所白银库存；白银库存为周频数据，不能用日行情日期替代库存真实截止日期。

### 2. 运行统一更新

在项目根目录执行：

```powershell
py -3 src/update_all.py
```

默认流程：

1. 当 Project-010 中的主工作簿或租赁利率文件较新时，自动同步至 `data/wind/`
2. 自动增量拉取 SHFE 会员持仓/龙虎榜原始排名、SGE Ag(T+D)、GFEX 铂钯仓单
3. 检查本地必需源数据，并从当日 SHFE 原始排名重建龙虎榜
4. 生成全部看板 JSON，并提取现货报价（共享源存在时）
5. 生成香港、美国、英国、印度月度贸易数据
6. 执行 TypeScript 校验和 Vite 生产构建
7. 将 `web/dist/` 同步至 `docs/`，写入 `output/update_runs/latest.json`

可选参数：

```powershell
py -3 src/update_all.py --data-only
py -3 src/update_all.py --skip-docs
py -3 src/update_all.py --sync-only
py -3 src/update_all.py --skip-exchange-fetch
```

- `--data-only`：只生成 JSON，不校验或构建前端
- `--skip-docs`：构建前端，但不覆盖 `docs/`
- `--sync-only`：仅把已有 `web/dist/` 同步至 `docs/`

统一更新脚本不会自动提交或推送 Git。

### 3. 本地开发

```powershell
Set-Location web
npm run dev -- --host 127.0.0.1 --port 7100
```

生产构建：

```powershell
Set-Location web
npm run build
```

如固定端口显示旧内容，应先检查驻留进程和实际监听端口，并以页面关键内容、资源哈希和数据日期判断版本。

## 主要数据流

| 源数据 | 处理脚本 | 主要产出 |
|---|---|---|
| `data/wind/白银所有数据.xlsx`、租赁利率 | `src/build_dashboard_data.py` | 日频、市场、持仓、虚实比、季节性、租赁利率、分钟线、基差和进出口盈亏 JSON |
| `data/shfe/ranking/`、`data/sge/` | `src/build_dashboard_data.py` | `shfe_positioning.json` |
| `data/shfe/lhb/` | `src/build_lhb.py` | `lhb.json` |
| `data/gfex/`、Wind 铂钯数据 | `src/build_dashboard_data.py` | `metal_virtual_ratio.json`、`pp_warehouse.json` |
| `data/monitoring/`、Wind 库存列 | `src/build_dashboard_data.py` | `monitoring.json`、`market.json` |
| `data/hk_silver_trade.csv` | `src/build_hk_trade.py` | `hk_trade.json` |
| USITC DataWeb（美国 Census 官方贸易统计）HS/HTS 7106 | `src/fetch_us_trade_data.py`、`src/fetch_us_trade_history.py` | 1989 年起美国月度 CSV、`us_trade.json` |
| HMRC UK Trade Info BDS archive CN8 71069100 | `src/fetch_uk_trade_data.py`、`src/fetch_uk_trade_history.py` | 2016 年起英国月度 CSV、`uk_trade.json` |
| 印度 TradeStat / DGCI&S HS 7106 | `src/fetch_india_trade_data.py`、`src/preview_india_trade_chart.py` | 印度月度 CSV、`india_trade.json` |
| SUNAT HS7106 年度税则号/国家 + 瑞士/美国/印度进口镜像 | `data/peru/` | 秘鲁口径研究底稿；当前不接入网页 |
| 白银每日报价共享工作簿 | `src/extract_spot_quotes.py` | `spot_quotes.json` |

美国贸易管道通过 DataWeb 公开报表一次取得 1989 年以来的 Census 月度第一数量，并分别汇总 GM（克）与 CGM（含量克）。英国贸易管道会下载 HMRC replacement archives，检查档案月份是否重叠；2026 年 1—4 月档案与只含 5 月的 `2605` 文件分开拼接，避免重复计数。旧年度汇编脚本会识别两条新主序列，不再覆盖。

## 看板结构

页面按投研阅读顺序分为 12 个 Part：

1. 市场脉搏
2. 库存、递延费与铂钯仓单
3. 持仓量与虚实比
4. COMEX
5. 上期所持仓
6. 龙虎榜
7. 香港及美英印贸易、现货基差、进出口盈亏与季节性
8. 租赁利率
9. 五项固定监测
10. 趋势与结构
11. 信号动态
12. 十七项指标库

主要交互包括明暗主题、锚点导航、图例显隐、tab 切换、dataZoom、月度范围选择、基差合约选择、龙虎榜双边席位联动、指标筛选和详情抽屉。

## 发布

发布前必须确认：

- `output/update_runs/latest.json` 状态为 `success`
- `web/public/data/` 与 `docs/data/` 的关键日期正确
- TypeScript 与 Vite 构建成功
- `docs/index.html` 引用当前构建生成的哈希资源
- Git 状态中没有对话记录、凭据、坚果云冲突副本或临时文件

优先明确暂存需要发布的路径，避免未经检查直接执行全量暂存。`publish.bat` 会自动更新、执行 `git add -A`、提交并推送，仅在确认工作区干净且确实需要发布时使用。

详细流程见 [发布流程 SOP](docs/发布流程SOP.md)。

推送成功后，EdgeOne Pages 通常在 5—10 分钟内自动完成部署。HTML 和 JSON 默认重新验证，JS/CSS 使用内容哈希和长期缓存。

## 项目边界

- Project-004、005、010 继续作为只读历史回退，不再作为 002 的日常运行入口
- Project-006 仅迁出监测模块；客户池和研究报告仍由 006 独立维护
- `docs/` 是构建发布目录，统一更新时可能被重建，不存放对话记录或不可再生源文件
- `conversation_logs/` 仅本地保存，并由 `.gitignore` 排除
- Git 提交和推送属于发布动作，应在用户确认后执行

## 关键里程碑

- 2026-07-19：项目初始化，完成第一版数据管道和交互式看板
- 2026-07-20：接入 Project-010 全量历史、现货报价和日期区间交互；完成公开仓库安全整改
- 2026-07-21：完成自定义域名部署、香港贸易模块及 CSS `zoom` 下 ECharts 指针命中修复
- 2026-07-22：合并 004、005、006 监测模块和 010，建立统一数据目录与 `update_all.py`
- 2026-07-23：完成全量更新、美英印贸易区块、龙虎榜统一接入、防缓存改造及发布 SOP；随后将美英印贸易图改为月度视图，并用 Census 官方 USA Trade Online + IMDB/EXDB 补齐美国 2026-01 至 2026-05
- 2026-07-24：修正香港贸易图可见标题；从印度商务部 TradeStat / DGCI&S 补齐 2018-01 至 2026-05 共 101 个月；从 USITC DataWeb 补齐美国 1989-01 至 2026-05 共 449 个月；从 HMRC BDS archive 补齐英国 2016-01 至 2026-05 共 125 个月，三者均为真实官方月度数据；发布流程SOP 防丢失改造（正本移入 web/public）；当日完成提交发布
