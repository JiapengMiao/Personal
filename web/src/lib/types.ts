// ——— monitoring.json ———
export interface OverallPulse {
  score: number;
  status: string;
  position: number;
}

export interface ThemeSummary {
  theme: string;
  short: string;
  value: string;
  delta: string;
  description: string;
  icon: string;
  score: number;
  status: string;
  tone: string;
}

export interface HistoryPoint {
  period: string;
  kind: string;
  value: number;
  delta: number | null;
  score: number | null;
  status: string;
}

export interface Indicator {
  id: number;
  theme: string;
  role: string;
  name: string;
  period: string;
  value: number | null;
  priorPeriod: string;
  priorValue: number | null;
  unit: string;
  displayMultiplier?: number;
  breakdown?: Array<{
    label: string;
    value: number;
    sign: 1 | -1;
    asOfDate: string | null;
  }>;
  direction: string;
  upperThreshold: number | null;
  lowerThreshold: number | null;
  thresholdNote: string;
  score: number | null;
  status: string;
  tone: string;
  dataStatus: string;
  frequency: string;
  updatedAt: string;
  sourceLabel: string;
  sourceUrl: string;
  note: string;
  history: HistoryPoint[];
}

export interface Trigger {
  id: string;
  indicatorId: number;
  name: string;
  theme: string;
  period: string;
  kind: string;
  severity: "positive" | "negative" | "neutral";
  prevScore: number | null;
  score: number | null;
  delta: number | null;
  description: string;
}

export interface MarketBalancePoint {
  year: number;
  value: number;
  type: string; // "实际" | "预测"
}

export interface IndustrialMix {
  year: string;
  photovoltaic: number;
  nonPv: number;
  brazing: number;
  other: number;
}

export interface ActionItem {
  cadence: string;
  task: string;
  owner: string;
  status: string;
}

export interface MonitoringSource {
  label: string;
  url: string;
}

export interface MonitoringLineageItem {
  label: string;
  sourceKey: string | null;
  note: string;
}

export interface MonitoringData {
  generatedAt: string;
  asOfDate: string;
  attributionUpdatedAt?: string;
  overallPulse: OverallPulse;
  sources: Record<string, MonitoringSource>;
  dataLineage?: Record<string, MonitoringLineageItem>;
  themeSummaries: ThemeSummary[];
  indicators: Indicator[];
  triggers: Trigger[];
  marketBalance: MarketBalancePoint[];
  industrialMix: IndustrialMix[];
  actions: ActionItem[];
}

// ——— market.json ———
export interface MarketPoint {
  date: string;
  value: number;
}

export interface FuturesPoint {
  date: string;
  close: number;
  volume: number;
}

export interface MarketSeriesValue {
  label: string;
  unit: string;
  frequency?: string;
  points: MarketPoint[];
}

export interface FundSeries extends MarketSeriesValue {
  snapshot?: { name: string; nav: number; scaleYi: number };
}

export interface AgTdLatest {
  label: string;
  unit: string;
  snapshot?: { code: string; price: number; tradeTime: string };
  points: MarketPoint[];
}

export interface FuturesSeries {
  label: string;
  unit: string;
  points: FuturesPoint[];
}

export interface MarketData {
  fetchedAt: string;
  items: {
    londonSilverCnyKg: MarketSeriesValue;   // 伦敦银（人民币/千克）
    londonGoldCnyG: MarketSeriesValue;      // 伦敦金（人民币/克）
    silverFundNav: MarketSeriesValue;       // 白银期货 LOF 净值
    shfeSilver: MarketSeriesValue;          // 沪银主力
    sgeAgTd: MarketSeriesValue;             // 上金所 Ag(T+D)
    goldSilverRatio: MarketSeriesValue;     // 金银比
  };
}

// ——— daily.json ———
export type DailySeriesMap = Record<string, (number | null)[]>;

export interface DailyData {
  generatedAt: string;
  asOfDate: string;
  dates: string[];
  series: DailySeriesMap;
  /** 各序列最后真实值日期（ffill 前），如 {"shfeInvT":"2026-07-17"}；管道未升级时可能缺省 */
  lastActual?: Record<string, string>;
  /** 近期数据起点（daily_recent.json 特有），前端据此判断是否需懒加载历史 */
  recentFrom?: string;
}

// ——— positions_curve.json / virtual_ratio.json ———
export interface CurvePoint {
  x: number;
  y: number;
}

