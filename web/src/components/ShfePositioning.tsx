import { useMemo } from "react";
import type { ShfePositioningData } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";
import { formatNumber } from "../lib/format";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";

export function ShfePositioningSection({ data, theme }: { data: ShfePositioningData; theme: ThemeMode }) {
  return (
    <section className="section-block" id="shfe-positioning">
      <SectionHeading
        index="06a"
        title="上期所持仓"
        desc={`Project-004 跨项目数据 · 最新 ${data.asOfDate} · SHFE ${data.quality.shfeTradingDays} 个交易日`}
        id="shfe-positioning"
      />
      <article className="panel chart-panel positioning-summary-panel">
        <div className="panel-heading">
          <div>
            <span>SHFE · MEMBER STRUCTURE</span>
            <h3>白银会员持仓结构</h3>
          </div>
          <div className="panel-stat">
            <small>agall 品种汇总</small>
            <strong>{data.asOfDate}</strong>
          </div>
        </div>
        <PositioningSummary rows={data.summary} />
      </article>
      <div className="positioning-chart-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>SHFE · NON-FUTURES MEMBERS</span>
              <h3>非期货公司会员多空趋势</h3>
            </div>
            <div className="panel-stat"><small>净持仓 = 持买 − 持卖</small><strong>单位：手</strong></div>
          </div>
          <NonFuturesTrend data={data} theme={theme} />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>SHFE × SGE · COMPARABLE TONS</span>
              <h3>国内白银持仓综合趋势</h3>
            </div>
            <div className="panel-stat"><small>共同交易日 {data.quality.commonTradingDays}</small><strong>统一单位：吨</strong></div>
          </div>
          <CombinedTrend data={data} theme={theme} />
        </article>
      </div>
      <p className="chart-note">
        口径：SHFE 非期货公司会员持买/持卖按 1 手=15 千克换算；SGE Ag(T+D) 市场持仓按 1 手=1 千克换算；综合趋势仅保留两市场共同交易日。
      </p>
    </section>
  );
}

function PositioningSummary({ rows }: { rows: ShfePositioningData["summary"] }) {
  return (
    <div className="positioning-table-wrap">
      <table className="positioning-table">
        <thead><tr><th>会员类别</th><th>持买单量</th><th>日增减</th><th>持卖单量</th><th>日增减</th><th>净持仓</th></tr></thead>
        <tbody>
          {rows.map((row) => {
            const net = row.long - row.short;
            return (
              <tr key={row.category}>
                <td>{row.category}</td>
                <td>{formatNumber(row.long, 0)}</td>
                <td className={tone(row.longChange)}>{signed(row.longChange)}</td>
                <td>{formatNumber(row.short, 0)}</td>
                <td className={tone(row.shortChange)}>{signed(row.shortChange)}</td>
                <td className={tone(net)}>{signed(net)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function NonFuturesTrend({ data, theme }: { data: ShfePositioningData; theme: ThemeMode }) {
  const build = useMemo(() => () => {
    const p = getPalette(theme);
    const trend = data.nonFuturesTrend;
    return {
      animationDuration: 400,
      grid: { top: 42, right: 66, bottom: 54, left: 70 },
      tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: number) => `${formatNumber(v, 0)} 手` },
      legend: { ...baseLegend(p), top: 0, left: 0 },
      xAxis: { type: "category", data: trend.dates, ...baseAxis(p), boundaryGap: false },
      yAxis: { type: "value", ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } },
      dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],
      series: [
        lineSeries("持买单量", trend.longLots, p.up),
        lineSeries("持卖单量", trend.shortLots, p.down),
        { ...lineSeries("净持仓", trend.netLots, p.gold), lineStyle: { width: 1.5, color: p.gold, type: "dashed" }, markLine: { silent: true, symbol: "none", label: { show: false }, lineStyle: { color: p.edge, width: 1 }, data: [{ yAxis: 0 }] } },
      ],
    };
  }, [data, theme]);
  const ref = useEChart(build, [data], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 360 }} />;
}

function CombinedTrend({ data, theme }: { data: ShfePositioningData; theme: ThemeMode }) {
  const build = useMemo(() => () => {
    const p = getPalette(theme);
    const trend = data.combinedTrend;
    return {
      animationDuration: 400,
      grid: { top: 42, right: 66, bottom: 54, left: 70 },
      tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: number) => `${formatNumber(v, 1)} 吨` },
      legend: { ...baseLegend(p), top: 0, left: 0 },
      xAxis: { type: "category", data: trend.dates, ...baseAxis(p), boundaryGap: false },
      yAxis: { type: "value", ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } },
      dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],
      series: [
        lineSeries("SHFE 持买", trend.shfeLongTons, p.up),
        lineSeries("SHFE 持卖", trend.shfeShortTons, p.down),
        { ...lineSeries("SGE Ag(T+D)", trend.sgeOpenInterestTons, p.live), lineStyle: { width: 1.8, color: p.live, type: "dashed" } },
      ],
    };
  }, [data, theme]);
  const ref = useEChart(build, [data], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 360 }} />;
}

function lineSeries(name: string, values: number[], color: string) {
  return { name, type: "line" as const, data: values, showSymbol: false, connectNulls: true, smooth: 0.12, lineStyle: { width: 1.8, color }, itemStyle: { color } };
}

function tone(value: number) { return value > 0 ? "val-up" : value < 0 ? "val-down" : ""; }
function signed(value: number) { return `${value > 0 ? "+" : ""}${formatNumber(value, 0)}`; }
