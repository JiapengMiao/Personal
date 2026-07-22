import { useEffect, useMemo, useRef, useState } from "react";
import type { Indicator, MonitoringData, Trigger } from "../lib/types";
import { baseAxis, baseTooltip, getPalette, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading, SignalBadge, Sparkline } from "./shared";
import { formatNumber, formatScore } from "../lib/format";

// ——— 10 信号动态 ———
export function DynamicsSection({
  monitoring,
  theme,
  onOpenTrigger,
}: {
  monitoring: MonitoringData;
  theme: ThemeMode;
  onOpenTrigger: (trigger: Trigger) => void;
}) {
  const balanceHistory = monitoring.indicators.find((i) => i.id === 14)?.history ?? [];
  const reversed = [...monitoring.triggers].reverse();
  return (
    <section className="section-block" id="dynamics">
      <SectionHeading index="11" title="信号动态" desc="触发记录与市场平衡历年信号分数" id="dynamics" />
      <div className="dynamics-grid">
        <article className="panel trigger-panel">
          <div className="panel-heading">
            <div>
              <span>触发 · TRIGGERS</span>
              <h3>信号触发记录</h3>
            </div>
            <div className="panel-stat">
              <small>倒序排列 · 点击开指标详情</small>
              <strong>{monitoring.triggers.length} 条</strong>
            </div>
          </div>
          <div className="trigger-list">
            {reversed.map((t) => (
              <button key={t.id} className="trigger-row" onClick={() => onOpenTrigger(t)}>
                <span className="trigger-period">{t.period}</span>
                <span className={`kind-badge ${t.severity}`}>{t.kind}</span>
                <span className="trigger-text">
                  <strong>{t.name}</strong>
                  <small>{t.description}</small>
                </span>
                <span className="trigger-score">
                  {t.prevScore ?? "—"}
                  <i>→</i>
                  {t.score ?? "—"}
                </span>
              </button>
            ))}
          </div>
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>分数 · SCORE</span>
              <h3>全球市场平衡 · 历年信号</h3>
            </div>
            <div className="panel-stat">
              <small>范围 -2 ~ +2</small>
              <strong>同比变动打分</strong>
            </div>
          </div>
          <ScoreBars history={balanceHistory} theme={theme} />
        </article>
      </div>
    </section>
  );
}

function ScoreBars({ history, theme }: { history: Indicator["history"]; theme: ThemeMode }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      return {
        animationDuration: 400,
        grid: { top: 26, right: 16, bottom: 28, left: 40 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const arr = params as { dataIndex: number }[];
            const idx = arr[0]?.dataIndex ?? 0;
            const h = history[idx];
            if (!h) return "";
            return `<strong>${h.period}</strong><br/>信号 ${formatScore(h.score)} · ${h.status}<br/>${formatNumber(h.value)} 吨`;
          },
        },
        xAxis: { type: "category", data: history.map((h) => h.period), ...baseAxis(p) },
        yAxis: {
          type: "value",
          min: -2.5,
          max: 2.5,
          interval: 1,
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => (v > 0 ? `+${v}` : `${v}`) },
        },
        series: [
          {
            type: "bar",
            data: history.map((h) => (h.score === null ? null : h.score)),
            barMaxWidth: 34,
            itemStyle: {
              borderRadius: 3,
              color: (params: { value: number | null }) => {
                const v = params.value;
                if (v === null || v === 0) return p.weak;
                return v > 0 ? p.up : p.down;
              },
            },
            label: {
              show: true,
              position: "top",
              color: p.sub,
              fontFamily: "JetBrains Mono",
              fontSize: 11,
              fontWeight: 700,
              formatter: (params: { value: number | null }) => (params.value === null ? "" : formatScore(params.value)),
            },
            markLine: {
              silent: true,
              symbol: "none",
              label: { show: false },
              lineStyle: { color: p.edge, width: 1.4 },
              data: [{ yAxis: 0 }],
            },
          },
        ],
      };
    };
  }, [history, theme]);
  const ref = useEChart(build, [history], theme);
  return <div ref={ref} className="echart chart-wrap" style={{ height: 300 }} />;
}

