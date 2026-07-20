import { useEffect, useRef, useState } from "react";

export function useInView<T extends HTMLElement>(threshold = 0.3) {
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
      { threshold },
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [threshold]);
  return { ref, inView };
}

export function useCountUp(target: number, active: boolean, duration = 900) {
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
      setValue(target * (1 - Math.pow(1 - progress, 3)));
      if (progress < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [active, target, duration]);
  return value;
}

export function Sparkline({
  values,
  tone,
  width = 64,
  height = 24,
}: {
  values: number[];
  tone?: string;
  width?: number;
  height?: number;
}) {
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
  const points = values
    .map((value, index) => `${2 + index * step},${height - 3 - ((value - min) / span) * (height - 6)}`)
    .join(" ");
  return (
    <svg viewBox={`0 0 ${width} ${height}`} className="sparkline" preserveAspectRatio="none" aria-hidden="true">
      <polyline points={points} className={`spark-line ${tone ?? ""}`} />
    </svg>
  );
}

export function ScoreScale({ score }: { score: number }) {
  return (
    <div className="score-scale" aria-label={`信号分数${score}`}>
      {[-2, -1, 0, 1, 2].map((step) => (
        <i key={step} className={step === score ? "active" : ""} />
      ))}
      <span>{score > 0 ? `+${score}` : score}</span>
    </div>
  );
}

export function SignalBadge({ tone, status }: { tone: string; status: string }) {
  return <span className={`signal-badge ${tone}`}>{status}</span>;
}

export function LedBadge({ tone, status }: { tone: string; status: string }) {
  return (
    <span className={`led-badge ${tone}`}>
      <i className="led" />
      {status}
    </span>
  );
}

export function DeltaTag({ delta, decimals = 1, unit = "" }: { delta: number | null; decimals?: number; unit?: string }) {
  if (delta === null) return <span className="delta-tag flat">—</span>;
  const up = delta >= 0;
  return (
    <span className={`delta-tag ${up ? "up" : "down"}`}>
      {up ? "▲" : "▼"} {new Intl.NumberFormat("zh-CN", { maximumFractionDigits: decimals }).format(Math.abs(delta))}
      {unit ? ` ${unit}` : ""}
    </span>
  );
}

export function SectionHeading({
  index,
  title,
  desc,
  id,
}: {
  index: string;
  title: string;
  desc: string;
  id: string;
}) {
  return (
    <div className="section-heading" id={`${id}-heading`}>
      <div>
        <span className="section-index">{index}</span>
        <h2>{title}</h2>
      </div>
      <p>{desc}</p>
    </div>
  );
}
