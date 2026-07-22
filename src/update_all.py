#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Project-002 统一更新入口。

默认流程：检查本地源数据 -> 生成全部 JSON -> TypeScript 校验 -> Vite 构建 ->
同步 GitHub Pages 的 docs/。本脚本不会自动抓取网络数据，也不会提交或推送 Git。

用法：
  python src/update_all.py
  python src/update_all.py --data-only
  python src/update_all.py --skip-docs
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
PUBLIC_DATA = WEB / "public" / "data"
DIST = WEB / "dist"
DOCS = ROOT / "docs"
RUNS_DIR = ROOT / "output" / "update_runs"


def _latest(pattern: str) -> Path | None:
    matches = sorted(ROOT.glob(pattern))
    return matches[-1] if matches else None


def preflight() -> dict[str, Path]:
    required: dict[str, Path | None] = {
        "Wind 主工作簿": ROOT / "data" / "wind" / "白银所有数据.xlsx",
        "租赁利率": _latest("data/wind/租赁利率/*.xlsx"),
        "SHFE 会员持仓": _latest("data/shfe/ranking/*"),
        "SGE Ag(T+D)": ROOT / "data" / "sge" / "ag_td_daily_2026.csv",
        "GFEX 仓单": _latest("data/gfex/铂钯仓单数据_*.csv"),
        "监测数据": ROOT / "data" / "monitoring" / "monitoring-data.json",
        "龙虎榜历史": _latest("data/shfe/lhb/*.xlsx"),
        "香港白银贸易": ROOT / "data" / "hk_silver_trade.csv",
    }
    missing = [name for name, path in required.items() if path is None or not path.exists()]
    if missing:
        raise FileNotFoundError("统一更新缺少源数据：" + "、".join(missing))
    resolved = {name: path.resolve() for name, path in required.items() if path is not None}
    print("[preflight] 本地统一数据源齐全")
    for name, path in resolved.items():
        print(f"  - {name}: {path.relative_to(ROOT)}")
    return resolved


def run_step(name: str, command: list[str], cwd: Path = ROOT) -> dict:
    print(f"\n=== {name} ===")
    started = time.perf_counter()
    result = subprocess.run(command, cwd=cwd, text=True)
    duration = round(time.perf_counter() - started, 2)
    if result.returncode != 0:
        raise RuntimeError(f"{name} 失败（退出码 {result.returncode}）")
    print(f"[OK] {name} ({duration:.2f}s)")
    return {"name": name, "status": "ok", "durationSeconds": duration}


def sync_docs() -> dict:
    """用已验证的 dist 覆盖 GitHub Pages 目录。"""
    if not (DIST / "index.html").exists():
        raise FileNotFoundError(f"缺少构建产物: {DIST / 'index.html'}")
    docs = DOCS.resolve()
    root = ROOT.resolve()
    if docs.parent != root or docs.name != "docs":
        raise RuntimeError(f"拒绝同步到非预期目录: {docs}")
    if docs.exists():
        shutil.rmtree(docs)
    shutil.copytree(DIST, docs)
    count = sum(1 for path in docs.rglob("*") if path.is_file())
    print(f"[OK] docs/ 已同步 web/dist（{count} 个文件）")
    return {"name": "同步 docs", "status": "ok", "fileCount": count}


def write_report(started_at: str, sources: dict[str, Path], steps: list[dict], status: str, error: str | None = None) -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "startedAt": started_at,
        "finishedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "status": status,
        "sources": {
            name: {
                "path": str(path.relative_to(ROOT)),
                "modifiedAt": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds"),
                "sizeBytes": path.stat().st_size if path.is_file() else None,
            }
            for name, path in sources.items()
        },
        "steps": steps,
        "error": error,
    }
    (RUNS_DIR / "latest.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Project-002 统一数据与网页更新")
    parser.add_argument("--data-only", action="store_true", help="只生成 JSON，不校验或构建前端")
    parser.add_argument("--skip-docs", action="store_true", help="构建前端但不覆盖 docs/")
    parser.add_argument("--sync-only", action="store_true", help="只把已有 web/dist 安全同步到 docs/")
    args = parser.parse_args()

    started_at = datetime.now().astimezone().isoformat(timespec="seconds")
    steps: list[dict] = []
    sources: dict[str, Path] = {}
    try:
        if args.sync_only:
            steps.append(sync_docs())
            write_report(started_at, sources, steps, "success")
            return 0
        sources = preflight()
        steps.append(run_step("生成看板数据", [sys.executable, str(ROOT / "src" / "build_dashboard_data.py")]))

        # 报价 Excel 位于共享投研目录，不属于 004/005/006/010 合并范围；存在时一并刷新。
        spot_source = Path(r"C:\Users\56558\Nutstore\1\金属投研小组\MJP-苗嘉鹏\数据计算\白银报价\白银每日报价.xlsx")
        if spot_source.exists():
            steps.append(run_step("提取现货报价", [sys.executable, str(ROOT / "src" / "extract_spot_quotes.py")]))
        else:
            print(f"[SKIP] 共享报价源不存在，保留现有 spot_quotes.json: {spot_source}")

        steps.append(run_step("生成香港贸易数据", [sys.executable, str(ROOT / "src" / "build_hk_trade.py")]))
        if not args.data_only:
            node = shutil.which("node")
            if not node:
                raise FileNotFoundError("未找到 Node.js，无法校验和构建前端")
            steps.append(run_step(
                "TypeScript 校验",
                [node, str(WEB / "node_modules" / "typescript" / "bin" / "tsc"), "--noEmit"],
                WEB,
            ))
            steps.append(run_step(
                "Vite 生产构建",
                [node, str(WEB / "node_modules" / "vite" / "bin" / "vite.js"), "build"],
                WEB,
            ))
            if not args.skip_docs:
                steps.append(sync_docs())
        write_report(started_at, sources, steps, "success")
        print("\n统一更新完成。Git 提交和推送需由用户确认后单独执行。")
        return 0
    except Exception as exc:  # noqa: BLE001
        write_report(started_at, sources, steps, "failed", f"{type(exc).__name__}: {exc}")
        print(f"\n[FAIL] 统一更新中止: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
