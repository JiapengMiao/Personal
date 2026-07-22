import { useMemo, useState } from "react";
import type { PpWarehouseData, PpWarehouseMetal } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";
import { formatNumber } from "../lib/format";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";

export function PpWarehouseSection({ data, theme }: { data: PpWarehouseData; theme: ThemeMode }) {
  const [metalKey, setMetalKey] = useState<"pt" | "pd">("pt");
  const metal = data.metals[metalKey];
  return (
    <section className="section-block" id="pp-warehouse">
      <SectionHeading index="02" title="铂钯仓单" desc={`广期所仓单 · Project-005 跨项目数据 · 截至 ${data.asOfDate}`} id="pp-warehouse" />
      <article className="panel chart-panel">
        <div className="panel-heading">
          <div><span>GFEX · WARRANTS</span><h3>{metal.label}仓单结构与日度变化</h3></div>
          <div className="lhb-tabs" role="tablist" aria-label="铂钯仓单品种切换">
            {(["pt", "pd"] as const).map((key) => (
              <button key={key} type="button" role="tab" aria-selected={metalKey === key} className={`lhb-tab${metalKey === key ? " active" : ""}`} onClick={() => setMetalKey(key)}>
                {key === "pt" ? "铂金" : "钯金"}
              </button>
            ))}
          </div>
        </div>
        <WarehouseStats metal={metal} />
        <WarehouseTrend metal={metal} theme={theme} />
      </article>
      <article className="panel chart-panel pp-location-panel">
        <div className="panel-heading">
          <div><span>LATEST LOCATIONS · {metal.symbol}</span><h3>{metal.latest.date} 仓单分布</h3></div>
          <div className="panel-stat"><small>仓库明细 {metal.locations.length} 个</small><strong>合计 {formatNumber(metal.latest.totalKg, 0)} 千克</strong></div>
        </div>
        <div className="pp-location-wrap">
          <table className="pp-location-table">
            <thead><tr><th>仓库/厂库</th><th>类型</th><th>今日仓单</th><th>注册</th><th>注销</th><th>增减</th></tr></thead>
            <tbody>
              {metal.locations.map((row) => (
                <tr key={row.code}>
                  <td>{row.name}</td><td><span className={`pp-type ${row.type === "仓库" ? "warehouse" : "factory"}`}>{row.type}</span></td>
                  <td>{formatNumber(row.quantityKg, 0)}</td><td>{formatNumber(row.registeredKg, 0)}</td><td>{formatNumber(row.cancelledKg, 0)}</td>
                  <td className={tone(row.changeKg)}>{signed(row.changeKg)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
      <p className="chart-note">单位：千克。逐行满足“昨日仓单 + 今日注册 − 今日注销 = 今日仓单”；仓库/厂库分类沿用 Project-005 的品种专属名单。</p>
    </section>
  );
}

function WarehouseStats({ metal }: { metal: PpWarehouseMetal }) {
  const items = [
    ["仓单总量", metal.latest.totalKg, ""], ["仓库", metal.latest.warehouseKg, ""], ["厂库", metal.latest.factoryKg, ""],
    ["今日注册", metal.latest.registeredKg, ""], ["今日注销", metal.latest.cancelledKg, ""], ["净增减", metal.latest.netChangeKg, tone(metal.latest.netChangeKg)],
  ] as const;
  return <div className="pp-stat-grid">{items.map(([label, value, cls]) => <div key={label}><span>{label}</span><strong className={cls}>{label === "净增减" ? signed(value) : formatNumber(value, 0)}</strong><small>千克</small></div>)}</div>;
}

function WarehouseTrend({ metal, theme }: { metal: PpWarehouseMetal; theme: ThemeMode }) {
  const build = useMemo(() => () => {
    const p = getPalette(theme);
    return {
      animationDuration: 400,
      grid: { top: 42, right: 66, bottom: 54, left: 70 },
      tooltip: { trigger: "axis", ...baseTooltip(p), valueFormatter: (v: number) => `${formatNumber(v, 0)} 千克` },
      legend: { ...baseLegend(p), top: 0, left: 0 },
      xAxis: { type: "category", data: metal.dates, ...baseAxis(p), boundaryGap: false },
      yAxis: { type: "value", ...baseAxis(p), axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) } },
      dataZoom: [{ type: "inside", throttle: 40 }, { type: "slider", height: 18, bottom: 8, ...zoomFill(p) }],
      series: [
        line("仓库", metal.warehouseKg, p.up),
        line("厂库", metal.factoryKg, p.down),
        { ...line("合计", metal.totalKg, p.gold), lineStyle: { width: 2, color: p.gold, type: "dashed" } },
      ],
    };
  }, [metal, theme]);
  const ref = useEChart(build, [metal], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 380 }} />;
}

function line(name: string, values: number[], color: string) {
  return { name, type: "line" as const, data: values, showSymbol: false, smooth: 0.12, lineStyle: { width: 1.8, color }, itemStyle: { color } };
}
function tone(value: number) { return value > 0 ? "val-up" : value < 0 ? "val-down" : ""; }
function signed(value: number) { return `${value > 0 ? "+" : ""}${formatNumber(value, 0)}`; }
