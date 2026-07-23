import { useEffect, useMemo, useState } from "react";
import { baseAxis, baseLegend, baseTooltip, getPalette, hexToRgba, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { formatNumber } from "../lib/format";
import { fetchData } from "../lib/data";

// ——— 07b 美 / 英 / 印白银贸易 · 年度（风格对齐香港贸易区块）———

interface TradeData {
  generatedAt: string;
  country?: string;
  source: string;
  unit: string;
  asOf: string;
  years: string[];
  imports: (number | null)[];
  exports: (number | null)[];
  netImport: (number | null)[];
  partialYears?: Record<string, string>;
  events?: { date: string; label: string; kind: string }[];
  disclaimer: string;
}

interface CountrySpec {
  key: string;
  file: string;
  name: string;
  code: string;
  sub: string;
}

const COUNTRIES: CountrySpec[] = [
  { key: "us", file: "data/us_trade.json", name: "美国", code: "US TRADE", sub: "USGS 银含量口径" },
  { key: "uk", file: "data/uk_trade.json", name: "英国", code: "UK TRADE", sub: "HMRC BDS HS71069100" },
  { key: "in", file: "data/india_trade.json", name: "印度", code: "IN TRADE", sub: "WSS / Comtrade 汇编" },
];

function fmtAsOf(asOf: string): string {
  if (/^\d{4}$/.test(asOf)) return asOf;
  if (/^\d{6}$/.test(asOf)) return `${asOf.slice(0, 4)}-${asOf.slice(4, 6)}`;
  return asOf;
}

export function WorldTradeSection({ theme }: { theme: ThemeMode }) {
  const [dataMap, setDataMap] = useState<Record<string, TradeData>>({});

  useEffect(() => {
    Promise.all(
      COUNTRIES.map((c) =>
        fetchData<TradeData>(c.file)
          .then((d) => [c.key, d] as const)
          .catch(() => [c.key, null] as const),
      ),
    ).then((entries) => {
      const m: Record<string, TradeData> = {};
      entries.forEach(([k, d]) => {
        if (d) m[k] = d;
      });
      setDataMap(m);
    });
  }, []);

  const loaded = COUNTRIES.filter((c) => dataMap[c.key]);
  if (!loaded.length) return null;

  return (
    <section className="section-block" id="worldtrade">
      <SectionHeading
        index="07"
        title="美英印白银贸易 · 年度"
        desc="净进口 = 进口 − 出口（正=净流入）· 美国 USGS / 英国 HMRC BDS / 印度 WSS-Comtrade"
        id="worldtrade"
      />
      {loaded.map((c) => (
        <CountryPanel key={c.key} spec={c} data={dataMap[c.key]} theme={theme} />
      ))}
    </section>
  );
}

function CountryPanel({ spec, data, theme }: { spec: CountrySpec; data: TradeData; theme: ThemeMode }) {
  const p = getPalette(theme);

  const stats = useMemo(() => {
    const n = data.years.length;
    // 最新完整年（跳过不完整年）
    const partialSet = new Set(Object.keys(data.partialYears ?? {}));
    let li = n - 1;
    while (li > 0 && partialSet.has(data.years[li])) li -= 1;
    const latestNet = data.netImport[li];
    const latestImp = data.imports[li];
    let peak = -Infinity, peakY = "";
    data.netImport.forEach((v, i) => {
      if (v != null && v > peak) { peak = v; peakY = data.years[i]; }
    });
    const partialKey = Object.keys(data.partialYears ?? {})[0];
    const partialNote = partialKey ? (data.partialYears ?? {})[partialKey] : null;
    const partialNet = partialKey ? data.netImport[data.years.indexOf(partialKey)] : null;
    return { latestNet, latestImp, latestYear: data.years[li], peak, peakY, partialKey, partialNote, partialNet };
  }, [data]);

  const impColor = p.live;
  const expColor = p.series[7];
  const netColor = p.gold;

  return (
    <article className="panel chart-panel hk-trade-panel">
      <div className="hk-stats">
        <div className="hk-stat">
          <small>{stats.latestYear} 年净进口</small>
          <strong style={{ color: (stats.latestNet ?? 0) < 0 ? p.down : p.up }}>
            {(stats.latestNet ?? 0) >= 0 ? "+" : ""}{formatNumber(stats.latestNet ?? 0, 0)} 吨
          </strong>
          <small>{(stats.latestNet ?? 0) < 0 ? "净流出 / 再出口" : "净流入"}</small>
        </div>
        <div className="hk-stat">
          <small>{stats.latestYear} 年进口</small>
          <strong>{formatNumber(stats.latestImp ?? 0, 0)} 吨</strong>
          <small>{spec.sub}</small>
        </div>
        <div className="hk-stat">
          <small>历史峰值净进口</small>
          <strong>{formatNumber(stats.peak, 0)} 吨</strong>
          <small>{stats.peakY}</small>
        </div>
        <div className="hk-stat">
          <small>{stats.partialKey ? `${stats.partialKey}* 不完整年` : "数据截至"}</small>
          {stats.partialKey ? (
            <>
              <strong style={{ color: p.gold }}>
                {(stats.partialNet ?? 0) >= 0 ? "+" : ""}{formatNumber(stats.partialNet ?? 0, 0)} 吨
              </strong>
              <small>{stats.partialNote}</small>
            </>
          ) : (
            <>
              <strong>{fmtAsOf(data.asOf)}</strong>
              <small>官方最新</small>
            </>
          )}
        </div>
      </div>

      <div className="panel-heading">
        <div>
          <span>贸易 · {spec.code}</span>
          <h3>{spec.name}年度进出口与净进口（吨）</h3>
        </div>
        <div className="panel-stat">
          <small>数据截至</small>
          <strong>{fmtAsOf(data.asOf)}</strong>
        </div>
      </div>
      <CountryChart data={data} impColor={impColor} expColor={expColor} netColor={netColor} theme={theme} />
      <p className="chart-note">{data.disclaimer}</p>
    </article>
  );
}

function CountryChart({ data, impColor, expColor, netColor, theme }: {
  data: TradeData;
  impColor: string;
  expColor: string;
  netColor: string;
  theme: ThemeMode;
}) {
  const partialSet = useMemo(() => new Set(Object.keys(data.partialYears ?? {})), [data]);
  const cats = useMemo(() => data.years.map((y) => (partialSet.has(y) ? `${y}*` : y)), [data, partialSet]);

  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const isPartial = (i: number) => partialSet.has(data.years[i]);
      const bar = (vals: (number | null)[], color: string, baseAlpha: number) =>
        vals.map((v, i) => {
          const alpha = isPartial(i) ? 0.35 : baseAlpha;
          return v == null ? null : { value: v, itemStyle: { color: hexToRgba(color, alpha) } };
        });
      const lineVals = data.netImport.map((v, i) => {
        if (v == null) return null;
        return isPartial(i)
          ? { value: v, itemStyle: { color: netColor }, symbolSize: 7, symbol: "circle" }
          : v;
      });

      const events = (data.events ?? [])
        .map((ev) => {
          const yr = ev.date.slice(0, 4);
          const idx = data.years.indexOf(yr);
          return idx >= 0 ? { xAxis: cats[idx], label: { formatter: ev.label, position: "insideEndTop" as const, fontSize: 10, color: p.sub } } : null;
        })
        .filter(Boolean) as { xAxis: string; label: object }[];

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
            const isP = arr[0].name.endsWith("*");
            const head = `<div style="margin-bottom:4px"><strong>${arr[0].name.replace("*", "")}${isP ? "（不完整年 YTD）" : ""}</strong></div>`;
            const lines = arr.map((it) => {
              const v = it.value == null ? "—" : formatNumber(it.value, 0);
              return `<div style="display:flex;gap:8px;align-items:center"><i style="width:8px;height:8px;border-radius:2px;background:${it.color};display:inline-block"></i>${it.seriesName} <b>${v} 吨</b></div>`;
            });
            return head + lines.join("");
          },
        },
        legend: { ...baseLegend(p), top: 0, left: 0 },
        xAxis: { type: "category", data: cats, ...baseAxis(p), boundaryGap: true },
        yAxis: {
          type: "value",
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
        },
        dataZoom: [
          { type: "inside", throttle: 80, start: 0, end: 100 },
          { type: "slider", height: 18, bottom: 8, throttle: 80, start: 0, end: 100, ...zoomFill(p) },
        ],
        series: [
          {
            name: "进口",
            type: "bar" as const,
            data: bar(data.imports, impColor, theme === "light" ? 0.55 : 0.75),
            barGap: "10%",
            barMaxWidth: 22,
          },
          {
            name: "出口",
            type: "bar" as const,
            data: bar(data.exports, expColor, theme === "light" ? 0.5 : 0.6),
            barMaxWidth: 22,
          },
          {
            name: "净进口",
            type: "line" as const,
            data: lineVals,
            showSymbol: false,
            connectNulls: true,
            lineStyle: { width: 2.4, type: "solid" as const, color: netColor },
            itemStyle: { color: netColor },
            markLine: {
              symbol: "none",
              silent: true,
              lineStyle: { color: p.weak, type: "dashed" as const, width: 1 },
              label: { show: false },
              data: [{ yAxis: 0 }, ...events],
            },
            markPoint: (() => {
              const last = data.netImport[data.netImport.length - 1];
              if (last == null) return undefined;
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
                data: [{ coord: [cats.length - 1, last] }],
              };
            })(),
          },
        ],
      };
    };
  }, [data, cats, partialSet, impColor, expColor, netColor, theme]);

  const chartRef = useEChart(build, [data, cats, theme], theme);
  return <div ref={chartRef} className="echart chart-wrap" style={{ height: 380 }} />;
}
