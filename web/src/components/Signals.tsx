import { useMemo } from "react";
import type { MonitoringData } from "../lib/types";
import { baseAxis, baseLegend, baseTooltip, getPalette, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { LedBadge, ScoreScale, SectionHeading, Sparkline } from "./shared";

// ——— 01 五项固定监测 ———
export function SignalsSection({
  monitoring,
  selectedTheme,
  onSelectTheme,
}: {
  monitoring: MonitoringData;
  selectedTheme: string | null;
  onSelectTheme: (theme: string | null) => void;
}) {
  const sparkOf = (theme: string): number[] => {
    const main =
      monitoring.indicators.find((i) => i.theme === theme && i.role === "主指标" && i.history.length > 0) ??
      monitoring.indicators.find((i) => i.theme === theme && i.history.length > 0);
    return main ? main.history.map((h) => h.value) : [];
  };
  return (
    <section className="section-block" id="signals">
      <SectionHeading index="09" title="五项固定监测" desc="点击信号卡可筛选下方指标库主题，再次点击取消" id="signals" />
      <div className="signal-grid">
        {monitoring.themeSummaries.map((t) => {
          const selected = selectedTheme === t.theme;
          return (
            <button
              key={t.theme}
              className={`signal-card ${t.tone} ${selected ? "selected" : ""}`}
              onClick={() => onSelectTheme(selected ? null : t.theme)}
              aria-pressed={selected}
            >
              <div className="signal-card-top">
                <span className="theme-icon">{t.icon}</span>
                <LedBadge tone={t.tone} status={t.status} />
              </div>
              <h3>{t.theme}</h3>
              <span className="signal-value">{t.value}</span>
              <span className={`signal-delta ${t.score > 0 ? "up" : t.score < 0 ? "down" : ""}`}>{t.delta}</span>
              <p>{t.description}</p>
              <div className="signal-spark">
                <Sparkline values={sparkOf(t.theme)} tone={t.score > 0 ? "pos" : t.score < 0 ? "neg" : undefined} width={220} height={26} />
              </div>
              <ScoreScale score={t.score} />
            </button>
          );
        })}
      </div>
    </section>
  );
}

// ——— 02 趋势与结构 ———
export function TrendsSection({ monitoring, theme }: { monitoring: MonitoringData; theme: ThemeMode }) {
  return (
    <section className="section-block" id="trends">
      <SectionHeading index="10" title="趋势与结构" desc="全球市场平衡与工业用银需求结构（World Silver Survey）" id="trends" />
      <div className="analytics-grid">
        <article className="panel chart-panel balance-panel">
          <span className="year-watermark">Ag</span>
          <div className="panel-heading">
            <div>
              <span>供需 · BALANCE</span>
              <h3>全球白银市场平衡</h3>
            </div>
            <div className="panel-stat">
              <small>负值为缺口 · 单位：吨</small>
              <strong>{monitoring.marketBalance[monitoring.marketBalance.length - 1]?.year} 预测</strong>
            </div>
          </div>
          <BalanceChart data={monitoring.marketBalance} theme={theme} />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>需求 · DEMAND MIX</span>
              <h3>工业用银需求拆分</h3>
            </div>
            <div className="panel-stat">
              <small>单位：吨</small>
              <strong>光伏 / 非光伏 / 钎焊 / 其他</strong>
            </div>
          </div>
          <IndustrialChart data={monitoring.industrialMix} theme={theme} />
        </article>
      </div>
      <article className="panel action-panel">
        <div className="panel-heading">
          <div>
            <span>行动清单 · ACTIONS</span>
            <h3>数据建设待办</h3>
          </div>
          <span className="coverage-pill">{monitoring.actions.length} 项进行中</span>
        </div>
        <div className="action-list">
          {monitoring.actions.map((a, i) => (
            <div key={i} className="action-row">
              <span className="action-number">{String(i + 1).padStart(2, "0")}</span>
              <span className="action-cadence">{a.cadence}</span>
              <div>
                <strong>{a.task}</strong>
                <small>负责主题：{a.owner}</small>
              </div>
              <span className={`action-status ${a.status.includes("优先") ? "priority" : ""}`}>{a.status}</span>
            </div>
          ))}
        </div>
      </article>
    </section>
  );
}

function BalanceChart({ data, theme }: { data: MonitoringData["marketBalance"]; theme: ThemeMode }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const years = data.map((d) => String(d.year));
      const lastActualIdx = data.reduce((acc, d, i) => (d.type === "预测" ? acc : i), 0);
      const actual = data.map((d, i) => (i <= lastActualIdx ? d.value : null));
      const forecast = data.map((d, i) => (i >= lastActualIdx ? d.value : null));
      return {
        animationDuration: 500,
        grid: { top: 24, right: 18, bottom: 30, left: 58 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          valueFormatter: (v: unknown) => `${Number(v).toLocaleString("zh-CN")} 吨`,
        },
        xAxis: {
          type: "category",
          data: years,
          ...baseAxis(p),
          boundaryGap: false,
        },
        yAxis: {
          type: "value",
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => (v / 1000).toString() + "k" },
        },
        series: [
          {
            name: "实际",
            type: "line",
            data: actual,
            smooth: false,
            symbol: "circle",
            symbolSize: 6,
            lineStyle: { width: 2.5, color: p.gold },
            itemStyle: { color: p.gold, borderColor: p.panel, borderWidth: 2 },
            areaStyle: { color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [
              { offset: 0, color: theme === "light" ? "rgba(154,109,18,.18)" : "rgba(217,164,65,.24)" },
              { offset: 1, color: "rgba(217,164,65,0)" },
            ] } },
            markLine: {
              silent: true,
              symbol: "none",
              label: { show: false },
              lineStyle: { color: p.edge, width: 1.4 },
              data: [{ yAxis: 0 }],
            },
          },
          {
            name: "预测",
            type: "line",
            data: forecast,
            symbol: "circle",
            symbolSize: 7,
            lineStyle: { width: 2, type: "dashed", color: p.goldBright },
            itemStyle: { color: p.goldBright, borderColor: p.panel, borderWidth: 2 },
          },
        ],
        legend: { ...baseLegend(p), top: 0, right: 0 },
      };
    };
  }, [data, theme]);
  const ref = useEChart(build, [data], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 300 }} />;
}

function IndustrialChart({ data, theme }: { data: MonitoringData["industrialMix"]; theme: ThemeMode }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const seriesDef = [
        { key: "photovoltaic" as const, label: "光伏", color: p.gold },
        { key: "nonPv" as const, label: "非光伏电气电子", color: p.live },
        { key: "brazing" as const, label: "钎焊与焊料", color: p.down },
        { key: "other" as const, label: "其他工业", color: p.silver },
      ];
      return {
        animationDuration: 500,
        grid: { top: 34, right: 14, bottom: 30, left: 58 },
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "shadow" },
          ...baseTooltip(p),
          valueFormatter: (v: unknown) => `${Number(v).toLocaleString("zh-CN")} 吨`,
        },
        legend: { ...baseLegend(p), top: 0, left: 0 },
        xAxis: { type: "category", data: data.map((d) => d.year), ...baseAxis(p) },
        yAxis: { type: "value", ...baseAxis(p) },
        series: seriesDef.map((s) => ({
          name: s.label,
          type: "bar" as const,
          data: data.map((d) => d[s.key]),
          itemStyle: { color: s.color, borderRadius: [3, 3, 0, 0] },
          barMaxWidth: 34,
          barGap: "18%",
        })),
      };
    };
  }, [data, theme]);
  const ref = useEChart(build, [data], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 300 }} />;
}
