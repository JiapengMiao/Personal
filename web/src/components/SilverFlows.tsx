import { useEffect, useMemo, useState } from "react";
import { baseAxis, baseTooltip, getPalette, hexToRgba, type ThemeMode } from "../lib/echarts";
import { useEChart } from "../lib/useEChart";
import { SectionHeading } from "./shared";
import { formatNumber } from "../lib/format";
import { fetchData } from "../lib/data";

// ——— 07C 全球银条流向 · 2025（WSS 2026 Appendix 23-30 + 官方海关伙伴拆分）———

interface FlowPartner {
  name: string;
  tonnes: number;
  lowConfidence?: boolean;   // wss：几何证据较弱或与官方口径矛盾的小流量项
}

interface FlowGroup {
  hub: string;
  direction: "export" | "import";
  kind?: "wss" | "official";     // wss = WSS 2026 报告口径；official = 官方海关 2025 全年口径
  sharePct: number;              // wss：展示部分占枢纽总量比例（%）；official：恒为 100
  impliedTotalTonnes: number;    // wss：占比反推的枢纽总量；official：全年实际合计
  partners: FlowPartner[];       // 伙伴（从大到小；official 组末位可为「其他」）
  source?: string;
}

interface SilverFlowsData {
  generatedAt: string;
  source: string;
  asOf: string;
  unit: string;
  note?: string;
  flows: FlowGroup[];
}

const T_PER_MOZ = 31.1035; // 1 Moz = 31.1035 吨

// 语义色：出口橙 / 进口蓝（与主题无关的语义色，明暗两套主题下均可读，不走调色板轮换色）
const EXPORT_COLOR = "#e07b39";
const IMPORT_COLOR = "#3f8fd1";

export function SilverFlowsSection({ theme }: { theme: ThemeMode }) {
  const [data, setData] = useState<SilverFlowsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchData<SilverFlowsData>("data/silver_flows.json")
      .then((d: SilverFlowsData) => setData(d))
      .catch((e: Error) => setError(e.message));
  }, []);

  if (error) return null;
  if (!data) return <div className="section-block" style={{ minHeight: 60 }} />;

  const wssCount = data.flows.filter((f) => f.kind !== "official").length;
  const officialCount = data.flows.length - wssCount;

  return (
    <section className="section-block" id="silverflows">
      <SectionHeading
        index="07C"
        title="全球银条流向"
        desc={`WSS 2026 报告口径 ${wssCount} 组（占枢纽总量 85%–98%）+ 官方海关 2025 全年口径 ${officialCount} 组（Top 伙伴+其他）· 出口橙 / 进口蓝 · 条标为吨数，悬停可见 Moz 换算`}
        id="silverflows"
      />

      <article className="panel chart-panel">
        <div className="panel-heading">
          <div>
            <span>贸易 · BULLION FLOWS</span>
            <h3>全球银条流向（2025，吨）</h3>
          </div>
          <div className="panel-stat">
            <small>报告口径 + 海关口径并列展示</small>
            <strong>{data.flows.length} 组流向</strong>
          </div>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(min(430px, 100%), 1fr))",
            gap: 14,
            marginTop: 6,
          }}
        >
          {data.flows.map((f) => (
            <FlowCard key={`${f.hub}-${f.direction}-${f.kind ?? "wss"}`} flow={f} theme={theme} />
          ))}
        </div>

        <p className="chart-note">
          来源：World Silver Survey 2026（Silver Institute）Appendix 23-30 银条流向示意图（瑞士进出口 / 英国进出口 /
          香港出口 / 印度进口 6 组，展示为主要伙伴、占枢纽总量 85%–98%，枢纽总量由占比反推）。WSS 组配对已于
          2026-07-24 经 PDF 箭头矢量几何重做，并以官方海关 2025 全年数据交叉验证（英国出口 HMRC 6/6 吻合、
          香港出口 IDDS 9/11 吻合、印度进口 TradeStat 8/9 吻合；英国进口图面为 Metals Focus 原产地口径，
          与 HMRC 发货国口径构成不同，详见报告）；标 <b>*</b>（半透明虚线边）为低置信项。
          官方海关 2025 全年口径 Top 伙伴 + 其他（累计 ≥95%）：美国进出口（USITC DataWeb / U.S. Census HS/HTS 7106，
          GM+CGM 克加总换算）、印度出口（TradeStat 印度商务部 HS7106，Calendar Year）、香港进口（香港政府统计处
          HKHS6 7106 按原产地）· 1 Moz = 31.1035 吨
        </p>
      </article>
    </section>
  );
}

