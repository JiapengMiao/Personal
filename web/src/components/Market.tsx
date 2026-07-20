import { useMemo, useState } from "react";
import type { MarketData, MarketPoint } from "../lib/types";
import { baseAxis, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { DeltaTag, SectionHeading } from "./shared";
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

type TabKey = "londonSilver" | "shfeSilver" | "sgeAgTd" | "goldSilverRatio";

function PricePanel({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  const [tab, setTab] = useState<TabKey>("londonSilver");
  const items = market.items;
  const tabs: { key: TabKey; label: string; unit: string; decimals: number }[] = [
    { key: "londonSilver", label: "伦敦银 元/千克", unit: items.londonSilverCnyKg.unit, decimals: 0 },
    { key: "shfeSilver", label: "沪银主力 元/千克", unit: items.shfeSilver.unit, decimals: 0 },
    { key: "sgeAgTd", label: "Ag(T+D) 元/千克", unit: items.sgeAgTd.unit, decimals: 0 },
    { key: "goldSilverRatio", label: "金银比", unit: "", decimals: 1 },
  ];
  const active = tabs.find((t) => t.key === tab)!;

  const points: MarketPoint[] = useMemo(() => {
    if (tab === "londonSilver") return items.londonSilverCnyKg.points;
    if (tab === "shfeSilver") return items.shfeSilver.points;
    if (tab === "sgeAgTd") return items.sgeAgTd.points;
    return items.goldSilverRatio.points;
  }, [tab, items]);

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
        grid: { top: 16, right: 14, bottom: 56, left: 58 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          valueFormatter: (v: unknown) => formatNumber(Number(v), active.decimals),
        },
        xAxis: { type: "category", data: points.map((pt) => pt.date), ...baseAxis(p), boundaryGap: false },
        yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, active.decimals) } },
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
            lineStyle: { width: 2, type: "solid" as const, color: p.gold },
            itemStyle: { color: p.gold },
            areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [
              { offset: 0, color: theme === "light" ? "rgba(154,109,18,.16)" : "rgba(217,164,65,.22)" },
              { offset: 1, color: "rgba(217,164,65,0)" },
            ] } },
            markPoint: {
              symbol: "circle",
              symbolSize: 7,
              itemStyle: { color: p.goldBright },
              label: { show: false },
              data: [{ coord: [points.length - 1, points[points.length - 1].value] }],
            },
          },
        ],
      };
    };
  }, [points, active.decimals, theme]);
  const ref = useEChart(build, [points, active.decimals], theme);

  return (
    <article className="panel market-panel">
      <div className="panel-heading">
        <div>
          <span>价格 · PRICE</span>
          <h3>白银价格</h3>
        </div>
        <div className="panel-stat">
          <small>{latest?.date ?? "—"}</small>
          <strong>{latest ? `${formatNumber(latest.value, active.decimals)}${active.unit ? ` ${active.unit}` : ""}` : "—"}</strong>
          <DeltaTag delta={delta} decimals={active.decimals} unit={active.unit} />
        </div>
      </div>
      <div className="tab-row" role="tablist" aria-label="价格序列切换">
        {tabs.map((t) => (
          <button key={t.key} role="tab" aria-selected={tab === t.key} className={tab === t.key ? "active" : ""} onClick={() => setTab(t.key)}>
            {t.label}
          </button>
        ))}
      </div>
      <RangePicker dates={points.map((p) => p.date)} chartRef={ref} />
      <div ref={ref} className="echart chart-wrap" style={{ height: 320 }} />
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
          <DeltaTag delta={delta} decimals={4} unit="元" />
        </div>
      </div>
      <RangePicker dates={points.map((p) => p.date)} chartRef={ref} />
      <div ref={ref} className="echart chart-wrap" style={{ height: 300 }} />
    </article>
  );
}
