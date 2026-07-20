# ============ Restructure Market.tsx: keep only Price + Fund ============
path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Market.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Update MarketSection: remove stock panels, update desc
old_section = '''export function MarketSection({ market, daily, theme }: { market: MarketData; daily: DailyData; theme: ThemeMode }) {
  return (
    <section className="section-block" id="market">
      <SectionHeading index="03" title="市场脉搏 · 日频" desc="伦敦现货 / 沪银 / 上金所 / 金银比 / 交易所库存 / 白银基金" id="market" />
      <div className="market-grid">
        <PricePanel market={market} theme={theme} />
        <DomesticStocksPanel daily={daily} theme={theme} />
        <OverseasStocksPanel daily={daily} theme={theme} />
        <FundPanel market={market} theme={theme} />
      </div>
    </section>
  );
}'''

new_section = '''export function MarketSection({ market, theme }: { market: MarketData; theme: ThemeMode }) {
  return (
    <section className="section-block" id="market">
      <SectionHeading index="03" title="市场脉搏 · 日频" desc="伦敦现货 / 沪银 / 上金所 / 金银比 / 白银基金" id="market" />
      <div className="market-grid">
        <PricePanel market={market} theme={theme} />
        <FundPanel market={market} theme={theme} />
      </div>
    </section>
  );
}'''
src = src.replace(old_section, new_section, 1)

# 2. Remove DomesticStocksPanel, OverseasStocksPanel, StockLines functions
# Find and remove from "function DomesticStocksPanel" to just before "function FundPanel"
import re
src = re.sub(
    r'\nfunction DomesticStocksPanel\{.*?\nfunction FundPanel',
    '\nfunction FundPanel',
    src,
    flags=re.DOTALL
)

# 3. Remove unused imports
src = src.replace(
    'import { formatNumber, formatTradeTime, lastActualDate, lastNonNull, lastPoint, shortMd } from "../lib/format";',
    'import { formatNumber, formatTradeTime, lastNonNull, lastPoint } from "../lib/format";'
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Market.tsx restructured: only Price + Fund")

# ============ Restructure Daily.tsx: add overseas panels ============
path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\components\Daily.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Update section title
src = src.replace(
    '<SectionHeading index="04" title="递延费与国内库存 · 日频" desc="上金所递延费支付旫吐 / 国内库存（单位：吨）" id="daily" />',
    '<SectionHeading index="04" title="递延费与库存 · 日频" desc="递延费方向 / 国内库存 / 海外库存 / ETF（单位：吨）" id="daily" />'
)

# 2. Add overseas panels after the grid-2 closing div, before section closing
old_daily_end = '''      </div>
    </section>
  );
}

function fmtT'''

new_daily_end = '''      </div>
      <div className="grid-2" style={{ marginTop: 14 }}>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>美国 · US</span>
              <h3>COMEX 库存 / 注册仓单 / PSLV</h3>
            </div>
            <div className="panel-stat">
              <small>COMEX 最新</small>
              <strong>{fmtT(lastNonNull(daily.series.comexInvT))}</strong>
            </div>
          </div>
          <MultiLineChart
            theme={theme}
            dates={daily.dates}
            series={[
              { name: "COMEX 库存", data: daily.series.comexInvT, colorIdx: 0 },
              { name: "COMEX 注册仓单", data: daily.series.comexWarrantT, colorIdx: 1 },
              { name: "PSLV 持仓", data: daily.series.etfPSLV, colorIdx: 2 },
            ]}
            height={248}
            zoom
            connectNulls={false}
          />
        </article>
        <article className="panel chart-panel">
          <div className="panel-heading">
            <div>
              <span>欧洲 · EU/UK</span>
              <h3>LBMA 库存 / 英国 ETF / SLV</h3>
            </div>
            <div className="panel-stat">
              <small>LBMA（日频估算）最新</small>
              <strong>{fmtT(lastNonNull(daily.series.lbmaDailyT))}</strong>
            </div>
          </div>
          <MultiLineChart
            theme={theme}
            dates={daily.dates}
            series={[
              { name: "LBMA 库存（日频）", data: daily.series.lbmaDailyT, colorIdx: 0 },
              { name: "英国 ETF 合计", data: daily.series.etfUKSum, colorIdx: 1 },
              { name: "SLV 持仓", data: daily.series.etfSLV, colorIdx: 2 },
            ]}
            height={248}
            zoom
            connectNulls
          />
        </article>
      </div>
    </section>
  );
}

function fmtT'''
src = src.replace(old_daily_end, new_daily_end, 1)

# 3. Remove the old DailyOverseasSection export (it's now merged into DailySection)
import re
src = re.sub(
    r'\n// ——— 06 欧美库存与 ETF ———\nexport function DailyOverseasSection.*?\n\}\n',
    '\n',
    src,
    flags=re.DOTALL
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Daily.tsx restructured: added overseas panels, removed DailyOverseasSection")

# ============ Update App.tsx: remove DailyOverseasSection ============
path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\web\src\App.tsx"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Remove import
src = src.replace(
    'import { DailySection, DailyOverseasSection } from "./components/Daily";',
    'import { DailySection } from "./components/Daily";'
)

# Remove MarketSection daily prop
src = src.replace(
    '<MarketSection market={data.market} daily={data.daily} theme={theme} />',
    '<MarketSection market={data.market} theme={theme} />'
)

# Remove DailyOverseasSection usage
src = src.replace(
    '        <DailyOverseasSection daily={data.daily} theme={theme} />\n',
    ''
)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("App.tsx updated: removed DailyOverseasSection")

print("\nLayout restructure complete!")