export interface CurveContract {
  code: string;
  expiry: string;
  points: CurvePoint[];
}

export interface CurveData {
  generatedAt?: string;
  formula?: string;
  label?: string;
  symbol?: string;
  asOfDate?: string;
  windowTradingDays?: number;
  contracts: CurveContract[];
}

export interface MetalVirtualRatioData {
  generatedAt?: string;
  source?: {
    workbook: string;
    warehouseSheet: string;
    contractSheet: string;
  };
  qualityNotes?: string[];
  metals: {
    pt: CurveData;
    pd: CurveData;
  };
}

// ——— shfe_positioning.json（Project-004） ———
export interface PositioningSummaryRow {
  category: string;
  label: string;
  long: number;
  longChange: number;
  short: number;
  shortChange: number;
}

export interface ShfePositioningData {
  generatedAt: string;
  asOfDate: string;
  source: {
    project: string;
    rankingPattern: string;
    sgeFile: string;
  };
  quality: {
    shfeTradingDays: number;
    sgeTradingDays: number;
    commonTradingDays: number;
    notes: string[];
  };
  summary: PositioningSummaryRow[];
  nonFuturesTrend: {
    dates: string[];
    longLots: number[];
    shortLots: number[];
    netLots: number[];
  };
  combinedTrend: {
    dates: string[];
    shfeLongTons: number[];
    shfeShortTons: number[];
    sgeOpenInterestTons: number[];
  };
}

// ——— pp_warehouse.json（Project-005） ———
export interface PpWarehouseLocation {
  code: string;
  name: string;
  type: "仓库" | "厂库";
  quantityKg: number;
  registeredKg: number;
  cancelledKg: number;
  changeKg: number;
}

export interface PpWarehouseMetal {
  label: string;
  symbol: string;
  dates: string[];
  warehouseKg: number[];
  factoryKg: number[];
  totalKg: number[];
  registeredKg: number[];
  cancelledKg: number[];
  netChangeKg: number[];
  latest: {
    date: string;
    warehouseKg: number;
    factoryKg: number;
    totalKg: number;
    registeredKg: number;
    cancelledKg: number;
    netChangeKg: number;
  };
  locations: PpWarehouseLocation[];
}

export interface PpWarehouseData {
  generatedAt: string;
  asOfDate: string;
  source: { project: string; file: string; unit: string };
  quality: { rowCount: number; notes: string[] };
  metals: { pt: PpWarehouseMetal; pd: PpWarehouseMetal };
}

// ——— basis_*.json ———
export interface BasisStats {
  latest: number;
  mean: number;
  percentile: number;
  min: number;
  max: number;
}

export interface BasisData {
  pair: string;
  generatedAt?: string;
  times: string[];
  values: number[];
  stats: BasisStats;
}

// ——— import_profit.json ———
export interface ImportProfitStats {
  importLatest: number;
  importMean: number;
  importPercentile: number;
  processingExportLatest: number;
  processingExportMean: number;
  processingExportPercentile: number;
  generalExportLatest: number;
  generalExportMean: number;
  generalExportPercentile: number;
}

export interface ImportProfitData {
  generatedAt?: string;
  frequency: "minute" | "daily";
  selectionMethod: string;
  foreignContract: string;
  domesticContract: string;
  fxContract: string;
  mainQuoteCount: number;
  windowTradingDays?: number;
  windowStart?: string;
  windowEnd?: string;
  importFormula: string;
  processingExportFormula: string;
  generalExportFormula: string;
  times: string[];
  importProfit: number[];
  processingExportProfit: number[];
  generalExportProfit: number[];
  stats: ImportProfitStats;
}

// ——— seasonality.json ———
export interface SeasonalityData {
  generatedAt?: string;
  dates: string[];
  years: Record<string, (number | null)[]>;
}

// ——— lease_rates.json ———
export interface LeaseRatesData {
  generatedAt?: string;
  dates: string[];
  series: Record<string, (number | null)[]>;
}

// ——— 汇总 ———
export interface DashboardData {
  monitoring: MonitoringData;
  market: MarketData;
  daily: DailyData;
  positions: CurveData;
  virtualRatio: CurveData;
  metalVirtualRatio: MetalVirtualRatioData;
  shfePositioning: ShfePositioningData;
  ppWarehouse: PpWarehouseData;
  seasonality: SeasonalityData;
  leaseRates: LeaseRatesData;
}
