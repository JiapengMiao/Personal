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

export interface MonitoringData {
  generatedAt: string;
  asOfDate: string;
  overallPulse: OverallPulse;
  sources: Record<string, unknown>;
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
    comexStocks: MarketSeriesValue;
    shfeWarrants: MarketSeriesValue;
    londonSilverUsd: MarketSeriesValue;
    londonGoldUsd: MarketSeriesValue;
    agFuturesClose: FuturesSeries;
    silverFund: FundSeries;
    sgeAg9999Close: MarketSeriesValue;
    sgeAgTdLatest: AgTdLatest;
    sgeInventory: MarketSeriesValue;
    goldSilverRatio: MarketSeriesValue;
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
  contracts: CurveContract[];
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
  exportLatest: number;
  exportMean: number;
  exportPercentile: number;
}

export interface ImportProfitData {
  generatedAt?: string;
  times: string[];
  importProfit: number[];
  exportProfit: number[];
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
  seasonality: SeasonalityData;
  leaseRates: LeaseRatesData;
}
