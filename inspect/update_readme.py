path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\README.md"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Update the board section description to reflect new layout
src = src.replace(
    "- 看板区块：信号跑马灯 / Hero+紧张度仪表 / 01 五项固定监测 / 02 趋势与结构 / 03 市场脉搏·日频 / 04 库存与递延 / 05 持仓量与虚实比 / 06 COMEX 头寸 / 07 基差与进出口盈亏（分钟级懒加载）/ 08 进口盈亏季节性 / 09 租借利率 / 10 信号动态 / 11 十七项指标库+详情抽屉 / 方法论 / 页脚",
    "- 看板区块：信号跑马灯 / Hero+紧张度仪表 / 01 五项固定监测 / 02 趋势与结构 / 03 市场脉搏（价格+LOF） / 04 递延费与库存（递延费+国内+海外+ETF） / 05 持仓量与虚实比 / 06 COMEX 头寸 / 07 基差与进出口盈亏（分钟级懒加载+合约选择） / 08 进口盈亏季节性 / 09 租借利率 / 10 信号动态 / 11 十七项指标库+详情抽屉 / 方法论 / 页脚"
)

# Update interaction description
src = src.replace(
    "- 交互：明暗双主题持久化、锚点滚动监听、count-up、tab 切换、图例显隐、dataZoom 缩放、指标筛选/搜索/排序、抽屉键盘导航",
    "- 交互：明暗双主题持久化、锚点滚动监听、count-up、tab 切换、图例显隐、dataZoom 缩放（全板块 slider+滚轮）、基差合约双下拉框+预设、指标筛选/搜索/排序、抽屉键盘导航"
)

# Update data flow table
src = src.replace(
    "| 010《白银所有数据.xlsx》《20260719租借利率.xlsx》 | src/build_dashboard_data.py | web/public/data/ 下 daily/positions_curve/virtual_ratio/seasonality/lease_rates/basis_×6/import_profit 共 13 个 JSON |",
    "| 010《白银所有数据.xlsx》（全量历史 16435 行 1968→2026）《20260719租借利率.xlsx》 | src/build_dashboard_data.py | web/public/data/ 下 daily(2.5MB)/positions_curve/virtual_ratio/seasonality/lease_rates/min_×13/basis_×6/import_profit 共 28 个 JSON |"
)

# Add new progress entries
old_progress_end = "- 2026-07-20: 存档——全部代码与对话记录落盘"
new_progress = """- 2026-07-20: 存档——全部代码与对话记录落盘
- 2026-07-20: 集成010全量历史数据（daily.json 561→16435条，1968→2026）；新增trading_calendar（15283天）用于虚实比/持仓量x轴；各板块添加dataZoom slider时间区间选择器；Hero徽章布局修复（库存明细移至行外）
- 2026-07-20: dataZoom滑块重置修复（移除startValue）；布局重组：03市场脉搏仅保留价格+LOF，库存全部合并到04递延费与库存；持仓量/虚实比图对齐010参考（已到期合约延伸到x=0+端点标注+x=0竖线+trading_calendar构建顺序修复）
- 2026-07-20: 存档——全部代码与对话记录落盘"""
src = src.replace(old_progress_end, new_progress)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("README.md updated")
