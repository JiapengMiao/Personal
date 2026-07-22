import { useEffect, useMemo, useState } from "react";
import { SectionHeading } from "./shared";

interface QuoteRow {
  name: string;
  cat: string;
  fSh: string | null;
  fGd: string | null;
  fCt: string | null;
  sSh: string | null;
  sGd: string | null;
  sCt: string | null;
  note: string | null;
}

interface DayData {
  date: string;
  tdSpread: string | null;
  count: number;
  quoted: number;
  quotes: QuoteRow[];
}

interface SpotQuotesAll {
  dates: string[];
  days: DayData[];
}

const CAT_LABELS: Record<string, string> = {
  smelter: "冶炼厂",
  trader: "贸易商",
  futures: "期货风险子",
  bank: "银行",
  other: "其他",
};

export function SpotQuotesSection() {
  const [data, setData] = useState<SpotQuotesAll | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedDate, setSelectedDate] = useState<string>("");

  useEffect(() => {
    fetch("data/spot_quotes.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: SpotQuotesAll) => {
        setData(d);
        if (d.dates.length) setSelectedDate(d.dates[d.dates.length - 1]);
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const day = useMemo(() => {
    if (!data || !selectedDate) return null;
    return data.days.find((d) => d.date === selectedDate) ?? null;
  }, [data, selectedDate]);

  if (error) return null;
  if (!data || !day) return <div className="section-block" style={{ minHeight: 60 }} />;

  const minDate = data.dates[0];
  const maxDate = data.dates[data.dates.length - 1];

  return (
    <section className="section-block" id="spot-quotes">
      <SectionHeading
        index="07"
        title="现货基差报价"
        desc={`${day.date} · ${day.quoted}/${day.count} 家有报价${day.tdSpread ? ` · ${day.tdSpread}` : ""}`}
        id="spot-quotes"
      />
      <article className="panel chart-panel" style={{ overflow: "auto" }}>
        {/* 日期选择器 */}
        <div className="spot-date-picker">
          <label>
            选择日期
            <select value={selectedDate} onChange={(e) => setSelectedDate(e.target.value)}>
              {[...data.dates].reverse().map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </label>
          <label>
            或指定
            <input
              type="date"
              value={selectedDate}
              min={minDate}
              max={maxDate}
              onChange={(e) => { if (data.dates.includes(e.target.value)) setSelectedDate(e.target.value); }}
            />
          </label>
          <div className="spot-legend">
            {Object.entries(CAT_LABELS).map(([key, label]) => (
              <span key={key} className={`spot-cat-dot cat-${key}`}>{label}</span>
            ))}
          </div>
        </div>
        {/* 报价表 */}
        <table className="spot-table">
          <thead>
            <tr>
              <th rowSpan={2}>报价方</th>
              <th colSpan={3}>大厂银锭</th>
              <th colSpan={3}>国标 1#</th>
              <th rowSpan={2}>备注</th>
            </tr>
            <tr>
              <th>上海</th>
              <th>广东</th>
              <th>厂提</th>
              <th>上海</th>
              <th>广东</th>
              <th>厂提</th>
            </tr>
          </thead>
          <tbody>
            {day.quotes.map((q, i) => {
              const hasQuote = q.fSh || q.fGd || q.fCt || q.sSh || q.sGd || q.sCt;
              return (
                <tr key={i} className={`${hasQuote ? "" : "no-quote"} cat-${q.cat}`}>
                  <td className="quoter-name">
                    <span className={`spot-dot cat-${q.cat}`} />
                    {q.name}
                  </td>
                  <td>{q.fSh ?? ""}</td>
                  <td>{q.fGd ?? ""}</td>
                  <td>{q.fCt ?? ""}</td>
                  <td>{q.sSh ?? ""}</td>
                  <td>{q.sGd ?? ""}</td>
                  <td>{q.sCt ?? ""}</td>
                  <td className="note-cell">{q.note ?? ""}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </article>
    </section>
  );
}
