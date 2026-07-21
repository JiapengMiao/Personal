import { useMemo } from "react";
import type { DashboardData, Trigger } from "../lib/types";
import { formatFetchedAt, formatNumber, lastActualDate, lastNonNull, lastPoint, shortMd } from "../lib/format";
import { useCountUp, useInView } from "./shared";

// ——— 信号跑马灯 ———
export function Ticker({ triggers, onOpen }: { triggers: Trigger[]; onOpen: (trigger: Trigger) => void }) {
  const items = useMemo(() => [...triggers, ...triggers], [triggers]);
  return (
    <div className="ticker">
      <div className="ticker-chip">
        <i className="live-dot" style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor" }} />
        信号触发 · TRIGGERS
      </div>
      <div className="ticker-mask">
        <div className="ticker-track">
          {items.map((t, i) => (
            <button key={`${t.id}-${i}`} className="ticker-item" onClick={() => onOpen(t)}>
              <i className={`ticker-sev-dot ${t.severity}`} />
              <span className="ticker-period">{t.period}</span>
              <strong>{t.name}</strong>
              <span className={`ticker-kind ${t.severity}`}>{t.kind}</span>
              <span className="ticker-score">
                {t.prevScore ?? "—"}→{t.score ?? "—"}
              </span>
              <i className="ticker-sep">/</i>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

// ——— 顶栏 ———
export const NAV_ITEMS = [
  { id: "signals", label: "监测" },
  { id: "trends", label: "趋势" },
  { id: "market", label: "市场" },
  { id: "daily", label: "库存" },
  { id: "positions", label: "持仓" },
  { id: "hktrade", label: "贸易" },
  { id: "basis", label: "基差" },
  { id: "season", label: "季节" },
  { id: "indicators", label: "指标库" },
];

export function Topbar({
  active,
  asOf,
  dailyAsOf,
  theme,
  zoom,
  onToggleTheme,
  onZoom,
}: {
  active: string;
  asOf: string;
  dailyAsOf: string;
  theme: "dark" | "light";
  zoom: number;
  onToggleTheme: () => void;
  onZoom: (z: number) => void;
}) {
  return (
    <header className="topbar">
      <a className="brand" href="#top">
        <span className="brand-mark">
          <b>Ag</b>
          <small>47</small>
        </span>
        <span>
          <strong>白银数据全景看板</strong>
          <small>SILVER PANORAMA</small>
        </span>
      </a>
      <nav>
        {NAV_ITEMS.map((item) => (
          <a key={item.id} href={`#${item.id}`} className={active === item.id ? "active" : ""}>
            {item.label}
          </a>
        ))}
      </nav>
      <div className="top-actions">
        <span className="data-clock">
          监测 {asOf} · 日频 {dailyAsOf}
        </span>
        <div className="zoom-ctl" role="group" aria-label="演示缩放(投屏放大)">
          <button
            className="zoom-btn"
            onClick={() => onZoom(Math.max(100, zoom - 25))}
            disabled={zoom <= 100}
            aria-label="缩小"
          >
            A−
          </button>
          <span className="zoom-val">{zoom}%</span>
          <button
            className="zoom-btn"
            onClick={() => onZoom(Math.min(200, zoom + 25))}
            disabled={zoom >= 200}
            aria-label="放大"
          >
            A+
          </button>
        </div>
        <button className="icon-button" onClick={onToggleTheme} aria-label="切换明暗主题">
          {theme === "dark" ? "◐ 浅色" : "◑ 深色"}
        </button>
        <a className="download-button" href="/白银五项固定监测看板_20260719.xlsx" download>
          下载Excel底稿
        </a>
      </div>
    </header>
  );
}

// ——— Hero ———
function CountBadge({ label, target, decimals = 0, unit, active }: { label: string; target: number; decimals?: number; unit: string; active: boolean }) {
  const v = useCountUp(target, active, 1100);
  return (
    <span>
      {label} <b className="count">{formatNumber(v, decimals)}</b> {unit}
    </span>
  );
}

export function Hero({ data }: { data: DashboardData }) {
  const { ref, inView } = useInView<HTMLDivElement>(0.25);
  const agtdClose = lastNonNull(data.daily.series.agtdClose) ?? 0;
  const domestic = lastNonNull(data.daily.series.domesticInvT) ?? 0;
  const comex = lastNonNull(data.daily.series.comexInvT) ?? 0;
  const ratio = lastPoint(data.market.items.goldSilverRatio.points)?.value ?? 0;
  const pulse = data.monitoring.overallPulse;

  // 国内库存构成：上期所 + 上金所（日期取 lastActual，缺省回退为末个非空点日期）
  const daily = data.daily;
  const shfeV = lastNonNull(daily.series.shfeInvT);
  const sgeV = lastNonNull(daily.series.sgeInvT);
  const shfeD = lastActualDate(daily.dates, daily.series.shfeInvT, daily.lastActual, "shfeInvT");
  const sgeD = lastActualDate(daily.dates, daily.series.sgeInvT, daily.lastActual, "sgeInvT");
  const sgeSuffix = sgeD && sgeD < daily.asOfDate ? " 起沿用" : "";

  return (
    <section className="hero" id="top">
      <div className="hero-copy" ref={ref}>
        <div className="eyebrow">
          <i className="live-dot" />
          SILVER DATA PANORAMA · 日频 × 分钟级
        </div>
        <h1>
          白银市场<em>全景</em>数据终端
        </h1>
        <p>
          五项固定监测信号、全球库存与递延费方向、期货持仓虚实比、分钟级基差与进出口盈亏、
          租借利率与季节性，一屏看尽白银市场的紧张程度与结构变化。
        </p>
        <div className="hero-meta">
          <CountBadge label="Ag(T+D) 收盘" target={agtdClose} decimals={0} unit="元/千克" active={inView} />
          <span>
            国内库存 <DomesticCount target={domestic} active={inView} /> 吨
          </span>
          <CountBadge label="COMEX 库存" target={comex} decimals={1} unit="吨" active={inView} />
          <CountBadge label="金银比" target={ratio} decimals={1} unit="" active={inView} />
        </div>
        <div className="hero-meta-note">
          上期所 {shfeV === null ? "—" : formatNumber(shfeV, 3)}（{shortMd(shfeD)}）+ 上金所 {sgeV === null ? "—" : formatNumber(sgeV, 3)}（{shortMd(sgeD)}{sgeSuffix}）
        </div>
      </div>
      <PulseCard score={pulse.score} status={pulse.status} position={pulse.position} />
    </section>
  );
}

function DomesticCount({ target, active }: { target: number; active: boolean }) {
  const v = useCountUp(target, active, 1100);
  return <b className="count">{formatNumber(v, 1)}</b>;
}

function PulseCard({ score, status, position }: { score: number; status: string; position: number }) {
  const cx = 110;
  const cy = 106;
  const r = 82;
  const arc = `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
  const arcLen = Math.PI * r;
  const pos = Math.min(1, Math.max(0, position));
  const angle = Math.PI * (1 - pos);
  const needleR = r - 26;
  const nx = cx + needleR * Math.cos(angle);
  const ny = cy - needleR * Math.sin(angle);
  const ticks = [0, 25, 50, 75, 100];
  return (
    <aside className="pulse-card">
      <div className="pulse-card-head">
        <span>市场紧张度 · PULSE</span>
        <span className="live-chip">
          <i className="live-dot" />
          LIVE
        </span>
      </div>
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
          <strong>{status}</strong>
          <span>{score > 0 ? `+${score}` : score}</span>
        </div>
      </div>
      <p className="pulse-desc">
        综合五项固定监测主题的信号分数，刻画当前白银市场供需与资金面的紧张程度。指针越靠右，市场越偏紧。
      </p>
    </aside>
  );
}

// ——— 方法论 ———
export function Methodology() {
  return (
    <section className="method-section">
      <article>
        <span>口径说明</span>
        <h3>统一计量</h3>
        <p>
          白银库存统一为吨（金衡盎司 ÷ 32,150.7 换算）；虚实比 = 持仓量 × 15 千克 ÷ 注册仓单；
          基差 = Ag(T+D) − 对应期货合约（元/千克）；进口盈亏 = Ag(T+D) − 伦敦银人民币到岸价 × 1.13（含增值税）。
        </p>
      </article>
      <article>
        <span>数据质量</span>
        <h3>频率与缺失</h3>
        <p>
          日频主表按日历日对齐，节假日为 null（图中断点）；COMEX 头寸为周频、LBMA 库存为月频，
          稀疏序列以 connectNulls 连线展示；分钟级基差/盈亏按交易日聚合，非交易时段在横轴上压缩。
        </p>
      </article>
      <article>
        <span>主要来源</span>
        <h3>数据来源</h3>
        <p>
          Wind（行情与库存）、彭博（ETF 持仓）、<a href="https://www.sge.com.cn" target="_blank" rel="noreferrer">上金所 SGE</a>、
          <a href="https://www.shfe.com.cn" target="_blank" rel="noreferrer">上期所 SHFE</a>、COMEX / CFTC、LBMA，
          年度供需取自 World Silver Survey 2026。
        </p>
      </article>
    </section>
  );
}

// ——— 页脚 ———
export function Footer({ data }: { data: DashboardData }) {
  return (
    <footer>
      <span>监测截至 {data.monitoring.asOfDate} · 日频截至 {data.daily.asOfDate}</span>
      <span>市场数据抓取 {formatFetchedAt(data.market.fetchedAt)} · 生成 {formatFetchedAt(data.daily.generatedAt)}</span>
    </footer>
  );
}