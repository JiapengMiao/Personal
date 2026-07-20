import { useEffect, useRef } from "react";
import { echarts, type ThemeMode } from "./echarts";
import type { EChartsCoreOption } from "echarts/core";

/**
 * 轻量 useEChart hook：
 * - build 返回完整 option；deps 变化时重建 option（主题切换时整个重算）
 * - 自动 init / resize（ResizeObserver）/ dispose
 * - onChart：每次 option 重建后回调 chart 实例（用于挂 datazoom 等事件，组件内自行 off/on 防重复）
 */
export function useEChart(
  build: () => EChartsCoreOption | null,
  deps: unknown[],
  theme: ThemeMode,
  onChart?: (chart: echarts.ECharts) => void,
) {
  const ref = useRef<HTMLDivElement | null>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const buildRef = useRef(build);
  buildRef.current = build;
  const onChartRef = useRef(onChart);
  onChartRef.current = onChart;

  // 主题或数据变化时重建 option
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(el);
    }
    const option = buildRef.current();
    if (option) {
      chartRef.current.setOption(option, { notMerge: true });
    }
    if (chartRef.current) onChartRef.current?.(chartRef.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, theme]);

  // resize
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const chart = () => chartRef.current;
    const ro = new ResizeObserver(() => {
      chart()?.resize();
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // dispose
  useEffect(() => {
    return () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  return ref;
}
