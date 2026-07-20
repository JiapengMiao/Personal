"use client";

import { useEffect, useMemo, useRef, useState, type CSSProperties, type MouseEvent as ReactMouseEvent } from "react";
import {
  actions,
  asOfDate,
  comexStocks,
  generatedAt,
  goldSilverRatioSeries,
  hasMarketData,
  indicators,
  industrialMix,
  londonSilverKg,
  marketBalance,
  marketFetchedAt,
  overallPulse,
  sgeAg9999Close,
  sgeAgTdLatest,
  sgeInventory,
  shfeSilverClose,
  shfeStocks,
  silverFundNav,
  silverFundSnapshot,
  sources,
  themeSummaries,
  triggers,
  type HistoryPoint,
  type Indicator,
  type MarketPoint,
} from "./data";

const themes = ["全部", ...themeSummaries.map((item) => item.theme)];
const statusOptions = ["全部状态", "利多", "利空", "待接入"];
const navItems = [
  { id: "signals", label: "五项信号" },
  { id: "trends", label: "趋势" },
  { id: "market", label: "市场脉搏" },
  { id: "dynamics", label: "信号动态" },
  { id: "indicators", label: "指标库" },
];

function formatNumber(value: number, decimals = 1) {
  return new Intl.NumberFormat("zh-CN", { maximumFractionDigits: decimals, minimumFractionDigits: 0 }).format(value);
}

function formatMetric(value: number | null, unit: string) {
  if (value === null) return "待接入";
  if (unit === "%") return `${(value * 100).toFixed(1)}%`;
  return `${formatNumber(value)} ${unit}`;
}

function formatDelta(item: Indicator) {
  if (item.value === null || item.priorValue === null) return "—";
  const delta = item.value - item.priorValue;
  if (item.unit === "%") return `${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)}个百分点`;
  return `${delta >= 0 ? "+" : ""}${formatNumber(delta)} ${item.unit}`;
}

function formatScore(score: number | null) {
  if (score === null) return "基线";
  return score > 0 ? `+${score}` : `${score}`;
}

function formatFetchedAt(iso: string | null) {
  if (!iso) return "";
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return iso.slice(0, 10);
  const shifted = new Date(time + 8 * 3600 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${shifted.getUTCFullYear()}-${pad(shifted.getUTCMonth() + 1)}-${pad(shifted.getUTCDate())} ${pad(shifted.getUTCHours())}:${pad(shifted.getUTCMinutes())}`;
}

function formatTradeTime(raw: string) {
  const match = raw.match(/^(\d{4})(\d{2})(\d{2})\s+(\d{2}:\d{2})/);
  return match ? `${match[1]}-${match[2]}-${match[3]} ${match[4]}` : raw;
}

function latestDelta(points: MarketPoint[]) {
  if (points.length === 0) return { latest: null as MarketPoint | null, delta: null as number | null };
  const latest = points[points.length - 1];
  const previous = points.length > 1 ? points[points.length - 2] : null;
  return { latest, delta: previous ? latest.value - previous.value : null };
}

function useInView<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    if (!ref.current) return;
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setInView(true);
          observer.disconnect();
        }
      },
      { threshold: 0.3 },
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);
  return { ref, inView };
}

function useCountUp(target: number, active: boolean, duration = 900) {
  const [value, setValue] = useState(0);
  useEffect(() => {
    if (!active) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setValue(target);
      return;
    }
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - start) / duration);
      setValue(Math.round(target * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, target, duration]);
  return value;
}

function SignalBadge({ tone, status }: Pick<Indicator, "tone" | "status">) {
  return <span className={`signal-badge ${tone}`}>{status}</span>;
}

function LedBadge({ tone, status }: { tone: string; status: string }) {
  return (
    <span className={`led-badge ${tone}`}>
      <i className="led" />
      {status}
    </span>
  );
}

function Sparkline({ values, tone, width = 64, height = 24 }: { values: number[]; tone?: string; width?: number; height?: number }) {
  if (values.length === 0) {
    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="sparkline" preserveAspectRatio="none" aria-hidden="true">
        <line x1="2" y1={height / 2} x2={width - 2} y2={height / 2} className="spark-placeholder" />
      </svg>
    );
  }
  if (values.length === 1) {
    return (
      <svg viewBox={`0 0 ${width} ${height}`} className="sparkline" preserveAspectRatio="none" aria-hidden="true">
        <circle cx={width / 2} cy={height / 2} r="2.6" className={`spark-dot ${tone ?? ""}`} />
      </svg>
    );
  }
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = (width - 4) / (values.length - 1);
  const points = values.map((value, index) => `${2 + index * step},${height - 3 - ((value - min) / span) * (height - 6)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="sparkline" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} className={`spark-line ${tone ?? ""}`} />
    </svg>
  );
}

function ScoreScale({ score }: { score: number }) {
  return (
    <div className="score-scale" aria-label={`信号分数${score}`}>
      {[-2, -1, 0, 1, 2].map((step) => (
        <i key={step} className={step === score ? "active" : ""} />
      ))}
      <span>{score > 0 ? `+${score}` : score}</span>
    </div>
  );
}

function themeSparkValues(theme: string) {
  const main = indicators.find((item) => item.theme === theme && item.role === "主指标" && item.history.length > 0)
    ?? indicators.find((item) => item.theme === theme && item.history.length > 0);
  return main ? main.history.map((point) => point.value) : [];
}

function PulseGauge() {
  const cx = 110;
  const cy = 106;
  const r = 82;
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const arcLen = Math.PI * r;
  const pos = Math.min(1, Math.max(0, overallPulse.position));
  const angle = Math.PI * (1 - pos);
  const needleR = r - 26;
  const nx = cx + needleR * Math.cos(angle);
  const ny = cy - needleR * Math.sin(angle);
  const ticks = [0, 25, 50, 75, 100];
  return (
    <div className="gauge-wrap">
      <svg viewBox="0 0 220 122" className="gauge-svg" role="img" aria-label={`紧张度仪表，当前${Math.round(pos * 100)}%`}>
        <path d={arc} className="gauge-track" />
        <path d={arc} className="gauge-progress" style={{ strokeDasharray: `${arcLen * pos} ${arcLen}` }} />
        {ticks.map((tick) => {
          const a = Math.PI * (1 - tick / 100);
          return (
            <line
              key={tick}
              x1={cx + (r - 7) * Math.cos(a)}
              y1={cy - (r - 7) * Math.sin(a)}
              x2={cx + (r + 2) * Math.cos(a)}
              y2={cy - (r + 2) * Math.sin(a)}
              className="gauge-tick"
            />
          );
        })}
        <text x={cx - r + 2} y={cy + 15} className="gauge-label">宽松</text>
        <text x={cx + r - 2} y={cy + 15} textAnchor="end" className="gauge-label">紧张</text>
        <line x1={cx} y1={cy} x2={nx} y2={ny} className="gauge-needle" />
        <circle cx={cx} cy={cy} r="5" className="gauge-hub" />
      </svg>
      <div className="gauge-center">
        <small>综合状态</small>
        <strong>{overallPulse.status}</strong>
        <span>{overallPulse.score > 0 ? `+${overallPulse.score}` : overallPulse.score}</span>
      </div>
    </div>
  );
}

