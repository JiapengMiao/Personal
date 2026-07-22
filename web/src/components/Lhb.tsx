import { useEffect, useMemo, useState } from "react";
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
  dates?: LhbSnapshot[];
}

export interface LhbSnapshot {
  date: string;
  contracts: LhbContract[];
}

// ——— 06b 龙虎榜（上期所成交持仓排名） ———
export function LhbSection({ data }: { data: LhbData | null }) {
  const [activeDate, setActiveDate] = useState("");
  const [activeCode, setActiveCode] = useState("");
  const [hoveredMember, setHoveredMember] = useState<string | null>(null);

  const snapshots = useMemo<LhbSnapshot[]>(() => {
    if (!data) return [];
    return data.dates?.length ? data.dates : [{ date: data.date, contracts: data.contracts }];
  }, [data]);

  const snapshot = snapshots.find((item) => item.date === activeDate) ?? snapshots[snapshots.length - 1];
  const contract = snapshot?.contracts.find((item) => item.code === activeCode) ?? snapshot?.contracts[0];

  useEffect(() => {
    if (!snapshots.length) return;
    setActiveDate((current) => current && snapshots.some((item) => item.date === current) ? current : snapshots[snapshots.length - 1].date);
  }, [snapshots]);

  useEffect(() => {
    if (!snapshot?.contracts.length) return;
    setActiveCode((current) => current && snapshot.contracts.some((item) => item.code === current) ? current : snapshot.contracts[0].code);
  }, [snapshot]);

  const selectDate = (value: string) => {
    const exact = snapshots.find((item) => item.date === value);
    const nearestPrevious = [...snapshots].reverse().find((item) => item.date <= value);
    const nextDate = exact?.date ?? nearestPrevious?.date ?? snapshots[0]?.date;
    if (nextDate) setActiveDate(nextDate);
    setHoveredMember(null);
  };

  if (!data || !snapshot || !contract) return null;

  return (
    <section className="section-block" id="lhb">
      <SectionHeading index="06b" title="龙虎榜" desc={`上期所 AG ${snapshot.date} 成交持仓排名（多/空 TOP20）`} id="lhb" />
      <article className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <span>SHFE · DRAGON TIGER</span>
            <h3>持仓排名（多/空 TOP20）</h3>
          </div>
          <div className="lhb-controls">
            <label className="lhb-date-picker">
              <span>交易日</span>
              <input
                type="date"
                aria-label="龙虎榜交易日"
                title="休市日会自动回退到此前最近的有效交易日"
                value={snapshot.date}
                min={snapshots[0]?.date}
                max={snapshots[snapshots.length - 1]?.date}
                onChange={(event) => selectDate(event.target.value)}
              />
            </label>
            <div className="lhb-tabs">
              {snapshot.contracts.map((c) => (
                <button
                  key={c.code}
                  className={`lhb-tab ${c.code === contract.code ? "active" : ""}`}
                  onClick={() => { setActiveCode(c.code); setHoveredMember(null); }}
                >
                  {c.code}
                </button>
              ))}
            </div>
          </div>
        </div>
        <div className="lhb-grid">
          <RankTable title="多头持仓 TOP20" rows={contract.long} hoveredMember={hoveredMember} setHoveredMember={setHoveredMember} />
          <RankTable title="空头持仓 TOP20" rows={contract.short} hoveredMember={hoveredMember} setHoveredMember={setHoveredMember} />
        </div>
      </article>
    </section>
  );
}

function RankTable({ title, rows, hoveredMember, setHoveredMember }: {
  title: string;
  rows: LhbMember[];
  hoveredMember: string | null;
  setHoveredMember: (member: string | null) => void;
}) {
  const sumPos = rows.reduce((s, r) => s + r.position, 0);
  const sumChg = rows.reduce((s, r) => s + r.change, 0);
  const sumNet = rows.reduce((s, r) => s + r.net, 0);
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
            <tr
              key={r.member}
              tabIndex={0}
              className={hoveredMember === r.member ? "is-linked" : ""}
              onMouseEnter={() => setHoveredMember(r.member)}
              onMouseLeave={() => setHoveredMember(null)}
              onFocus={() => setHoveredMember(r.member)}
              onBlur={() => setHoveredMember(null)}
            >
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
        <tfoot>
          <tr className="lhb-total">
            <td></td>
            <td className="lhb-member">合计 TOP{rows.length}</td>
            <td><strong>{formatNumber(sumPos, 0)}</strong></td>
            <td className={sumChg > 0 ? "val-up" : sumChg < 0 ? "val-down" : ""}>
              <strong>{sumChg > 0 ? "+" : ""}{formatNumber(sumChg, 0)}</strong>
            </td>
            <td className={sumNet > 0 ? "val-up" : sumNet < 0 ? "val-down" : ""}>
              <strong>{formatNumber(sumNet, 0)}</strong>
            </td>
          </tr>
        </tfoot>
      </table>
    </div>
  );
}
