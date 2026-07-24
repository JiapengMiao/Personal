// 数据请求防缓存：构建时注入的版本号 + no-store。
// 每次 vite build（update_all 数据更新必经）产生新版本号，
// data/*.json 的 URL 随之变化，浏览器与 CDN 旧缓存自动失效。

declare const __BUILD_VERSION__: string;

const BUILD_VERSION: string =
  typeof __BUILD_VERSION__ !== "undefined" ? __BUILD_VERSION__ : "dev";

export function dataUrl(path: string): string {
 const sep = path.includes("?") ? "&" : "?";
  // 三个静态入口页位于 /silver/、/platinum-palladium/、/monitoring/。
  // 它们需要回到站点根目录读取同一套 data/*.json；根入口页则保持原相对路径。
  const page = document.documentElement.dataset.dashboardPage;
  const resolvedPath = page ? "../" + path.replace(/^\.\//, "") : path;
  return resolvedPath + sep + "v=" + encodeURIComponent(BUILD_VERSION);
}

export async function fetchData<T>(path: string): Promise<T> {
  const r = await fetch(dataUrl(path), { cache: "no-store" });
  if (!r.ok) throw new Error(`${path}: HTTP ${r.status}`);
  return r.json() as Promise<T>;
}