function BalanceChart({ yearIndex, onOpenIndicator }: { yearIndex: number; onOpenIndicator: () => void }) {
  const [hover, setHover] = useState<number | null>(null);
  const width = 720;
  const height = 300;
  const margin = { top: 24, right: 24, bottom: 40, left: 58 };
  const yMin = -8000;
  const yMax = 2000;
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const n = marketBalance.length;
  const x = (index: number) => margin.left + (index * plotWidth) / (n - 1);
  const y = (value: number) => margin.top + ((yMax - value) / (yMax - yMin)) * plotHeight;
  const path = marketBalance.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.value)}`).join(" ");
  const ticks = [2000, 0, -2000, -4000, -6000, -8000];
  const revealWidth = x(yearIndex) - margin.left + 6;
  const balanceHistory = indicators.find((item) => item.id === 14)?.history ?? [];
  const scoreOf = (year: number) => balanceHistory.find((point) => point.period.startsWith(String(year)));

  const onMove = (event: ReactMouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const xPos = ((event.clientX - rect.left) / rect.width) * width;
    const index = Math.round(((xPos - margin.left) / plotWidth) * (n - 1));
    setHover(Math.max(0, Math.min(n - 1, index)));
  };

  const hoverPoint = hover !== null ? marketBalance[hover] : null;
  const hoverScore = hoverPoint ? scoreOf(hoverPoint.year) : undefined;

  return (
    <div className="chart-wrap" role="img" aria-label="2017年至2026年全球白银市场平衡折线图，负值表示缺口">
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="balanceArea" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#d9a441" stopOpacity="0.26" />
            <stop offset="100%" stopColor="#d9a441" stopOpacity="0" />
          </linearGradient>
          <pattern id="forecastHatch" patternUnits="userSpaceOnUse" width="6" height="6" patternTransform="rotate(45)">
            <rect width="6" height="6" className="hatch-bg" />
            <line x1="0" y1="0" x2="0" y2="6" stroke="#d9a441" strokeWidth="2" />
          </pattern>
          <clipPath id="balanceReveal">
            <rect x="0" y="0" height={height} className="reveal-rect" style={{ width: margin.left + revealWidth }} />
          </clipPath>
        </defs>
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} className={tick === 0 ? "zero-line" : "grid-line"} />
            <text x={margin.left - 10} y={y(tick) + 4} textAnchor="end" className="axis-label">{formatNumber(tick)}</text>
          </g>
        ))}
        <g clipPath="url(#balanceReveal)">
          <path d={`${path} L${x(n - 1)},${y(0)} L${x(0)},${y(0)} Z`} fill="url(#balanceArea)" />
          <path d={path} className="balance-line" />
        </g>
        {marketBalance.map((point, index) => (
          <g key={point.year} opacity={index <= yearIndex ? 1 : 0.22}>
            {point.type === "预测" ? (
              <circle cx={x(index)} cy={y(point.value)} r="6.5" fill="url(#forecastHatch)" className="point forecast-hatch" onClick={onOpenIndicator}>
                <title>{`${point.year}：${formatNumber(point.value)}吨（${point.type}）`}</title>
              </circle>
            ) : (
              <circle cx={x(index)} cy={y(point.value)} r="4.5" className="point" onClick={onOpenIndicator}>
                <title>{`${point.year}：${formatNumber(point.value)}吨（${point.type}）`}</title>
              </circle>
            )}
            <text x={x(index)} y={height - 12} textAnchor="middle" className={`axis-label ${index === yearIndex ? "axis-current" : ""}`}>{point.year}</text>
          </g>
        ))}
        {hover !== null && hoverPoint && (
          <g className="crosshair">
            <line x1={x(hover)} x2={x(hover)} y1={margin.top} y2={height - margin.bottom} className="crosshair-line" />
            <circle cx={x(hover)} cy={y(hoverPoint.value)} r="5.5" className="crosshair-dot" />
          </g>
        )}
      </svg>
      {hover !== null && hoverPoint && (
        <div className="chart-tooltip" style={{ left: `${(x(hover) / width) * 100}%` }}>
          <strong>{hoverPoint.year} {hoverPoint.type}</strong>
          <span>{formatNumber(hoverPoint.value)} 吨{hoverPoint.value < 0 ? "（缺口）" : "（盈余）"}</span>
          {hoverScore && <em>信号 {formatScore(hoverScore.score)} · {hoverScore.status}</em>}
        </div>
      )}
    </div>
  );
}

const industrialSeries = [
  { key: "photovoltaic", label: "光伏", color: "#d9a441" },
  { key: "nonPv", label: "非光伏电气电子", color: "#56c8dc" },
  { key: "brazing", label: "钎焊与焊料", color: "#f26d6d" },
  { key: "other", label: "其他工业", color: "#9fb0c3" },
] as const;

function IndustrialChart() {
  const [hidden, setHidden] = useState<Set<string>>(new Set());
  const [hover, setHover] = useState<number | null>(null);
  const width = 720;
  const height = 300;
  const margin = { top: 18, right: 18, bottom: 42, left: 58 };
  const max = 9000;
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const groupWidth = plotWidth / industrialMix.length;
  const visibleSeries = industrialSeries.filter((series) => !hidden.has(series.key));
  const barWidth = 26;
  const gap = 5;
  const y = (value: number) => margin.top + plotHeight - (value / max) * plotHeight;
  const ticks = [0, 2000, 4000, 6000, 8000];

  const toggle = (key: string) => {
    setHidden((current) => {
      const next = new Set(current);
      if (next.has(key)) next.delete(key);
      else if (next.size < industrialSeries.length - 1) next.add(key);
      return next;
    });
  };

  const hoverGroup = hover !== null ? industrialMix[hover] : null;

  return (
    <div className="chart-wrap" role="img" aria-label="2024年至2026年工业用银主要板块分组柱状图">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="chart-svg"
        onMouseMove={(event) => {
          const rect = event.currentTarget.getBoundingClientRect();
          const xPos = ((event.clientX - rect.left) / rect.width) * width;
          const index = Math.floor((xPos - margin.left) / groupWidth);
          setHover(index >= 0 && index < industrialMix.length ? index : null);
        }}
        onMouseLeave={() => setHover(null)}
      >
        {ticks.map((tick) => (
          <g key={tick}>
            <line x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} className="grid-line" />
            <text x={margin.left - 10} y={y(tick) + 4} textAnchor="end" className="axis-label">{formatNumber(tick)}</text>
          </g>
        ))}
        {industrialMix.map((group, groupIndex) => {
          const totalBarsWidth = visibleSeries.length * barWidth + (visibleSeries.length - 1) * gap;
          const startX = margin.left + groupIndex * groupWidth + (groupWidth - totalBarsWidth) / 2;
          return (
            <g key={group.year}>
              {hover === groupIndex && (
                <rect x={margin.left + groupIndex * groupWidth + 2} y={margin.top} width={groupWidth - 4} height={plotHeight} className="group-highlight" />
              )}
              {visibleSeries.map((series, seriesIndex) => {
                const value = group[series.key];
                const barHeight = (value / max) * plotHeight;
                return (
                  <rect
                    key={series.key}
                    x={startX + seriesIndex * (barWidth + gap)}
                    y={y(value)}
                    width={barWidth}
                    height={barHeight}
                    rx="3"
                    fill={series.color}
                    className="bar"
                  >
                    <title>{`${group.year} ${series.label}：${formatNumber(value)}吨`}</title>
                  </rect>
                );
              })}
              <text x={margin.left + groupIndex * groupWidth + groupWidth / 2} y={height - 14} textAnchor="middle" className="axis-label year-label">{group.year}</text>
            </g>
          );
        })}
      </svg>
      {hoverGroup && (
        <div className="chart-tooltip" style={{ left: `${((margin.left + (hover! + 0.5) * groupWidth) / width) * 100}%` }}>
          <strong>{hoverGroup.year}</strong>
          {visibleSeries.map((series) => (
            <span key={series.key}><i style={{ background: series.color }} />{series.label} {formatNumber(hoverGroup[series.key])} 吨</span>
          ))}
        </div>
      )}
      <div className="chart-legend">
        {industrialSeries.map((series) => (
          <button
            key={series.key}
            className={`legend-chip ${hidden.has(series.key) ? "off" : ""}`}
            onClick={() => toggle(series.key)}
            aria-pressed={!hidden.has(series.key)}
          >
            <i style={{ background: series.color }} />
            {series.label}
          </button>
        ))}
      </div>
    </div>
  );
}

function ScoreBarsChart({ history }: { history: HistoryPoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const width = 720;
  const height = 268;
  const margin = { top: 26, right: 16, bottom: 36, left: 36 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const slot = plotWidth / history.length;
  const barWidth = Math.min(44, slot * 0.52);
  const yZero = margin.top + plotHeight / 2;
  const unit = plotHeight / 4.6;
  const y = (score: number) => yZero - score * unit;

  const hoverPoint = hover !== null ? history[hover] : null;

  return (
    <div className="chart-wrap" role="img" aria-label="全球市场平衡历年信号分数柱状图，范围从负二到正二">
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" onMouseLeave={() => setHover(null)}>
        {[-2, -1, 0, 1, 2].map((tick) => (
          <g key={tick}>
            <line x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} className={tick === 0 ? "zero-line" : "grid-line"} />
            <text x={margin.left - 8} y={y(tick) + 3.5} textAnchor="end" className="axis-label">{tick > 0 ? `+${tick}` : tick}</text>
          </g>
        ))}
        {history.map((point, index) => {
          const centerX = margin.left + index * slot + slot / 2;
          if (point.score === null) {
            return (
              <g key={point.period} onMouseEnter={() => setHover(index)}>
                <circle cx={centerX} cy={yZero} r={4} className="score-base-dot"><title>{`${point.period}：基线期，不判断方向`}</title></circle>
                <text x={centerX} y={height - 12} textAnchor="middle" className="axis-label">{point.period}</text>
              </g>
            );
          }
          const barY = point.score >= 0 ? y(point.score) : yZero;
          const barHeight = Math.max(Math.abs(point.score) * unit, 4);
          const labelY = point.score >= 0 ? barY - 7 : barY + barHeight + 13;
          return (
            <g key={point.period} onMouseEnter={() => setHover(index)}>
              <rect x={centerX - barWidth / 2} y={barY} width={barWidth} height={barHeight} rx={3} className={point.score > 0 ? "score-bar pos" : point.score < 0 ? "score-bar neg" : "score-bar flat"}>
                <title>{`${point.period}：${formatScore(point.score)}（${point.status}）`}</title>
              </rect>
              <text x={centerX} y={labelY} textAnchor="middle" className="score-bar-label">{formatScore(point.score)}</text>
              <text x={centerX} y={height - 12} textAnchor="middle" className="axis-label">{point.period}</text>
            </g>
          );
        })}
      </svg>
      {hoverPoint && hover !== null && (
        <div className="chart-tooltip" style={{ left: `${((margin.left + hover * slot + slot / 2) / width) * 100}%` }}>
          <strong>{hoverPoint.period}</strong>
          <span>信号 {formatScore(hoverPoint.score)} · {hoverPoint.status}</span>
          <em>{formatNumber(hoverPoint.value)} 吨</em>
        </div>
      )}
    </div>
  );
}

function MarketLineChart({ points, decimals = 1, unit = "", accent = "gold" }: { points: MarketPoint[]; decimals?: number; unit?: string; accent?: "gold" | "cyan" | "silver" }) {
  const [hover, setHover] = useState<number | null>(null);
  const width = 640;
  const height = 212;
  const margin = { top: 14, right: 16, bottom: 28, left: 60 };
  if (points.length < 2) return <p className="history-empty">序列数据不足，等待下一次取数。</p>;
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const values = points.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = (max - min || 1) * 0.12;
  const yMin = min - padding;
  const yMax = max + padding;
  const x = (index: number) => margin.left + (index * plotWidth) / (points.length - 1);
  const y = (value: number) => margin.top + ((yMax - value) / (yMax - yMin)) * plotHeight;
  const path = points.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.value)}`).join(" ");
  const gridTicks = [yMin + padding, (yMin + yMax) / 2, yMax - padding];
  const gradientId = `marketArea-${accent}`;
  const labelIndexes = [0, Math.floor((points.length - 1) / 2), points.length - 1];

  const onMove = (event: ReactMouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const xPos = ((event.clientX - rect.left) / rect.width) * width;
    const index = Math.round(((xPos - margin.left) / plotWidth) * (points.length - 1));
    setHover(Math.max(0, Math.min(points.length - 1, index)));
  };

  const hoverPoint = hover !== null ? points[hover] : null;

  return (
    <div className="chart-wrap market-chart">
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" className={`area-start ${accent}`} />
            <stop offset="100%" className="area-end" />
          </linearGradient>
        </defs>
        {gridTicks.map((tick, index) => (
          <g key={index}>
            <line x1={margin.left} x2={width - margin.right} y1={y(tick)} y2={y(tick)} className="grid-line" />
            <text x={margin.left - 8} y={y(tick) + 3.5} textAnchor="end" className="axis-label">{formatNumber(tick, decimals)}</text>
          </g>
        ))}
        <path d={`${path} L${x(points.length - 1)},${y(yMin)} L${x(0)},${y(yMin)} Z`} fill={`url(#${gradientId})`} />
        <path d={path} className={`market-line ${accent}`} />
        <circle cx={x(points.length - 1)} cy={y(points[points.length - 1].value)} r="3.6" className={`market-end ${accent}`} />
        {labelIndexes.map((index) => (
          <text key={index} x={x(index)} y={height - 8} textAnchor="middle" className="axis-label">{points[index].date.slice(5)}</text>
        ))}
        {hover !== null && hoverPoint && (
          <g className="crosshair">
            <line x1={x(hover)} x2={x(hover)} y1={margin.top} y2={height - margin.bottom} className="crosshair-line" />
            <circle cx={x(hover)} cy={y(hoverPoint.value)} r="4.5" className="crosshair-dot" />
          </g>
        )}
      </svg>
      {hover !== null && hoverPoint && (
        <div className="chart-tooltip" style={{ left: `${(x(hover) / width) * 100}%` }}>
          <strong>{hoverPoint.date}</strong>
          <span>{formatNumber(hoverPoint.value, decimals)}{unit ? ` ${unit}` : ""}</span>
        </div>
      )}
    </div>
  );
}

