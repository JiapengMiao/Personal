# 发布流程 SOP（2026-07-23 实测验证版）

> 适用：本项目（Project-002 白银数据网页可视化）每次数据/代码更新后的上线发布。
> 部署方式：GitHub push → **EdgeOne Pages（国际站，项目 `silverdaily-global`）自动构建部署** → `https://silverdaily.cfd/`

---

## 一、发布前检查（本地）

1. 数据更新已跑完：`py -3 src/update_all.py`（或对应单项采集器），确认目标日期已入库
2. 本地构建通过：`cd web && npx tsc --noEmit`（0 错）→ `npm run build`（成功）
3. 构建产物已同步到发布目录 `docs/`（项目惯例：docs/ 即 Pages 发布根）
4. 快速目检：`web/public/data/` 与 `docs/data/` 的关键 JSON 已包含最新日期

## 二、发布（两步）

```bash
git add -A
git commit -m "data: YYYY-MM-DD 全量数据更新 + <其他改动说明>"
git push origin main
```

- 若 github.com 直连失败：改用 `src/deploy_git_api.py`（Git Data API 通道）
- push 成功后 **无需任何控制台操作**，EdgeOne Pages 会自动拉取 main 分支重新部署

## 三、发布后验证（push 后等 5~10 分钟）

### 1. 验证线上文件版本（最核心）

```bash
curl.exe -s "https://silverdaily.cfd/" | findstr /R "assets.index-.*\.js"
```

返回的 JS 哈希名应与本地 `docs/assets/` 里新构建的文件名一致。

### 2. 验证缓存头（确认缓存策略正常，可选）

```bash
curl.exe -sI "https://silverdaily.cfd/"
```

期望看到：
- `Cache-Control: public,max-age=0,must-revalidate`（HTML/JSON 每次回源验证，安全）
- `Server: edgeone-pages`
- `Last-Modified` 为本次部署时间

### 3. 验证数据新鲜度

```bash
curl.exe -s "https://silverdaily.cfd/data/lhb.json?v=check" | python -c "import sys,json;d=json.load(sys.stdin);print(d['dates'][-1]['date'], d['generatedAt'])"
```

日期应为当天（交易日）。其他关键 JSON（daily.json / market.json）可同法抽查。

### 4. 浏览器确认

打开 `https://silverdaily.cfd/` 普通刷新即可。前端数据请求自带 `?v=构建版本` 参数，发布后版本号变化会强制拉新数据。

## 四、缓存机制速查（为什么不用管 CDN 配置）

| 层 | 机制 | 旧版本风险 |
|---|---|---|
| 浏览器 → 数据 JSON | 前端 `fetchData()` 自动附加 `?v=构建版本` + `no-store` | 无：发布后参数变，必拉新 |
| EdgeOne 节点 → HTML/JSON | 源站默认 `max-age=0, must-revalidate` + ETag | 无：节点每次回源验证 |
| 任意端 → JS/CSS | 文件名带构建哈希 + `max-age=31536000, immutable` | 无：内容变则文件名变 |

> 实测结论（2026-07-23，见【全局复盘与踩坑日志】同日条目）：EdgeOne **Pages** 默认缓存头即安全策略，**无需登录控制台配任何缓存规则**。该结论仅适用于 Pages 产品，不适用于国内站「网站加速」自定义 CDN。

## 五、故障排查

| 现象 | 排查 |
|---|---|
| push 后 10 分钟线上还是旧版 | ① 确认 `git push` 成功且远端 main 有新 commit；② 用第三节 curl 命令看线上 JS 哈希和 Last-Modified；③ 仍旧则等 EdgeOne 构建队列，一般不超过 15 分钟 |
| 网页白屏/报错 | F12 看 Console；多为构建产物与数据字段不匹配，回滚到上一个 commit 再查 |
| 需要登国际站控制台 | `console.edgeone.ai` 国内网络无法直连，需代理；平时发布不需要登录 |
| GitHub 连不上 | 用 `src/deploy_git_api.py` 走 Git Data API 提交 |

---

*首次验证：2026-07-23，commit baaa796 发布后 8 分钟线上生效，lhb.json 当日数据实测在线。*
