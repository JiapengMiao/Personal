import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // 部署在 GitHub Pages 子路径（/Personal/）下，资源与数据请求必须用相对路径
  base: "./",
  build: {
    chunkSizeWarningLimit: 1200,
  },
});
