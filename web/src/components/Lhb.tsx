import { useState } from "react";
import { SectionHeading } from "./shared";
import { formatNumber } from "../lib/format";

// ——— 龙虎榜类型 ———
export interface LhbMember {
  rank: number;
  member: string;
  position: number;
  change: number;
  net: number;
}

export interface LhbContract {
  code: string;
  long: LhbMember[];
  short: LhbMember[];
}

export interface LhbData {
  date: string;
  generatedAt?: string;
  contracts: LhbContract[];
}

// ——— 06b 龙虎榜（上期所成交持仓排名） ———
export function LhbSection({ data }: { data: LhbData | null }) {
  const [activeIdx, setActiveIdx] = useState(0);

  if (!data || !data.contracts.length) return null;

  const contract = data.contracts[activeIdx] ?? data.contracts[0];

  return (
    <section className="section-block" id="lhb">
      <SectionHeading index="06b" title="龙虎榜" desc={`上期所 AG ${data.date} 成交持仓排名（多/空 TOP20）`} id="lhb" />
      <article className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <span>SHFE · DRAGON TIGER</span>
            <h3>持仓排名（多/空 TOP20）</h3>
          </div>
          <div className="lhb-tabs">
            {data.contracts.map((c, i) => (
              <button
                key={c.code}
                className={`lhb-tab ${i === activeIdx ? "active" : ""}`}
                onClick={() => setActiveIdx(i)}
              >
                {c.code}
              </button>
            ))}
          </div>
        </div>
        <div className="lhb-grid">
          <RankTable title="多头持仓 TOP20" rows={contract.long} side="long" />
          <RankTable title="空头持仓 TOP20" rows={contract.short} side="short" />
        </div>
      </article>
    </section>
  );
}

function RankTable({ title, rows, side }: { title: string; rows: LhbMember[]; side: "long" | "short" }) {
  return (
    <div className="lhb-table-wrap">
      <h4 className="lhb-table-title">{title}</h4>
      <table className="lhb-table">
        <thead>
          <tr>
            <th>#</th>
            <th>席位</th>
            <th>持仓量</th>
            <th>增减</th>
            <th>净持仓</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.rank}>
              <td className="lhb-rank">{r.rank}</td>
              <td className="lhb-member">{r.member}</td>
              <td>{formatNumber(r.position, 0)}</td>
              <td className={r.change > 0 ? "val-up" : r.change < 0 ? "val-down" : ""}>
                {r.change > 0 ? "+" : ""}{formatNumber(r.change, 0)}
              </td>
              <td className={r.net > 0 ? "val-up" : r.net < 0 ? "val-down" : ""}>
                {formatNumber(r.net, 0)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
