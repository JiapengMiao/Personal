import { useCallback, useEffect, useState } from "react";
import type { DashboardData, Indicator, Trigger } from "./lib/types";
import type { ThemeMode } from "./lib/echarts";
import { Footer, Hero, Methodology, NAV_ITEMS, Ticker, Topbar } from "./components/Chrome";
import { SignalsSection, TrendsSection } from "./components/Signals";
import { MarketSection } from "./components/Market";
import { DailySection } from "./components/Daily";
import { ComexSection, PositionsSection } from "./components/Positions";
import { BasisSection, LeaseSection, SeasonalitySection } from "./components/Basis";
import { DynamicsSection, IndicatorDrawer, IndicatorLibrarySection } from "./components/Library";
import { SpotQuotesSection } from "./components/SpotQuotes";
import { HkTradeSection } from "./components/HkTrade";

const THEME_KEY = "ag-monitor-theme";

async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`);
  return r.json() as Promise<T>;
}

export default function App() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [theme, setTheme] = useState<ThemeMode>(() => {
    const saved = localStorage.getItem(THEME_KEY);
    return saved === "light" ? "light" : "dark";
  });
  const [active, setActive] = useState("signals");
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<{ indicator: Indicator; list: Indicator[] } | null>(null);

  // 数据加载（三级加载：首屏只拉 daily_recent.json 近2年 ~133KB，历史数据拖到早期再懒加载）
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchJson<DashboardData["monitoring"]>("data/monitoring.json"),
      fetchJson<DashboardData["market"]>("data/market.json"),
      fetchJson<DashboardData["daily"]>("data/daily_recent.json"),
      fetchJson<DashboardData["positions"]>("data/positions_curve.json"),
      fetchJson<DashboardData["virtualRatio"]>("data/virtual_ratio.json"),
      fetchJson<DashboardData["seasonality"]>("data/seasonality.json"),
      fetchJson<DashboardData["leaseRates"]>("data/lease_rates.json"),
    ])
      .then(([monitoring, market, daily, positions, virtualRatio, seasonality, leaseRates]) => {
        if (!cancelled) {
          setData({ monitoring, market, daily, positions, virtualRatio, seasonality, leaseRates });
        }
      })
      .catch((e: Error) => {
        if (!cancelled) setError(e.message);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // 历史数据懒加载：用户点击按钮后拉取全量历史
  const [historyLoading, setHistoryLoading] = useState(false);
  const historyLoaded = data ? data.daily.dates.length > 2000 : false;
  const loadDailyHistory = useCallback(async () => {
    if (!data || historyLoaded || historyLoading) return;
    setHistoryLoading(true);
    try {
      const history = await fetchJson<DashboardData["daily"]>("data/daily_history.json");
      setData((d) => (d ? { ...d, daily: history } : d));
    } catch {
      /* 静默失败，保持近期数据 */
    } finally {
      setHistoryLoading(false);
    }
  }, [data, historyLoaded, historyLoading]);

  // 主题持久化
  const toggleTheme = useCallback(() => {
    setTheme((t) => {
      const next = t === "dark" ? "light" : "dark";
      localStorage.setItem(THEME_KEY, next);
      return next;
    });
  }, []);

  // 滚动监听高亮导航
  useEffect(() => {
    const sections = NAV_ITEMS.map((n) => document.getElementById(n.id)).filter((el): el is HTMLElement => !!el);
    if (!sections.length) return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.id);
        }
      },
      { rootMargin: "-30% 0px -60% 0px" },
    );
    sections.forEach((s) => observer.observe(s));
    return () => observer.disconnect();
  }, [data]);

  const openIndicator = useCallback(
    (indicator: Indicator, list?: Indicator[]) => {
      setDrawer({ indicator, list: list ?? data?.monitoring.indicators ?? [indicator] });
    },
    [data],
  );

  const openTrigger = useCallback(
    (trigger: Trigger) => {
      const ind = data?.monitoring.indicators.find((i) => i.id === trigger.indicatorId);
      if (ind) openIndicator(ind);
    },
    [data, openIndicator],
  );

  if (error) {
    return (
      <div className={`dashboard-shell ${theme === "light" ? "light-mode" : ""}`}>
        <main style={{ padding: "120px 0" }}>
          <p style={{ color: "var(--down)" }}>数据加载失败：{error}</p>
        </main>
      </div>
    );
  }

  if (!data) {
    return (
      <div className={`dashboard-shell ${theme === "light" ? "light-mode" : ""}`}>
        <main style={{ padding: "120px 0" }}>
          <div className="chart-loading" style={{ minHeight: 300 }}>
            正在加载白银数据全景看板…
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className={`dashboard-shell ${theme === "light" ? "light-mode" : ""}`}>
      <Ticker triggers={data.monitoring.triggers} onOpen={openTrigger} />
      <Topbar
        active={active}
        asOf={data.monitoring.asOfDate}
        dailyAsOf={data.daily.asOfDate}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <main>
        <Hero data={data} />
        <SignalsSection monitoring={data.monitoring} selectedTheme={selectedTheme} onSelectTheme={setSelectedTheme} />
        <TrendsSection monitoring={data.monitoring} theme={theme} />
        <MarketSection market={data.market} theme={theme} />
        <DailySection daily={data.daily} theme={theme} onLoadHistory={loadDailyHistory} historyLoaded={historyLoaded} historyLoading={historyLoading} />
        <PositionsSection positions={data.positions} virtualRatio={data.virtualRatio} theme={theme} />
        <SpotQuotesSection />
        <ComexSection daily={data.daily} theme={theme} />
        <HkTradeSection theme={theme} />
        <BasisSection theme={theme} />
        <SeasonalitySection data={data.seasonality} asOfDate={data.daily.asOfDate} theme={theme} />
        <LeaseSection data={data.leaseRates} theme={theme} />
        <DynamicsSection monitoring={data.monitoring} theme={theme} onOpenTrigger={openTrigger} />
        <IndicatorLibrarySection
          monitoring={data.monitoring}
          theme={theme}
          selectedTheme={selectedTheme}
          onSelectTheme={setSelectedTheme}
          onOpen={(ind, list) => openIndicator(ind, list)}
        />
        <Methodology />
      </main>
      <Footer data={data} />
      {drawer && (
        <IndicatorDrawer
          indicator={drawer.indicator}
          list={drawer.list}
          theme={theme}
          onClose={() => setDrawer(null)}
          onNavigate={(ind) => setDrawer((d) => (d ? { ...d, indicator: ind } : d))}
        />
      )}
    </div>
  );
}