// ——— 11 十七项指标库 ———
type SortKey = "value" | "score";

export function IndicatorLibrarySection({
  monitoring,
  theme,
  selectedTheme,
  onSelectTheme,
  onOpen,
}: {
  monitoring: MonitoringData;
  theme: ThemeMode;
  selectedTheme: string | null;
  onSelectTheme: (t: string | null) => void;
  onOpen: (indicator: Indicator, list: Indicator[]) => void;
}) {
  const [status, setStatus] = useState("全部");
  const [query, setQuery] = useState("");
  const [sortKey, setSortKey] = useState<SortKey | null>(null);
  const [sortAsc, setSortAsc] = useState(false);
  const searchRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "/" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "SELECT") {
        e.preventDefault();
        searchRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const themes = useMemo(() => monitoring.themeSummaries.map((t) => t.theme), [monitoring]);

  const filtered = useMemo(() => {
    let list = monitoring.indicators.slice();
    if (selectedTheme) list = list.filter((i) => i.theme === selectedTheme);
    if (status !== "全部") {
      if (status === "待接入") list = list.filter((i) => i.dataStatus === "待接入" || i.tone === "missing");
      else if (status === "利多") list = list.filter((i) => i.score !== null && i.score > 0);
      else if (status === "利空") list = list.filter((i) => i.score !== null && i.score < 0);
    }
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      list = list.filter((i) => i.name.toLowerCase().includes(q) || i.theme.toLowerCase().includes(q));
    }
    if (sortKey) {
      list.sort((a, b) => {
        const av = sortKey === "value" ? a.value ?? -Infinity : a.score ?? -Infinity;
        const bv = sortKey === "value" ? b.value ?? -Infinity : b.score ?? -Infinity;
        return sortAsc ? (av as number) - (bv as number) : (bv as number) - (av as number);
      });
    }
    return list;
  }, [monitoring, selectedTheme, status, query, sortKey, sortAsc]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      if (sortAsc) setSortKey(null);
      else setSortAsc(true);
    } else {
      setSortKey(key);
      setSortAsc(false);
    }
  };

  return (
    <section className="section-block indicators-section" id="indicators">
      <SectionHeading index="12" title="十七项指标库" desc="主题 / 状态 / 文本三维筛选，点击行打开详情抽屉" id="indicators" />
      <div className="filterbar">
        <div className="radar-filter" role="tablist" aria-label="主题筛选">
          <button className={`radar-node ${selectedTheme === null ? "active" : ""}`} onClick={() => onSelectTheme(null)}>
            <i className="node-dot" />
            全部
          </button>
          {themes.map((t) => (
            <button key={t} className={`radar-node ${selectedTheme === t ? "active" : ""}`} onClick={() => onSelectTheme(selectedTheme === t ? null : t)}>
              <i className="node-dot" />
              {t}
            </button>
          ))}
        </div>
        <div className="filter-controls">
          <input
            ref={searchRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="搜索指标…（按 / 聚焦）"
            aria-label="搜索指标"
          />
          <select value={status} onChange={(e) => setStatus(e.target.value)} aria-label="状态筛选">
            {["全部", "利多", "利空", "待接入"].map((s) => (
              <option key={s} value={s}>
                {s === "全部" ? "全部状态" : s}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="table-card">
        <div className="table-head">
          <span>指标</span>
          <span>
            <button className="sort-button" onClick={() => toggleSort("value")}>
              最新值{sortKey === "value" ? <i>{sortAsc ? " ↑" : " ↓"}</i> : null}
            </button>
          </span>
          <span>本期变化</span>
          <span>信号</span>
          <span>走势</span>
          <span>
            <button className="sort-button" onClick={() => toggleSort("score")}>
              分数 · 频率{sortKey === "score" ? <i>{sortAsc ? " ↑" : " ↓"}</i> : null}
            </button>
          </span>
          <span />
        </div>
        {filtered.length === 0 && <div className="empty-state">没有匹配的指标，请调整筛选条件。</div>}
        {filtered.map((ind) => {
          const delta =
            ind.value !== null && ind.priorValue !== null ? ind.value - ind.priorValue : null;
          const sparkTone = ind.score !== null && ind.score > 0 ? "pos" : ind.score !== null && ind.score < 0 ? "neg" : undefined;
          return (
            <button key={ind.id} className="table-row" onClick={() => onOpen(ind, filtered)}>
              <span className="indicator-name">
                <i>{String(ind.id).padStart(2, "0")}</i>
                <span>
                  <strong>{ind.name}</strong>
                  <small>
                    {ind.theme} · {ind.role}
                  </small>
                </span>
              </span>
              <span className={`metric-value ${ind.value === null ? "muted-value" : ""}`}>
                <strong>{ind.value === null ? "待接入" : formatNumber(ind.value)}</strong>
                <small>{ind.value === null ? ind.dataStatus : `${ind.unit} · ${ind.period}`}</small>
              </span>
              <span>
                <strong className={delta !== null && delta > 0 ? "metric-value" : ""} style={{ color: delta === null ? "var(--weak)" : delta > 0 ? "var(--up)" : delta < 0 ? "var(--down)" : "var(--weak)" }}>
                  {delta === null ? "—" : `${delta > 0 ? "+" : ""}${formatNumber(delta)}`}
                </strong>
                <small>
                  vs {ind.priorPeriod}
                </small>
              </span>
              <span>
                <SignalBadge tone={ind.tone} status={ind.status} />
              </span>
              <span className="row-spark">
                {ind.history.length > 0 ? (
                  <Sparkline values={ind.history.map((h) => h.value)} tone={sparkTone} width={64} height={22} />
                ) : (
                  <em>无历史</em>
                )}
              </span>
              <span>
                <strong>{formatScore(ind.score)}</strong>
                <small>{ind.frequency}</small>
              </span>
              <span className="row-arrow">→</span>
            </button>
          );
        })}
      </div>
    </section>
  );
}

// ——— 详情抽屉 ———
export function IndicatorDrawer({
  indicator,
  list,
  theme,
  onClose,
  onNavigate,
}: {
  indicator: Indicator;
  list: Indicator[];
  theme: ThemeMode;
  onClose: () => void;
  onNavigate: (indicator: Indicator) => void;
}) {
  const index = list.findIndex((i) => i.id === indicator.id);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowLeft" && index > 0) onNavigate(list[index - 1]);
      if (e.key === "ArrowRight" && index >= 0 && index < list.length - 1) onNavigate(list[index + 1]);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, list, onClose, onNavigate]);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <aside className="detail-drawer" onClick={(e) => e.stopPropagation()} role="dialog" aria-label={`${indicator.name} 详情`}>
        <button className="close-button" onClick={onClose} aria-label="关闭">
          ×
        </button>
        <span className="drawer-kicker">
          {indicator.theme} · {indicator.role} · #{String(indicator.id).padStart(2, "0")}
        </span>
        <div className="drawer-title-row">
          <h2>{indicator.name}</h2>
          <SignalBadge tone={indicator.tone} status={indicator.status} />
        </div>
        <div className="drawer-value">
          <strong>{indicator.value === null ? "待接入" : `${formatNumber(indicator.value)} ${indicator.unit}`}</strong>
          <span className="data-clock">{indicator.period}</span>
        </div>
        {indicator.history.length > 1 && <DrawerChart indicator={indicator} theme={theme} />}
        {indicator.upperThreshold !== null && indicator.lowerThreshold !== null && (
          <ThresholdBar indicator={indicator} />
        )}
        {indicator.note && (
          <div className="drawer-rule">
            <small>口径备注</small>
            <p>{indicator.note}</p>
          </div>
        )}
        <div className="drawer-history">
          <small>历史读数 · HISTORY</small>
          <div className="history-strip">
            {[...indicator.history].reverse().slice(0, 8).map((h) => {
              const cls = h.score === null ? "flat" : h.score > 0 ? "pos" : h.score < 0 ? "neg" : "flat";
              return (
                <div key={h.period} className={`history-cell ${cls}`}>
                  <span className="history-period">{h.period}</span>
                  <strong>{formatNumber(h.value)}</strong>
                  <small>{h.status}</small>
                </div>
              );
            })}
          </div>
        </div>
        <dl className="detail-grid" style={{ marginTop: 20 }}>
          <div>
            <dt>周期</dt>
            <dd>{indicator.period}</dd>
          </div>
          <div>
            <dt>单位</dt>
            <dd>{indicator.unit}</dd>
          </div>
          <div>
            <dt>方向</dt>
            <dd>{indicator.direction}</dd>
          </div>
          <div>
            <dt>频率</dt>
            <dd>{indicator.frequency}</dd>
          </div>
          <div>
            <dt>更新日期</dt>
            <dd>{indicator.updatedAt}</dd>
          </div>
          <div>
            <dt>数据状态</dt>
            <dd>{indicator.dataStatus}</dd>
          </div>
        </dl>
        <div className="drawer-source">
          <small>数据来源 · SOURCE</small>
          <a href={indicator.sourceUrl} target="_blank" rel="noreferrer">
            <strong>{indicator.sourceLabel}</strong>
            <span>↗</span>
          </a>
        </div>
        <p className="drawer-nav-hint">
          {index + 1} / {list.length} · ← → 切换 · Esc 关闭
        </p>
      </aside>
    </div>
  );
}

