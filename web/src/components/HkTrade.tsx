import { useEffect, useMemo, useState } from "react";
import { baseAxis, baseLegend, baseTooltip, echarts, getPalette, hexToRgba, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { formatNumber } from "../lib/format";
import { fetchData } from "../lib/data";

// ——— 07 香港白银进出口 · 月度 ———

interface HkTradeData {
  generatedAt: string;
  source: string;
  unit: string;
  asOf: string;
  months: string[];           // "YYYYMM"
  imports: number[];          // 进口（吨）
  exports: number[];          // 出口总额（吨）
  reexports: number[];        // 转口（吨）
  net: number[];              // 净流入 = 进口-出口（吨）
  importsUsdM: number[];      // 进口货值（亿美元）
  exportsUsdM: number[];      // 出口货值（亿美元）
}

/** "YYYYMM" → "YYYY-MM" */
function toMonth(m: string): string {
  return `${m.slice(0, 4)}-${m.slice(4, 6)}`;
}

export function HkTradeSection({ theme }: { theme: ThemeMode }) {
  const [data, setData] = useState<HkTradeData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData<HkTradeData>("data/hk_trade.json")
      .then((d: HkTradeData) => setData(d))
      .catch((e: Error) => setError(e.message));
  }, []);

  // 净出口 = 出口 - 进口（正=净流出，负=净流入/白银滞留）
  const netExport = useMemo(() => (data ? data.net.map((v) => -v) : []), [data]);

  // 关键统计
  const stats = useMemo(() => {
    if (!data) return null;
    const n = netExport;
    const last = n[n.length - 1];
    // 2026 年迄今
    const yIdx = data.months.findIndex((m) => m.startsWith("2026"));
    const ytd = yIdx >= 0 ? n.slice(yIdx).reduce((a, b) => a + b, 0) : 0;
    const total = n.reduce((a, b) => a + b, 0);
    // 历史峰值（最大净出口）与谷值（最大净流入）
    let peak = -Infinity, peakM = "";
    let trough = Infinity, troughM = "";
    n.forEach((v, i) => {
      if (v > peak) { peak = v; peakM = data.months[i]; }
      if (v < trough) { trough = v; troughM = data.months[i]; }
    });
    return { last, ytd, total, peak, peakM, trough, troughM };
  }, [data, netExport]);

  if (error) return null;
  if (!data || !stats) return <div className="section-block" style={{ minHeight: 60 }} />;

  const p = getPalette(theme);
  const impColor = p.live;         // 进口 青
  const expColor = p.series[7];    // 出口 银灰
  const netColor = p.gold;         // 净出口 金

  return (
    <section className="section-block" id="hktrade">
      <SectionHeading index="07" title="香港白银进出口 · 月度" desc="政府统计处 HS7106（吨）· 净出口折线 + 进出口柱状" id="hktrade" />

      <article className="panel chart-panel hk-trade-panel">
        {/* 关键指标 */}
        <div className="hk-stats">
          <div className="hk-stat">
            <small>最新月（{toMonth(data.asOf)}）净出口</small>
            <strong style={{ color: stats.last < 0 ? p.down : p.up }}>
              {stats.last >= 0 ? "+" : ""}{formatNumber(stats.last, 0)} 吨
            </strong>
            <small>{stats.last < 0 ? "白银净流入（滞留）" : "白银净流出"}</small>
          </div>
          <div className="hk-stat">
            <small>2026 年迄今累计净出口</small>
            <strong style={{ color: stats.ytd < 0 ? p.down : p.up }}>
              {stats.ytd >= 0 ? "+" : ""}{formatNumber(stats.ytd, 0)} 吨
            </strong>
            <small>{stats.ytd < 0 ? "持续净流入" : "净流出"}</small>
          </div>
          <div className="hk-stat">
            <small>历史峰值净出口</small>
            <strong>{formatNumber(stats.peak, 0)} 吨</strong>
            <small>{toMonth(stats.peakM)}</small>
          </div>
          <div className="hk-stat">
            <small>最大单月净流入</small>
            <strong style={{ color: p.down }}>{formatNumber(stats.trough, 0)} 吨</strong>
            <small>{toMonth(stats.troughM)}</small>
          </div>
        </div>

        <div className="panel-heading">
          <div>
            <span>贸易 · HK TRADE</span>
            <h3>香港月度进出口与净出口（吨）</h3>
          </div>
          <div className="panel-stat">
            <small>数据截至</small>
            <strong>{toMonth(data.asOf)}</strong>
          </div>
        </div>
        <HkTradeChart data={data} netExport={netExport} impColor={impColor} expColor={expColor} netColor={netColor} theme={theme} />
        <p className="chart-note">净出口 = 出口 − 进口：正值 = 白银净流出（转口），负值 = 白银净流入（滞留香港）· 数量为官方 6 位 HS 口径（710610+710691+710692）</p>
      </article>
    </section>
  );
}

