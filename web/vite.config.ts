import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // 部署在 GitHub Pages 子路径（/Personal/）下，资源与数据请求必须用相对路径
  base: "./",
  // 每次构建注入唯一版本号：所有 data/*.json 请求带 ?v=<构建时间>，
  // 浏览器与 CDN 缓存随部署自动失效，刷新即拿最新数据
  define: {
    __BUILD_VERSION__: JSON.stringify(new Date().toISOString()),
  },
  build: {
    chunkSizeWarningLimit: 1200,
    rollupOptions: {
      input: {
        index: "index.html",
        silver: "silver/index.html",
        platinumPalladium: "platinum-palladium/index.html",
        monitoring: "monitoring/index.html",
      },
    },
  },
});