function alignStockSeries() {
  const mapA = new Map(comexStocks.map((point) => [point.date, point.value]));
  const mapB = new Map(shfeStocks.map((point) => [point.date, point.value]));
  const dates = [...new Set([...mapA.keys(), ...mapB.keys()])].sort();
  let curA: number | null = null;
  let curB: number | null = null;
  const aligned: { date: string; comex: number; shfe: number }[] = [];
  for (const date of dates) {
    if (mapA.has(date)) curA = mapA.get(date)!;
    if (mapB.has(date)) curB = mapB.get(date)!;
    if (curA !== null && curB !== null) aligned.push({ date, comex: curA, shfe: curB });
  }
  return aligned;
}

function StocksAreaChart() {
  const [hover, setHover] = useState<number | null>(null);
  const data = useMemo(alignStockSeries, []);
  const width = 640;
  const height = 212;
  const margin = { top: 14, right: 16, bottom: 28, left: 60 };
  if (data.length < 2) return <p className="history-empty">库存序列数据不足。</p>;
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const totals = data.map((point) => point.comex + point.shfe);
  const yMax = Math.max(...totals) * 1.04;
  const yMin = Math.min(...data.map((point) => point.comex)) * 0.97;
  const x = (index: number) => margin.left + (index * plotWidth) / (data.length - 1);
  const y = (value: number) => margin.top + ((yMax - value) / (yMax - yMin)) * plotHeight;
  const comexLine = data.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.comex)}`).join(" ");
  const totalLine = data.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.comex + point.shfe)}`).join(" ");
  const totalArea = `${totalLine} ${[...data].map((_, index) => data.length - 1 - index).map((index) => `L${x(index)},${y(data[index].comex)}`).join(" ")} Z`;
  const comexArea = `${comexLine} L${x(data.length - 1)},${y(yMin)} L${x(0)},${y(yMin)} Z`;
  const labelIndexes = [0, Math.floor((data.length - 1) / 2), data.length - 1];

  const onMove = (event: ReactMouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const xPos = ((event.clientX - rect.left) / rect.width) * width;
    const index = Math.round(((xPos - margin.left) / plotWidth) * (data.length - 1));
    setHover(Math.max(0, Math.min(data.length - 1, index)));
  };

  const hoverPoint = hover !== null ? data[hover] : null;

  return (
    <div className="chart-wrap market-chart">
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <line x1={margin.left} x2={width - margin.right} y1={y(yMin)} y2={y(yMin)} className="zero-line" />
        <path d={totalArea} className="stack-shfe" />
        <path d={comexArea} className="stack-comex" />
        <path d={totalLine} className="market-line cyan" />
        <path d={comexLine} className="market-line gold" />
        {labelIndexes.map((index) => (
          <text key={index} x={x(index)} y={height - 8} textAnchor="middle" className="axis-label">{data[index].date.slice(5)}</text>
        ))}
        {hover !== null && hoverPoint && (
          <g className="crosshair">
            <line x1={x(hover)} x2={x(hover)} y1={margin.top} y2={height - margin.bottom} className="crosshair-line" />
            <circle cx={x(hover)} cy={y(hoverPoint.comex + hoverPoint.shfe)} r="4.5" className="crosshair-dot" />
          </g>
        )}
      </svg>
      {hover !== null && hoverPoint && (
        <div className="chart-tooltip" style={{ left: `${(x(hover) / width) * 100}%` }}>
          <strong>{hoverPoint.date}</strong>
          <span><i className="tip-swatch gold" />COMEX {formatNumber(hoverPoint.comex)} 吨</span>
          <span><i className="tip-swatch cyan" />上期所 {formatNumber(hoverPoint.shfe)} 吨</span>
          <em>合计 {formatNumber(hoverPoint.comex + hoverPoint.shfe)} 吨</em>
        </div>
      )}
    </div>
  );
}

