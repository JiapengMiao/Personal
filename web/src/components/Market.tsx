import { useMemo, useState } from "react";
import type { MarketData, MarketPoint } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { DeltaTag, SectionHeading } from "./shared";
import { formatNumber, formatTradeTime, lastPoint } from "../lib/format";

// ——— 03 市场脉搏 ———
export function MarketSection({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  return (
    <section className="section-block" id="market">
      <SectionHeading index="03" title="市场脉搏 · 日频" desc="伦敦现货 / 沪银 / 上金所 / 金银比 / 白银基金" id="market" />
      <div className="stack-grid">
        <PricePanel market={market} theme={theme} />
        <FundPanel market={market} theme={theme} />
      </div>
    </section>
  );
}

type PriceTabKey = "london" | "shfe" | "ag9999" | "ratio";

function PricePanel({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  const [tab, setTab] = useState<PriceTabKey>("london");
  const items = market.items;
  const tabs: { key: PriceTabKey; label: string; unit: string; decimals: number }[] = [
    { key: "london", label: "伦敦银 USD/盎司", unit: items.londonSilverUsd.unit, decimals: 2 },
    { key: "shfe", label: "沪银主力 元/千克", unit: items.agFuturesClose.unit, decimals: 0 },
    { key: "ag9999", label: "Ag99.99", unit: items.sgeAg9999Close.unit, decimals: 0 },
    { key: "ratio", label: "金银比", unit: "", decimals: 1 },
  ];
  const active = tabs.find((t) => t.key === tab)!;

  const points: MarketPoint[] = useMemo(() => {
    if (tab === "london") return items.londonSilverUsd.points;
    if (tab === "shfe") return items.agFuturesClose.points.map((p) => ({ date: p.date, value: p.close }));
    if (tab === "ag9999") return items.sgeAg9999Close.points;
    return items.goldSilverRatio.points;
  }, [tab, items]);

  const latest = lastPoint(points);
  const prev = points.length > 1 ? points[points.length - 2] : null;
  const delta = latest && prev ? latest.value - prev.value : null;

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
      {tab === "ag9999" && items.sgeAgTdLatest.snapshot && (
        <div className="sge-snapshot">
          <span className="sge-chip">Ag(T+D) {formatNumber(items.sgeAgTdLatest.snapshot.price, 0)} 元/千克</span>
          <span className="sge-time">快照 {formatTradeTime(items.sgeAgTdLatest.snapshot.tradeTime)} · 仅最新价无序列</span>
        </div>
      )}
      <PriceChart points={points} decimals={active.decimals} isRatio={tab === "ratio"} theme={theme} />
      {tab === "ratio" && <RatioNote points={points} />}
    </article>
  );
}

function PriceChart({ points, decimals, isRatio, theme }: { points: MarketPoint[]; decimals: number; isRatio: boolean; theme: ThemeMode }) {
  const build = useMemo(() => {
    return () => {
      if (points.length < 2) return null;
      const p = getPalette(theme);
      const values = points.map((pt) => pt.value);
      const mean = values.reduce((a, b) => a + b, 0) / values.length;
      const markLineData = isRatio
        ? [
            { yAxis: mean, label: { show: true, formatter: `均值 ${formatNumber(mean, 1)}`, color: p.weak, fontFamily: "JetBrains Mono" }, lineStyle: { type: "dashed" as const, color: p.silver } },
          ]
        : [];
      return {
        animationDuration: 400,
        grid: { top: 16, right: 14, bottom: 56, left: 58 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          valueFormatter: (v: unknown) => formatNumber(Number(v), decimals),
        },
        xAxis: { type: "category", data: points.map((pt) => pt.date), ...baseAxis(p), boundaryGap: false },
        yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, decimals) } },
        dataZoom: [
          { type: "inside", throttle: 40 },
          { type: "slider", height: 18, bottom: 8, ...zoomFill(p) },
        ],
        series: [
          {
            type: "line",
            data: values,
            showSymbol: false,
            lineStyle: { width: 2, color: p.gold },
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
              data: [{ coord: [points.length - 1, values[values.length - 1]] }],
            },
            markLine: markLineData.length
              ? { silent: true, symbol: "none", data: markLineData }
              : undefined,
          },
        ],
      };
    };
  }, [points, decimals, isRatio, theme]);
  const ref = useEChart(build, [points, decimals, isRatio], theme);
  if (points.length < 2) return <p className="history-empty">序列数据不足，等待下一次取数。</p>;
  return <div ref={ref} className="echart chart-wrap" style={{ height: 320 }} />;
}

function RatioNote({ points }: { points: MarketPoint[] }) {
  if (points.length === 0) return null;
  const values = points.map((pt) => pt.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const current = values[values.length - 1];
  const position = max > min ? (current - min) / (max - min) : 0.5;
  const zone = position > 0.66 ? "高位" : position < 0.33 ? "低位" : "中位";
  return (
    <p className="chart-note">
      金银比 {formatNumber(current)}：区间 {formatNumber(min)}–{formatNumber(max)}，当前处于{zone}；比值走高代表白银相对黄金偏弱。
    </p>
  );
}

function FundPanel({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  const fund = market.items.silverFund;
  const points = fund.points;
  const latest = lastPoint(points);
  const prev = points.length > 1 ? points[points.length - 2] : null;
  const delta = latest && prev ? latest.value - prev.value : null;

  const build = useMemo(() => {
    return () => {
      if (points.length < 2) return null;
      const p = getPalette(theme);
      return {
        animationDuration: 400,
        grid: { top: 16, right: 14, bottom: 56, left: 52 },
        tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => formatNumber(Number(v), 4) },
        xAxis: { type: "category", data: points.map((pt) => pt.date), ...baseAxis(p), boundaryGap: false },
        yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 2) } },
        dataZoom: [
          { type: "inside", throttle: 40 },
          { type: "slider", height: 18, bottom: 8, ...zoomFill(p) },
        ],
        series: [
          {
            type: "line",
            data: points.map((pt) => pt.value),
            showSymbol: false,
            lineStyle: { width: 2, color: p.live },
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
          <h3>白银期货 LOF</h3>
        </div>
        <div className="panel-stat">
          <small>{latest?.date ?? "—"}</small>
          <strong>{latest ? formatNumber(latest.value, 4) : "—"} 元</strong>
          <DeltaTag delta={delta} decimals={4} unit="元" />
        </div>
      </div>
      <div ref={ref} className="echart chart-wrap" style={{ height: 320 }} />
      {fund.snapshot && (
        <div className="fund-meta">
          <div>
            <small>基金名称</small>
            <strong>{fund.snapshot.name}</strong>
          </div>
          <div>
            <small>最新净值</small>
            <strong>{formatNumber(fund.snapshot.nav, 4)}</strong>
          </div>
          <div>
            <small>规模（亿元）</small>
            <strong>{formatNumber(fund.snapshot.scaleYi)}</strong>
          </div>
        </div>
      )}
    </article>
  );
}