# Project-002-白银数据网页可视化

> 白银市场全景数据终端
> 创建时间：2026-07-19
> 最近更新：2026-07-24

## 项目概述

本项目使用 Vite、React、TypeScript 和 ECharts 构建交互式白银数据看板，整合价格、库存、递延费、持仓、虚实比、龙虎榜、租赁利率、现货基差、进出口盈亏、全球贸易及产业监测指标。

原 Project-004、Project-005、Project-006 的监测模块及 Project-010 的相关数据管道已统一并入本项目：

- Project-004：SHFE、SGE 数据和采集器
- Project-005：GFEX 铂钯仓单数据和采集器
- Project-006：仅迁入监测模块；客户池、客户分析、报告、PDF 和工作簿仍保留在 Project-006
- Project-010：Wind 主工作簿、租赁利率、龙虎榜及必要刷新逻辑

正式网站：<https://silverdaily.cfd/>

部署链路：GitHub `main` 分支 → EdgeOne Pages 国际站项目 `silverdaily-global` 自动部署。

## 当前状态

- 最近一次全量基础数据更新：2026-07-23 18:38—18:39
- 2026-07-24 定向更新：香港贸易卡片补回可见国别标题；印度、美国、英国均改用官方连续月度数据
- 更新结果：美国和英国完整历史月度数据已拉取并完成连续性、重复月份和净进口公式校验；TypeScript、Vite 构建、`docs/` 同步及本地浏览器预览均通过；尚未提交 Git 或发布线上站点
- 当前本地数据与功能：
  - SGE、SHFE、GFEX、龙虎榜、现货报价、基差及租赁利率更新至 2026-07-23
  - 美、英、印三国白银贸易区块已接入 Part 07
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
│   └── india/                      # 印度白银贸易
├── web/                            # Vite + React 前端
│   └── public/data/                # 页面读取的 JSON
├── docs/                           # Pages 发布目录，仅放构建产物
├── output/
│   ├── update_runs/latest.json     # 最近一次统一更新报告
│   └── verify/                     # 验证截图
├── conversation_logs/              # 本地对话记录，不进入 Git
├── Project-002-monitoring数据源清单.md
└── publish.bat                     # 更新、提交并推送的一键脚本
```

## 日常更新流程

### 1. 更新外部源数据

`src/update_all.py` 负责使用已有源数据重建看板，不会自动抓取交易所数据。需要当天最新数据时，先按需运行 `src/collectors/` 中的采集器：

| 采集器 | 数据 | 输出 |
|---|---|---|
| `shfe_incremental_fetch.py` | 上期所会员持仓 | `data/shfe/ranking/` |
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
2. 检查本地必需源数据
3. 生成全部看板 JSON
4. 提取现货报价（共享源存在时）
5. 生成香港、美国、英国、印度月度贸易及龙虎榜数据
6. 执行 TypeScript 校验
7. 执行 Vite 生产构建
8. 将 `web/dist/` 同步至 `docs/`
9. 写入 `output/update_runs/latest.json`

可选参数：

```powershell
py -3 src/update_all.py --data-only
py -3 src/update_all.py --skip-docs
py -3 src/update_all.py --sync-only
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
- 2026-07-24：修正香港贸易图可见标题；从印度商务部 TradeStat / DGCI&S 补齐 2018-01 至 2026-05 共 101 个月；从 USITC DataWeb 补齐美国 1989-01 至 2026-05 共 449 个月；从 HMRC BDS archive 补齐英国 2016-01 至 2026-05 共 125 个月，三者均为真实官方月度数据