function HkTradeChart({ data, netExport, impColor, expColor, netColor, theme }: {
  data: HkTradeData;
  netExport: number[];
  impColor: string;
  expColor: string;
  netColor: string;
  theme: ThemeMode;
}) {
  const months = useMemo(() => data.months.map(toMonth), [data]);
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      return {
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        grid: { top: 38, right: 16, bottom: 56, left: 56 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          axisPointer: { type: "shadow" as const },
          formatter: (params: unknown) => {
            const arr = params as { seriesName: string; value: number | null; name: string; color: string }[];
            if (!arr.length) return "";
            const head = `<div style="margin-bottom:4px"><strong>${arr[0].name}</strong></div>`;
            const lines = arr.map((it) => {
              const v = it.value == null ? "—" : formatNumber(it.value, 0);
              return `<div style="display:flex;gap:8px;align-items:center"><i style="width:8px;height:8px;border-radius:2px;background:${it.color};display:inline-block"></i>${it.seriesName} <b>${v} 吨</b></div>`;
            });
            return head + lines.join("");
          },
        },
        legend: { ...baseLegend(p), top: 0, left: 0 },
        xAxis: { type: "category", data: months, ...baseAxis(p), boundaryGap: true },
        yAxis: {
          type: "value",
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
        },
        dataZoom: [
          { type: "inside", throttle: 80, start: 60, end: 100 },
          { type: "slider", height: 18, bottom: 8, throttle: 80, start: 60, end: 100, ...zoomFill(p) },
        ],
        series: [
          {
            name: "进口",
            type: "bar" as const,
            data: data.imports,
            itemStyle: { color: hexToRgba(impColor, theme === "light" ? 0.55 : 0.75) },
            barGap: "10%",
            barMaxWidth: 14,
          },
          {
            name: "出口",
            type: "bar" as const,
            data: data.exports,
            itemStyle: { color: hexToRgba(expColor, theme === "light" ? 0.5 : 0.6) },
            barMaxWidth: 14,
          },
          {
            name: "净出口",
            type: "line" as const,
            data: netExport,
            showSymbol: false,
            lineStyle: { width: 2.4, type: "solid" as const, color: netColor },
            itemStyle: { color: netColor },
            markLine: {
              symbol: "none",
              silent: true,
              lineStyle: { color: p.weak, type: "dashed" as const, width: 1 },
              label: { show: false },
              data: [{ yAxis: 0 }],
            },
            markPoint: (() => {
              const last = netExport[netExport.length - 1];
              return {
                symbol: "circle",
                symbolSize: 7,
                itemStyle: { color: last < 0 ? p.down : p.up },
                label: {
                  show: true,
                  formatter: `${last < 0 ? "" : "+"}${formatNumber(last, 0)}`,
                  color: last < 0 ? p.down : p.up,
                  fontFamily: "JetBrains Mono",
                  fontSize: 11,
                  offset: [0, -14] as [number, number],
                },
                data: [{ coord: [months.length - 1, last] }],
              };
            })(),
          },
        ],
      };
    };
  }, [data, netExport, months, impColor, expColor, netColor, theme]);

  const chartRef = useEChart(build, [data, netExport, months, theme], theme);

  // 月份区间选择器
  const apply = () => {
    if (!start || !end) return;
    const el = chartRef.current;
    if (!el) return;
    const inst = echarts.getInstanceByDom(el);
    if (!inst) return;
    // "YYYY-MM" → "YYYYMM" 匹配类目值
    const s = start.replace("-", "");
    const e = end.replace("-", "");
    inst.dispatchAction({ type: "dataZoom", startValue: s, endValue: e });
  };
  const minM = toMonth(data.months[0]);
  const maxM = toMonth(data.months[data.months.length - 1]);

  return (
    <>
      <div className="range-picker">
        <label>
          起始 <input type="month" value={start} min={minM} max={maxM} onChange={(ev) => setStart(ev.target.value)} />
        </label>
        <span className="range-sep">—</span>
        <label>
          截止 <input type="month" value={end} min={minM} max={maxM} onChange={(ev) => setEnd(ev.target.value)} />
        </label>
        <button type="button" onClick={apply} disabled={!start || !end}>应用</button>
      </div>
      <div ref={chartRef} className="echart chart-wrap" style={{ height: 380 }} />
    </>
  );
}
