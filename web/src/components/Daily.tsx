import { useMemo, useState } from "react";
import type { DailyData } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, echarts, getPalette, hexToRgba, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { ffill, formatNumber, lastNonNull } from "../lib/format";

// ——— 04 库存与递延 ———
export function DailySection({ daily, theme }: { daily: DailyData; theme: ThemeMode }) {
  return (
    <section className="section-block" id="daily">
      <SectionHeading index="04" title="递延费与库存 · 日频" desc="递延费方向 / 国内库存 / 海外库存 / ETF（单位：吨）" id="daily" />
      <div className="stack-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>递延费 · DEFERRED</span>
              <h3>金交所递延费支付方向</h3>
            </div>
            <div className="panel-stat">
              <small>最新方向</small>
              <strong>{deferredLabel(lastNonNull(daily.series.deferredDirection))}</strong>
            </div>
          </div>
          <DeferredChart daily={daily} theme={theme} />
          <p className="chart-note">青带 = 空付多（2，交货压力大，偏空） · 红带 = 多付空（1，收货意愿强，偏多） · 方向状态持续到下次公布，节假日沿用前值</p>
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>国内 · DOMESTIC</span>
              <h3>国内库存</h3>
            </div>
            <div className="panel-stat">
              <small>国内合计</small>
              <strong>{fmtT(lastNonNull(daily.series.domesticInvT))}</strong>
            </div>
          </div>
          <MultiLineChart
            theme={theme}
            dates={daily.dates}
            series={[
              { name: "上期所库存", data: daily.series.shfeInvT, colorIdx: 0 },
              { name: "上金所库存", data: daily.series.sgeInvT, colorIdx: 1 },
            ]}
            height={320}
            zoom
            markLatest
          />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>美国 · US</span>
              <h3>COMEX 库存 / 注册仓单 / PSLV</h3>
            </div>
            <div className="panel-stat">
              <small>COMEX 最新</small>
              <strong>{fmtT(lastNonNull(daily.series.comexInvT))}</strong>
            </div>
          </div>
          <MultiLineChart
            theme={theme}
            dates={daily.dates}
            series={[
              { name: "COMEX 库存", data: daily.series.comexInvT, colorIdx: 0, width: 2 },
              { name: "COMEX 注册仓单", data: daily.series.comexWarrantT, colorIdx: 1, width: 2 },
              { name: "PSLV 持仓", data: daily.series.etfPSLV, colorIdx: 2, width: 2 },
            ]}
            height={320}
            zoom
            connectNulls={false}
          />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>欧洲 · EU/UK</span>
              <h3>LBMA 库存 / 英国 ETF / SLV</h3>
            </div>
            <div className="panel-stat">
              <small>LBMA（日频估算）最新</small>
              <strong>{fmtT(lastNonNull(daily.series.lbmaDailyT))}</strong>
            </div>
          </div>
          <MultiLineChart
            theme={theme}
            dates={daily.dates}
            series={[
              { name: "LBMA 库存（日频）", data: daily.series.lbmaDailyT, colorIdx: 0 },
              { name: "英国 ETF 合计", data: daily.series.etfUKSum, colorIdx: 1 },
              { name: "SLV 持仓", data: daily.series.etfSLV, colorIdx: 2 },
            ]}
            height={320}
            zoom
            connectNulls
          />
        </article>
      </div>
    </section>
  );
}

function fmtT(v: number | null): string {
  return v === null ? "—" : `${formatNumber(v)} 吨`;
}

function deferredLabel(v: number | null): string {
  if (v === 1) return "多付空 (1)";
  if (v === 2) return "空付多 (2)";
  return "—";
}

function DeferredChart({ daily, theme }: { daily: DailyData; theme: ThemeMode }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      // 前端 ffill：方向状态持续到下次公布，节假日沿用前值（头部 null 保留）
      const filled = ffill(daily.series.deferredDirection);
      const bandAlpha = theme === "light" ? 0.16 : 0.12;
      // 按连续段生成区间色带
      const bands: [{ itemStyle: { color: string }; xAxis: string }, { xAxis: string }][] = [];
      let runStart = -1;
      let runVal: number | null = null;
      for (let i = 0; i <= filled.length; i += 1) {
        const v = i < filled.length ? filled[i] : null;
        if (v !== runVal) {
          if (runVal !== null && runStart >= 0) {
            const color = runVal === 1 ? hexToRgba(p.down, bandAlpha) : hexToRgba(p.live, bandAlpha);
            bands.push([{ itemStyle: { color }, xAxis: daily.dates[runStart] }, { xAxis: daily.dates[i - 1] }]);
          }
          runStart = i;
          runVal = v;
        }
      }
      // 默认缩放起点：从首个有效值开始，避免 1993–2009 无数据死区
      const n = filled.length;
      let firstIdx = 0;
      for (let i = 0; i < n; i += 1) { if (filled[i] !== null && filled[i] !== undefined) { firstIdx = i; break; } }
      const zoomStart = n > 1 ? Math.max(0, (firstIdx / (n - 1)) * 100) : 0;
      return {
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        grid: { top: 16, right: 16, bottom: 52, left: 72 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const arr = params as { name: string; value: number | null }[];
            const item = arr[0];
            if (!item) return "";
            const v = item.value;
            const label = v === 1 ? "多付空（1）" : v === 2 ? "空付多（2）" : "无数据";
            return `<div><strong>${item.name}</strong></div><div>${label}</div>`;
          },
        },
        xAxis: { type: "category", data: daily.dates, ...baseAxis(p), boundaryGap: false },
        yAxis: {
          type: "value",
          min: 0.5,
          max: 2.5,
          interval: 1,
          ...baseAxis(p),
          axisLabel: {
            ...baseAxis(p).axisLabel,
            formatter: (v: number) => (v === 1 ? "1 多付空" : v === 2 ? "2 空付多" : ""),
          },
          splitLine: { show: false },
        },
        dataZoom: [
          { type: "inside", throttle: 80, start: zoomStart, end: 100 },
          { type: "slider", height: 18, bottom: 8, throttle: 80, start: zoomStart, end: 100, ...zoomFill(p) },
        ],
        series: [
          {
            type: "line",
            step: "end",
            data: filled,
            connectNulls: false,
            showSymbol: false,
            lineStyle: { width: 1.4, color: p.gold },
            itemStyle: { color: p.gold },
            markArea: {
              silent: true,
              data: bands,
            },
          },
        ],
      };
    };
  }, [daily, theme]);
  const ref = useEChart(build, [daily], theme);
  return (
    <>
      <RangePicker dates={daily.dates} chartRef={ref} />
      <div ref={ref} className="echart chart-wrap" style={{ height: 320 }} />
    </>
  );
}