function DeltaTag({ delta, decimals = 1, unit = "" }: { delta: number | null; decimals?: number; unit?: string }) {
  if (delta === null) return <span className="delta-tag flat">— 缺上期</span>;
  const up = delta >= 0;
  return (
    <span className={`delta-tag ${up ? "up" : "down"}`}>
      {up ? "▲" : "▼"} {formatNumber(Math.abs(delta), decimals)}{unit ? ` ${unit}` : ""}
    </span>
  );
}

const priceTabs = [
  { key: "london", label: "伦敦银 美元/千克", points: londonSilverKg, unit: "美元/千克", decimals: 1, accent: "gold" as const },
  { key: "shfe", label: "沪银主力 元/千克", points: shfeSilverClose, unit: "元/千克", decimals: 0, accent: "cyan" as const },
  ...(sgeAg9999Close.length > 0
    ? [{ key: "sge", label: "上金所 Ag99.99", points: sgeAg9999Close, unit: "元/千克", decimals: 0, accent: "gold" as const }]
    : []),
  { key: "ratio", label: "金银比", points: goldSilverRatioSeries, unit: "", decimals: 1, accent: "silver" as const },
];

function RatioNote() {
  if (goldSilverRatioSeries.length === 0) return null;
  const values = goldSilverRatioSeries.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const current = values[values.length - 1];
  const position = max > min ? (current - min) / (max - min) : 0.5;
  const zone = position > 0.66 ? "高位" : position < 0.33 ? "低位" : "中位";
  return (
    <p className="chart-note">
      金银比 {formatNumber(current)}：近三个月区间 {formatNumber(min)}–{formatNumber(max)}，当前处于{zone}；比值走高代表白银相对黄金偏弱。
    </p>
  );
}

function PricePanel() {
  const [tab, setTab] = useState("london");
  const active = priceTabs.find((item) => item.key === tab) ?? priceTabs[0];
  const { latest, delta } = latestDelta(active.points);

  return (
    <article className="panel market-panel">
      <div className="panel-heading">
        <div><span>价格 · PRICE</span><h3>白银价格</h3></div>
        <div className="panel-stat">
          <small>{latest?.date ?? "—"}</small>
          <strong>{latest ? `${formatNumber(latest.value, active.decimals)}${active.unit ? ` ${active.unit}` : ""}` : "—"}</strong>
          <DeltaTag delta={delta} decimals={active.decimals} unit={active.unit} />
        </div>
      </div>
      <div className="tab-row" role="tablist" aria-label="价格序列切换">
        {priceTabs.map((item) => (
          <button key={item.key} role="tab" aria-selected={tab === item.key} className={tab === item.key ? "active" : ""} onClick={() => setTab(item.key)}>
            {item.label}
          </button>
        ))}
      </div>
      <div className="tab-panels">
        {priceTabs.map((item) => (
          <div key={item.key} className="tab-panel" hidden={tab !== item.key}>
            {item.key === "sge" && sgeAgTdLatest && (
              <div className="sge-snapshot">
                <span className="sge-chip">Ag(T+D) {formatNumber(sgeAgTdLatest.price, 0)} 元/千克</span>
                <span className="sge-time">快照 {formatTradeTime(sgeAgTdLatest.tradeTime)} · 仅最新价无序列</span>
              </div>
            )}
            <MarketLineChart points={item.points} decimals={item.decimals} unit={item.unit} accent={item.accent} />
            {item.key === "ratio" && <RatioNote />}
          </div>
        ))}
      </div>
    </article>
  );
}