function FlowCard({ flow, theme }: { flow: FlowGroup; theme: ThemeMode }) {
  const isWss = flow.kind !== "official";
  const color = flow.direction === "export" ? EXPORT_COLOR : IMPORT_COLOR;
  const dirLabel = flow.direction === "export" ? "出口" : "进口";
  const title = isWss
    ? `${flow.hub}${dirLabel} · 占 ${flow.sharePct}%`
    : `${flow.hub}${dirLabel} · 2025 全年`;
  const totalLine = isWss
    ? `总量 ≈ ${formatNumber(flow.impliedTotalTonnes, 0)} 吨 · WSS报告`
    : `合计 ${formatNumber(flow.impliedTotalTonnes, 1)} 吨 · 官方海关`;

  const build = useMemo(() => {
    return () => {
      const p = getPalette(theme);
      const names = flow.partners.map((x) => x.name);
      const values = flow.partners.map((x) =>
        x.lowConfidence
          ? { value: x.tonnes, itemStyle: { opacity: 0.45, borderType: "dashed" as const, borderWidth: 1, borderColor: color } }
          : x.tonnes,
      );
      const tipFoot = isWss
        ? `枢纽${dirLabel}总量 ≈ ${formatNumber(flow.impliedTotalTonnes, 0)} 吨（按占比 ${flow.sharePct}% 反推）· WSS 2026 报告口径`
        : `${flow.hub}${dirLabel} 2025 全年合计 ${formatNumber(flow.impliedTotalTonnes, 1)} 吨 · 官方海关口径（Top 伙伴+其他）`;
      return {
        animation: false,
        animationDuration: 0,
        animationDurationUpdate: 0,
        grid: { top: 6, right: 58, bottom: 6, left: 6, containLabel: true },
        tooltip: {
          trigger: "item",
          ...baseTooltip(p),
          formatter: (params: unknown) => {
            const it = params as { name: string; value: number; color: string; dataIndex: number };
            const partner = flow.partners[it.dataIndex];
            const moz = it.value / T_PER_MOZ;
            const lines = [
              `<div style="margin-bottom:4px"><strong>${flow.hub}${dirLabel} → ${it.name}</strong></div>`,
              `<div style="display:flex;gap:8px;align-items:center"><i style="width:8px;height:8px;border-radius:2px;background:${it.color};display:inline-block"></i><b>${formatNumber(it.value, 1)} 吨</b> · ${formatNumber(moz, 1)} Moz</div>`,
            ];
            if (partner?.lowConfidence) {
              lines.push(`<div style="margin-top:4px;color:#d9a441;font-size:11px">* 低置信：几何证据较弱或与官方口径存在差异</div>`);
            }
            lines.push(`<div style="margin-top:5px;color:${p.weak};font-size:11px">${tipFoot}</div>`);
            return lines.join("");
          },
        },
        xAxis: {
          type: "value",
          ...baseAxis(p),
          axisLabel: { ...baseAxis(p).axisLabel, formatter: (v: number) => formatNumber(v, 0) },
        },
        yAxis: {
          type: "category",
          data: names,
          inverse: true,
          ...baseAxis(p),
          axisLabel: {
            color: p.sub,
            fontSize: 12,
            formatter: (v: string) => {
              const partner = flow.partners.find((x) => x.name === v);
              return partner?.lowConfidence ? `${v} *` : v;
            },
          },
          splitLine: { show: false },
        },
        series: [
          {
            name: title,
            type: "bar" as const,
            data: values,
            barMaxWidth: 15,
            itemStyle: {
              color: hexToRgba(color, theme === "light" ? 0.82 : 0.9),
              borderRadius: [0, 4, 4, 0],
            },
            label: {
              show: true,
              position: "right" as const,
              formatter: (pr: unknown) => formatNumber((pr as { value: number }).value, 1),
              color: p.weak,
              fontFamily: "JetBrains Mono, monospace",
              fontSize: 11,
            },
          },
        ],
      };
    };
  }, [flow, color, dirLabel, title, isWss, theme]);

  const chartRef = useEChart(build, [flow, theme], theme);
  const height = Math.max(216, flow.partners.length * 26 + 16);

  return (
    <div
      style={{
        background: "var(--raised)",
        border: "1px solid var(--hairline)",
        borderRadius: 10,
        padding: "12px 12px 4px",
        minWidth: 0,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <strong style={{ fontSize: 13.5, color: "var(--text)", display: "flex", alignItems: "center" }}>
          <i style={{ width: 8, height: 8, borderRadius: 2, background: color, display: "inline-block", marginRight: 7 }} />
          {title}
        </strong>
        <small style={{ color: "var(--weak)", fontFamily: "var(--mono)", fontSize: 11, whiteSpace: "nowrap" }}>
          {totalLine}
        </small>
      </div>
      <div ref={chartRef} className="echart chart-wrap" style={{ height, marginTop: 2 }} />
    </div>
  );
}
