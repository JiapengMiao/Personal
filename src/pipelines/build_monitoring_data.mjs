// 监测数据底稿编译器：把 data/monitoring/monitoring-source.json 编译成
// data/monitoring/monitoring-base.json。指标16的实时全球库存由
// build_dashboard_data.py 根据统一 Wind 主表覆盖计算。
// 信号规则（与 Excel 底稿一致）：变动值 = 本期值 - 上期值（% 单位按百分点差）；
// 方向“越高越利多”时，变动 >= 上阈值 => +2，<= 下阈值 => -2，之间取符号；方向“越低越利多”时反转。
// 缺少上期值 => 不判断方向，保留基线。
// 触发记录：相邻两期之间，升为 +2 => 站上强利多；降为 -2 => 跌入强利空；
// 非零方向反转 => 方向反转；离开 ±2 => 强信号解除。
// 用法：node src/pipelines/build_monitoring_data.mjs
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const monitoringRoot = path.join(projectRoot, "data", "monitoring");
const sourcePath = path.join(monitoringRoot, "monitoring-source.json");
const outputPath = path.join(monitoringRoot, "monitoring-base.json");

const EPS = 1e-9;
const UNITS = new Set(["吨", "%", "TWh", "GW", "mg/W"]);
const DIRECTIONS = new Set(["越高越利多", "越低越利多"]);
const KINDS = new Set(["actual", "forecast", "estimate"]);
const STATUS_LABEL = { "2": "强利多", "1": "偏利多", "0": "中性", "-1": "偏利空", "-2": "强利空" };
const TONE_LABEL = { "2": "strong-positive", "1": "positive", "0": "neutral", "-1": "negative", "-2": "strong-negative" };
// 日频序列（如 Wind 接入的指标 16）使用 YYYY-MM-DD 期间标签
const DAILY_PERIOD = /^\d{4}-\d{2}-\d{2}$/;

const problems = [];
const fail = (message) => problems.push(message);

function round1(value) {
  return Math.round(value * 10) / 10;
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}

function formatDelta(delta, unit) {
  if (unit === "%") return `${delta >= 0 ? "+" : ""}${(delta * 100).toFixed(1)}个百分点`;
  return `${delta >= 0 ? "+" : ""}${round1(delta).toFixed(1)} ${unit}`;
}

function scoreForDelta(delta, direction, upperThreshold, lowerThreshold) {
  if (delta >= upperThreshold - EPS) return direction === "越高越利多" ? 2 : -2;
  if (delta <= lowerThreshold + EPS) return direction === "越高越利多" ? -2 : 2;
  if (delta > EPS) return direction === "越高越利多" ? 1 : -1;
  if (delta < -EPS) return direction === "越高越利多" ? -1 : 1;
  return 0;
}

function buildHistory(indicator) {
  const { series, direction, upperThreshold, lowerThreshold, unit, dataStatus } = indicator;
  return series.map((point, index) => {
    if (index === 0) {
      return {
        period: point.period,
        kind: point.kind,
        value: point.value,
        delta: null,
        score: null,
        status: series.length === 1 ? dataStatus : "基线",
      };
    }
    const previous = series[index - 1];
    const delta = unit === "%" ? round4(point.value - previous.value) : round1(point.value - previous.value);
    const score = scoreForDelta(delta, direction, upperThreshold, lowerThreshold);
    return {
      period: point.period,
      kind: point.kind,
      value: point.value,
      delta,
      score,
      status: STATUS_LABEL[String(score)],
    };
  });
}

