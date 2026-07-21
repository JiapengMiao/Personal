import { useEffect, useRef } from "react";
import { echarts, type ThemeMode } from "./echarts";
import type { EChartsCoreOption } from "echarts/core";

/**
 * 轻量 useEChart hook：
 * - build 返回完整 option；deps 变化时重建 option（主题切换时整个重算）
 * - 自动 init / resize（ResizeObserver）/ dispose
 * - onChart：每次 option 重建后回调 chart 实例（用于挂 datazoom 等事件，组件内自行 off/on 防重复）
 * - devicePixelRatio：读 CSS zoom 值（部署时固定为放大档，如 1.25），让 canvas 缓冲区按该倍率提高分辨率，
 *   避免图表文字模糊；zoom 为固定值，init 时一次定型即可，无运行期 re-init。
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
  const unpatchRef = useRef<(() => void) | null>(null);

  // 读取当前 CSS zoom 值（用于计算 devicePixelRatio）
  const getZoom = () => {
    if (typeof window === "undefined") return 1;
    const z = getComputedStyle(document.documentElement).zoom;
    const n = parseFloat(z);
    return Number.isFinite(n) && n > 0 ? n : 1;
  };

  /**
   * CSS zoom 命中修复：
   * html { zoom: 1.25 } 下，容器 getBoundingClientRect 返回视觉（放大后）尺寸，
   * 而 ECharts 内部网格按布局尺寸（clientWidth）排布，两者相差 zoom 倍。
   * zrender 换算鼠标坐标时优先读 e.offsetX（zoom 下是视觉坐标），结果偏大 zoom 倍，
   * 导致 tooltip 显示偏移、dataZoom 滑块抓不到。
   * 克隆重派发不可靠：zrender 还会经 document 捕获阶段的 global listener 处理原始事件。
   * 因此在 window 捕获阶段直接重写事件实例上的坐标属性（own property 遮蔽原型 getter），
   * 让事件携带修正后的布局坐标自然传播，local/global 两条路径都拿到正确值。
   */
  const patchZoomHit = (el: HTMLDivElement, zoom: number) => {
    if (!zoom || zoom === 1 || typeof window === "undefined") return null;
    const handler = (e: Event) => {
      const target = e.target as Node | null;
      if (!target || !el.contains(target)) return;
      const me = e as MouseEvent;
      const rect = el.getBoundingClientRect();
      const cx = rect.left + (me.clientX - rect.left) / zoom;
      const cy = rect.top + (me.clientY - rect.top) / zoom;
      const defs: Record<string, number> = {
        clientX: cx,
        clientY: cy,
        x: cx,
        y: cy,
        pageX: cx + (me.pageX - me.clientX),
        pageY: cy + (me.pageY - me.clientY),
        offsetX: cx - rect.left,
        offsetY: cy - rect.top,
      };
      for (const k of Object.keys(defs)) {
        try {
          Object.defineProperty(me, k, { value: defs[k], configurable: true, writable: true });
        } catch {
          /* 个别属性不可定义时忽略 */
        }
      }
    };
    const types = [
      // zrender 在支持 Pointer Events 的浏览器里只监听 pointer*（命中换算走这里）
      "pointermove",
      "pointerdown",
      "pointerup",
      "pointerover",
      "pointerout",
      "pointerenter",
      "pointerleave",
      "pointercancel",
      // 鼠标/滚轮事件：tooltip DOM、click 等仍会用到
      "mousemove",
      "mousedown",
      "mouseup",
      "click",
      "dblclick",
      "mouseover",
      "mouseout",
      "wheel",
    ];
    types.forEach((t) => window.addEventListener(t, handler, { capture: true, passive: true }));
    return () => {
      types.forEach((t) => window.removeEventListener(t, handler, { capture: true }));
    };
  };

  // 主题或数据变化时重建 option
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const zoom = getZoom();
    const dpr = Math.max(1, (window.devicePixelRatio || 1) * zoom);
    if (!chartRef.current) {
      unpatchRef.current?.();
      unpatchRef.current = patchZoomHit(el, zoom);
      chartRef.current = echarts.init(el, undefined, { devicePixelRatio: dpr });
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
      unpatchRef.current?.();
      unpatchRef.current = null;
      chartRef.current?.dispose();
      chartRef.current = null;
    };
  }, []);

  return ref;
}
