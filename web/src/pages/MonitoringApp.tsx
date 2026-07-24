import { useCallback, useEffect, useState } from "react";
import type { Indicator, MonitoringData, Trigger } from "../lib/types";
import { fetchData } from "../lib/data";
import { Ticker } from "../components/Chrome";
import { DynamicsSection, IndicatorDrawer, IndicatorLibrarySection } from "../components/Library";
import { SignalsSection, TrendsSection } from "../components/Signals";
import {
  MONITORING_NAV_ITEMS,
  PageError,
  PageFooter,
  PageHero,
  PageLoading,
  PageTopbar,
  useActiveSection,
  usePageTheme,
} from "./ProductChrome";

export default function MonitoringApp() {
  const { theme, toggleTheme } = usePageTheme();
  const [monitoring, setMonitoring] = useState<MonitoringData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTheme, setSelectedTheme] = useState<string | null>(null);
  const [drawer, setDrawer] = useState<{ indicator: Indicator; list: Indicator[] } | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchData<MonitoringData>("data/monitoring.json")
      .then((next) => { if (!cancelled) setMonitoring(next); })
      .catch((reason: Error) => { if (!cancelled) setError(reason.message); });
    return () => { cancelled = true; };
  }, []);

  const openIndicator = useCallback((indicator: Indicator, list?: Indicator[]) => {
    setDrawer({ indicator, list: list ?? monitoring?.indicators ?? [indicator] });
  }, [monitoring]);

  const openTrigger = useCallback((trigger: Trigger) => {
    const indicator = monitoring?.indicators.find((item) => item.id === trigger.indicatorId);
    if (indicator) openIndicator(indicator);
  }, [monitoring, openIndicator]);

  const active = useActiveSection(MONITORING_NAV_ITEMS, Boolean(monitoring));
  if (error) return <PageError message={error} theme={theme} />;
  if (!monitoring) return <PageLoading label="监测中心" theme={theme} />;

  const pulse = monitoring.overallPulse;
  return (
    <div className={"dashboard-shell " + (theme === "light" ? "light-mode" : "")}>
      <Ticker triggers={monitoring.triggers} onOpen={openTrigger} />
      <PageTopbar
        page="monitoring"
        title="白银监测中心"
        subtitle="MONITORING & RESEARCH"
        navItems={MONITORING_NAV_ITEMS}
        active={active}
        asOfText={"监测 " + monitoring.asOfDate}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <main>
        <PageHero
          eyebrow="MONITORING CENTER · 09–12"
          title="白银研究"
          accent="监测中心"
          description="五项固定监测、长期趋势、信号动态与指标口径集中管理；市场与交易层数据已分别归入白银页和铂钯页。"
          meta={[
            { label: "监测日期", value: monitoring.asOfDate },
            { label: "指标覆盖", value: monitoring.indicators.length + " 项" },
            { label: "实时信号", value: monitoring.triggers.length + " 条" },
          ]}
          aside={
            <aside className="pulse-card monitoring-pulse-card">
              <div className="pulse-card-head"><span>综合状态 · PULSE</span><span className="live-chip"><i className="live-dot" />LIVE</span></div>
              <strong className="monitoring-pulse-value">{pulse.status}</strong>
              <span>五项固定监测综合分数</span>
              <b>{pulse.score > 0 ? "+" : ""}{pulse.score}</b>
            </aside>
          }
        />
        <SignalsSection monitoring={monitoring} selectedTheme={selectedTheme} onSelectTheme={setSelectedTheme} />
        <TrendsSection monitoring={monitoring} theme={theme} />
        <DynamicsSection monitoring={monitoring} theme={theme} onOpenTrigger={openTrigger} />
        <IndicatorLibrarySection
          monitoring={monitoring}
          theme={theme}
          selectedTheme={selectedTheme}
          onSelectTheme={setSelectedTheme}
          onOpen={(indicator, list) => openIndicator(indicator, list)}
        />
      </main>
      <PageFooter>
        <span>白银监测截至 {monitoring.asOfDate}</span>
        <span>生成 {monitoring.generatedAt.slice(0, 16).replace("T", " ")}</span>
      </PageFooter>
      {drawer && (
        <IndicatorDrawer
          indicator={drawer.indicator}
          list={drawer.list}
          theme={theme}
          onClose={() => setDrawer(null)}
          onNavigate={(indicator) => setDrawer((current) => (current ? { ...current, indicator } : current))}
        />
      )}
    </div>
  );
}