function buildTriggers(indicator, history) {
  const events = [];
  for (let index = 1; index < history.length; index += 1) {
    const current = history[index];
    if (current.score === null) continue;
    // 日频点（YYYY-MM-DD）不参与触发记录：高频噪声会产生大量方向反转事件，
    // 触发记录只保留年度/月度口径的信号变化。
    if (DAILY_PERIOD.test(current.period)) continue;
    const previous = history[index - 1];
    const prevScore = previous.score;
    let kind = null;
    let severity = "neutral";
    let reason = "";
    if (current.score === 2 && prevScore !== 2) {
      kind = "站上强利多";
      severity = "positive";
      reason = `变动${formatDelta(current.delta, indicator.unit)}，突破上阈值`;
    } else if (current.score === -2 && prevScore !== -2) {
      kind = "跌入强利空";
      severity = "negative";
      reason = `变动${formatDelta(current.delta, indicator.unit)}，跌破下阈值`;
    } else if (prevScore !== null && Math.sign(prevScore) !== 0 && Math.sign(current.score) !== 0 && Math.sign(prevScore) !== Math.sign(current.score)) {
      kind = "方向反转";
      severity = current.score > 0 ? "positive" : "negative";
      reason = `信号由${STATUS_LABEL[String(prevScore)]}转为${current.status}`;
    } else if (prevScore !== null && Math.abs(prevScore) === 2 && Math.abs(current.score) !== 2) {
      kind = "强信号解除";
      severity = "neutral";
      reason = `由${STATUS_LABEL[String(prevScore)]}转为${current.status}`;
    }
    if (!kind) continue;
    events.push({
      id: `t${indicator.id}-${current.period}`,
      indicatorId: indicator.id,
      name: indicator.name,
      theme: indicator.theme,
      period: current.period,
      kind,
      severity,
      prevScore,
      score: current.score,
      delta: current.delta,
      description: `${reason}（阈值口径：${indicator.thresholdNote}）`,
    });
  }
  return events;
}

function validateSource(source) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(source.asOfDate ?? "")) fail("asOfDate 必须是 YYYY-MM-DD");
  const themes = new Set((source.themeSummaries ?? []).map((item) => item.theme));
  if (themes.size !== 5) fail("themeSummaries 必须包含五项监测主题");
  const ids = new Set();
  for (const indicator of source.indicators ?? []) {
    const tag = `指标 ${indicator.id ?? "?"}（${indicator.name ?? "未命名"}）`;
    if (ids.has(indicator.id)) fail(`${tag}：id 重复`);
    ids.add(indicator.id);
    if (!themes.has(indicator.theme)) fail(`${tag}：主题“${indicator.theme}”不在五项监测中`);
    if (!UNITS.has(indicator.unit)) fail(`${tag}：单位“${indicator.unit}”非法`);
    if (!DIRECTIONS.has(indicator.direction)) fail(`${tag}：利多方向非法`);
    if (!(indicator.upperThreshold > 0 && indicator.lowerThreshold < 0)) fail(`${tag}：阈值必须上正下负`);
    if (!/^\d{4}-\d{2}-\d{2}$/.test(indicator.updatedAt ?? "")) fail(`${tag}：updatedAt 必须是 YYYY-MM-DD`);
    if (indicator.sourceLabel !== "待确定" && !source.sources[indicator.sourceLabel]) fail(`${tag}：sourceLabel 未在 sources 中定义`);
    if (!Array.isArray(indicator.series)) fail(`${tag}：series 必须是数组`);
    if (indicator.dataStatus === "待接入" && indicator.series.length > 0) fail(`${tag}：待接入指标不应带有数值序列`);
    if (indicator.series.length === 0 && indicator.dataStatus !== "待接入") fail(`${tag}：空序列指标的数据状态应为“待接入”`);
    if (indicator.series.length === 1 && indicator.dataStatus !== "仅有基线") fail(`${tag}：单期序列的数据状态应为“仅有基线”`);
    for (const point of indicator.series) {
      if (!/^\d{4}[AFE]$/.test(point.period) && !DAILY_PERIOD.test(point.period)) fail(`${tag}：期间标签“${point.period}”应为 2026F/2025A/2026E 或 YYYY-MM-DD 形式`);
      if (!KINDS.has(point.kind)) fail(`${tag}：kind“${point.kind}”非法`);
      if (typeof point.value !== "number" || Number.isNaN(point.value)) fail(`${tag}：${point.period} 数值非法`);
    }
  }
  if (ids.size !== 17) fail(`指标数量应为 17，当前为 ${ids.size}`);
  if (!Array.isArray(source.marketBalance) || source.marketBalance.length < 2) fail("marketBalance 序列过短");
  if (!Array.isArray(source.industrialMix) || source.industrialMix.length < 2) fail("industrialMix 序列过短");
  if (!Array.isArray(source.actions) || source.actions.length === 0) fail("actions 不能为空");
}

