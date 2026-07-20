export function formatNumber(value: number, decimals = 1): string {
  return new Intl.NumberFormat("zh-CN", {
    maximumFractionDigits: decimals,
    minimumFractionDigits: 0,
  }).format(value);
}

export function formatScore(score: number | null): string {
  if (score === null) return "基线";
  return score > 0 ? `+${score}` : `${score}`;
}

/** ISO → "YYYY-MM-DD HH:mm"（按 UTC+8 显示） */
export function formatFetchedAt(iso: string | null | undefined): string {
  if (!iso) return "—";
  const time = new Date(iso).getTime();
  if (Number.isNaN(time)) return iso.slice(0, 10);
  const shifted = new Date(time + 8 * 3600 * 1000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${shifted.getUTCFullYear()}-${pad(shifted.getUTCMonth() + 1)}-${pad(shifted.getUTCDate())} ${pad(shifted.getUTCHours())}:${pad(shifted.getUTCMinutes())}`;
}

export function formatTradeTime(raw: string): string {
  const match = raw.match(/^(\d{4})(\d{2})(\d{2})\s+(\d{2}:\d{2})/);
  return match ? `${match[1]}-${match[2]}-${match[3]} ${match[4]}` : raw;
}

/** 平行数组里最后一个非 null 值 */
export function lastNonNull(series: (number | null)[] | undefined): number | null {
  if (!series) return null;
  for (let i = series.length - 1; i >= 0; i -= 1) {
    const v = series[i];
    if (v !== null && v !== undefined) return v;
  }
  return null;
}

export function lastPoint(points: { date: string; value: number }[]): { date: string; value: number } | null {
  return points.length ? points[points.length - 1] : null;
}

/** 序列最后"真实值"日期：优先 lastActual 字段，缺省时回退为最后一个非 null 点的日期 */
export function lastActualDate(
  dates: string[],
  series: (number | null)[] | undefined,
  lastActual?: Record<string, string>,
  key?: string,
): string | null {
  if (lastActual && key && lastActual[key]) return lastActual[key];
  if (!series) return null;
  for (let i = series.length - 1; i >= 0; i -= 1) {
    if (series[i] !== null && series[i] !== undefined) return dates[i] ?? null;
  }
  return null;
}

/** 前值填充：头部 null 保留，首个有效值后不再出现 null */
export function ffill(series: (number | null)[] | undefined): (number | null)[] {
  if (!series) return [];
  let cur: number | null = null;
  return series.map((v) => {
    if (v !== null && v !== undefined) cur = v;
    return cur;
  });
}

/** "2026-07-10" → "7/10" */
export function shortMd(date: string | null): string {
  if (!date) return "—";
  const m = date.match(/^\d{4}-(\d{1,2})-(\d{1,2})/);
  return m ? `${Number(m[1])}/${Number(m[2])}` : date;
}

export function deltaOf(series: (number | null)[] | undefined): number | null {
  if (!series) return null;
  let latest: number | null = null;
  for (let i = series.length - 1; i >= 0; i -= 1) {
    const v = series[i];
    if (v === null || v === undefined) continue;
    if (latest === null) {
      latest = v;
    } else {
      return latest - v;
    }
  }
  return null;
}
