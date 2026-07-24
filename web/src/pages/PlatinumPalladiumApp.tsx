import { useEffect, useState } from "react";
import type { MetalVirtualRatioData, PpWarehouseData } from "../lib/types";
import { fetchData } from "../lib/data";
import { formatNumber } from "../lib/format";
import { PpWarehouseSection } from "../components/PpWarehouse";
import { PpVirtualRatioSection } from "../components/Positions";
import {
  PageError,
  PageFooter,
  PageHero,
  PageLoading,
  PageTopbar,
  PP_NAV_ITEMS,
  useActiveSection,
  usePageTheme,
} from "./ProductChrome";

export default function PlatinumPalladiumApp() {
  const { theme, toggleTheme } = usePageTheme();
  const [warehouse, setWarehouse] = useState<PpWarehouseData | null>(null);
  const [virtualRatio, setVirtualRatio] = useState<MetalVirtualRatioData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetchData<PpWarehouseData>("data/pp_warehouse.json"),
      fetchData<MetalVirtualRatioData>("data/metal_virtual_ratio.json"),
    ])
      .then(([nextWarehouse, nextVirtualRatio]) => {
        if (!cancelled) {
          setWarehouse(nextWarehouse);
          setVirtualRatio(nextVirtualRatio);
        }
      })
      .catch((reason: Error) => {
        if (!cancelled) setError(reason.message);
      });
    return () => { cancelled = true; };
  }, []);

  const ready = Boolean(warehouse && virtualRatio);
  const active = useActiveSection(PP_NAV_ITEMS, ready);
  if (error) return <PageError message={error} theme={theme} />;
  if (!warehouse || !virtualRatio) return <PageLoading label="铂钯数据" theme={theme} />;

  return (
    <div className={"dashboard-shell " + (theme === "light" ? "light-mode" : "")}>
      <PageTopbar
        page="platinum-palladium"
        title="铂钯数据终端"
        subtitle="PLATINUM & PALLADIUM"
        navItems={PP_NAV_ITEMS}
        active={active}
        asOfText={"仓单 " + warehouse.asOfDate}
        theme={theme}
        onToggleTheme={toggleTheme}
      />
      <main>
        <PageHero
          eyebrow="PLATINUM & PALLADIUM · 01–08"
          title="铂钯仓单与"
          accent="虚实比"
          description="独立展示广期所铂金、钯金仓单结构、仓库明细和分合约虚实比；后续铂钯行情及贸易数据将继续在此页扩充。"
          meta={[
            { label: "铂金仓单", value: formatNumber(warehouse.metals.pt.latest.totalKg, 0) + " kg" },
            { label: "钯金仓单", value: formatNumber(warehouse.metals.pd.latest.totalKg, 0) + " kg" },
            { label: "数据截至", value: warehouse.asOfDate },
          ]}
        />
        <PpWarehouseSection data={warehouse} theme={theme} index="01" />
        <PpVirtualRatioSection metalVirtualRatio={virtualRatio} theme={theme} />
      </main>
      <PageFooter>
        <span>广期所铂钯仓单截至 {warehouse.asOfDate}</span>
        <span>虚实比数据 {virtualRatio.metals.pt.asOfDate ?? virtualRatio.metals.pd.asOfDate ?? "按合约更新"}</span>
      </PageFooter>
    </div>
  );
}