function DrawerChart({ indicator, theme }: { indicator: Indicator; theme: ThemeMode }) {
  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      return {
        animationDuration: 400,
        grid: { top: 20, right: 16, bottom: 28, left: 60 },
        tooltip: {
          trigger: "axis",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const arr = params as { dataIndex: number }[];
            const h = indicator.history[arr[0]?.dataIndex ?? 0];
            if (!h) return "";
            return `<strong>${h.period}</strong><br/>${formatNumber(h.value)} ${indicator.unit}<br/>信号 ${formatScore(h.score)} · ${h.status}`;
          },
        },
        xAxis: { type: "category", data: indicator.history.map((h) => h.period), ...baseAxis(p), boundaryGap: false },
        yAxis: {
          type: "value",
          scale: true,
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
        },
        series: [
          {
            type: "line",
            data: indicator.history.map((h) => h.value),
            symbol: "circle",
            symbolSize: 5,
            lineStyle: { width: 2, color: p.gold },
            itemStyle: { color: p.gold, borderColor: p.panel, borderWidth: 2 },
            areaStyle: {
              color: {
                type: "linear",
                x: 0, y: 0, x2: 0, y2: 1,
                colorStops: [
                  { offset: 0, color: theme === "light" ? "rgba(154,109,18,.16)" : "rgba(217,164,65,.22)" },
                  { offset: 1, color: "rgba(217,164,65,0)" },
                ],
              },
            },
          },
        ],
      };
    };
  }, [indicator, theme]);
  const ref = useEChart(build, [indicator], theme);
  return <div ref={ref} className="echart drawer-chart" style={{ height: 220 }} />;
}

function ThresholdBar({ indicator }: { indicator: Indicator }) {
  const lo = indicator.lowerThreshold!;
  const hi = indicator.upperThreshold!;
  const v = indicator.value;
  const pct = v === null ? null : Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100));
  const overflow = v !== null && (v < lo || v > hi);
  return (
    <div className="threshold-bar">
      <div className="threshold-head">
        <small>阈值区间 · {indicator.thresholdNote}</small>
        <small>方向：{indicator.direction}</small>
      </div>
      <div className="threshold-track">
        {pct !== null && (
          <div className={`threshold-marker ${overflow ? "overflow" : ""}`} style={{ left: `${pct}%` }} />
        )}
      </div>
      <div className="threshold-labels">
        <span>下限 {formatNumber(lo)}</span>
        <span className="threshold-current">当前 {v === null ? "—" : formatNumber(v)}</span>
        <span>上限 {formatNumber(hi)}</span>
      </div>
    </div>
  );
}
