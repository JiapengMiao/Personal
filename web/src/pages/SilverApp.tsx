import { useCallback, useEffect, useState } from "react";
import type { DashboardData } from "../lib/types";
import { fetchData } from "../lib/data";
import { MarketSection } from "../components/Market";
import { DailySection } from "../components/Daily";
import { ComexSection, SilverPositionsSection } from "../components/Positions";
import { BasisSection, LeaseSection, SeasonalitySection } from "../components/Basis";
import { SpotQuotesSection } from "../components/SpotQuotes";
import { HkTradeSection } from "../components/HkTrade";
import { WorldTradeSection } from "../components/WorldTrade";
import { SilverFlowsSection } from "../components/SilverFlows";
import { LhbSection, type LhbData } from "../components/Lhb";
import { ShfePositioningSection } from "../components/ShfePositioning";
import { Methodology } from "../components/Chrome";
import { SectionHeading } from "../components/shared";
import {
  PageError,
  PageFooter,
  PageHero,
  PageLoading,
  PageTopbar,
  SILVER_NAV_ITEMS,
  useActiveSection,
  usePageTheme,
} from "./ProductChrome";

type SilverData = Pick<
  DashboardData,
  "market" | "daily" | "positions" | "virtualRatio" | "shfePositioning" | "seasonality" | "leaseRates"
>;

async function fetchJson<T>(url: string): Promise<T> {
  return fetchData<T>(url);
}

export default function SilverApp() {
  const { theme, toggleTheme } = usePageTheme();
  const [data, setData] = useState<SilverData | null>(null);
  const [lhb, setLhb] = useState<LhbData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyLoading, setHistoryLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchJson<SilverData["market"]>("data/market.json"),
      fetchJson<SilverData["daily"]>("data/daily_recent.json"),
      fetchJson<SilverData["positions"]>("data/positions_curve.json"),
      fetchJson<SilverData["virtualRatio"]>("data/virtual_ratio.json"),
      fetchJson<SilverData["shfePositioning"]>("data/shfe_positioning.json"),
      fetchJson<SilverData["seasonality"]>("data/seasonality.json"),
      fetchJson<SilverData["leaseRates"]>("data/lease_rates.json"),
    ])
      .then(([market, daily, positions, virtualRatio, shfePositioning, seasonality, leaseRates]) => {
        if (!cancelled) setData({ market, daily, positions, virtualRatio, shfePositioning, seasonality, leaseRates });
      })
      .catch((reason: Error) => {
        if (!cancelled) setError(reason.message);
      });
    fetchJson<LhbData>("data/lhb.json").then(setLhb).catch(() => { /* 无数据时不显示 */ });
    return () => { cancelled = true; };
  }, []);

  const historyLoaded = data ? data.daily.dates.length > 2000 : false;
  const loadDailyHistory = useCallback(async () => {
    if (!data || historyLoaded || historyLoading) return;
    setHistoryLoading(true);
    try {
      const history = await fetchJson<SilverData["daily"]>("data/daily_history.json");
      setData((current) => (current ? { ...current, daily: history } : current));
    } finally {
      setHistoryLoading(false);
    }
  }, [data, historyLoaded, historyLoading]);

  const active = useActiveSection(SILVER_NAV_ITEMS, Boolean(data));
  if (error) return <PageError message={error} theme={theme} />;
  if (!data) return <PageLoading label="白银数据" theme={theme} />;

  return (
    <div className={"dashboard-shell " + (theme === "light" ? "light-mode" : "")}>
      <PageTopbar
        page="silver"
        title="白银数据终端"
        subtitle="SILVER MARKET DATA"
        navItems={SILVER_NAV_ITEMS}
        active={active}
        asOfText={"日频 " + data.daily.asOfDate}
        theme={theme}
        onToggleTheme={toggleTheme}
        showDownload
      />
      <main>
        <PageHero
          eyebrow="SILVER DATA · 01–08"
          title="白银市场"
          accent="数据终端"
          description="行情、库存、持仓、贸易与租赁利率集中于同一条白银研究链路；监测信号与指标库已独立至监测中心。"
          meta={[
            { label: "日频截至", value: data.daily.asOfDate },
            { label: "上期持仓", value: data.shfePositioning.asOfDate },
            { label: "龙虎榜", value: lhb?.date ?? "加载中" },
          ]}
        />
        <MarketSection market={data.market} theme={theme} />
        <DailySection daily={data.daily} theme={theme} onLoadHistory={loadDailyHistory} historyLoaded={historyLoaded} historyLoading={historyLoading} />
        <SilverPositionsSection positions={data.positions} virtualRatio={data.virtualRatio} theme={theme} />
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
            <SilverFlowsSection theme={theme} />
            <SpotQuotesSection />
            <BasisSection theme={theme} />
            <SeasonalitySection data={data.seasonality} asOfDate={data.daily.asOfDate} theme={theme} />
          </div>
        </section>
        <LeaseSection data={data.leaseRates} theme={theme} />
        <Methodology />
      </main>
      <PageFooter>
        <span>白银日频截至 {data.daily.asOfDate} · 上期持仓截至 {data.shfePositioning.asOfDate}</span>
        <span>市场数据 {data.market.fetchedAt.slice(0, 16).replace("T", " ")}</span>
      </PageFooter>
    </div>
  );
}
