# 数据采集器

这里集中保存原 Project-004、005、010 中可复用的数据采集/刷新脚本。所有产物都写入 Project-002 的 `data/` 标准目录。

| 脚本 | 数据 | 输出目录 | 说明 |
|---|---|---|---|
| `shfe_incremental_fetch.py` | 上期所会员持仓、龙虎榜原始排名 | `data/shfe/ranking/` | 增量补齐，优先使用；`build_lhb.py` 可直接读取当日 JSON |
| `shfe_full_fetch.py` | 上期所会员持仓 | `data/shfe/ranking/` | 全量回填 |
| `sge_ag_td_fetch.py` | 上金所 Ag(T+D) | `data/sge/` | 从最新有效日之后增量更新日行情；不等同于周度白银库存 |
| `gfex_incremental_fetch.py` | 广期所铂钯仓单 | `data/gfex/` | 日常增量更新，并输出完整历史 CSV |
| `gfex_batch_fetch.py` | 广期所铂钯仓单 | `data/gfex/` | 首次全量抓取/历史回填 |
| `gfex_classify_warehouse.py` | 铂钯仓库/厂库分类 | `data/gfex/` | 默认处理最新原始 CSV |
| `wind_refresh_xls.py` | Wind 主工作簿 | `data/wind/` | 需要本机 Wind/Excel；不会强制关闭其他 Excel |

`update_all.py` 默认会先执行 SHFE、SGE、GFEX 三个可直连交易所采集器，再重建网页。Wind 刷新仍依赖本机 Wind/Excel 会话，因此继续由 Project-010 维护后自动同步；如需只用已有数据重建，可传入 `--skip-exchange-fetch`。
