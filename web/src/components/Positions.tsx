import { useMemo, useState } from "react";
import type { CurveData, DailyData, MetalVirtualRatioData } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, getPalette, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { formatNumber } from "../lib/format";

// ——— 05 持仓量与虚实比 ———
export function PositionsSection({
  positions,
  virtualRatio,
  metalVirtualRatio,
  theme,
}: {
  positions: CurveData;
  virtualRatio: CurveData;
  metalVirtualRatio: MetalVirtualRatioData;
  theme: ThemeMode;
}) {
  const [ratioMetal, setRatioMetal] = useState<"ag" | "pt" | "pd">("ag");
  const ratioData = ratioMetal === "ag" ? virtualRatio : metalVirtualRatio.metals[ratioMetal];
  const ratioMeta = {
    ag: { label: "白银", title: "白银到期前虚实比（倍）", multiplier: 15, window: 90 },
    pt: { label: "铂金", title: "铂金到期前虚实比（倍）", multiplier: 1, window: 120 },
    pd: { label: "钯金", title: "钯金到期前虚实比（倍）", multiplier: 1, window: 120 },
  }[ratioMetal];
  return (
    <section className="section-block" id="positions">
      <SectionHeading index="03" title="持仓量与虚实比" desc="白银持仓，以及白银/铂金/钯金分合约虚实比走势" id="positions" />
      <div className="stack-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>持仓 · OPEN INTEREST</span>
              <h3>到期前持仓量（手）</h3>
            </div>
          </div>
          <CurveChart data={positions} theme={theme} decimals={0} unit="手" />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>虚实比 · RATIO</span>
              <h3>{ratioMeta.title}</h3>
            </div>
            <div className="lhb-tabs" role="tablist" aria-label="虚实比品种切换">
              {(["ag", "pt", "pd"] as const).map((key) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={ratioMetal === key}
                  className={`lhb-tab${ratioMetal === key ? " active" : ""}`}
                  onClick={() => setRatioMetal(key)}
                >
                  {{ ag: "白银", pt: "铂金", pd: "钯金" }[key]}
                </button>
              ))}
            </div>
          </div>
          <CurveChart data={ratioData} theme={theme} decimals={ratioMetal === "ag" ? 2 : 4} unit="倍" xMin={-ratioMeta.window} />
          <p className="chart-note">
            口径：{ratioMeta.label}虚实比 = 持仓量 × {ratioMeta.multiplier} 千克 ÷ 注册仓单；横轴为距最后交易日的交易日数，展示最近 {ratioMeta.window} 个交易日
            {ratioData.asOfDate ? `；数据截至 ${ratioData.asOfDate}` : ""}。
          </p>
        </article>
      </div>
    </section>
  );
}

// ——— 白银页：白银持仓量与虚实比 ———
export function SilverPositionsSection({
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
      <SectionHeading index="03" title="持仓量与虚实比" desc="白银分合约到期前持仓量与虚实比走势" id="positions" />
      <div className="stack-grid">
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>持仓 · OPEN INTEREST</span>
              <h3>白银到期前持仓量（手）</h3>
            </div>
          </div>
          <CurveChart data={positions} theme={theme} decimals={0} unit="手" />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>虚实比 · RATIO</span>
              <h3>白银到期前虚实比（倍）</h3>
            </div>
          </div>
          <CurveChart data={virtualRatio} theme={theme} decimals={2} unit="倍" xMin={-90} />
          <p className="chart-note">
            口径：白银虚实比 = 持仓量 × 15 千克 ÷ 注册仓单；横轴为距最后交易日的交易日数，展示最近 90 个交易日
            {virtualRatio.asOfDate ? "；数据截至 " + virtualRatio.asOfDate : ""}。
          </p>
        </article>
      </div>
    </section>
  );
}

