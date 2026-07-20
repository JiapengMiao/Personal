path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Positions.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Replace the CurveChart function entirely
old_curve = '''function CurveChart({ data, theme, decimals }: { data: CurveData; theme: ThemeMode; decimals: number }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const expiryMap = new Map(data.contracts.map((c) => [c.code, c.expiry]));
      return {
        animationDuration: 400,
        grid: { top: 40, right: 16, bottom: 30, left: 66 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const arr = params as { seriesName: string; value: [number, number]; color: string }[];
            if (!arr.length) return "";
            const x = arr[0].value[0];
            const lines = arr.map(
              (it) =>
                `<div style="display:flex;gap:8px;align-items:center"><i style="width:8px;height:8px;border-radius:2px;background:${it.color};display:inline-block"></i>${it.seriesName}（到期 ${expiryMap.get(it.seriesName) ?? "—"}）<b>${formatNumber(it.value[1], decimals)}</b></div>`,
            );
            return `<div style="margin-bottom:4px"><strong>距到期 ${x} 交易日</strong></div>${lines.join("")}`;
          },
        },
        legend: { ...baseLegend(p), top: 0, left: 0, type: "scroll" },
        xAxis: {
          type: "value",
          min: -90,
          max: 0,
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => `${v}` },
          splitLine: { show: false },
        },
        yAxis: {
          type: "value",
          scale: true,
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, decimals) },
        },
        series: data.contracts.map((c, i) => ({
          name: c.code,
          type: "line" as const,
          data: c.points.map((pt) => [pt.x, pt.y]),
          showSymbol: false,
          smooth: 0.15,
          lineStyle: { width: 1.8, color: p.series[i % p.series.length] },
          itemStyle: { color: p.series[i % p.series.length] },
        })),
      };
    };
  }, [data, theme, decimals]);
  const ref = useEChart(build, [data, decimals], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 300 }} />;
}'''

new_curve = '''function CurveChart({ data, theme, decimals }: { data: CurveData; theme: ThemeMode; decimals: number }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const expiryMap = new Map(data.contracts.map((c) => [c.code, c.expiry]));
      return {
        animationDuration: 400,
        grid: { top: 40, right: 120, bottom: 30, left: 66 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const arr = params as { seriesName: string; value: [number, number]; color: string }[];
            if (!arr.length) return "";
            const x = arr[0].value[0];
            const lines = arr.map(
              (it) =>
                `<div style="display:flex;gap:8px;align-items:center"><i style="width:8px;height:8px;border-radius:2px;background:${it.color};display:inline-block"></i>${it.seriesName}（到期 ${expiryMap.get(it.seriesName) ?? "—"}）<b>${formatNumber(it.value[1], decimals)}</b></div>`,
            );
            return `<div style="margin-bottom:4px"><strong>距到期 ${x} 交易日</strong></div>${lines.join("")}`;
          },
        },
        legend: { ...baseLegend(p), top: 0, left: 0, type: "scroll" },
        xAxis: {
          type: "value",
          min: -90,
          max: 0,
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => `${v}` },
          splitLine: { show: false },
        },
        yAxis: {
          type: "value",
          scale: true,
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, decimals) },
        },
        series: data.contracts.map((c, i) => {
          const color = p.series[i % p.series.length];
          const pts = c.points.map((pt) => [pt.x, pt.y] as [number, number]);
          const lastPt = pts[pts.length - 1];
          return {
            name: c.code,
            type: "line" as const,
            data: pts,
            showSymbol: false,
            smooth: 0.15,
            lineStyle: { width: 1.8, color },
            itemStyle: { color },
            markLine: {
              silent: true,
              symbol: "none",
              label: { show: false },
              lineStyle: { color: p.edge, width: 1, type: "dashed" as const },
              data: [{ xAxis: 0 }],
            },
            markPoint: lastPt
              ? {
                  symbol: "circle",
                  symbolSize: 7,
                  itemStyle: { color },
                  label: {
                    show: true,
                    position: "right" as const,
                    formatter: `${c.code}  ${formatNumber(lastPt[1], decimals)}\\n距最后交易日${Math.abs(lastPt[0])}日`,
                    color,
                    fontFamily: "JetBrains Mono",
                    fontSize: 10,
                    lineHeight: 13,
                  },
                  data: [{ coord: lastPt }],
                }
              : undefined,
          };
        }),
      };
    };
  }, [data, theme, decimals]);
  const ref = useEChart(build, [data, decimals], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 340 }} />;
}'''

src = src.replace(old_curve, new_curve, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Positions.tsx: added endpoint markers + x=0 line + wider right margin")
