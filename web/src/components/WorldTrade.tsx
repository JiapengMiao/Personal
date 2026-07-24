import { useEffect, useMemo, useState } from "react";
import { baseAxis, baseLegend, baseTooltip, echarts, getPalette, hexToRgba, zoomFill, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { formatNumber } from "../lib/format";
import { fetchData } from "../lib/data";

// ——— 07b 美 / 英 / 印白银贸易 · 月度（风格对齐香港贸易区块）———

type MaybeNumber = number | null;

interface NestedMonthlyTrade {
  months: string[];
  imports?: MaybeNumber[];
  exports?: MaybeNumber[];
  netImport?: MaybeNumber[];
  note?: string;
}

interface TradeData {
  generatedAt: string;
  country?: string;
  source: string;
  unit: string;
  asOf: string;
  years?: string[];
  imports?: MaybeNumber[];
  exports?: MaybeNumber[];
  netImport?: MaybeNumber[];
  partialYears?: Record<string, string>;
  events?: { date: string; label: string; kind: string }[];
  monthlyAvailable?: boolean;
  monthlySeriesComplete?: boolean;
  months?: string[];
  monthlyImports?: MaybeNumber[];
  monthlyExports?: MaybeNumber[];
  monthlyNetImport?: MaybeNumber[];
  monthly?: NestedMonthlyTrade;
  monthlyNote?: string;
  requestedThrough?: string;
  latestPublished?: string;
  unavailablePeriods?: string[];
  publishedButMonthlyFileNotCached?: string[];
  disclaimer: string;
}

interface MonthlySeries {
  months: string[];
  imports: MaybeNumber[];
  exports: MaybeNumber[];
  netImport: MaybeNumber[];
  observedCount: number;
  missingCount: number;
  complete: boolean;
  note: string;
}

interface CountrySpec {
  key: string;
  file: string;
  name: string;
  code: string;
  sub: string;
}

const COUNTRIES: CountrySpec[] = [
  { key: "us", file: "data/us_trade.json", name: "美国", code: "US TRADE", sub: "Census HS/HTS 7106" },
  { key: "uk", file: "data/uk_trade.json", name: "英国", code: "UK TRADE", sub: "HMRC BDS HS71069100" },
  { key: "in", file: "data/india_trade.json", name: "印度", code: "IN TRADE", sub: "印度商务部 TradeStat HS7106" },
];

function toMonth(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.length >= 6) return `${digits.slice(0, 4)}-${digits.slice(4, 6)}`;
  return value;
}

function monthRange(start: string, end: string): string[] {
  const out: string[] = [];
  let year = Number(start.slice(0, 4));
  let month = Number(start.slice(5, 7));
  const endYear = Number(end.slice(0, 4));
  const endMonth = Number(end.slice(5, 7));
  while (year < endYear || (year === endYear && month <= endMonth)) {
    out.push(`${year}-${String(month).padStart(2, "0")}`);
    month += 1;
    if (month > 12) {
      month = 1;
      year += 1;
    }
  }
  return out;
}

