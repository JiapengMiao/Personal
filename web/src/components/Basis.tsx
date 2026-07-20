import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ImportProfitData, LeaseRatesData, SeasonalityData } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, echarts, getPalette, zoomFill, type Palette, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { formatNumber, lastNonNull } from "../lib/format";

interface WindowStats { mean: number | null; subset: number[]; }

function computeWindow(values: (number | null)[], startPct: number, endPct: number): WindowStats {
  const n = values.length;
  if (n === 0) return { mean: null, subset: [] };
  let i0 = Math.floor((Math.min(startPct, endPct) / 100) * (n - 1));
  let i1 = Math.ceil((Math.max(startPct, endPct) / 100) * (n - 1));
  i0 = Math.max(0, Math.min(n - 1, i0));
  i1 = Math.max(0, Math.min(n - 1, i1));
  const subset: number[] = [];
  for (let i = i0; i <= i1; i += 1) { const v = values[i]; if (v !== null && v !== undefined) subset.push(v); }
  const mean = subset.length ? subset.reduce((a, b) => a + b, 0) / subset.length : null;
  return { mean, subset };
}

function percentileOf(subset: number[], latest: number | null): number | null {
  if (!subset.length || latest === null) return null;
  return subset.filter((v) => v <= latest).length / subset.length;
}

function readZoomRange(chart: echarts.ECharts, ev: unknown, n: number): [number, number] {
  const batch = (ev as { batch?: { start?: number; end?: number; startValue?: number; endValue?: number }[] })?.batch?.[0];
  let start = batch?.start; let end = batch?.end;
  if ((start == null || end == null) && batch?.startValue != null && batch?.endValue != null && n > 1) {
    start = (batch.startValue / (n - 1)) * 100; end = (batch.endValue / (n - 1)) * 100;
  }
  if (start == null || end == null) {
    const dz = ((chart.getOption().dataZoom as { start?: number; end?: number }[] | undefined) ?? [])[0] ?? {};
    start = dz.start ?? 0; end = dz.end ?? 100;
  }
  return [start, end];
}

interface MinContract { code: string; label: string; points: number; }
interface MinData { times: string[]; values: number[]; }

const PRESETS = [
  { left: "AGTD", right: "AG2608", label: "AGTD-AG2608" },
  { left: "AGTD", right: "AG2609", label: "AGTD-AG2609" },
  { left: "AGTD", right: "AG2610", label: "AGTD-AG2610" },
  { left: "AG2608", right: "AG2609", label: "AG2608-AG2609" },
  { left: "AG2609", right: "AG2610", label: "AG2609-AG2610" },
  { left: "AG2610", right: "AG2611", label: "AG2610-AG2611" },
];

