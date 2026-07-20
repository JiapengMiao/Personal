import { useEffect, useState } from "react";
import { SectionHeading } from "./shared";

interface QuoteRow {
  name: string;
  factorySh: string | null;
  factoryGd: string | null;
  factoryCt: string | null;
  stdSh: string | null;
  stdGd: string | null;
  stdCt: string | null;
  note: string | null;
}

interface SpotQuotesData {
  date: string;
  tdFuturesSpread: string | null;
  count: number;
  quotedCount: number;
  quotes: QuoteRow[];
}

export function SpotQuotesSection() {
  const [data, setData] = useState<SpotQuotesData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("data/spot_quotes.json")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((d: SpotQuotesData) => setData(d))
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return null;
  if (!data) return <div className="section-block" style={{ minHeight: 60 }} />;

  return (
    <section className="section-block" id="spot-quotes">
      <SectionHeading
        index="05b"
        title="现货基差报价"
        desc={`最新报价日：${data.date} · ${data.quotedCount}/${data.count} 家有报价${data.tdFuturesSpread ? ` · ${data.tdFuturesSpread}` : ""}`}
        id="spot-quotes"
      />
      <article className="panel chart-panel" style={{ overflow: "auto" }}>
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
            {data.quotes.map((q, i) => {
              const hasQuote = q.factorySh || q.factoryGd || q.factoryCt || q.stdSh || q.stdGd || q.stdCt;
              return (
                <tr key={i} className={hasQuote ? "" : "no-quote"}>
                  <td className="quoter-name">{q.name}</td>
                  <td>{q.factorySh ?? ""}</td>
                  <td>{q.factoryGd ?? ""}</td>
                  <td>{q.factoryCt ?? ""}</td>
                  <td>{q.stdSh ?? ""}</td>
                  <td>{q.stdGd ?? ""}</td>
                  <td>{q.stdCt ?? ""}</td>
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
