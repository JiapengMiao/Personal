import { useMemo } from "react";
import type { CurveData, DailyData } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { formatNumber } from "../lib/format";

// ——— 05 持仓量与虚实比 ———
export function PositionsSection({
  positions,
  virtualRatio,
  theme,
}: {
  positions: CurveData;
  virtualRatio: CurveData;
  theme: ThemeMode;
}) {
  return (
    <section className="section-block" id="positions">
      <SectionHeading index="05" title="持仓量与虚实比" desc="各合约到期日前 90 个交易日的持仓与虚实比走势" id="positions" />
      <div className="stack-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>持仓 · OPEN INTEREST</span>
              <h3>到期前持仓量（手）</h3>
            </div>
          </div>
          <CurveChart data={positions} theme={theme} decimals={0} />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>虚实比 · RATIO</span>
              <h3>到期前虚实比（倍）</h3>
            </div>
          </div>
          <CurveChart data={virtualRatio} theme={theme} decimals={2} />
          <p className="chart-note">口径：虚实比 = 持仓量 × 15 千克 ÷ 注册仓单（{virtualRatio.formula ?? "oi*15/st_stock_kg"}）；横轴为距到期日的交易日数。</p>
        </article>
      </div>
    </section>
  );
}

function CurveChart({ data, theme, decimals }: { data: CurveData; theme: ThemeMode; decimals: number }) {
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
                    formatter: `${c.code}  ${formatNumber(lastPt[1], decimals)}\n距最后交易日${Math.abs(lastPt[0])}日`,
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
  return <div ref={ref} className="echart chart-wrap" style={{ height: 360 }} />;
}

// ——— 06 COMEX 头寸 ———
export function ComexSection({ daily, theme }: { daily: DailyData; theme: ThemeMode }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const rows: { date: string; net: number; london: number | null }[] = [];
      daily.dates.forEach((d, i) => {
        const net = daily.series.comexNonCommNet?.[i];
        if (net !== null && net !== undefined) {
          rows.push({ date: d, net, london: daily.series.londonSilverUsd?.[i] ?? null });
        }
      });
      return {
        animationDuration: 400,
        grid: { top: 40, right: 74, bottom: 52, left: 70 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const arr = params as { seriesName: string; value: number | null; name: string; color: string }[];
            const head = `<div style="margin-bottom:4px"><strong>${arr[0]?.name ?? ""}</strong></div>`;
            const lines = arr.map((it) => {
              const unit = it.seriesName.includes("伦敦") ? " 美元/盎司" : " 手";
              return `<div style="display:flex;gap:8px;align-items:center"><i style="width:8px;height:8px;border-radius:2px;background:${it.color};display:inline-block"></i>${it.seriesName} <b>${it.value == null ? "—" : formatNumber(it.value, it.seriesName.includes("伦敦") ? 2 : 0)}${unit}</b></div>`;
            });
            return head + lines.join("");
          },
        },
        legend: { ...baseLegend(p), top: 0, left: 0 },
        xAxis: { type: "category", data: rows.map((r) => r.date), ...baseAxis(p), boundaryGap: true },
        yAxis: [
          {
            type: "value",
            ...baseAxis(p),
            axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
          },
          {
            type: "value",
            ...baseAxis(p),
            splitLine: { show: false },
            axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
          },
        ],
        dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],
        series: [
          {
            name: "非商业净头寸",
            type: "bar",
            data: rows.map((r) => r.net),
            itemStyle: {
              color: (params: { value: number }) => (params.value >= 0 ? p.gold : p.down),
              borderRadius: [2, 2, 0, 0],
            },
            barMaxWidth: 22,
            markLine: {
              silent: true,
              symbol: "none",
              label: { show: false },
              lineStyle: { color: p.edge, width: 1.2 },
              data: [{ yAxis: 0 }],
            },
          },
          {
            name: "伦敦银",
            type: "line",
            yAxisIndex: 1,
            data: rows.map((r) => r.london),
            showSymbol: false,
            connectNulls: true,
            lineStyle: { width: 1.8, color: p.live },
            itemStyle: { color: p.live },
          },
        ],
      };
    };
  }, [daily, theme]);
  const ref = useEChart(build, [daily], theme);

  return (
    <section className="section-block" id="comex">
      <SectionHeading index="06" title="COMEX 头寸" desc="非商业净头寸（周频）与伦敦银现货对照" id="comex" />
      <article className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <span>CFTC · POSITIONING</span>
            <h3>COMEX 白银非商业净头寸 × 伦敦银</h3>
          </div>
          <div className="panel-stat">
            <small>净头寸为基金多头减空头</small>
            <strong>周频 · 仅显示有数据的周</strong>
          </div>
        </div>
        <div ref={ref} className="echart chart-wrap" style={{ height: 360 }} />
      </article>
    </section>
  );
}