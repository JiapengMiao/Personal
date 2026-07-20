import * as echarts from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  MarkAreaComponent,
  MarkLineComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  LineChart,
  BarChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  DataZoomComponent,
  MarkLineComponent,
  MarkAreaComponent,
  CanvasRenderer,
]);

export { echarts };

export type ThemeMode = "dark" | "light";

export interface Palette {
  hairline: string;
  edge: string;
  text: string;
  sub: string;
  weak: string;
  gold: string;
  goldBright: string;
  silver: string;
  up: string;
  down: string;
  base: string;
  live: string;
  panel: string;
  raised: string;
  tooltipBg: string;
  series: string[];
}

const darkPalette: Palette = {
  hairline: "rgba(150, 180, 214, 0.12)",
  edge: "rgba(150, 180, 214, 0.26)",
  text: "#e8eef6",
  sub: "#9fb0c3",
  weak: "#64748b",
  gold: "#d9a441",
  goldBright: "#f0c264",
  silver: "#c7d3e0",
  up: "#3ecf8e",
  down: "#f26d6d",
  base: "#e8b34a",
  live: "#56c8dc",
  panel: "#0a101b",
  raised: "#0e1524",
  tooltipBg: "#0e1524",
  series: ["#d9a441", "#56c8dc", "#3ecf8e", "#f26d6d", "#c7d3e0", "#e8b34a", "#f0c264", "#8a9bb5"],
};

const lightPalette: Palette = {
  hairline: "rgba(16, 26, 38, 0.12)",
  edge: "rgba(16, 26, 38, 0.26)",
  text: "#101a26",
  sub: "#46596c",
  weak: "#627386",
  gold: "#9a6d12",
  goldBright: "#7c5a10",
  silver: "#5c7186",
  up: "#157a4c",
  down: "#bf3b34",
  base: "#8f660f",
  live: "#0d7d92",
  panel: "#ffffff",
  raised: "#edf1f5",
  tooltipBg: "#ffffff",
  series: ["#9a6d12", "#0d7d92", "#157a4c", "#bf3b34", "#5c7186", "#8f660f", "#7c5a10", "#8a9bb5"],
};

export function getPalette(mode: ThemeMode): Palette {
  return mode === "light" ? lightPalette : darkPalette;
}

/** 通用坐标轴/分割线/工具提示基础配置 */
export function baseAxis(p: Palette) {
  return {
    axisLine: { lineStyle: { color: p.edge } },
    axisTick: { lineStyle: { color: p.edge } },
    axisLabel: { color: p.weak, fontFamily: "JetBrains Mono, monospace", fontSize: 11 },
    splitLine: { lineStyle: { color: p.hairline, type: [3, 5] as const, opacity: 0.5 } },
  };
}

export function baseTooltip(p: Palette) {
  return {
    backgroundColor: p.tooltipBg,
    borderColor: p.edge,
    borderWidth: 1,
    padding: [10, 12] as [number, number],
    textStyle: { color: p.text, fontFamily: "JetBrains Mono, monospace", fontSize: 12 },
    extraCssText: "box-shadow: 0 18px 50px rgba(0,0,0,.35); border-radius: 8px;",
  };
}

export function baseLegend(p: Palette) {
  return {
    textStyle: { color: p.sub, fontFamily: "JetBrains Mono, monospace", fontSize: 11 },
    inactiveColor: p.weak,
    icon: "roundRect",
    itemWidth: 10,
    itemHeight: 8,
    itemGap: 14,
  };
}

export function zoomFill(p: Palette) {
  return {
    borderColor: p.edge,
    backgroundColor: "transparent",
    fillerColor: modeFiller(p),
    handleStyle: { color: p.gold, borderColor: p.goldBright },
    moveHandleStyle: { color: p.gold },
    emphasis: { moveHandleStyle: { color: p.goldBright } },
    dataBackground: {
      lineStyle: { color: p.edge },
      areaStyle: { color: p.hairline },
    },
    selectedDataBackground: {
      lineStyle: { color: p.gold },
      areaStyle: { color: "rgba(217,164,65,.15)" },
    },
    textStyle: { color: p.weak, fontFamily: "JetBrains Mono, monospace" },
  };
}

function modeFiller(p: Palette) {
  return p.tooltipBg === "#ffffff" ? "rgba(16,26,38,.08)" : "rgba(150,180,214,.10)";
}

/** "#f26d6d" + 0.12 → "rgba(242,109,109,0.12)" */
export function hexToRgba(hex: string, alpha: number): string {
  const m = hex.match(/^#([0-9a-f]{2})([0-9a-f]{2})([0-9a-f]{2})$/i);
  if (!m) return hex;
  return `rgba(${parseInt(m[1], 16)},${parseInt(m[2], 16)},${parseInt(m[3], 16)},${alpha})`;
}