function valueAt(values: MaybeNumber[] | undefined, index: number): MaybeNumber {
  const value = values?.[index];
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function normalizeMonthly(data: TradeData): MonthlySeries {
  const rawMonths = data.months ?? data.monthly?.months ?? [];
  const rawImports = data.monthlyImports ?? data.monthly?.imports ?? [];
  const rawExports = data.monthlyExports ?? data.monthly?.exports ?? [];
  const rawNet = data.monthlyNetImport ?? data.monthly?.netImport ?? [];
  const byMonth = new Map<string, { imports: MaybeNumber; exports: MaybeNumber; netImport: MaybeNumber }>();

  rawMonths.forEach((rawMonth, index) => {
    const imports = valueAt(rawImports, index);
    const exports = valueAt(rawExports, index);
    const explicitNet = valueAt(rawNet, index);
    byMonth.set(toMonth(rawMonth), {
      imports,
      exports,
      netImport: explicitNet ?? (imports != null && exports != null ? imports - exports : null),
    });
  });

  const observedMonths = [...byMonth.keys()].sort();
  if (!observedMonths.length) {
    return {
      months: [],
      imports: [],
      exports: [],
      netImport: [],
      observedCount: 0,
      missingCount: 0,
      complete: false,
      note: data.monthlyNote ?? data.monthly?.note ?? data.disclaimer,
    };
  }

  let first = observedMonths[0];
  let last = observedMonths[observedMonths.length - 1];
  if (
    data.monthlySeriesComplete === false
    && observedMonths.every((month) => month.slice(0, 4) === last.slice(0, 4))
    && first.slice(5, 7) !== "01"
  ) {
    first = `${last.slice(0, 4)}-01`;
  }
  if (data.requestedThrough) {
    const requested = toMonth(data.requestedThrough);
    if (requested > last) last = requested;
  }

  const months = monthRange(first, last);
  const imports = months.map((month) => byMonth.get(month)?.imports ?? null);
  const exports = months.map((month) => byMonth.get(month)?.exports ?? null);
  const netImport = months.map((month) => byMonth.get(month)?.netImport ?? null);
  const observedCount = months.filter((_, index) => (
    imports[index] != null || exports[index] != null || netImport[index] != null
  )).length;

  return {
    months,
    imports,
    exports,
    netImport,
    observedCount,
    missingCount: months.length - observedCount,
    complete: data.monthlySeriesComplete === true && observedCount === months.length,
    note: data.monthlyNote ?? data.monthly?.note ?? data.disclaimer,
  };
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
        index="07B"
        title="美英印白银贸易 · 月度"
        desc="进口、出口柱状 + 净进口折线（正=净流入）· 缺失月份保留空档，不做估算填充"
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
  const series = useMemo(() => normalizeMonthly(data), [data]);

  const stats = useMemo(() => {
    let latestIndex = -1;
    series.months.forEach((_, index) => {
      if (
        series.imports[index] != null
        || series.exports[index] != null
        || series.netImport[index] != null
      ) latestIndex = index;
    });
    if (latestIndex < 0) return null;

    const latestMonth = series.months[latestIndex];
    const latestYear = latestMonth.slice(0, 4);
    const hasNet = series.netImport.some((value) => value != null);
    const latestNet = series.netImport[latestIndex];
    const latestImport = series.imports[latestIndex];
    const ytdValues = hasNet ? series.netImport : series.imports;
    const ytd = ytdValues.reduce((sum: number, value, index) => (
      series.months[index].startsWith(latestYear) && value != null ? sum + value : sum
    ), 0);
    let peakValue = -Infinity;
    let peakMonth = "";
    (hasNet ? series.netImport : series.imports).forEach((value, index) => {
      if (value != null && value > peakValue) {
        peakValue = value;
        peakMonth = series.months[index];
      }
    });
    return { latestMonth, latestNet, latestImport, latestYear, hasNet, ytd, peakValue, peakMonth };
  }, [series]);

  const impColor = p.live;
  const expColor = p.series[7];
  const netColor = p.gold;

  if (!series.months.length || !stats) {
    return (
      <article className="panel chart-panel hk-trade-panel">
        <div className="panel-heading">
          <div>
            <span>贸易 · {spec.code}</span>
            <h3>{spec.name}月度进出口与净进口（吨）</h3>
          </div>
        </div>
        <p className="chart-note">当前数据文件尚未包含可绘制的月度明细。</p>
      </article>
    );
  }

  const latestMetric = stats.hasNet ? stats.latestNet : stats.latestImport;

  return (
    <article className="panel chart-panel hk-trade-panel">
      <div className="hk-stats">
        <div className="hk-stat">
          <small>最新月（{stats.latestMonth}）{stats.hasNet ? "净进口" : "进口"}</small>
          <strong style={{ color: stats.hasNet ? ((latestMetric ?? 0) < 0 ? p.down : p.up) : undefined }}>
            {stats.hasNet && (latestMetric ?? 0) >= 0 ? "+" : ""}
            {latestMetric == null ? "—" : `${formatNumber(latestMetric, 0)} 吨`}
          </strong>
          <small>
            {stats.hasNet
              ? ((latestMetric ?? 0) < 0 ? "净流出 / 再出口" : "净流入")
              : "月度出口缺失，暂不推算净进口"}
          </small>
        </div>
        <div className="hk-stat">
          <small>{stats.latestYear} 年迄今{stats.hasNet ? "累计净进口" : "已披露进口"}</small>
          <strong style={{ color: stats.hasNet ? (stats.ytd < 0 ? p.down : p.up) : undefined }}>
            {stats.hasNet && stats.ytd >= 0 ? "+" : ""}{formatNumber(stats.ytd, 0)} 吨
          </strong>
          <small>{spec.sub}</small>
        </div>
        <div className="hk-stat">
          <small>区间峰值{stats.hasNet ? "净进口" : "进口"}</small>
          <strong>{formatNumber(stats.peakValue, 0)} 吨</strong>
          <small>{stats.peakMonth}</small>
        </div>
        <div className="hk-stat">
          <small>月度覆盖</small>
          <strong style={{ color: series.complete ? undefined : p.gold }}>
            {series.observedCount}/{series.months.length} 月
          </strong>
          <small>
            {series.complete ? "连续完整" : `${series.missingCount} 个空档 / 未发布月`}
          </small>
        </div>
      </div>

      <div className="panel-heading">
        <div>
          <span>贸易 · {spec.code}</span>
          <h3>{spec.name}月度进出口与净进口（吨）</h3>
        </div>
        <div className="panel-stat">
          <small>数据截至</small>
          <strong>{stats.latestMonth}</strong>
        </div>
      </div>
      <CountryChart
        data={data}
        series={series}
        impColor={impColor}
        expColor={expColor}
        netColor={netColor}
        theme={theme}
      />
      <p className="chart-note">{series.note}</p>
    </article>
  );
}

function CountryChart({ data, series, impColor, expColor, netColor, theme }: {
  data: TradeData;
  series: MonthlySeries;
  impColor: string;
  expColor: string;
  netColor: string;
  theme: ThemeMode;
}) {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");

  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const hasImports = series.imports.some((value) => value != null);
      const hasExports = series.exports.some((value) => value != null);
      const hasNet = series.netImport.some((value) => value != null);
      const zoomStart = series.months.length > 24
        ? Math.max(0, ((series.months.length - 24) / series.months.length) * 100)
        : 0;
      const events = (data.events ?? [])
        .map((ev) => {
          const month = toMonth(ev.date);
          return series.months.includes(month)
            ? {
                xAxis: month,
                label: {
                  show: true,
                  formatter: ev.label,
                  position: "insideEndTop" as const,
                  fontSize: 10,
                  color: p.sub,
                },
              }
            : null;
        })
        .filter(Boolean) as { xAxis: string; label: object }[];

      const chartSeries: object[] = [];
      if (hasImports) {
        chartSeries.push({
          name: "进口",
          type: "bar" as const,
          data: series.imports,
          itemStyle: { color: hexToRgba(impColor, theme === "light" ? 0.55 : 0.75) },
          barGap: "10%",
          barMaxWidth: 14,
          markLine: !hasNet && events.length ? {
            symbol: "none",
            silent: true,
            lineStyle: { color: p.weak, type: "dashed" as const, width: 1 },
            data: events,
          } : undefined,
        });
      }
      if (hasExports) {
        chartSeries.push({
          name: "出口",
          type: "bar" as const,
          data: series.exports,
          itemStyle: { color: hexToRgba(expColor, theme === "light" ? 0.5 : 0.6) },
          barMaxWidth: 14,
        });
      }
      if (hasNet) {
        let lastNetIndex = -1;
        series.netImport.forEach((value, index) => {
          if (value != null) lastNetIndex = index;
        });
        const lastNet = lastNetIndex >= 0 ? series.netImport[lastNetIndex] : null;
        chartSeries.push({
          name: "净进口",
          type: "line" as const,
          data: series.netImport,
          showSymbol: false,
          connectNulls: false,
          lineStyle: { width: 2.4, type: "solid" as const, color: netColor },
          itemStyle: { color: netColor },
          markLine: {
            symbol: "none",
            silent: true,
            lineStyle: { color: p.weak, type: "dashed" as const, width: 1 },
            label: { show: false },
            data: [{ yAxis: 0 }, ...events],
          },
          markPoint: lastNet == null ? undefined : {
            symbol: "circle",
            symbolSize: 7,
            itemStyle: { color: lastNet < 0 ? p.down : p.up },
            label: {
              show: true,
              formatter: `${lastNet < 0 ? "" : "+"}${formatNumber(lastNet, 0)}`,
              color: lastNet < 0 ? p.down : p.up,
              fontFamily: "JetBrains Mono",
              fontSize: 11,
              offset: [0, -14] as [number, number],
            },
            data: [{ coord: [series.months[lastNetIndex], lastNet] }],
          },
        });
      }

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
        xAxis: { type: "category", data: series.months, ...baseAxis(p), boundaryGap: true },
        yAxis: {
          type: "value",
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
        },
        dataZoom: [
          { type: "inside", throttle: 80, start: zoomStart, end: 100 },
          { type: "slider", height: 18, bottom: 8, throttle: 80, start: zoomStart, end: 100, ...zoomFill(p) },
        ],
        series: chartSeries,
      };
    };
  }, [data.events, series, impColor, expColor, netColor, theme]);

  const chartRef = useEChart(build, [data.events, series, theme], theme);
  const apply = () => {
    if (!start || !end || start > end || !chartRef.current) return;
    const instance = echarts.getInstanceByDom(chartRef.current);
    instance?.dispatchAction({ type: "dataZoom", startValue: start, endValue: end });
  };
  const minMonth = series.months[0];
  const maxMonth = series.months[series.months.length - 1];

  return (
    <>
      <div className="range-picker">
        <label>
          起始
          <input
            type="month"
            value={start}
            min={minMonth}
            max={maxMonth}
            onChange={(event) => setStart(event.target.value)}
          />
        </label>
        <span className="range-sep">—</span>
        <label>
          截止
          <input
            type="month"
            value={end}
            min={minMonth}
            max={maxMonth}
            onChange={(event) => setEnd(event.target.value)}
          />
        </label>
        <button type="button" onClick={apply} disabled={!start || !end || start > end}>应用</button>
      </div>
      <div ref={chartRef} className="echart chart-wrap" style={{ height: 380 }} />
    </>
  );
}
