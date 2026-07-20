import re

# ============ Patch Market.tsx: remove TAIL slicing ============
path_market = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Market.tsx"
with open(path_market, "r", encoding="utf-8") as f:
    src = f.read()

# Remove TAIL constant and slice calls
src = src.replace("const TAIL = 120;\n", "")
src = src.replace("const TAIL = 120;", "")
# Replace .slice(-TAIL) with full data
src = src.replace(".slice(-TAIL)", "")
# Replace dates slice
src = src.replace("const dates = daily.dates.slice(-TAIL);", "const dates = daily.dates;")

with open(path_market, "w", encoding="utf-8") as f:
    f.write(src)
print("Market.tsx patched: removed TAIL slicing")

# ============ Patch Positions.tsx: add dataZoom to ComexSection ============
path_pos = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Positions.tsx"
with open(path_pos, "r", encoding="utf-8") as f:
    src = f.read()

# Add zoomFill import if not present
if "zoomFill" not in src:
    src = src.replace(
        'import { baseAxis, baseLegend, baseTooltip, getPalette, type ThemeMode } from "../lib/echarts";',
        'import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";'
    )

# Add dataZoom to ComexSection chart - find the grid line and add dataZoom after yAxis
old_comex_yaxis = '''          {
            type: "value",
            ...baseAxis(p),
            splitLine: { show: false },
            axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
          },
        ],'''
new_comex_yaxis = '''          {
            type: "value",
            ...baseAxis(p),
            splitLine: { show: false },
            axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
          },
        ],
        dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],'''
src = src.replace(old_comex_yaxis, new_comex_yaxis, 1)

# Also update grid bottom for ComexSection to accommodate slider
src = src.replace(
    'grid: { top: 40, right: 74, bottom: 30, left: 70 },',
    'grid: { top: 40, right: 74, bottom: 52, left: 70 },'
)

with open(path_pos, "w", encoding="utf-8") as f:
    f.write(src)
print("Positions.tsx patched: added dataZoom to ComexSection")

# ============ Patch Basis.tsx: add dataZoom to SeasonalitySection and LeaseSection ============
path_basis = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Basis.tsx"
with open(path_basis, "r", encoding="utf-8") as f:
    src = f.read()

# SeasonalitySection: add dataZoom after yAxis
old_season_yaxis = '''yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } }, series: years.map'''
new_season_yaxis = '''yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } }, dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }], series: years.map'''
src = src.replace(old_season_yaxis, new_season_yaxis, 1)

# SeasonalitySection: update grid bottom
src = src.replace(
    'grid: { top: 34, right: 16, bottom: 30, left: 58 }, tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 1)} 元/千克`) }, legend: { ...baseLegend(p), top: 0, left: 0 }, xAxis: { type: "category", data: data.dates, ...baseAxis(p), boundaryGap: false, axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: string) => v.slice(5), interval: 29 } }',
    'grid: { top: 34, right: 16, bottom: 52, left: 58 }, tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 1)} 元/千克`) }, legend: { ...baseLegend(p), top: 0, left: 0 }, xAxis: { type: "category", data: data.dates, ...baseAxis(p), boundaryGap: false, axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: string) => v.slice(5), interval: 29 } }'
)

# LeaseSection: add dataZoom after yAxis
old_lease_yaxis = '''yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => `${formatNumber(v, 2)}%` } }, series: keys.map'''
new_lease_yaxis = '''yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => `${formatNumber(v, 2)}%` } }, dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }], series: keys.map'''
src = src.replace(old_lease_yaxis, new_lease_yaxis, 1)

# LeaseSection: update grid bottom
src = src.replace(
    'grid: { top: 34, right: 16, bottom: 30, left: 58 }, tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 4)}%`) }',
    'grid: { top: 34, right: 16, bottom: 52, left: 58 }, tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 4)}%`) }'
)

with open(path_basis, "w", encoding="utf-8") as f:
    f.write(src)
print("Basis.tsx patched: added dataZoom to Seasonality + Lease sections")

# ============ Patch Daily.tsx: add sampling for large datasets + default zoom range ============
path_daily = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Daily.tsx"
with open(path_daily, "r", encoding="utf-8") as f:
    src = f.read()

# Add sampling to MultiLineChart series for performance with large data
old_multi_series = '''        series: series.map((s) => ({
          name: s.name,
          type: "line" as const,
          data: s.data ?? [],
          showSymbol: false,
          connectNulls,'''
new_multi_series = '''        series: series.map((s) => ({
          name: s.name,
          type: "line" as const,
          data: s.data ?? [],
          showSymbol: false,
          sampling: "lttb" as const,
          connectNulls,'''
src = src.replace(old_multi_series, new_multi_series, 1)

# Add default startValue to dataZoom in MultiLineChart (show last ~250 trading days by default)
old_dz_multi = '''        dataZoom: zoom
          ? [
              { type: "inside", throttle: 40 },
              { type: "slider", height: 18, bottom: 8, ...zoomFill(p) },
            ]
          : undefined,'''
new_dz_multi = '''        dataZoom: zoom
          ? [
              { type: "inside", throttle: 40, startValue: Math.max(0, dates.length - 250) },
              { type: "slider", height: 18, bottom: 8, ...zoomFill(p), startValue: Math.max(0, dates.length - 250) },
            ]
          : undefined,'''
src = src.replace(old_dz_multi, new_dz_multi, 1)

# Add sampling to DeferredChart series
old_def_series = '''            type: "line",
            step: "end",'''
new_def_series = '''            type: "line",
            step: "end",
            sampling: "lttb" as const,'''
src = src.replace(old_def_series, new_def_series, 1)

# Add default zoom range to DeferredChart (show last ~250 days)
old_def_dz = '''        dataZoom: [
          { type: "inside", throttle: 40 },
          { type: "slider", height: 18, bottom: 8, ...zoomFill(p) },
        ],'''
new_def_dz = '''        dataZoom: [
          { type: "inside", throttle: 40, startValue: Math.max(0, daily.dates.length - 250) },
          { type: "slider", height: 18, bottom: 8, ...zoomFill(p), startValue: Math.max(0, daily.dates.length - 250) },
        ],'''
src = src.replace(old_def_dz, new_def_dz, 1)

with open(path_daily, "w", encoding="utf-8") as f:
    f.write(src)
print("Daily.tsx patched: added sampling + default zoom range")

print("\nAll frontend patches applied!")