function StocksPanel() {
  const data = useMemo(alignStockSeries, []);
  const latest = data[data.length - 1];
  const previous = data.length > 1 ? data[data.length - 2] : null;
  const total = latest ? latest.comex + latest.shfe : null;
  const delta = latest && previous ? latest.comex + latest.shfe - (previous.comex + previous.shfe) : null;
  const sgeLatest = sgeInventory.length > 0 ? sgeInventory[sgeInventory.length - 1] : null;
  return (
    <article className="panel market-panel">
      <div className="panel-heading">
        <div><span>库存 · STOCKS</span><h3>交易所库存</h3></div>
        <div className="panel-stat">
          <small>{latest?.date ?? "—"} 合计</small>
          <strong>{total !== null ? `${formatNumber(total)} 吨` : "—"}</strong>
          <DeltaTag delta={delta} unit="吨" />
        </div>
      </div>
      <div className="chart-legend legend-top">
        <span className="legend-chip static"><i style={{ background: "#d9a441" }} />COMEX</span>
        <span className="legend-chip static"><i style={{ background: "#56c8dc" }} />上期所仓单</span>
      </div>
      <StocksAreaChart />
      {sgeLatest && (
        <div className="sge-stat">
          <div className="sge-stat-text">
            <small>上金所库存（周频）</small>
            <strong>{formatNumber(sgeLatest.value)} 吨</strong>
            <span>{sgeLatest.date} 更新</span>
          </div>
          <span className="sge-spark">
            <Sparkline values={sgeInventory.map((point) => point.value)} width={96} height={26} />
          </span>
        </div>
      )}
      <p className="chart-note">COMEX 与上期所库存为日频（堆叠合计），上金所库存为周频单列；COMEX 库存原始数据经金衡制换算为吨。</p>
    </article>
  );
}

function FundPanel() {
  const { latest, delta } = latestDelta(silverFundNav);
  return (
    <article className="panel market-panel">
      <div className="panel-heading">
        <div><span>基金 · FUND</span><h3>白银 LOF 基金（161226）</h3></div>
        <div className="panel-stat">
          <small>{latest?.date ?? "—"} 净值</small>
          <strong>{latest ? formatNumber(latest.value, 4) : "—"}</strong>
          <DeltaTag delta={delta} decimals={4} />
        </div>
      </div>
      <MarketLineChart points={silverFundNav} decimals={4} accent="silver" />
      <div className="fund-meta">
        <div><small>基金名称</small><strong>{silverFundSnapshot?.name ?? "—"}</strong></div>
        <div><small>最新规模</small><strong>{silverFundSnapshot ? `${formatNumber(silverFundSnapshot.scaleYi)} 亿元` : "—"}</strong></div>
        <div><small>基金代码</small><strong>161226</strong></div>
      </div>
    </article>
  );
}

function MarketSection({ onCopy, copied }: { onCopy: () => void; copied: boolean }) {
  return (
    <section id="market" className="section-block">
      <div className="section-heading">
        <div><span className="section-index">03</span><h2>市场脉搏 · 日频</h2></div>
        <p>Wind 日频行情、库存与基金净值，随取数脚本滚动更新</p>
      </div>
      <div className="market-source panel">
        <span className="source-tag">Wind · 日频 · 更新于 {formatFetchedAt(marketFetchedAt)}</span>
        <button className={`copy-chip ${copied ? "copied" : ""}`} onClick={onCopy} aria-label="复制取数命令">
          <code>npm run fetch:data</code>
          <span className="copy-state">{copied ? "已复制" : "复制"}</span>
        </button>
      </div>
      <div className="market-grid">
        <PricePanel />
        <StocksPanel />
        <FundPanel />
      </div>
    </section>
  );
}

function HistoryStrip({ history, unit }: { history: HistoryPoint[]; unit: string }) {
  if (history.length === 0) return <p className="history-empty">暂无历史数据，接入来源后开始积累。</p>;
  return (
    <div className="history-strip">
      {history.map((point) => (
        <div key={point.period} className={`history-cell ${point.score === null ? "baseline" : point.score > 0 ? "pos" : point.score < 0 ? "neg" : "flat"}`}>
          <span className="history-period">{point.period}</span>
          <strong>{formatScore(point.score)}</strong>
          <small>{point.score === null ? point.status : `${formatMetric(point.value, unit)}`}</small>
        </div>
      ))}
    </div>
  );
}

