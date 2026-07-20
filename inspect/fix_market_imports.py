path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Market.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Clean up imports - remove unused ones
src = src.replace(
    'import { useMemo, useState } from "react";',
    'import { useMemo, useState } from "react";'
)
# Remove DailyData from type import if no longer used
if "DailyData" in src and "daily" not in src.split("function ")[0]:
    src = src.replace(
        'import type { DailyData, MarketData, MarketPoint } from "../lib/types";',
        'import type { MarketData, MarketPoint } from "../lib/types";'
    )
# Remove unused format imports
src = src.replace(
    'import { formatNumber, formatTradeTime, lastNonNull, lastPoint } from "../lib/format";',
    'import { formatNumber, formatTradeTime, lastPoint } from "../lib/format";'
)
# Remove zoomFill if no longer used
if "zoomFill" not in src.split("import")[0] and src.count("zoomFill") == 1:
    src = src.replace(
        'import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";',
        'import { baseAxis, baseLegend, baseTooltip, getPalette, type ThemeMode } from "../lib/echarts";'
    )

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Market.tsx imports cleaned")