export function BasisSection({ theme }: { theme: ThemeMode }) {
  const [contracts, setContracts] = useState<MinContract[]>([]);
  const [leftCode, setLeftCode] = useState("AGTD");
  const [rightCode, setRightCode] = useState("AG2608");
  const [liveData, setLiveData] = useState<{ times: string[]; values: number[] } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const cacheRef = useRef(new Map<string, MinData>());
  const [profit, setProfit] = useState<ImportProfitData | null>(null);
  const [profitLoading, setProfitLoading] = useState(true);

  useEffect(() => {
    fetch("data/min_contracts.json").then(r => r.json()).then((d: { contracts: MinContract[] }) => setContracts(d.contracts)).catch(() => {});
  }, []);

  useEffect(() => {
    let cancelled = false;
    fetch("data/import_profit.json").then(r => r.json()).then((d: ImportProfitData) => { if (!cancelled) { setProfit(d); setProfitLoading(false); } }).catch(() => { if (!cancelled) setProfitLoading(false); });
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (leftCode === rightCode) { setError("左右合约不能相同"); setLoading(false); return; }
    let cancelled = false;
    setLoading(true); setError(null);
    const fetchMin = (code: string): Promise<MinData> => {
      const cached = cacheRef.current.get(code);
      if (cached) return Promise.resolve(cached);
      return fetch(`data/min_${code}.json`).then(r => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }).then((d: MinData) => { cacheRef.current.set(code, d); return d; });
    };
    Promise.all([fetchMin(leftCode), fetchMin(rightCode)]).then(([a, b]) => {
      if (cancelled) return;
      const mapB = new Map(b.times.map((t, i) => [t, b.values[i]] as const));
      const times: string[] = []; const values: number[] = [];
      for (let i = 0; i < a.times.length; i++) {
        const bv = mapB.get(a.times[i]);
        if (bv !== undefined) { times.push(a.times[i]); values.push(Math.round((a.values[i] - bv) * 10) / 10); }
      }
      setLiveData({ times, values }); setLoading(false);
    }).catch((e: Error) => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [leftCode, rightCode]);

  const pairLabel = (leftCode === "AGTD" ? "AG(T+D)" : leftCode) + "-" + (rightCode === "AGTD" ? "AG(T+D)" : rightCode);
  const activePreset = PRESETS.findIndex(p => p.left === leftCode && p.right === rightCode);

  return (
    <section className="section-block" id="basis">
      <SectionHeading index="08" title="基差与进出口盈亏" desc="分钟级基差（元/千克）与进口／出口盈亏窗口（元/千克）" id="basis" />
      <article className="panel chart-panel">
        <div className="panel-heading">
          <div><span>基差 · BASIS</span><h3>{pairLabel}</h3></div>
          <div className="panel-stat"><small>分钟级 · 非交易时段横轴压缩</small><strong>{liveData && liveData.values.length ? `最新 ${formatNumber(liveData.values[liveData.values.length - 1], 1)}` : "—"}</strong></div>
        </div>
        <div className="basis-selector">
          <label>左合约 <select value={leftCode} onChange={e => setLeftCode(e.target.value)}>{contracts.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}</select></label>
          <span className="basis-minus"> − </span>
          <label>右合约 <select value={rightCode} onChange={e => setRightCode(e.target.value)}>{contracts.map(c => <option key={c.code} value={c.code}>{c.label}</option>)}</select></label>
        </div>
        <div className="tab-row" role="tablist" aria-label="快捷预设">
          {PRESETS.map((p, i) => (
            <button key={p.label} role="tab" aria-selected={activePreset === i} className={activePreset === i ? "active" : ""} onClick={() => { setLeftCode(p.left); setRightCode(p.right); }}>{p.label}</button>
          ))}
        </div>
        {loading ? <div className="chart-loading">加载中…</div> : error ? <div className="chart-loading">加载失败：{error}</div> : liveData ? <MinuteLineChart times={liveData.times} values={liveData.values} theme={theme} height={320} colorIdx={0} /> : null}
      </article>
      <article className="panel chart-panel" style={{ marginTop: 14 }}>
        <div className="panel-heading">
          <div><span>进出口盈亏 · ARBITRAGE</span><h3>进口盈亏 / 出口盈亏</h3></div>
          <div className="panel-stat"><small>进口盈亏 &gt; 0 表示国内存在套利</small><strong>{profit ? `最新 ${formatNumber(profit.stats.importLatest, 1)}` : "—"}</strong></div>
        </div>
        {profitLoading ? <div className="chart-loading">加载进出口盈亏数据…</div> : profit ? <ProfitChart data={profit} theme={theme} /> : <div className="chart-loading">数据不可用</div>}
      </article>
    </section>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (<div className="stat-card"><small>{label}</small><strong>{value}</strong></div>);
}

function PercentileCard({ label, percentile }: { label: string; percentile: number | null }) {
  const pct = percentile === null ? null : percentile <= 1 ? percentile * 100 : percentile;
  return (<div className="stat-card"><small>{label}</small><strong>{pct === null ? "—" : `${formatNumber(pct, 0)}%`}</strong><div className="percentile-track"><div className="percentile-fill" style={{ width: pct === null ? "0%" : `${Math.min(100, Math.max(0, pct))}%` }} /></div></div>);
}

function minuteOption(p: Palette, times: string[], values: (number | null)[], colorIdx: number) {
  return {
    animationDuration: 300,
    grid: { top: 20, right: 16, bottom: 54, left: 64 },
    tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 1)} 元/千克`) },
    xAxis: { type: "category", data: times, ...baseAxis(p), boundaryGap: false, axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: string) => v.slice(5, 10), interval: Math.max(1, Math.floor(times.length / 8)) } },
    yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } },
    dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],
    series: [{ type: "line", data: values, showSymbol: false, connectNulls: false, lineStyle: { width: 1.4, color: p.series[colorIdx % p.series.length] }, itemStyle: { color: p.series[colorIdx % p.series.length] }, markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: p.edge, width: 1.2 }, data: [{ yAxis: 0 }] } }],
  };
}

function MinuteLineChart({ times, values, theme, height, colorIdx }: { times: string[]; values: number[]; theme: ThemeMode; height: number; colorIdx: number }) {
  const latest = useMemo(() => lastNonNull(values), [values]);
  const [win, setWin] = useState<WindowStats>(() => computeWindow(values, 0, 100));
  useEffect(() => { setWin(computeWindow(values, 0, 100)); }, [values, theme]);
  const onChart = useCallback((chart: echarts.ECharts) => { chart.off("datazoom"); chart.on("datazoom", (ev: unknown) => { const [start, end] = readZoomRange(chart, ev, values.length); setWin(computeWindow(values, start, end)); }); }, [values]);
  const build = useMemo(() => { return () => minuteOption(getPalette(theme), times, values, colorIdx); }, [times, values, theme, colorIdx]);
  const ref = useEChart(build, [times, values, colorIdx], theme, onChart);
  return (<>
    <div ref={ref} className="echart chart-wrap" style={{ height }} />
    <div className="stat-cards">
      <StatCard label="最新值" value={latest === null ? "—" : formatNumber(latest, 1)} />
      <StatCard label="区间均值（随缩放）" value={win.mean === null ? "—" : formatNumber(win.mean, 1)} />
      <PercentileCard label="当前百分位（随缩放）" percentile={percentileOf(win.subset, latest)} />
    </div>
  </>);
}

function ProfitChart({ data, theme }: { data: ImportProfitData; theme: ThemeMode }) {
  const impLatest = useMemo(() => lastNonNull(data.importProfit), [data]);
  const expLatest = useMemo(() => lastNonNull(data.exportProfit), [data]);
  const [range, setRange] = useState<[number, number]>([0, 100]);
  useEffect(() => { setRange([0, 100]); }, [data, theme]);
  const stats = useMemo(() => { const imp = computeWindow(data.importProfit, range[0], range[1]); const exp = computeWindow(data.exportProfit, range[0], range[1]); return { imp, exp, impPct: percentileOf(imp.subset, impLatest), expPct: percentileOf(exp.subset, expLatest) }; }, [data, range, impLatest, expLatest]);
  const onChart = useCallback((chart: echarts.ECharts) => { chart.off("datazoom"); chart.on("datazoom", (ev: unknown) => { setRange(readZoomRange(chart, ev, data.times.length)); }); }, [data]);
  const build = useMemo(() => { return () => { const p = getPalette(theme); return { animationDuration: 300, grid: { top: 36, right: 16, bottom: 54, left: 64 }, tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 1)} 元/千克`) }, legend: { ...baseLegend(p), top: 0, left: 0 }, xAxis: { type: "category", data: data.times, ...baseAxis(p), boundaryGap: false, axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: string) => v.slice(5, 10), interval: Math.max(1, Math.floor(data.times.length / 8)) } }, yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } }, dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }], series: [{ name: "进口盈亏", type: "line", data: data.importProfit, showSymbol: false, lineStyle: { width: 1.4, color: p.series[0] }, itemStyle: { color: p.series[0] } }, { name: "出口盈亏", type: "line", data: data.exportProfit, showSymbol: false, lineStyle: { width: 1.4, color: p.series[1] }, itemStyle: { color: p.series[1] } }] }; }; }, [data, theme]);
  const ref = useEChart(build, [data], theme, onChart);
  return (<>
    <div ref={ref} className="echart chart-wrap" style={{ height: 320 }} />
    <div className="stat-cards">
      <StatCard label="进口最新" value={impLatest === null ? "—" : formatNumber(impLatest, 1)} />
      <StatCard label="进口均值" value={stats.imp.mean === null ? "—" : formatNumber(stats.imp.mean, 1)} />
      <PercentileCard label="进口百分位" percentile={stats.impPct} />
      <StatCard label="出口最新" value={expLatest === null ? "—" : formatNumber(expLatest, 1)} />
      <StatCard label="出口均值" value={stats.exp.mean === null ? "—" : formatNumber(stats.exp.mean, 1)} />
      <PercentileCard label="出口百分位" percentile={stats.expPct} />
    </div>
  </>);
}