function DrawerChart({ history, unit }: { history: HistoryPoint[]; unit: string }) {
  const [hover, setHover] = useState<number | null>(null);
  const width = 460;
  const height = 150;
  const margin = { top: 12, right: 12, bottom: 24, left: 48 };
  if (history.length < 2) return null;
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;
  const values = history.map((point) => point.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const padding = (max - min || 1) * 0.14;
  const yMin = min - padding;
  const yMax = max + padding;
  const x = (index: number) => margin.left + (index * plotWidth) / (history.length - 1);
  const y = (value: number) => margin.top + ((yMax - value) / (yMax - yMin)) * plotHeight;
  const path = history.map((point, index) => `${index === 0 ? "M" : "L"}${x(index)},${y(point.value)}`).join(" ");
  const labelIndexes = [0, history.length - 1];

  const onMove = (event: ReactMouseEvent<SVGSVGElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const xPos = ((event.clientX - rect.left) / rect.width) * width;
    const index = Math.round(((xPos - margin.left) / plotWidth) * (history.length - 1));
    setHover(Math.max(0, Math.min(history.length - 1, index)));
  };
  const hoverPoint = hover !== null ? history[hover] : null;

  return (
    <div className="chart-wrap drawer-chart">
      <svg viewBox={`0 0 ${width} ${height}`} className="chart-svg" onMouseMove={onMove} onMouseLeave={() => setHover(null)}>
        <defs>
          <linearGradient id="drawerArea" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#d9a441" stopOpacity="0.24" />
            <stop offset="100%" stopColor="#d9a441" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={`${path} L${x(history.length - 1)},${y(yMin)} L${x(0)},${y(yMin)} Z`} fill="url(#drawerArea)" />
        <path d={path} className="market-line gold" />
        {history.map((point, index) => (
          <circle key={point.period} cx={x(index)} cy={y(point.value)} r={point.kind === "forecast" ? 4 : 2.6} className={point.kind === "forecast" ? "point forecast" : "spark-dot gold"} />
        ))}
        {labelIndexes.map((index) => (
          <text key={index} x={x(index)} y={height - 6} textAnchor="middle" className="axis-label">{history[index].period}</text>
        ))}
        {hover !== null && hoverPoint && (
          <g className="crosshair">
            <line x1={x(hover)} x2={x(hover)} y1={margin.top} y2={height - margin.bottom} className="crosshair-line" />
            <circle cx={x(hover)} cy={y(hoverPoint.value)} r="4.5" className="crosshair-dot" />
          </g>
        )}
      </svg>
      {hover !== null && hoverPoint && (
        <div className="chart-tooltip" style={{ left: `${(x(hover) / width) * 100}%` }}>
          <strong>{hoverPoint.period}</strong>
          <span>{formatMetric(hoverPoint.value, unit)}</span>
          <em>信号 {formatScore(hoverPoint.score)}</em>
        </div>
      )}
    </div>
  );
}

function ThresholdBar({ item }: { item: Indicator }) {
  const delta = item.value !== null && item.priorValue !== null ? item.value - item.priorValue : null;
  const span = item.upperThreshold - item.lowerThreshold;
  const rawPos = delta === null || span <= 0 ? null : (delta - item.lowerThreshold) / span;
  const pos = rawPos === null ? null : Math.min(1, Math.max(0, rawPos));
  const overflow = rawPos !== null && (rawPos > 1 || rawPos < 0);
  return (
    <div className="threshold-bar">
      <div className="threshold-head">
        <small>阈值区间</small>
        <small>{item.thresholdNote}</small>
      </div>
      <div className="threshold-track">
        <i className="threshold-fill" style={pos !== null ? { width: `${pos * 100}%` } : { width: "50%" }} />
        {pos !== null && <b className={`threshold-marker ${overflow ? "overflow" : ""}`} style={{ left: `${pos * 100}%` }} />}
      </div>
      <div className="threshold-labels">
        <span>下阈值 {formatMetric(item.lowerThreshold, item.unit)}</span>
        <span className="threshold-current">{delta === null ? "本期无变动值" : `变动 ${formatDelta(item)}`}</span>
        <span>上阈值 {formatMetric(item.upperThreshold, item.unit)}</span>
      </div>
    </div>
  );
}

export default function Home() {
  const [theme, setTheme] = useState("全部");
  const [status, setStatus] = useState("全部状态");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<"score" | "updatedAt" | null>(null);
  const [sortDir, setSortDir] = useState<1 | -1>(-1);
  const [selected, setSelected] = useState<Indicator | null>(null);
  const [lightMode, setLightMode] = useState(false);
  const [activeSection, setActiveSection] = useState("signals");
  const [yearIndex, setYearIndex] = useState(marketBalance.length - 1);
  const [playing, setPlaying] = useState(false);
  const [copied, setCopied] = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const copyTimer = useRef<number | null>(null);
  const { ref: heroMetaRef, inView: heroInView } = useInView<HTMLDivElement>();

  const dataReady = indicators.filter((item) => item.value !== null).length;
  const bullish = indicators.filter((item) => item.score > 0).length;
  const bearish = indicators.filter((item) => item.score < 0).length;
  const pending = indicators.filter((item) => item.dataStatus === "待接入").length;
  const balanceHistory = indicators.find((item) => item.id === 14)?.history ?? [];

  const readyCount = useCountUp(dataReady, heroInView);
  const bullCount = useCountUp(bullish, heroInView);
  const bearCount = useCountUp(bearish, heroInView);
  const triggerCount = useCountUp(triggers.length, heroInView);

  useEffect(() => {
    const saved = window.localStorage.getItem("ag-monitor-theme");
    if (saved === "light") setLightMode(true);
  }, []);

  const toggleTheme = () => {
    setLightMode((value) => {
      window.localStorage.setItem("ag-monitor-theme", value ? "dark" : "light");
      return !value;
    });
  };

  useEffect(() => {
    const ids = hasMarketData ? navItems.map((item) => item.id) : navItems.filter((item) => item.id !== "market").map((item) => item.id);
    const sections = ids.map((id) => document.getElementById(id)).filter((node): node is HTMLElement => node !== null);
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActiveSection(entry.target.id);
        }
      },
      { rootMargin: "-35% 0px -58% 0px" },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const typing = target instanceof HTMLInputElement || target instanceof HTMLSelectElement || target instanceof HTMLTextAreaElement;
      if (event.key === "/" && !typing) {
        event.preventDefault();
        searchRef.current?.focus();
      }
      if (event.key === "Escape") setSelected(null);
      if (selected && !typing && (event.key === "ArrowLeft" || event.key === "ArrowRight")) {
        const index = filtered.findIndex((item) => item.id === selected.id);
        if (index === -1) return;
        const next = event.key === "ArrowRight" ? filtered[index + 1] : filtered[index - 1];
        if (next) setSelected(next);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });

  useEffect(() => {
    if (!playing) return;
    const timer = window.setInterval(() => {
      setYearIndex((index) => (index + 1) % marketBalance.length);
    }, 950);
    return () => window.clearInterval(timer);
  }, [playing]);

  const filtered = useMemo(
    () =>
      indicators.filter((item) => {
        const themeMatch = theme === "全部" || item.theme === theme;
        const queryMatch = !query || `${item.name}${item.role}${item.note}`.toLowerCase().includes(query.toLowerCase());
        const statusMatch =
          status === "全部状态" ||
          (status === "利多" && item.score > 0) ||
          (status === "利空" && item.score < 0) ||
          (status === "待接入" && item.dataStatus === "待接入");
        return themeMatch && queryMatch && statusMatch;
      }),
    [theme, status, query],
  );

  const sorted = useMemo(() => {
    if (!sortKey) return filtered;
    return [...filtered].sort((a, b) => {
      if (sortKey === "score") return (a.score - b.score) * sortDir;
      return a.updatedAt.localeCompare(b.updatedAt) * sortDir;
    });
  }, [filtered, sortKey, sortDir]);

  const toggleSort = (key: "score" | "updatedAt") => {
    if (sortKey === key) {
      setSortDir((dir) => (dir === 1 ? -1 : 1));
    } else {
      setSortKey(key);
      setSortDir(-1);
    }
  };

  const sortMark = (key: "score" | "updatedAt") => (sortKey === key ? (sortDir === 1 ? "▲" : "▼") : "⇅");

  const openIndicator = (id: number) => {
    const target = indicators.find((item) => item.id === id);
    if (target) setSelected(target);
  };

  const copyCommand = async () => {
    const command = "npm run fetch:data";
    try {
      await navigator.clipboard.writeText(command);
    } catch {
      const textarea = document.createElement("textarea");
      textarea.value = command;
      document.body.appendChild(textarea);
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }
    setCopied(true);
    if (copyTimer.current) window.clearTimeout(copyTimer.current);
    copyTimer.current = window.setTimeout(() => setCopied(false), 1600);
  };

  const currentYear = marketBalance[yearIndex];

  return (
    <div className={`dashboard-shell ${lightMode ? "light-mode" : ""}`}>
      <div className="ticker" aria-label="信号触发滚动播报">
        <div className="ticker-chip">
          <i className="live-dot" />
          信号触发
        </div>
        <div className="ticker-mask">
          <div className="ticker-track">
            {[...triggers, ...triggers].map((event, index) => (
              <button key={`${event.id}-${index}`} className="ticker-item" onClick={() => openIndicator(event.indicatorId)} tabIndex={index < triggers.length ? 0 : -1}>
                <span className="ticker-period">{event.period}</span>
                <strong>{event.name}</strong>
                <span className={`ticker-kind ${event.severity}`}>{event.kind}</span>
                <span className="ticker-score">{formatScore(event.prevScore)} → {formatScore(event.score)}</span>
                <i className="ticker-sep">◆</i>
              </button>
            ))}
          </div>
        </div>
      </div>

      <header className="topbar">
        <a className="brand" href="#top" aria-label="回到顶部">
          <span className="brand-mark"><b>Ag</b><small>47</small></span>
          <span><strong>白银产业监测</strong><small>Silver Intelligence Monitor</small></span>
        </a>
        <nav aria-label="页面导航">
          {navItems
            .filter((item) => hasMarketData || item.id !== "market")
            .map((item) => (
              <a key={item.id} href={`#${item.id}`} className={activeSection === item.id ? "active" : ""}>{item.label}</a>
            ))}
        </nav>
        <div className="top-actions">
          {marketFetchedAt && <span className="data-clock" title="市场数据取数时间">数据 {formatFetchedAt(marketFetchedAt)}</span>}
          <button className="icon-button" onClick={toggleTheme} aria-label="切换明暗主题">{lightMode ? "深色" : "浅色"}</button>
          <a className="download-button" href="/白银五项固定监测看板_20260719.xlsx" download>下载Excel底稿</a>
        </div>
      </header>

      <main id="top">
        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="live-dot" /> 产业需求 · 供需缺口 · 资金流动性</div>
            <h1>用五项信号，看清白银<br /><em>真正的边际变化</em></h1>
            <p>将光伏降银、电气化增长、功率封装、AI物理基础设施与供应紧张度放在同一监测框架中。所有银量统一采用吨。</p>
            <div className="hero-meta" ref={heroMetaRef}>
              <span>数据截至 {asOfDate}</span>
              <span><b className="count">{readyCount}</b>/17 项已接入</span>
              <span>利多 <b className="count up">{bullCount}</b> · 利空 <b className="count down">{bearCount}</b></span>
              <span>触发 <b className="count">{triggerCount}</b> 条</span>
            </div>
          </div>
          <aside className="pulse-card" aria-label="当前市场脉冲">
            <div className="pulse-card-head">
              <span>紧张度仪表 · PULSE</span>
              <span className="live-chip"><i className="live-dot" />日频联动</span>
            </div>
            <PulseGauge />
            <div className="pulse-stats">
              <div><strong className="up">{bullish}</strong><small>利多</small></div>
              <div><strong className="down">{bearish}</strong><small>利空</small></div>
              <div><strong>{pending}</strong><small>待接入</small></div>
            </div>
            <p className="pulse-desc">需求结构分化：光伏用银明显下降，但非光伏电气电子增长、市场缺口延续，暂未形成单向总量信号。</p>
          </aside>
        </section>

        <section id="signals" className="section-block">
          <div className="section-heading">
            <div><span className="section-index">01</span><h2>五项固定监测</h2></div>
            <p>点击卡片可直接筛选下方指标库</p>
          </div>
          <div className="signal-grid">
            {themeSummaries.map((item) => {
              const spark = themeSparkValues(item.theme);
              const deltaTone = item.delta.includes("-") ? "down" : item.delta.includes("+") ? "up" : "flat";
              return (
                <button key={item.theme} className={`signal-card ${item.tone} ${theme === item.theme ? "selected" : ""}`} onClick={() => setTheme(theme === item.theme ? "全部" : item.theme)}>
                  <div className="signal-card-top">
                    <span className="theme-icon">{item.icon}</span>
                    <LedBadge tone={item.tone} status={item.status} />
                  </div>
                  <h3>{item.theme}</h3>
                  <strong className="signal-value">{item.value}</strong>
                  <div className={`signal-delta ${deltaTone}`}>
                    {deltaTone === "up" && "▲ "}
                    {deltaTone === "down" && "▼ "}
                    {item.delta}
                  </div>
                  <p>{item.description}</p>
                  <div className="signal-spark">
                    <Sparkline values={spark} tone={item.score > 0 ? "pos" : item.score < 0 ? "neg" : "flat"} />
                  </div>
                  <ScoreScale score={item.score} />
                </button>
              );
            })}
          </div>
        </section>

        <section id="trends" className="section-block">
          <div className="section-heading">
            <div><span className="section-index">02</span><h2>趋势与结构</h2></div>
            <p>拖动时间轴逐年回放，悬停图形查看精确数值</p>
          </div>
          <div className="analytics-grid">
            <article className="panel chart-panel balance-panel">
              <span className="year-watermark" aria-hidden="true">{currentYear.year}</span>
              <div className="panel-heading">
                <div><span>供需紧张度</span><h3>全球白银市场平衡</h3></div>
                <div className="panel-stat">
                  <small>{currentYear.year}{currentYear.type === "预测" ? "F" : "A"}</small>
                  <strong>{formatNumber(currentYear.value)} 吨</strong>
                </div>
              </div>
              <BalanceChart yearIndex={yearIndex} onOpenIndicator={() => openIndicator(14)} />
              <div className="scrubber">
                <button className="play-button" onClick={() => setPlaying((value) => !value)} aria-label={playing ? "暂停回放" : "播放回放"}>
                  {playing ? (
                    <svg viewBox="0 0 12 12" aria-hidden="true"><rect x="2" y="1.5" width="3" height="9" /><rect x="7" y="1.5" width="3" height="9" /></svg>
                  ) : (
                    <svg viewBox="0 0 12 12" aria-hidden="true"><path d="M3 1.5 L10 6 L3 10.5 Z" /></svg>
                  )}
                </button>
                <input
                  type="range"
                  min={0}
                  max={marketBalance.length - 1}
                  value={yearIndex}
                  onChange={(event) => {
                    setPlaying(false);
                    setYearIndex(Number(event.target.value));
                  }}
                  style={{ "--fill": `${(yearIndex / (marketBalance.length - 1)) * 100}%` } as CSSProperties}
                  aria-label="年份时间轴"
                />
                <div className="scrubber-years">
                  <span>{marketBalance[0].year}</span>
                  <strong>{currentYear.year}</strong>
                  <span>{marketBalance[marketBalance.length - 1].year}</span>
                </div>
              </div>
              <p className="chart-note">负值代表供应缺口。2026年缺口较2025年扩大约186.6吨，不包含ETP资金流；预测年份以斜纹标记，点击数据点查看指标详情。</p>
            </article>
            <article className="panel chart-panel">
              <div className="panel-heading">
                <div><span>工业结构</span><h3>主要工业板块用银变化</h3></div>
                <div className="panel-stat"><small>2026F工业需求</small><strong>19,893.8 吨</strong></div>
              </div>
              <IndustrialChart />
              <p className="chart-note">2026年工业总量下降主要来自光伏；非光伏电气电子仍保持增长。点击图例可切换单个板块显隐。</p>
            </article>
          </div>
          <div className="action-panel panel">
            <div className="panel-heading"><div><span>监测节奏</span><h3>下一轮数据更新清单</h3></div><span className="coverage-pill">8项待接入</span></div>
            <div className="action-list">
              {actions.map((action, index) => (
                <div className="action-row" key={action.task}>
                  <span className="action-number">0{index + 1}</span>
                  <span className="action-cadence">{action.cadence}</span>
                  <div><strong>{action.task}</strong><small>{action.owner}</small></div>
                  <span className={`action-status ${action.status === "最高优先" ? "priority" : ""}`}>{action.status}</span>
                </div>
              ))}
            </div>
          </div>
        </section>

        {hasMarketData && <MarketSection onCopy={copyCommand} copied={copied} />}

        <section id="dynamics" className="section-block">
          <div className="section-heading">
            <div><span className="section-index">04</span><h2>信号动态</h2></div>
            <p>按期间排列，最新在上；点击记录打开对应指标详情</p>
          </div>
          <div className="dynamics-grid">
            <article className="panel trigger-panel">
              <div className="panel-heading"><div><span>触发日志</span><h3>阈值触发记录</h3></div><span className="coverage-pill">{triggers.length} 条</span></div>
              <div className="trigger-list">
                {[...triggers].reverse().map((event) => {
                  const indicator = indicators.find((item) => item.id === event.indicatorId);
                  return (
                    <button key={event.id} className="trigger-row" onClick={() => indicator && setSelected(indicator)}>
                      <span className="trigger-period">{event.period}</span>
                      <span className={`kind-badge ${event.severity}`}>{event.kind}</span>
                      <span className="trigger-text"><strong>{event.name}</strong><small>{event.description}</small></span>
                      <span className="trigger-score">{formatScore(event.prevScore)}<i>→</i>{formatScore(event.score)}</span>
                    </button>
                  );
                })}
              </div>
              <p className="chart-note">触发规则：分数升为 +2 记“站上强利多”，降为 -2 记“跌入强利空”，非零方向反转记“方向反转”，离开 ±2 记“强信号解除”。</p>
            </article>
            <article className="panel chart-panel">
              <div className="panel-heading"><div><span>信号历史</span><h3>全球市场平衡 · 年度信号</h3></div><div className="panel-stat"><small>2026F</small><strong>+2 强利多</strong></div></div>
              <ScoreBarsChart history={balanceHistory} />
              <p className="chart-note">缺口由收窄转为扩大，2026年信号从强利空翻为强利多；每项指标的完整历史见详情侧栏。</p>
            </article>
          </div>
        </section>

        <section id="indicators" className="section-block indicators-section">
          <div className="section-heading">
            <div><span className="section-index">05</span><h2>17项指标库</h2></div>
            <p>每项指标保留频率、阈值、数据状态与来源</p>
          </div>
          <div className="filterbar">
            <div className="radar-filter" role="radiogroup" aria-label="监测主题筛选">
              {themes.map((item) => (
                <button
                  key={item}
                  role="radio"
                  aria-checked={theme === item}
                  className={`radar-node ${theme === item ? "active" : ""}`}
                  onClick={() => setTheme(item)}
                >
                  <i className="node-dot" />
                  <span>{item === "AI物理基础设施" ? "AI基建" : item}</span>
                </button>
              ))}
            </div>
            <div className="filter-controls">
              <label>
                <span className="sr-only">按名称搜索，斜杠键聚焦</span>
                <input ref={searchRef} value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索指标… ( / 聚焦 )" />
              </label>
              <label>
                <span className="sr-only">状态筛选</span>
                <select value={status} onChange={(event) => setStatus(event.target.value)}>{statusOptions.map((item) => <option key={item}>{item}</option>)}</select>
              </label>
            </div>
          </div>
          <div className="table-card">
            <div className="table-head">
              <span>指标</span>
              <span>最新值</span>
              <span>本期变化</span>
              <span><button className="sort-button" onClick={() => toggleSort("score")}>信号 <i>{sortMark("score")}</i></button></span>
              <span>走势</span>
              <span><button className="sort-button" onClick={() => toggleSort("updatedAt")}>频率 / 状态与更新 <i>{sortMark("updatedAt")}</i></button></span>
              <span />
            </div>
            {sorted.map((item) => (
              <button className="table-row" key={item.id} onClick={() => setSelected(item)}>
                <span className="indicator-name"><i>{String(item.id).padStart(2, "0")}</i><span><strong>{item.name}</strong><small>{item.theme} · {item.role}</small></span></span>
                <span className={item.value === null ? "muted-value" : "metric-value"}><strong>{formatMetric(item.value, item.unit)}</strong><small>{item.period ?? "暂无期间"}</small></span>
                <span><strong>{formatDelta(item)}</strong><small>{item.priorPeriod ? `较${item.priorPeriod}` : "缺少上期值"}</small></span>
                <span><SignalBadge tone={item.tone} status={item.status} /><small>分数 {item.score > 0 ? `+${item.score}` : item.score}</small></span>
                <span className="row-spark">
                  {item.history.length > 0 ? (
                    <Sparkline values={item.history.map((point) => point.value)} tone={item.score > 0 ? "pos" : item.score < 0 ? "neg" : "flat"} />
                  ) : (
                    <em>—</em>
                  )}
                </span>
                <span><strong>{item.frequency}</strong><small>{item.dataStatus} · {item.updatedAt}</small></span>
                <span className="row-arrow">↗</span>
              </button>
            ))}
            {sorted.length === 0 && <div className="empty-state">没有符合当前筛选条件的指标。</div>}
          </div>
        </section>

        <section className="method-section">
          <article><span>口径</span><h3>信号不是价格预测</h3><p>+2代表需求增强、供应收缩或流动性明显趋紧；-2代表需求显著减弱、供应增加或流动性明显宽松。代理指标不可与吨数直接相加。</p></article>
          <article><span>数据质量</span><h3>缺失值保持为空</h3><p>AI服务器、银烧结、库存和租借利率尚无统一公开口径，明确标记“待接入”，不以零值代替，也不制造虚假精度。</p></article>
          <article><span>主要来源</span><h3>公开权威基线</h3><p><a href={sources.wss.url} target="_blank" rel="noreferrer">World Silver Survey 2026</a>、<a href={sources.ieaAi.url} target="_blank" rel="noreferrer">IEA Energy and AI</a>等；点击任一指标可查看具体来源。</p></article>
        </section>
      </main>

      <footer>
        <span>Project-006 · 白银产业固定监测</span>
        <span>本地快照 · 数据截至 {asOfDate}{marketFetchedAt ? ` · 市场数据 ${formatFetchedAt(marketFetchedAt)}` : ""} · 生成于 {generatedAt.slice(0, 10)}</span>
      </footer>

      {selected && (
        <div className="modal-backdrop" role="presentation" onMouseDown={() => setSelected(null)}>
          <aside className="detail-drawer" role="dialog" aria-modal="true" aria-labelledby="detail-title" onMouseDown={(event) => event.stopPropagation()}>
            <button className="close-button" onClick={() => setSelected(null)} aria-label="关闭详情">×</button>
            <span className="drawer-kicker">{selected.theme} · {selected.role}</span>
            <div className="drawer-title-row">
              <h2 id="detail-title">{selected.name}</h2>
              {selected.dataStatus === "已接入" && <span className="wind-pill">Wind 日频已接入</span>}
            </div>
            <div className="drawer-value"><strong>{formatMetric(selected.value, selected.unit)}</strong><SignalBadge tone={selected.tone} status={selected.status} /></div>
            {selected.history.length > 1 && <DrawerChart history={selected.history} unit={selected.unit} />}
            <div className="drawer-history">
              <small>历史信号</small>
              <HistoryStrip history={selected.history} unit={selected.unit} />
            </div>
            <ThresholdBar item={selected} />
            <p className="drawer-note">{selected.note}</p>
            <dl className="detail-grid">
              <div><dt>最新期间</dt><dd>{selected.period ?? "待接入"}</dd></div>
              <div><dt>上期值</dt><dd>{formatMetric(selected.priorValue, selected.unit)}</dd></div>
              <div><dt>本期变化</dt><dd>{formatDelta(selected)}</dd></div>
              <div><dt>更新频率</dt><dd>{selected.frequency}</dd></div>
              <div><dt>利多方向</dt><dd>{selected.direction}</dd></div>
              <div><dt>数据状态</dt><dd>{selected.dataStatus}</dd></div>
              <div><dt>强信号上阈值</dt><dd>{formatMetric(selected.upperThreshold, selected.unit)}</dd></div>
              <div><dt>强信号下阈值</dt><dd>{formatMetric(selected.lowerThreshold, selected.unit)}</dd></div>
            </dl>
            <div className="drawer-source"><small>主要来源</small>{selected.sourceUrl ? <a href={selected.sourceUrl} target="_blank" rel="noreferrer">{selected.sourceLabel}<span>↗</span></a> : <strong>待确定可靠数据源</strong>}</div>
            <div className="drawer-rule"><small>信号解释</small><p>当前分数为{selected.score > 0 ? `+${selected.score}` : selected.score}。只有最新值和上期值齐全时才判断方向与强弱；缺少上期值时保留为基线。</p></div>
            <div className="drawer-nav-hint">← → 在筛选结果内切换指标 · Esc 关闭</div>
          </aside>
        </div>
      )}
    </div>
  );
}