interface LineSpec {
  name: string;
  data: (number | null)[] | undefined;
  colorIdx: number;
  width?: number;
}

export function MultiLineChart({
  theme,
  dates,
  series,
  height = 248,
  zoom = false,
  connectNulls = false,
  markLatest = false,
}: {
  theme: ThemeMode;
  dates: string[];
  series: LineSpec[];
  height?: number;
  zoom?: boolean;
  connectNulls?: boolean;
  markLatest?: boolean;
}) {
  // 默认缩放窗口：从"至少一条系列有数据"的第一个日期开始，避免大片无数据死区
  const zoomStart = useMemo(() => {
    const n = dates.length;
    if (n < 2) return 0;
    let first = n - 1;
    for (const s of series) {
      const arr = s.data ?? [];
      for (let i = 0; i < arr.length; i += 1) {
        if (arr[i] !== null && arr[i] !== undefined) { first = Math.min(first, i); break; }
      }
    }
    return Math.max(0, (first / (n - 1)) * 100);
  }, [dates, series]);

  // 数据量阈值：超过此点数才启用"仅对缩放窗口内数据降采样"，兼顾拖动帧率与缩放点密度
  const largeData = useMemo(() => dates.length > 4000, [dates]);

  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      return {
        // 拖动 dataZoom 时禁用过渡动画，避免每帧插值重算
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        grid: { top: 34, right: 16, bottom: zoom ? 52 : 30, left: 66 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          valueFormatter: (v: unknown) => (v == null ? "—" : formatNumber(Number(v))),
        },
        legend: { ...baseLegend(p), top: 0, left: 0 },
        xAxis: { type: "category", data: dates, ...baseAxis(p), boundaryGap: false },
        yAxis: {
          type: "value",
          scale: true,
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
        },
        dataZoom: zoom
          ? [
              // throttle 提高到 80ms：拖动期间每秒最多触发 12 次完整重绘
              { type: "inside", throttle: 80, start: zoomStart, end: 100 },
              { type: "slider", height: 18, bottom: 8, throttle: 80, start: zoomStart, end: 100, ...zoomFill(p) },
            ]
          : undefined,
        series: series.map((s) => ({
          name: s.name,
          type: "line" as const,
          data: s.data ?? [],
          showSymbol: false,
          connectNulls,
          lineStyle: { width: s.width ?? 1.8, type: "solid" as const, color: p.series[s.colorIdx % p.series.length] },
          itemStyle: { color: p.series[s.colorIdx % p.series.length] },
          markPoint: markLatest
            ? (() => {
                const arr = s.data ?? [];
                for (let i = arr.length - 1; i >= 0; i -= 1) {
                  if (arr[i] !== null && arr[i] !== undefined) {
                    return {
                      symbol: "circle",
                      symbolSize: 7,
                      itemStyle: { color: p.series[s.colorIdx % p.series.length] },
                      label: { show: true, formatter: formatNumber(arr[i] as number, 0), color: p.goldBright, fontFamily: "JetBrains Mono", fontSize: 11, offset: [0, -14] },
                      data: [{ coord: [i, arr[i]] }],
                    };
                  }
                }
                return undefined;
              })()
            : undefined,
        })),
      };
    };
  }, [theme, dates, series, zoom, connectNulls, markLatest, zoomStart, largeData]);
  const chartRef = useEChart(build, [theme, dates, series, zoom, connectNulls, markLatest, zoomStart, largeData], theme);
  return (
    <>
      {zoom && <RangePicker dates={dates} chartRef={chartRef} />}
      <div ref={chartRef} className="echart chart-wrap" style={{ height }} />
    </>
  );
}

/** 日期区间选择器：通过 ref 拿到 ECharts 实例，dispatchAction 精确设定 dataZoom 窗口 */
export function RangePicker({ dates, chartRef }: { dates: string[]; chartRef: React.RefObject<HTMLDivElement | null> }) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const min = dates[0] ?? "";
  const max = dates[dates.length - 1] ?? "";

  const apply = () => {
    if (!start || !end) return;
    const el = chartRef.current;
    if (!el) return;
    const inst = echarts.getInstanceByDom(el);
    if (!inst) return;
    inst.dispatchAction({ type: "dataZoom", startValue: start, endValue: end });
  };

  return (
    <div className="range-picker">
      <label>
        起始 <input type="date" value={start} min={min} max={max} onChange={(e) => setStart(e.target.value)} />
      </label>
      <span className="range-sep">—</span>
      <label>
        截止 <input type="date" value={end} min={min} max={max} onChange={(e) => setEnd(e.target.value)} />
      </label>
      <button type="button" onClick={apply} disabled={!start || !end}>应用</button>
    </div>
  );
}