export function SeasonalitySection({ data, asOfDate, theme }: { data: SeasonalityData; asOfDate: string; theme: ThemeMode }) {
  const build = useMemo(() => { return () => { const p = getPalette(theme); const years = Object.keys(data.years); return { animationDuration: 400, grid: { top: 34, right: 16, bottom: 52, left: 58 }, tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 1)} 元/千克`) }, legend: { ...baseLegend(p), top: 0, left: 0 }, xAxis: { type: "category", data: data.dates, ...baseAxis(p), boundaryGap: false, axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: string) => v.slice(5), interval: 29 } }, yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } }, dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }], series: years.map((yr, i) => ({ name: yr, type: "line", data: data.years[yr], showSymbol: false, connectNulls: true, lineStyle: { width: 1.6, color: p.series[i % p.series.length] }, itemStyle: { color: p.series[i % p.series.length] } })) }; }; }, [data, theme]);
  const ref = useEChart(build, [data], theme);
  return (<section className="section-block" id="season"><SectionHeading index="09" title="进口盈亏季节性" desc="历年同期进口盈亏走势对比" id="season" /><article className="panel chart-panel"><div className="panel-heading"><div><span>季节性 · SEASONALITY</span><h3>进口盈亏历年对比</h3></div></div><div ref={ref} className="echart chart-wrap" style={{ height: 320 }} /></article></section>);
}

export function LeaseSection({ data, theme }: { data: LeaseRatesData; theme: ThemeMode }) {
  const build = useMemo(() => { return () => { const p = getPalette(theme); const keys = Object.keys(data.series); const labels: Record<string, string> = { m1: "1个月", m3: "3个月", m6: "6个月", m12: "12个月" }; return { animationDuration: 400, grid: { top: 34, right: 16, bottom: 52, left: 58 }, tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: unknown) => (v == null ? "—" : `${formatNumber(Number(v), 4)}%`) }, legend: { ...baseLegend(p), top: 0, left: 0 }, xAxis: { type: "category", data: data.dates, ...baseAxis(p), boundaryGap: false, axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: string) => v.slice(0, 7), interval: 29 } }, yAxis: { type: "value", scale: true, ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => `${formatNumber(v, 2)}%` } }, dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }], series: keys.map((k, i) => ({ name: labels[k] ?? k, type: "line", data: data.series[k], showSymbol: false, connectNulls: true, lineStyle: { width: 1.8, color: p.series[i % p.series.length] }, itemStyle: { color: p.series[i % p.series.length] } })) }; }; }, [data, theme]);
  const ref = useEChart(build, [data], theme);
  return (<section className="section-block" id="lease"><SectionHeading index="10" title="租借利率" desc="白银租借利率（年化%，近一年）" id="lease" /><article className="panel chart-panel"><div className="panel-heading"><div><span>租借 · LEASE RATE</span><h3>白银租借利率曲线</h3></div></div><div ref={ref} className="echart chart-wrap" style={{ height: 320 }} /></article></section>);
}
