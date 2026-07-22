# 数据采集器

这里集中保存原 Project-004、005、010 中可复用的数据采集/刷新脚本。所有产物都写入 Project-002 的 `data/` 标准目录。

| 脚本 | 数据 | 输出目录 | 说明 |
|---|---|---|---|
| `shfe_incremental_fetch.py` | 上期所会员持仓 | `data/shfe/ranking/` | 增量补齐，优先使用 |
| `shfe_full_fetch.py` | 上期所会员持仓 | `data/shfe/ranking/` | 全量回填 |
| `sge_ag_td_fetch.py` | 上金所 Ag(T+D) | `data/sge/` | 从最新有效日之后增量更新日行情；不等同于周度白银库存 |
| `gfex_incremental_fetch.py` | 广期所铂钯仓单 | `data/gfex/` | 日常增量更新，并输出完整历史 CSV |
| `gfex_batch_fetch.py` | 广期所铂钯仓单 | `data/gfex/` | 首次全量抓取/历史回填 |
| `gfex_classify_warehouse.py` | 铂钯仓库/厂库分类 | `data/gfex/` | 默认处理最新原始 CSV |
| `wind_refresh_xls.py` | Wind 主工作簿 | `data/wind/` | 需要本机 Wind/Excel；不会强制关闭其他 Excel |

采集器涉及交易所网络或本机 Wind 会话，不纳入默认的 `update_all.py`。先完成相应源数据更新，再运行统一更新入口。
