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
import { WorldTradeSection } from "./components/WorldTrade";
import { LhbSection, type LhbData } from "./components/Lhb";
import { ShfePositioningSection } from "./components/ShfePositioning";
import { PpWarehouseSection } from "./components/PpWarehouse";
import { SectionHeading } from "./components/shared";
import { fetchData } from "./lib/data";

const THEME_KEY = "ag-monitor-theme";

async function fetchJson<T>(url: string): Promise<T> {
  return fetchData<T>(url);
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
  const [lhb, setLhb] = useState<LhbData | null>(null);

  // 龙虎榜独立加载（失败静默，不影响主看板）
  useEffect(() => {
    fetchJson<LhbData>("data/lhb.json").then(setLhb).catch(() => { /* 无数据时不显示 */ });
  }, []);

  // 数据加载（三级加载：首屏只拉 daily_recent.json 近2年 ~133KB，历史数据拖到早期再懒加载）
  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchJson<DashboardData["monitoring"]>("data/monitoring.json"),
      fetchJson<DashboardData["market"]>("data/market.json"),
      fetchJson<DashboardData["daily"]>("data/daily_recent.json"),
      fetchJson<DashboardData["positions"]>("data/positions_curve.json"),
      fetchJson<DashboardData["virtualRatio"]>("data/virtual_ratio.json"),
      fetchJson<DashboardData["metalVirtualRatio"]>("data/metal_virtual_ratio.json"),
      fetchJson<DashboardData["shfePositioning"]>("data/shfe_positioning.json"),
      fetchJson<DashboardData["ppWarehouse"]>("data/pp_warehouse.json"),
      fetchJson<DashboardData["seasonality"]>("data/seasonality.json"),
      fetchJson<DashboardData["leaseRates"]>("data/lease_rates.json"),
    ])
      .then(([monitoring, market, daily, positions, virtualRatio, metalVirtualRatio, shfePositioning, ppWarehouse, seasonality, leaseRates]) => {
        if (!cancelled) {
          setData({ monitoring, market, daily, positions, virtualRatio, metalVirtualRatio, shfePositioning, ppWarehouse, seasonality, leaseRates });
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
        <MarketSection market={data.market} theme={theme} />
        <section className="section-block section-group" id="inventory">
          <SectionHeading
            index="02"
            title="库存、递延费与铂钯仓单"
            desc="白银递延费与境内外库存 / 广期所铂金、钯金仓单"
            id="inventory"
          />
          <div className="section-group-content">
            <DailySection daily={data.daily} theme={theme} onLoadHistory={loadDailyHistory} historyLoaded={historyLoaded} historyLoading={historyLoading} />
            <PpWarehouseSection data={data.ppWarehouse} theme={theme} />
          </div>
        </section>
        <PositionsSection
          positions={data.positions}
          virtualRatio={data.virtualRatio}
          metalVirtualRatio={data.metalVirtualRatio}
          theme={theme}
        />
        <ComexSection daily={data.daily} theme={theme} />
        <ShfePositioningSection data={data.shfePositioning} theme={theme} />
        <LhbSection data={lhb} />
        <section className="section-block section-group" id="trade-basis">
          <SectionHeading
            index="07"
            title="贸易、现货基差与进出口盈亏"
            desc="香港及美英印白银进出口 / 现货基差报价 / 分钟与日度基差 / 盈亏季节性"
            id="trade-basis"
          />
          <div className="section-group-content">
            <HkTradeSection theme={theme} />
            <WorldTradeSection theme={theme} />
            <SpotQuotesSection />
            <BasisSection theme={theme} />
            <SeasonalitySection data={data.seasonality} asOfDate={data.daily.asOfDate} theme={theme} />
          </div>
        </section>
        <LeaseSection data={data.leaseRates} theme={theme} />
        <SignalsSection monitoring={data.monitoring} selectedTheme={selectedTheme} onSelectTheme={setSelectedTheme} />
        <TrendsSection monitoring={data.monitoring} theme={theme} />
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
