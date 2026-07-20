# ============ Patch Market.tsx: add default zoom range + sampling ============
path_market = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Market.tsx"
with open(path_market, "r", encoding="utf-8") as f:
    src = f.read()

# PriceChart: add default startValue to dataZoom
# The PriceChart dataZoom is in the truncated part, let me find it
# Actually let me search for the pattern
import re

# For PriceChart - find dataZoom and add startValue
# PriceChart uses points.map(pt => pt.date) for x-axis
# Let's add startValue based on points length
old_price_dz = 'dataZoom: [\n          { type: "inside", throttle: 40 },\n          { type: "slider", height: 18, bottom: 8, ...zoomFill(p) },\n        ],'
new_price_dz = 'dataZoom: [\n          { type: "inside", throttle: 40, startValue: Math.max(0, points.length - 250) },\n          { type: "slider", height: 18, bottom: 8, ...zoomFill(p), startValue: Math.max(0, points.length - 250) },\n        ],'
src = src.replace(old_price_dz, new_price_dz)

# StockLines: add default startValue
old_stock_dz = 'dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],'
new_stock_dz = 'dataZoom: [{ type: "inside", throttle: 40, startValue: Math.max(0, dates.length - 250) }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p), startValue: Math.max(0, dates.length - 250) }],'
src = src.replace(old_stock_dz, new_stock_dz)

# Add sampling to StockLines series
old_stock_series = '''        series: series.map((s) => ({
          name: s.name,
          type: "line" as const,
          data: s.data,
          showSymbol: false,
          connectNulls: true,'''
new_stock_series = '''        series: series.map((s) => ({
          name: s.name,
          type: "line" as const,
          data: s.data,
          showSymbol: false,
          sampling: "lttb" as const,
          connectNulls: true,'''
src = src.replace(old_stock_series, new_stock_series, 1)

# FundPanel: add default startValue
old_fund_dz = '''        dataZoom: [
          { type: "inside", throttle: 40 },
          { type: "slider", height: 18, bottom: 8, ...zoomFill(p) },
        ],'''
new_fund_dz = '''        dataZoom: [
          { type: "inside", throttle: 40, startValue: Math.max(0, points.length - 250) },
          { type: "slider", height: 18, bottom: 8, ...zoomFill(p), startValue: Math.max(0, points.length - 250) },
        ],'''
src = src.replace(old_fund_dz, new_fund_dz)

with open(path_market, "w", encoding="utf-8") as f:
    f.write(src)
print("Market.tsx patched: added default zoom range + sampling")

# ============ Patch Positions.tsx: add default zoom range to ComexSection ============
path_pos = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Positions.tsx"
with open(path_pos, "r", encoding="utf-8") as f:
    src = f.read()

# ComexSection dataZoom - add startValue based on rows length
old_comex_dz = 'dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],'
new_comex_dz = 'dataZoom: [{ type: "inside", throttle: 40, startValue: Math.max(0, rows.length - 250) }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p), startValue: Math.max(0, rows.length - 250) }],'
src = src.replace(old_comex_dz, new_comex_dz)

with open(path_pos, "w", encoding="utf-8") as f:
    f.write(src)
print("Positions.tsx patched: added default zoom range to ComexSection")

print("\nAll Market/Positions patches applied!")