function resolveIndicators(source) {
  return source.indicators.map((indicator) => {
    const history = buildHistory(indicator);
    const last = history[history.length - 1] ?? null;
    const previous = history.length >= 2 ? history[history.length - 2] : null;
    const scored = last !== null && last.score !== null;
    const sourceDef = indicator.sourceLabel === "待确定" ? null : source.sources[indicator.sourceLabel];
    return {
      id: indicator.id,
      theme: indicator.theme,
      role: indicator.role,
      name: indicator.name,
      period: last ? last.period : null,
      value: last ? last.value : null,
      priorPeriod: previous ? previous.period : null,
      priorValue: previous ? previous.value : null,
      unit: indicator.unit,
      direction: indicator.direction,
      upperThreshold: indicator.upperThreshold,
      lowerThreshold: indicator.lowerThreshold,
      thresholdNote: indicator.thresholdNote,
      score: scored ? last.score : 0,
      status: scored ? last.status : indicator.dataStatus,
      tone: scored ? TONE_LABEL[String(last.score)] : indicator.dataStatus === "待接入" ? "missing" : "neutral",
      dataStatus: indicator.dataStatus,
      frequency: indicator.frequency,
      updatedAt: indicator.updatedAt,
      sourceLabel: sourceDef ? sourceDef.label : "待确定",
      sourceUrl: sourceDef ? sourceDef.url : "",
      note: indicator.note,
      history,
    };
  });
}

function resolveThemes(source, indicators) {
  return source.themeSummaries.map((theme) => {
    const members = indicators.filter((item) => item.theme === theme.theme);
    const primary = members.find((item) => item.role.includes("主指标") && item.history.some((point) => point.score !== null));
    if (!primary) {
      const fallback = members[0];
      return { ...theme, score: 0, status: fallback.dataStatus, tone: fallback.dataStatus === "待接入" ? "missing" : "neutral" };
    }
    const expectedValue = `${new Intl.NumberFormat("zh-CN", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(primary.value)} ${primary.unit}`;
    if (theme.value !== expectedValue) fail(`主题“${theme.theme}”卡片值“${theme.value}”与主指标计算值“${expectedValue}”不一致`);
    return { ...theme, score: primary.score, status: primary.status, tone: primary.tone };
  });
}

const source = JSON.parse(await readFile(sourcePath, "utf8"));
validateSource(source);
const indicators = resolveIndicators(source);
const themeSummaries = resolveThemes(source, indicators);
const triggers = indicators
  .flatMap((indicator) => buildTriggers(indicator, indicator.history))
  .sort((a, b) => Number.parseInt(a.period, 10) - Number.parseInt(b.period, 10) || a.indicatorId - b.indicatorId);

if (problems.length > 0) {
  console.error("[monitoring-data] 校验失败：");
  for (const problem of problems) console.error(`  - ${problem}`);
  process.exit(1);
}

const output = {
  generatedAt: new Date().toISOString(),
  asOfDate: source.asOfDate,
  overallPulse: source.overallPulse,
  sources: source.sources,
  themeSummaries,
  indicators,
  triggers,
  marketBalance: source.marketBalance,
  industrialMix: source.industrialMix,
  actions: source.actions,
};

await writeFile(outputPath, `${JSON.stringify(output, null, 2)}\n`, "utf8");
const ready = indicators.filter((item) => item.value !== null).length;
console.log(`[monitoring-data] 已生成 ${path.relative(projectRoot, outputPath)}`);
console.log(`[monitoring-data] 指标 ${indicators.length} 项（${ready} 项有数值），触发记录 ${triggers.length} 条`);