// ——— 铂钯页：铂金 / 钯金虚实比 ———
export function PpVirtualRatioSection({ metalVirtualRatio, theme }: { metalVirtualRatio: MetalVirtualRatioData; theme: ThemeMode }) {
  const [metalKey, setMetalKey] = useState<"pt" | "pd">("pt");
  const ratioData = metalVirtualRatio.metals[metalKey];
  const metalLabel = metalKey === "pt" ? "铂金" : "钯金";
  return (
    <section className="section-block" id="pp-virtual-ratio">
      <SectionHeading index="02" title="铂钯虚实比" desc="铂金 / 钯金分合约到期前虚实比走势" id="pp-virtual-ratio" />
      <article className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <span>虚实比 · RATIO</span>
            <h3>{metalLabel}到期前虚实比（倍）</h3>
          </div>
          <div className="lhb-tabs" role="tablist" aria-label="铂钯虚实比品种切换">
            {(["pt", "pd"] as const).map((key) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={metalKey === key}
                className={"lhb-tab" + (metalKey === key ? " active" : "")}
                onClick={() => setMetalKey(key)}
              >
                {key === "pt" ? "铂金" : "钯金"}
              </button>
            ))}
          </div>
        </div>
        <CurveChart data={ratioData} theme={theme} decimals={4} unit="倍" xMin={-120} />
        <p className="chart-note">
          口径：{metalLabel}虚实比 = 持仓量 × 1 千克 ÷ 注册仓单；横轴为距最后交易日的交易日数，展示最近 120 个交易日
          {ratioData.asOfDate ? "；数据截至 " + ratioData.asOfDate : ""}。
        </p>
      </article>
    </section>
  );
}

function CurveChart({
  data,
  theme,
  decimals,
  unit = "",
  xMin = -90,
}: {
  data: CurveData;
  theme: ThemeMode;
  decimals: number;
  unit?: string;
  xMin?: number;
}) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const expiryMap = new Map(data.contracts.map((c) => [c.code, c.expiry]));
      return {
        animationDuration: 400,
        grid: { top: 40, right: 30, bottom: 30, left: 66 },
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
          min: xMin,
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
          // 尾端读数：仅未到期合约（折线停在负 x；已到期者延伸到 0 归零，不叠标签以免在 x=0 挤成一团）
          const halo = theme === "light" ? "#ffffff" : "#0a101b";
          const tail =
            lastPt && lastPt[0] < 0
              ? {
                  code: c.code,
                  val: formatNumber(lastPt[1], decimals),
                  days: Math.abs(Math.round(lastPt[0])),
                  coord: lastPt as [number, number],
                }
              : null;
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
            markPoint: tail
              ? {
                  symbol: "circle",
                  symbolSize: 6,
                  itemStyle: { color, borderColor: halo, borderWidth: 1.5 },
                  label: {
                    show: true,
                    position: tail.days <= 12 ? ("left" as const) : ("right" as const),
                    distance: 7,
                    formatter: `{c|${tail.code}}  {v|${tail.val}${unit}}\n{d|距到期 ${tail.days} 交易日}`,
                    backgroundColor: theme === "light" ? "rgba(255,255,255,0.92)" : "rgba(10,16,27,0.9)",
                    borderColor: color,
                    borderWidth: 1,
                    borderRadius: 5,
                    padding: [5, 8],
                    fontFamily: "JetBrains Mono, monospace",
                    lineHeight: 14,
                    rich: {
                      c: { color, fontSize: 11, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" },
                      v: { color: p.text, fontSize: 11, fontWeight: 700, fontFamily: "JetBrains Mono, monospace" },
                      d: { color: p.sub, fontSize: 9.5, fontFamily: "JetBrains Mono, monospace" },
                    },
                  },
                  data: [{ coord: tail.coord }],
                }
              : undefined,
          };
        }),
      };
    };
  }, [data, theme, decimals, unit, xMin]);
  const ref = useEChart(build, [data, decimals, unit, xMin], theme);
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
      <SectionHeading index="04" title="COMEX 头寸" desc="非商业净头寸（周频）与伦敦银现货对照" id="comex" />
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
