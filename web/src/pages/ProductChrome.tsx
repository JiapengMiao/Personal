import { useCallback, useEffect, useState, type ReactNode } from "react";
import type { ThemeMode } from "../lib/echarts";

export type ProductPage = "silver" | "platinum-palladium" | "monitoring";

export interface PageNavItem {
  id: string;
  label: string;
}

export const SILVER_NAV_ITEMS: PageNavItem[] = [
  { id: "market", label: "市场" },
  { id: "daily", label: "库存" },
  { id: "positions", label: "持仓" },
  { id: "comex", label: "COMEX" },
  { id: "shfe-positioning", label: "上期持仓" },
  { id: "lhb", label: "龙虎" },
  { id: "trade-basis", label: "贸易基差" },
  { id: "lease", label: "租赁" },
];

export const PP_NAV_ITEMS: PageNavItem[] = [
  { id: "pp-warehouse", label: "仓单" },
  { id: "pp-virtual-ratio", label: "虚实比" },
];

export const MONITORING_NAV_ITEMS: PageNavItem[] = [
  { id: "signals", label: "固定监测" },
  { id: "trends", label: "趋势结构" },
  { id: "dynamics", label: "信号动态" },
  { id: "indicators", label: "指标库" },
];

const PAGE_TABS: Array<{ id: ProductPage; label: string; href: string }> = [
  { id: "silver", label: "白银", href: "../silver/" },
  { id: "platinum-palladium", label: "铂钯", href: "../platinum-palladium/" },
  { id: "monitoring", label: "监测中心", href: "../monitoring/" },
];

const THEME_KEY = "ag-monitor-theme";

export function usePageTheme() {
  const [theme, setTheme] = useState<ThemeMode>(() => (localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark"));
  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_KEY, next);
      return next;
    });
  }, []);
  return { theme, toggleTheme };
}

export function useActiveSection(items: PageNavItem[], ready: boolean) {
  const [active, setActive] = useState(items[0]?.id ?? "");
  useEffect(() => {
    if (!ready) return;
    const sections = items.map((item) => document.getElementById(item.id)).filter((element): element is HTMLElement => !!element);
    if (!sections.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.id);
        }
      },
      { rootMargin: "-30% 0px -60% 0px" },
    );
    sections.forEach((section) => observer.observe(section));
    return () => observer.disconnect();
  }, [items, ready]);
  return active;
}

export function PageTopbar({
  page,
  title,
  subtitle,
  navItems,
  active,
  asOfText,
  theme,
  onToggleTheme,
  showDownload = false,
}: {
  page: ProductPage;
  title: string;
  subtitle: string;
  navItems: PageNavItem[];
  active: string;
  asOfText: string;
  theme: ThemeMode;
  onToggleTheme: () => void;
  showDownload?: boolean;
}) {
  return (
    <header className="topbar product-topbar">
      <a className="brand" href="#top">
        <span className="brand-mark">
          <b>{page === "silver" ? "Ag" : page === "platinum-palladium" ? "Pt" : "Mx"}</b>
          <small>{page === "silver" ? "47" : page === "platinum-palladium" ? "78/46" : "09–12"}</small>
        </span>
        <span>
          <strong>{title}</strong>
          <small>{subtitle}</small>
        </span>
      </a>
      <div className="product-tabs" aria-label="页面切换">
        {PAGE_TABS.map((tab) => (
          <a key={tab.id} href={tab.href} className={tab.id === page ? "active" : ""}>
            {tab.label}
          </a>
        ))}
      </div>
      <nav aria-label="本页导航">
        {navItems.map((item) => (
          <a key={item.id} href={"#" + item.id} className={active === item.id ? "active" : ""}>
            {item.label}
          </a>
        ))}
      </nav>
      <div className="top-actions">
        <span className="data-clock">{asOfText}</span>
        <button className="icon-button" onClick={onToggleTheme} aria-label="切换明暗主题">
          {theme === "dark" ? "◐ 浅色" : "◑ 深色"}
        </button>
        {showDownload && (
          <a className="download-button" href="../白银五项固定监测看板_20260719.xlsx" download>
            下载Excel底稿
          </a>
        )}
      </div>
    </header>
  );
}

export function PageHero({
  eyebrow,
  title,
  accent,
  description,
  meta,
  aside,
}: {
  eyebrow: string;
  title: string;
  accent: string;
  description: string;
  meta: Array<{ label: string; value: string }>;
  aside?: ReactNode;
}) {
  return (
    <section className={"hero " + (aside ? "" : "page-hero-solo")} id="top">
      <div className="hero-copy">
        <div className="eyebrow"><i className="live-dot" />{eyebrow}</div>
        <h1>{title}<em>{accent}</em></h1>
        <p>{description}</p>
        <div className="hero-meta">
          {meta.map((item) => <span key={item.label}>{item.label} <b className="count">{item.value}</b></span>)}
        </div>
      </div>
      {aside}
    </section>
  );
}

export function PageFooter({ children }: { children: ReactNode }) {
  return <footer className="page-footer">{children}</footer>;
}

export function PageLoading({ label, theme }: { label: string; theme: ThemeMode }) {
  return (
    <div className={"dashboard-shell " + (theme === "light" ? "light-mode" : "")}>
      <main style={{ padding: "120px 0" }}>
        <div className="chart-loading" style={{ minHeight: 300 }}>正在加载{label}…</div>
      </main>
    </div>
  );
}

export function PageError({ message, theme }: { message: string; theme: ThemeMode }) {
  return (
    <div className={"dashboard-shell " + (theme === "light" ? "light-mode" : "")}>
      <main style={{ padding: "120px 0" }}>
        <p style={{ color: "var(--down)" }}>数据加载失败：{message}</p>
      </main>
    </div>
  );
}
