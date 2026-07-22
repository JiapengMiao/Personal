# 数据管道

统一入口：

```powershell
python src/update_all.py
```

流程会检查 `data/wind`、`data/shfe`、`data/sge`、`data/gfex`、`data/monitoring`，生成前端 JSON，执行 TypeScript 校验和 Vite 生产构建，并同步 `web/dist` 到 `docs/`。它不会自动提交或推送 Git。

`build_monitoring_data.mjs` 仅用于把人工维护的监测底稿编译成 `data/monitoring/monitoring-base.json`。指标16“全球可用库存”在总管道中根据 Wind 主表按 `LBMA + COMEX + 上期所 + 上金所 - SLV` 自动重算。

Project-006 的客户池、客户分析、报告、PDF 和工作簿不在本次迁移范围，仍由 Project-006 独立维护。

