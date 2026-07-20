import { useMemo } from "react";
import type { MarketData, MarketPoint } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { RangePicker } from "./Daily";
import { formatNumber, lastPoint } from "../lib/format";

// ——— 03 市场脉搏 ———
export function MarketSection({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  return (
    <section className="section-block" id="market">
      <SectionHeading index="03" title="市场脉搏 · 日频" desc="伦敦银 / 沪银 / Ag(T+D) / 金银比 / 白银基金" id="market" />
      <div className="stack-grid">
        <PricePanel market={market} theme={theme} />
        <FundPanel market={market} theme={theme} />
      </div>
    </section>
  );
}

/** 合并多个序列为统一日期轴 */
function mergeDates(seriesList: MarketPoint[][]): string[] {
  const set = new Set<string>();
  for (const pts of seriesList) for (const p of pts) set.add(p.date);
  return [...set].sort();
}

function toAligned(dates: string[], pts: MarketPoint[]): (number | null)[] {
  const map = new Map(pts.map((p) => [p.date, p.value] as const));
  return dates.map((d) => map.get(d) ?? null);
}

function PricePanel({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  const items = market.items;

  const dates = useMemo(
    () => mergeDates([items.londonSilverCnyKg.points, items.shfeSilver.points, items.sgeAgTd.points]),
    [items],
  );
  const latestRatio = lastPoint(items.goldSilverRatio.points);

  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const price = (pts: MarketPoint[]) => toAligned(dates, pts);
      const mk = (name: string, pts: MarketPoint[], colorIdx: number, yAxisIndex = 0, decimals = 0) => ({
        name,
        type: "line" as const,
        yAxisIndex,
        data: price(pts),
        showSymbol: false,
        connectNulls: true,
        lineStyle: { width: 1.8, type: "solid" as const, color: p.series[colorIdx % p.series.length] },
        itemStyle: { color: p.series[colorIdx % p.series.length] },
        emphasis: { focus: "series" as const },
        _decimals: decimals,
      });
      return {
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        grid: { top: 40, right: 76, bottom: 56, left: 64 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const arr = params as { seriesName: string; value: number | null; name: string; color: string }[];
            if (!arr.length) return "";
            const head = `<div style="margin-bottom:4px"><strong>${arr[0].name}</strong></div>`;
            const lines = arr.map((it) => {
              const isRatio = it.seriesName.includes("金银比");
              const v = it.value == null ? "—" : formatNumber(it.value, isRatio ? 1 : 0);
              const unit = isRatio ? "" : " 元/千克";
              return `<div style="display:flex;gap:8px;align-items:center"><i style="width:8px;height:8px;border-radius:2px;background:${it.color};display:inline-block"></i>${it.seriesName} <b>${v}${unit}</b></div>`;
            });
            return head + lines.join("");
          },
        },
        legend: { ...baseLegend(p), top: 0, left: 0 },
        xAxis: { type: "category", data: dates, ...baseAxis(p), boundaryGap: false },
        yAxis: [
          { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } },
          { type: "value", scale: true, ...baseAxis(p), splitLine: { show: false }, axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } },
        ],
        dataZoom: [
          { type: "inside", throttle: 80 },
          { type: "slider", height: 18, bottom: 8, throttle: 80, ...zoomFill(p) },
        ],
        series: [
          mk("伦敦银", items.londonSilverCnyKg.points, 0),
          mk("沪银主力", items.shfeSilver.points, 4),
          mk("Ag(T+D)", items.sgeAgTd.points, 1),
          mk("金银比（右）", items.goldSilverRatio.points, 3, 1),
        ],
      };
    };
  }, [dates, items, theme]);

  const ref = useEChart(build, [dates, items], theme);

  return (
    <article className="panel market-panel">
      <div className="panel-heading">
        <div>
          <span>价格 · PRICE</span>
          <h3>白银价格与金银比</h3>
        </div>
        <div className="panel-stat">
          <small>{latestRatio?.date ?? "—"}</small>
          <strong>金银比 {latestRatio ? formatNumber(latestRatio.value, 1) : "—"}</strong>
        </div>
      </div>
      <RangePicker dates={dates} chartRef={ref} />
      <div ref={ref} className="echart chart-wrap" style={{ height: 340 }} />
    </article>
  );
}

function FundPanel({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  const fund = market.items.silverFundNav;
  const points = fund.points;
  const latest = lastPoint(points);
  const prev = points.length > 1 ? points[points.length - 2] : null;
  const delta = latest && prev ? latest.value - prev.value : null;

  const build = useMemo(() => {
    return () => {
      if (points.length < 2) return null;
      const p = getPalette(theme);
      return {
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        grid: { top: 20, right: 16, bottom: 56, left: 56 },
        tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 4)} 元`) },
        xAxis: { type: "category", data: points.map((pt) => pt.date), ...baseAxis(p), boundaryGap: false },
        yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 3) } },
        dataZoom: [
          { type: "inside", throttle: 80 },
          { type: "slider", height: 18, bottom: 8, throttle: 80, ...zoomFill(p) },
        ],
        series: [
          {
            type: "line",
            data: points.map((pt) => pt.value),
            showSymbol: false,
            connectNulls: true,
            lineStyle: { width: 2, type: "solid" as const, color: p.live },
            itemStyle: { color: p.live },
            areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [
              { offset: 0, color: "rgba(86,200,220,.20)" },
              { offset: 1, color: "rgba(86,200,220,0)" },
            ] } },
            markPoint: {
              symbol: "circle",
              symbolSize: 7,
              itemStyle: { color: p.live },
              label: { show: false },
              data: [{ coord: [points.length - 1, points[points.length - 1].value] }],
            },
          },
        ],
      };
    };
  }, [points, theme]);
  const ref = useEChart(build, [points], theme);

  return (
    <article className="panel market-panel">
      <div className="panel-heading">
        <div>
          <span>基金 · FUND</span>
          <h3>白银期货 LOF（161226.OF）净值</h3>
        </div>
        <div className="panel-stat">
          <small>{latest?.date ?? "—"}</small>
          <strong>{latest ? formatNumber(latest.value, 4) : "—"} 元</strong>
          {delta !== null && (
            <small style={{ color: delta >= 0 ? "var(--up)" : "var(--down)", fontFamily: "var(--mono)" }}>
              {delta >= 0 ? "+" : ""}{formatNumber(delta, 4)}
            </small>
          )}
        </div>
      </div>
      <RangePicker dates={points.map((p) => p.date)} chartRef={ref} />
      <div ref={ref} className="echart chart-wrap" style={{ height: 300 }} />
    </article>
  );
}
