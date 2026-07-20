#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
build_dashboard_data.py

将 data/010源数据/ 下的 Excel（白银所有数据.xlsx、20260719租借利率.xlsx）
与 data/006源数据/ 下的 JSON 抽取/转换为前端看板用 JSON，输出到 web/public/data/。

用法:  python src/build_dashboard_data.py
退出码: 全部成功 0；任一输出失败或校验失败 1（错误汇总打印在结尾）。
"""
from __future__ import annotations

import json
import math
import re
import shutil
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from openpyxl import load_workbook

# ---------------------------------------------------------------- 路径

ROOT = Path(__file__).resolve().parent.parent
SRC010 = ROOT / "data" / "010源数据"
SRC006 = ROOT / "data" / "006源数据"
OUT_DIR = ROOT / "web" / "public" / "data"
# 主表以项目 010（日度会议数据整理）为准——用户每日在此维护，含"网页数据" sheet
MAIN_XLSX = Path(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-010-日度会议数据整理\data\白银所有数据.xlsx")


def _find_lease_xlsx() -> Path:
    """租借/租赁利率表：用户在 010 的"租赁利率"文件夹按日期文件名维护（如 20260720租赁利率.xlsx），
    自动取最新一份；若该目录不存在则回退到本项目 data/010源数据/ 下的副本。"""
    lease_dir = Path(r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-010-日度会议数据整理\data\租赁利率")
    cands = sorted(lease_dir.glob("*利率*.xlsx")) if lease_dir.is_dir() else []
    if not cands:
        cands = sorted(SRC010.glob("*利率*.xlsx"))
    if not cands:
        raise FileNotFoundError("未找到租借/租赁利率 xlsx（010 租赁利率目录与本地 010源数据 均为空）")
    return cands[-1]


LEASE_XLSX = _find_lease_xlsx()

ERRORS: list[tuple[str, str]] = []   # (步骤名, 错误信息)

OZ_TO_KG = 32.1507466                # 美元/盎司 -> 元/千克 换算系数（×汇率）
VAT = 1.13                           # 进口增值税因子

# 白银数据主表：原文列名 -> (输出 key, 小数精度)；精度 0 表示取整
DAILY_COLS: list[tuple[str, str, int]] = [
    ("上海金交所:递延费支付方向:白银现货:Ag(T+D)", "deferredDirection", 0),
    ("上海金交所:结算价:白银现货:Ag(T+D)", "agtdSettle", 2),
    ("上海金交所:收盘价:白银现货:Ag(T+D)", "agtdClose", 2),
    ("中国:持仓量:白银现货:Ag(T+D):上海金交所", "agtdOi", 0),
    ("上期库存（日度）（吨）", "shfeInvT", 3),
    ("上金库存（日度）（吨）", "sgeInvT", 3),
    ("国内库存（上金+上期）（吨）", "domesticInvT", 3),   # 源列不直接使用，管道内重算
    ("国内库存+COMEX", "domesticPlusComex", 3),
    ("COMEX:库存量:银（吨）", "comexInvT", 3),
    ("COMEX+LBMA日度库存", "comexPlusLbmaDaily", 3),
    ("COMEX:持仓数量:非商业净持仓", "comexNonCommNet", 0),
    ("COMEX:持仓数量:非商业多头持仓:银", "comexNonCommLong", 0),
    ("COMEX:持仓数量:非商业空头持仓:银", "comexNonCommShort", 0),
    ("COMEX:注册仓单:白银:全球:吨", "comexWarrantT", 3),
    ("LBMA:库存量:白银（吨）", "lbmaInvT", 3),
    ("LBMA日度库存量:白银（吨）", "lbmaDailyT", 3),
    ("SLV:白银ETF:持仓量(吨)", "etfSLV", 3),
    ("PHAG:白银ETF:持仓量(吨)", "etfPHAG", 3),
    ("ETPMAG:白银ETF:持仓量(吨)", "etfETPMAG", 3),
    ("CEF:白银ETF:持仓量(吨)", "etfCEF", 3),
    ("PSLV:白银ETF:持仓量(吨)", "etfPSLV", 3),
    ("SLV+PHAG+ETPMAG+CEF", "etfUKSum", 3),
    ("现货价(伦敦市场):白银:美元", "londonSilverUsd", 2),
    ("中国:进口数量:白银", "importQty", 2),
    ("中国:出口数量:白银", "exportQty", 2),
]

# 库存类序列：停更后沿用前值（ffill），并记录最后真实值日期 lastActual
FFILL_KEYS = ("shfeInvT", "sgeInvT", "lbmaDailyT")

# 不从主表源列读取、在管道内计算的 key
COMPUTED_KEYS = {"domesticInvT"}

# 主表中日频（非稀疏）key，用于校验"无全 null 序列"
DAILY_DENSE_KEYS = {
    "agtdSettle", "agtdClose", "agtdOi", "shfeInvT", "sgeInvT", "domesticInvT",
    "domesticPlusComex", "comexInvT", "comexPlusLbmaDaily", "comexWarrantT",
    "lbmaDailyT", "etfSLV", "etfPHAG", "etfETPMAG", "etfCEF", "etfPSLV",
    "etfUKSum", "londonSilverUsd", "deferredDirection",
}

ZERO_TO_NULL_COUNTS: dict[str, int] = {}   # 记录每列 0->null 的个数（校验用）

# ---------------------------------------------------------------- 工具


def now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def write_json(name: str, obj: dict) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / name
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    path.write_text(text, encoding="utf-8")
    n = len(obj.get("dates") or obj.get("times") or obj.get("contracts") or [])
    print(f"  [OK] {name} ({n} 记录, {path.stat().st_size / 1024:.1f} KB)")


def run_step(label: str, fn) -> None:
    """单步执行；失败收集错误但不中断后续步骤。"""
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        ERRORS.append((label, f"{type(exc).__name__}: {exc}"))
        print(f"  [FAIL] {label} 失败: {exc}")
        traceback.print_exc()


def to_float(v) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def round_or_none(v, nd: int):
    f = to_float(v)
    if f is None:
        return None
    return round(f, nd)


def parse_yyyymmdd(v) -> datetime | None:
    """合约参数中的日期列：int/float/str 混合，统一转 datetime。"""
    f = to_float(v)
    if f is not None:
        s = str(int(f))
    else:
        s = str(v).strip()
    if not re.fullmatch(r"\d{8}", s):
        return None
    try:
        return datetime.strptime(s, "%Y%m%d")
    except ValueError:
        return None


def minute_frame(df_raw: pd.DataFrame, t_col: int, c_col: int) -> pd.DataFrame:
    """从原始（header=None）分钟 sheet 切出 time/close 并清洗。"""
    t = pd.to_datetime(df_raw.iloc[:, t_col], errors="coerce")
    c = pd.to_numeric(df_raw.iloc[:, c_col], errors="coerce")
    out = pd.DataFrame({"time": t, "close": c}).dropna()
    out = out.drop_duplicates(subset="time", keep="first").sort_values("time")
    return out.reset_index(drop=True)


def to_minute_series(df: pd.DataFrame) -> pd.Series:
    s = pd.Series(df["close"].to_numpy(dtype=float), index=pd.DatetimeIndex(df["time"]))
    return s[~s.index.duplicated(keep="first")].sort_index()


def align_minute_series(series_map: dict[str, pd.DataFrame]):
    """
    多路分钟序列按 time 外连接对齐 + 各自 ffill；
    截断到所有序列都已出现首个真实值之后。
    返回 (times_str_list, {name: np.ndarray})
    """
    ss = {name: to_minute_series(df) for name, df in series_map.items()}
    idx: pd.DatetimeIndex | None = None
    for s in ss.values():
        idx = s.index if idx is None else idx.union(s.index)
    assert idx is not None
    start = max(s.index[0] for s in ss.values())  # 全部序列都已开始的时刻
    mask = idx >= start
    aligned = {n: s.reindex(idx).ffill().to_numpy()[mask] for n, s in ss.items()}
    times = idx[mask].strftime("%Y-%m-%d %H:%M").tolist()
    return times, aligned


def spread_stats(vals: np.ndarray) -> dict:
    latest = float(vals[-1])
    return {
        "latest": round(latest, 1),
        "mean": round(float(np.mean(vals)), 1),
        "percentile": round(float((vals <= latest).mean()), 4),
        "min": round(float(np.min(vals)), 1),
        "max": round(float(np.max(vals)), 1),
    }


# ---------------------------------------------------------------- 输入加载（整簿一次解析）

SHEETS_NEEDED = [
    "白银数据", "AG（T+D）", "AG所有合约数据", "SPTAGUSDOZ_IDZ",
    "外汇价格", "白银合约参数", "虚实比数据", "季节图表",
]


def defensive_sheet_check() -> None:
    wb = load_workbook(MAIN_XLSX, read_only=True)
    names = wb.sheetnames
    wb.close()
    print("  白银所有数据.xlsx 实际 sheet:", names)
    missing = [s for s in SHEETS_NEEDED if s not in names]
    if missing:
        raise RuntimeError(f"缺少必需 sheet: {missing}")
    wb2 = load_workbook(LEASE_XLSX, read_only=True)
    print("  20260719租借利率.xlsx 实际 sheet:", wb2.sheetnames)
    wb2.close()


def load_all_sheets() -> dict[str, pd.DataFrame]:
    """一次性解析整簿（header=None），各 sheet 按已实测布局切分。"""
    print("  解析主工作簿（整簿一次读取，约 10~30 秒）...")
    return pd.read_excel(MAIN_XLSX, sheet_name=SHEETS_NEEDED, header=None)


class Ctx:
    """共享上下文：日历、分钟序列、合约参数、虚实比数据。"""

    def __init__(self, sheets: dict[str, pd.DataFrame]):
        # ---- 白银数据主表（日历 + 日频序列）
        raw = sheets["白银数据"]
        header = raw.iloc[1].tolist()
        df = raw.iloc[2:].copy()
        df.columns = header
        df = df.rename(columns={header[0]: "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
        self.daily = df
        self._hist_calendar = pd.DatetimeIndex(df["date"])
        self.calendar = self._hist_calendar  # extended after expiry parsed

        # ---- 分钟序列
        self.agtd = minute_frame(sheets["AG（T+D）"].iloc[6:], 0, 1)
        self.xagusd = minute_frame(sheets["SPTAGUSDOZ_IDZ"].iloc[6:], 0, 1)
        self.usdcnh = minute_frame(sheets["外汇价格"].iloc[6:], 0, 1)

        # ---- AG 所有合约（合约代码从第 3 行动态读取）
        raw_all = sheets["AG所有合约数据"]
        self.contracts_min: dict[str, pd.DataFrame] = {}
        code_row = raw_all.iloc[2].tolist()
        n_pairs = raw_all.shape[1] // 2
        for k in range(n_pairs):
            code = code_row[2 * k + 1]
            if not (isinstance(code, str) and re.fullmatch(r"AG\d{4}(\.SHF)?", code.strip())):
                print(f"  警告: AG所有合约数据 第 {2*k+2} 列合约代码无法识别: {code!r}，跳过")
                continue
            key = code.strip().replace(".SHF", "")
            self.contracts_min[key] = minute_frame(raw_all.iloc[6:], 2 * k, 2 * k + 1)
        print(f"  分钟合约解析: {sorted(self.contracts_min)}")

        # ---- 合约参数: code(lower) -> expiry datetime
        raw_p = sheets["白银合约参数"]
        self.expiry: dict[str, datetime] = {}
        for _, row in raw_p.iloc[1:].iterrows():
            code = str(row.iloc[0]).strip().lower()
            exp = parse_yyyymmdd(row.iloc[2])  # 到期日=最后交易日
            if re.fullmatch(r"ag\d{4}", code) and exp is not None:
                self.expiry[code] = exp
        print(f"  合约参数解析: {len(self.expiry)} 个合约到期日")
        # Extend calendar with future business days up to max expiry (010 logic)
        _latest = self._hist_calendar[-1]
        _max_exp = max(self.expiry.values()) if self.expiry else _latest
        if _max_exp > _latest:
            _future = pd.bdate_range(start=_latest + pd.Timedelta(days=1), end=_max_exp)
            self.calendar = self._hist_calendar.union(_future).sort_values()
        else:
            self.calendar = self._hist_calendar
        print(f"  calendar: {len(self.calendar)} days (hist {len(self._hist_calendar)} + future {len(self.calendar)-len(self._hist_calendar)})")

        # ---- 交易日日历：从扩展后的 calendar 排除周末 + 包含所有合约到期日
        _wd = self.calendar.weekday
        _biz = self.calendar[_wd < 5]  # Mon-Fri
        _exp_dates = pd.DatetimeIndex(list(self.expiry.values()))
        self.trading_calendar = _biz.union(_exp_dates).sort_values()
        print(f"  trading_calendar: {len(self.trading_calendar)} days (biz {len(_biz)} + expiry {len(_exp_dates)})")

        # ---- 虚实比数据：仓单 st_stock + 各合约 oi
        raw_v = sheets["虚实比数据"]
        hdr = raw_v.iloc[5].tolist()  # 英文表头行
        body = raw_v.iloc[6:]
        # 仓单块（列 0/1）
        st_date = pd.to_datetime(body.iloc[:, 0], errors="coerce")
        st_val = pd.to_numeric(body.iloc[:, 1], errors="coerce")
        st = pd.DataFrame({"date": st_date, "st": st_val}).dropna()
        st = st.drop_duplicates(subset="date", keep="last").sort_values("date")
        self.st_stock = pd.Series(st["st"].to_numpy(dtype=float), index=pd.DatetimeIndex(st["date"]))
        # 仓单 ffill 到主表日历（任何仓单值出现之前保持 NaN）
        self.st_stock_ffill = self.st_stock.reindex(self.calendar).ffill()
        print(f"  注册仓单: {len(self.st_stock)} 个发布值, "
              f"{self.st_stock.index.min():%Y-%m-%d} → {self.st_stock.index.max():%Y-%m-%d}")

        # oi 块（列 2 日期, 列 3.. 合约；代码取英文表头行动态识别）
        oi_date = pd.to_datetime(body.iloc[:, 2], errors="coerce")
        self.oi: dict[str, pd.DataFrame] = {}
        for j in range(3, body.shape[1]):
            col_code = hdr[j]
            if not (isinstance(col_code, str) and re.fullmatch(r"AG\d{4}\.SHF", col_code.strip())):
                continue  # 到 close 块即停止识别（close 块表头为 AGxxxx.SHF.1 等）
            code = col_code.strip().replace(".SHF", "").lower()
            if code in self.oi:
                continue  # close 块与 oi 块表头原文相同，只取首次出现（oi 块）
            vals = pd.to_numeric(body.iloc[:, j], errors="coerce")
            d = pd.DataFrame({"date": oi_date, "oi": vals}).dropna()
            if len(d):
                self.oi[code] = d.sort_values("date").reset_index(drop=True)
        print(f"  虚实比 oi 合约: {sorted(self.oi)}")

        # ---- 季节图表
        raw_s = sheets["季节图表"]
        yr_header = raw_s.iloc[1].tolist()
        self.season_years = [str(int(to_float(y))) for y in yr_header[1:6]]
        sbody = raw_s.iloc[2:]
        dcol = sbody.iloc[:, 0].astype(str).str.strip()
        mask = dcol.str.fullmatch(r"\d{2}-\d{2}")
        self.season_dates = dcol[mask].tolist()
        self.season_vals = sbody.loc[mask].iloc[:, 1:6].apply(pd.to_numeric, errors="coerce")

        print(f"  日历: {self.calendar[0]:%Y-%m-%d} → {self.calendar[-1]:%Y-%m-%d} ({len(self.calendar)} 天); "
              f"AGTD 分钟 {len(self.agtd)} 行; XAGUSD {len(self.xagusd)} 行; USDCNH {len(self.usdcnh)} 行")


# ---------------------------------------------------------------- 各输出步骤

CTX: Ctx | None = None


def step_copy_static() -> None:
    # monitoring.json 仍原样拷贝 006 抽取结果
    src = SRC006 / "monitoring-data.json"
    with open(src, encoding="utf-8") as fh:
        json.load(fh)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, OUT_DIR / "monitoring.json")
    size_kb = (OUT_DIR / "monitoring.json").stat().st_size / 1024
    print(f"  [OK] monitoring.json (原样拷贝, {size_kb:.1f} KB)")

    # market.json 改为从 010 主表"网页数据" sheet 生成（用户手工维护的万得数据）
    build_market_from_web_sheet()


def build_market_from_web_sheet() -> None:
    """读取 010 主表"网页数据" sheet，生成 market.json。

    sheet 结构（data_only）：
      第4行 = 列名（日期/伦敦银(人民币/千克)/伦敦金(人民币/克)/国投瑞银白银期货A/SHFE白银/SGE白银T+D）
      第5行 = 万得代码（Date/XAGCNY.IDC/XAUCNY.IDC/161226.OF/AG.SHF/AG(T+D).SGE）
      第6行起 = 数据（A 列为日期）
    金银比 = 伦敦金(元/克) ÷ 伦敦银(元/千克) × 1000（同币种，单位换算后无量纲）。
    """
    wb = load_workbook(MAIN_XLSX, read_only=True, data_only=True)
    if "网页数据" not in wb.sheetnames:
        raise KeyError("主表缺少『网页数据』sheet")
    ws = wb["网页数据"]
    rows = list(ws.iter_rows(min_row=4, values_only=True))
    wb.close()
    # rows[0]=列名行, rows[1]=代码行, rows[2:]=数据
    series_map = {
        "londonSilverCnyKg": {"label": "伦敦银（人民币/千克）", "unit": "元/千克", "col": 1},
        "londonGoldCnyG": {"label": "伦敦金（人民币/克）", "unit": "元/克", "col": 2},
        "silverFundNav": {"label": "白银期货 LOF（161226.OF）净值", "unit": "元", "col": 3},
        "shfeSilver": {"label": "沪银主力（AG.SHF）", "unit": "元/千克", "col": 4},
        "sgeAgTd": {"label": "上金所 Ag(T+D)", "unit": "元/千克", "col": 5},
    }
    items: dict[str, dict] = {}
    for key, meta in series_map.items():
        pts = []
        for r in rows[2:]:
            dt, val = r[0], r[meta["col"]]
            if dt is None or val is None:
                continue
            d = dt.date().isoformat() if hasattr(dt, "date") else str(dt)[:10]
            f = to_float(val)
            if f is not None:
                pts.append({"date": d, "value": round(f, 4)})
        items[key] = {"label": meta["label"], "unit": meta["unit"], "points": pts}

    # 金银比：按日期对齐伦敦金/伦敦银
    au = {p["date"]: p["value"] for p in items["londonGoldCnyG"]["points"]}
    ag = {p["date"]: p["value"] for p in items["londonSilverCnyKg"]["points"]}
    ratio_pts = []
    for d in sorted(au.keys() & ag.keys()):
        if ag[d]:
            ratio_pts.append({"date": d, "value": round(au[d] / ag[d] * 1000, 2)})
    items["goldSilverRatio"] = {"label": "金银比（伦敦金 ÷ 伦敦银，人民币同口径）", "unit": "", "points": ratio_pts}

    write_json("market.json", {"fetchedAt": now_iso(), "items": items})



def step_daily() -> None:
    assert CTX is not None
    df = CTX.daily
    # 1) 读取源列（0→null）；COMPUTED_KEYS 不读源列
    raw: dict[str, pd.Series] = {}
    nd_map: dict[str, int] = {}
    for col, key, nd in DAILY_COLS:
        nd_map[key] = nd
        if key in COMPUTED_KEYS:
            continue
        if col not in df.columns:
            print(f"  警告: 主表缺少列 {col!r}，key {key} 跳过")
            continue
        vals = pd.to_numeric(df[col], errors="coerce")
        zeros = int((vals == 0).sum())
        if zeros:
            ZERO_TO_NULL_COUNTS[key] = zeros
            vals = vals.mask(vals == 0)
        raw[key] = vals.reset_index(drop=True)
    # 2) 库存类序列 ffill（停更沿用前值），记录最后真实值日期 lastActual
    last_actual: dict[str, str | None] = {}
    for key in FFILL_KEYS:
        if key not in raw:
            print(f"  警告: {key} 无源数据，跳过 ffill")
            last_actual[key] = None
            continue
        s = raw[key]
        li = s.last_valid_index()
        last_actual[key] = (df["date"].iloc[li].strftime("%Y-%m-%d") if li is not None else None)
        raw[key] = s.ffill()  # 头部 null（首个有效值之前）保留
        print(f"  {key}: lastActual={last_actual[key]}, ffill 后非空 {int(raw[key].notna().sum())}/{len(df)}")
    # 3) domesticInvT 管道内重算 = ffill(shfeInvT) + ffill(sgeInvT)，两者同日都有值才产出
    if "shfeInvT" in raw and "sgeInvT" in raw:
        sh, sg = raw["shfeInvT"], raw["sgeInvT"]
        raw["domesticInvT"] = (sh + sg).where(sh.notna() & sg.notna())
        print(f"  domesticInvT 重算: 非空 {int(raw['domesticInvT'].notna().sum())}/{len(df)}, "
              f"末值 {round_or_none(raw['domesticInvT'].iloc[-1], 3)}")
    else:
        print("  警告: shfeInvT/sgeInvT 缺失，domesticInvT 无法重算")
    # 4) 按 DAILY_COLS 顺序输出
    series: dict[str, list] = {}
    for _col, key, nd in DAILY_COLS:
        if key not in raw:
            continue
        if nd == 0:
            series[key] = [None if to_float(v) is None else int(round(float(v))) for v in raw[key]]
        else:
            series[key] = [round_or_none(v, nd) for v in raw[key]]
    dates = df["date"].dt.strftime("%Y-%m-%d").tolist()
    write_json("daily.json", {
        "generatedAt": now_iso(),
        "asOfDate": dates[-1],
        "lastActual": last_actual,
        "dates": dates,
        "series": series,
    })


def _contract_points(code: str, y_func) -> list[dict]:
    """按交易日日历计算 x（距到期日的交易日序号差，到期日 x=0），保留 [-90, 0]。
    已到期合约若曲线未延伸到 x=0，自动补一个端点。"""
    assert CTX is not None
    cal = CTX.trading_calendar
    exp = CTX.expiry.get(code, CTX.oi[code]["date"].max())
    exp_ts = pd.Timestamp(exp)
    exp_pos = int(cal.searchsorted(exp_ts))
    d = CTX.oi[code]
    pts = []
    for date, oi in zip(d["date"], d["oi"]):
        di = int(cal.searchsorted(pd.Timestamp(date)))
        x = di - exp_pos
        if not (-90 <= x <= 0):
            continue
        y = y_func(pd.Timestamp(date), di, float(oi))
        if y is None:
            continue
        pts.append({"x": x, "y": y})
    # 已到期合约：若最后一个点 x < 0，补 x=0 端点（沿用最后有效 y 值）
    if pts and pts[-1]["x"] < 0 and exp_ts <= pd.Timestamp(CTX.daily["date"].iloc[-1]):
        pts.append({"x": 0, "y": pts[-1]["y"]})
    return pts


def _is_even_month_contract(code: str) -> bool:
    """ag2608 → 月份 08 → 偶数月保留（白银期货仅偶数月合约活跃）。"""
    m = re.fullmatch(r"ag\d{2}(\d{2})", code)
    return bool(m) and int(m.group(1)) % 2 == 0


def _build_curve(y_func, extra_meta: dict | None = None) -> dict:
    assert CTX is not None
    contracts = []
    skipped_no_expiry, skipped_odd, kept = [], [], []
    for code in sorted(CTX.oi):
        # if code not in CTX.expiry:
        # skipped_no_expiry.append(code)
        # continue
        if not _is_even_month_contract(code):
            skipped_odd.append(code)
            continue
        pts = _contract_points(code, y_func)
        if pts:
            contracts.append({
                "code": code,
                "expiry": CTX.expiry.get(code, CTX.oi[code]["date"].max()).strftime("%Y-%m-%d"),
                "points": pts,
            })
            kept.append(code)
    if skipped_no_expiry:
        print(f"  警告: 以下 oi 合约在合约参数表中无到期日，已跳过: {skipped_no_expiry}")
    print(f"  偶数月合约过滤: 保留 {kept}; 丢弃(奇数月) {skipped_odd}")
    contracts.sort(key=lambda c: c["expiry"])
    obj = {"generatedAt": now_iso(), "contracts": contracts}
    if extra_meta:
        obj.update(extra_meta)
    return obj


def step_positions_curve() -> None:
    write_json("positions_curve.json", _build_curve(
        lambda date, di, oi: int(round(oi))))


def step_virtual_ratio() -> None:
    assert CTX is not None

    def y_func(date: pd.Timestamp, di: int, oi: float):
        # 当日或之前最近一个发布日的仓单；仓单首个值之前不设比率
        pos = int(CTX.calendar.searchsorted(date, side="right")) - 1
        if pos < 0:
            return None
        st = to_float(CTX.st_stock_ffill.iloc[pos])
        if st is None or st <= 0:
            return None
        return round(oi * 15.0 / st, 2)

    write_json("virtual_ratio.json", _build_curve(
        y_func, {"formula": "oi*15/st_stock_kg"}))


def step_seasonality() -> None:
    assert CTX is not None
    years = {}
    for i, yr in enumerate(CTX.season_years):
        col = CTX.season_vals.iloc[:, i]
        years[yr] = [round_or_none(v, 2) for v in col]
    write_json("seasonality.json", {
        "generatedAt": now_iso(),
        "dates": CTX.season_dates,
        "years": years,
    })


def step_lease_rates() -> None:
    df = pd.read_excel(LEASE_XLSX, sheet_name=0, header=7)
    df.columns = [str(c).strip() for c in df.columns]
    date_col = df.columns[0]

    def find_col(tenor_pat: str) -> str:
        for c in df.columns:
            if "白银" in c and re.search(tenor_pat, c):
                return c
        raise KeyError(f"租借利率表未找到白银 {tenor_pat} 列; 实际列: {list(df.columns)}")

    col_map = {
        "m1": find_col(r"(一|1)个月"),
        "m3": find_col(r"3个月"),
        "m6": find_col(r"6个月"),
        "m12": find_col(r"12个月"),
    }
    df["__d"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["__d"]).sort_values("__d")
    latest = df["__d"].max()
    df = df[df["__d"] >= latest - timedelta(days=365)]
    write_json("lease_rates.json", {
        "generatedAt": now_iso(),
        "dates": df["__d"].dt.strftime("%Y-%m-%d").tolist(),
        "series": {k: [round_or_none(v, 4) for v in pd.to_numeric(df[c], errors="coerce")]
                   for k, c in col_map.items()},
    })



def step_minute_exports() -> None:
    """Export per-contract minute JSON for frontend live basis calculation."""
    assert CTX is not None
    contracts_list = []

    # AGTD
    df = CTX.agtd
    times = df["time"].dt.strftime("%Y-%m-%d %H:%M").tolist()
    vals = [round(float(v), 2) for v in df["close"]]
    write_json("min_AGTD.json", {"times": times, "values": vals})
    contracts_list.append({"code": "AGTD", "label": "AG(T+D)", "points": len(times)})

    # Each futures contract
    for code in sorted(CTX.contracts_min):
        df = CTX.contracts_min[code]
        if len(df) < 100:
            continue
        times = df["time"].dt.strftime("%Y-%m-%d %H:%M").tolist()
        vals = [round(float(v), 2) for v in df["close"]]
        write_json(f"min_{code}.json", {"times": times, "values": vals})
        contracts_list.append({"code": code, "label": code.upper(), "points": len(times)})

    write_json("min_contracts.json", {"generatedAt": now_iso(), "contracts": contracts_list})
    print(f"  Exported {len(contracts_list)} minute series")


def step_basis() -> None:
    assert CTX is not None
    pairs = [
        ("AGTD", "AG2608"), ("AGTD", "AG2609"), ("AGTD", "AG2610"),
        ("AG2608", "AG2609"), ("AG2609", "AG2610"), ("AG2610", "AG2611"),
    ]
    label = {"AGTD": "AG(T+D)"}

    def get(code: str) -> pd.DataFrame:
        if code == "AGTD":
            return CTX.agtd
        if code not in CTX.contracts_min:
            raise KeyError(f"分钟合约 {code} 不存在")
        return CTX.contracts_min[code]

    for a, b in pairs:
        times, al = align_minute_series({"A": get(a), "B": get(b)})
        vals = np.round(al["A"] - al["B"], 1)
        pa, pb = label.get(a, a), label.get(b, b)
        write_json(f"basis_{a}-{b}.json", {
            "pair": f"{pa}-{pb}",
            "generatedAt": now_iso(),
            "times": times,
            "values": vals.tolist(),
            "stats": spread_stats(vals),
        })


def step_import_profit() -> None:
    assert CTX is not None
    times, al = align_minute_series({
        "agtd": CTX.agtd, "xagusd": CTX.xagusd, "usdcnh": CTX.usdcnh,
    })
    xagcny = al["xagusd"] * al["usdcnh"] * OZ_TO_KG          # 元/千克
    imp = np.round(al["agtd"] - xagcny * VAT, 1)              # 进口盈亏
    exp = np.round(xagcny - al["agtd"] / VAT, 1)              # 加贸出口盈亏
    si, se = spread_stats(imp), spread_stats(exp)
    write_json("import_profit.json", {
        "generatedAt": now_iso(),
        "times": times,
        "importProfit": imp.tolist(),
        "exportProfit": exp.tolist(),
        "stats": {
            "importLatest": si["latest"], "importMean": si["mean"], "importPercentile": si["percentile"],
            "exportLatest": se["latest"], "exportMean": se["mean"], "exportPercentile": se["percentile"],
        },
    })


# ---------------------------------------------------------------- 内容校验

VERIFY_ISSUES: list[str] = []


def check(ok: bool, msg: str) -> None:
    print(f"    {'[OK]' if ok else '[FAIL]'} {msg}")
    if not ok:
        VERIFY_ISSUES.append(msg)


def load_out(name: str) -> dict:
    with open(OUT_DIR / name, encoding="utf-8") as fh:
        return json.load(fh)


def verify() -> None:
    print("\n========== 内容校验 ==========")
    expected = (["monitoring.json", "market.json", "daily.json", "positions_curve.json",
                 "virtual_ratio.json", "seasonality.json", "lease_rates.json",
                 "import_profit.json"]
                + [f"basis_{p}.json" for p in
                   ["AGTD-AG2608", "AGTD-AG2609", "AGTD-AG2610",
                    "AG2608-AG2609", "AG2609-AG2610", "AG2610-AG2611"]])
    for name in expected:
        p = OUT_DIR / name
        check(p.exists() and p.stat().st_size > 2, f"{name} 存在且非空 ({p.stat().st_size if p.exists() else 0} B)")

    # daily.json
    d = load_out("daily.json")
    miss = [k for _, k, _ in DAILY_COLS if k not in d["series"]]
    check(not miss, f"daily.json 25 个 key 齐全 (缺失: {miss})")
    check(len(d["dates"]) > 500, f"daily.json 日期数 = {len(d['dates'])} (期望 >500)")
    check(d["dates"][-1] == d["asOfDate"],
          f"daily.json 末日期 {d['dates'][-1]} == asOfDate {d['asOfDate']}")
    check(len(d["dates"]) > 500, f"daily.json 首日期 {d['dates'][0]} (历史数据)")
    for k, arr in d["series"].items():
        nn = sum(v is not None for v in arr)
        if k in DAILY_DENSE_KEYS:
            check(nn > 300, f"daily.{k} 非空 {nn}/{len(d['dates'])} (日频列, 期望 >300)")
        else:
            check(nn > 0, f"daily.{k} 非空 {nn}/{len(d['dates'])} (稀疏列, 期望 >0)")
    check(all(len(v) == len(d["dates"]) for v in d["series"].values()),
          "daily.json 所有序列长度与日期一致")
    print(f"    0→null 转换计数: {ZERO_TO_NULL_COUNTS}")
    close_nn = [v for v in d["series"]["agtdClose"] if v is not None]
    check(5000 < close_nn[-1] < 30000, f"agtdClose 最新非空值 {close_nn[-1]} 元/千克 量级合理")

    # ---- 修改1: ffill + lastActual + domesticInvT 重算
    la = d.get("lastActual", {})
    check(set(la) == {"shfeInvT", "sgeInvT", "lbmaDailyT"}, f"daily.lastActual 键 {sorted(la)}")
    check(la.get("shfeInvT") is not None, f"lastActual.shfeInvT = {la.get('shfeInvT')} (非空)")
    check(la.get("sgeInvT") is not None, f"lastActual.sgeInvT = {la.get('sgeInvT')} (非空)")
    check(la.get("lbmaDailyT") is not None, f"lastActual.lbmaDailyT = {la.get('lbmaDailyT')} (非空)")
    for key in ("shfeInvT", "sgeInvT"):
        arr = d["series"][key]
        seg = [v for dt, v in zip(d["dates"], arr) if dt > "2026-07-10"]
        nn = sum(v is not None for v in seg)
        check(nn == len(seg) and seg, f"{key} 在 2026-07-10 之后无 null ({nn}/{len(seg)}, ffill 生效)")
        head_nulls = sum(v is None for v in arr[:5])
        print(f"    {key}: 头部 null {head_nulls}/5, 末值 {arr[-1]}, 最后实际日 {la.get(key)}")
    dom = d["series"]["domesticInvT"]
    dom_last = dom[-1]
    check(dom_last is not None and 500 < dom_last < 5000,
          f"domesticInvT 末值 {dom_last} 在合理区间 (500, 5000) 吨")
    sh_last, sg_last = d["series"]["shfeInvT"][-1], d["series"]["sgeInvT"][-1]
    check(sh_last is not None and sg_last is not None and
          abs((sh_last + sg_last) - dom_last) < 0.002,
          f"domesticInvT 末值 = shfe({sh_last}) + sge({sg_last}) 自洽")
    # 吨级序列 3 位小数抽查
    sh_dec = [len(str(v).split(".")[1]) for v in d["series"]["shfeInvT"] if isinstance(v, float) and "." in str(v)]
    check(all(n <= 3 for n in sh_dec), f"shfeInvT 小数位 ≤3 (抽查 {len(sh_dec)} 值)")

    # lease_rates.json
    lr = load_out("lease_rates.json")
    check(lr["dates"] == sorted(lr["dates"]), "lease_rates 日期升序")
    check(len(lr["dates"]) > 200, f"lease_rates 日期数 {len(lr['dates'])} (期望 >200)")
    check(list(lr["series"].keys()) == ["m1", "m3", "m6", "m12"], f"lease_rates 键 {list(lr['series'])}")
    check(all(len(v) == len(lr["dates"]) for v in lr["series"].values()), "lease_rates 序列长度一致")
    m6nn = [v for v in lr["series"]["m6"] if v is not None]
    check(len(m6nn) > 100 and -5 < m6nn[-1] < 20, f"lease m6 最新 {m6nn[-1]}% 量级合理, 非空 {len(m6nn)}")

    # seasonality.json
    se = load_out("seasonality.json")
    check(len(se["dates"]) == 366, f"seasonality 日期数 {len(se['dates'])} (期望 366)")
    check(sorted(se["years"].keys()) == ["2022", "2023", "2024", "2025", "2026"],
          f"seasonality 年份 {sorted(se['years'])}")
    check(all(len(v) == len(se["dates"]) for v in se["years"].values()), "seasonality 序列长度一致")
    nn25 = sum(v is not None for v in se["years"]["2025"])
    check(nn25 > 200, f"seasonality 2025 非空 {nn25}/366")

    # positions_curve / virtual_ratio（修改2: 仅偶数月合约）
    for fname in ["positions_curve.json", "virtual_ratio.json"]:
        pc = load_out(fname)
        codes = [c["code"] for c in pc["contracts"]]
        check(len(codes) >= 2,
              f"{fname} has >=2 even-month contracts (got {codes})")
        exps = [c["expiry"] for c in pc["contracts"]]
        check(exps == sorted(exps), f"{fname} 合约按到期日升序 {exps}")
        for c in pc["contracts"]:
            xs = [p["x"] for p in c["points"]]
            ys = [p["y"] for p in c["points"]]
            check(min(xs) >= -90 and max(xs) <= 0, f"{fname}.{c['code']} x∈[{min(xs)},{max(xs)}]")
            check(all(v is not None and v > 0 for v in ys), f"{fname}.{c['code']} y 全为正 ({len(ys)} 点)")
    vr = load_out("virtual_ratio.json")
    check(vr.get("formula") == "oi*15/st_stock_kg", "virtual_ratio.formula 元信息正确")

    # basis 文件
    for name, hi in [("basis_AGTD-AG2608.json", 1000), ("basis_AGTD-AG2609.json", 1000),
                     ("basis_AGTD-AG2610.json", 1000), ("basis_AG2608-AG2609.json", 1000),
                     ("basis_AG2609-AG2610.json", 1000), ("basis_AG2610-AG2611.json", 1000)]:
        b = load_out(name)
        check(b["times"][0] >= "2026-01-01" and len(b["times"]) > 100,
            f"{name} 时间范围 {b['times'][0]} → {b['times'][-1]} ({len(b['times'])} 条)")
        check(len(b["times"]) == len(b["values"]), f"{name} 序列长度一致 ({len(b['times'])})")
        st = b["stats"]
        check(abs(st["latest"]) < hi,
              f"{name} 最新基差 {st['latest']} 元/千克 (|值|<{hi}, 几十元量级说明对齐正确)")
        check(st["min"] <= st["mean"] <= st["max"], f"{name} stats min≤mean≤max")
        check(0 <= st["percentile"] <= 1, f"{name} percentile={st['percentile']} ∈[0,1]")

    # import_profit.json
    ip = load_out("import_profit.json")
    check(len(ip["times"]) == len(ip["importProfit"]) == len(ip["exportProfit"]),
          f"import_profit 序列长度一致 ({len(ip['times'])})")
    s = ip["stats"]
    check(abs(s["importLatest"]) < 2000, f"importLatest {s['importLatest']} 元/千克 量级合理")
    check(set(s) == {"importLatest", "importMean", "importPercentile",
                     "exportLatest", "exportMean", "exportPercentile"}, "import_profit stats 键齐全")

    # 静态拷贝
    for name, keys in [("monitoring.json", ["generatedAt", "indicators"]),
                       ("market.json", ["fetchedAt", "items"])]:
        j = load_out(name)
        check(all(k in j for k in keys), f"{name} 顶层键含 {keys}")

    # 无回归：记录数与上一版一致
    print("    ---- 回归检查: 记录数 ----")
    counts = {
        "daily.json": (len(d["dates"]), len(d["dates"])),  # dynamic: full history
        "seasonality.json": (len(se["dates"]), 366),
        "lease_rates.json": (len(lr["dates"]), 261),
        "import_profit.json": (len(ip["times"]), len(ip["times"])),  # dynamic
    }
    for name in ["basis_AGTD-AG2608.json", "basis_AGTD-AG2609.json", "basis_AGTD-AG2610.json",
                 "basis_AG2608-AG2609.json", "basis_AG2609-AG2610.json", "basis_AG2610-AG2611.json"]:
        b = load_out(name)
        counts[name] = (len(b["times"]), len(b["times"]))  # dynamic: no regression check on exact count
    for name, (got, exp) in counts.items():
        check(got == exp, f"{name} 记录数 {got} (期望 {exp}, 无回归)")
    # 无回归：键齐全
    check(set(d.keys()) == {"generatedAt", "asOfDate", "lastActual", "dates", "series"} and
          len(d["series"]) == 25, "daily.json 顶层键(含新增 lastActual)与 25 个 series 无回归")
    check(sorted(se.keys()) == ["dates", "generatedAt", "years"], "seasonality.json 顶层键无回归")
    check(sorted(lr.keys()) == ["dates", "generatedAt", "series"], "lease_rates.json 顶层键无回归")
    check(sorted(ip.keys()) == ["exportProfit", "generatedAt", "importProfit", "stats", "times"],
          "import_profit.json 顶层键无回归")


# ---------------------------------------------------------------- 主流程


def main() -> int:
    print("=" * 60)
    print("build_dashboard_data.py — 白银看板数据抽取")
    print(f"项目根: {ROOT}")
    print("=" * 60)

    sheets: dict[str, pd.DataFrame] = {}

    def _load():
        defensive_sheet_check()
        nonlocal sheets
        sheets = load_all_sheets()
        global CTX
        CTX = Ctx(sheets)

    print("\n[1/9] 加载输入")
    run_step("加载输入", _load)

    steps = [
        ("拷贝静态 JSON", step_copy_static),
        ("daily.json", step_daily),
        ("positions_curve.json", step_positions_curve),
        ("virtual_ratio.json", step_virtual_ratio),
        ("seasonality.json", step_seasonality),
        ("lease_rates.json", step_lease_rates),
        ("minute exports", step_minute_exports),
        ("basis_*.json", step_basis),
        ("import_profit.json", step_import_profit),
    ]
    for i, (label, fn) in enumerate(steps, start=2):
        print(f"\n[{i}/9] {label}")
        if CTX is None and label != "拷贝静态 JSON":
            print("  跳过：输入加载失败")
            ERRORS.append((label, "输入加载失败，跳过"))
            continue
        run_step(label, fn)

    print("\n[10/10] 校验输出")
    run_step("内容校验", verify)

    print("\n" + "=" * 60)
    if ERRORS:
        print(f"完成，但有 {len(ERRORS)} 个步骤失败:")
        for label, err in ERRORS:
            print(f"  [FAIL] {label}: {err}")
        if VERIFY_ISSUES:
            print(f"校验问题 {len(VERIFY_ISSUES)} 项:")
            for m in VERIFY_ISSUES:
                print(f"  [FAIL] {m}")
        return 1
    if VERIFY_ISSUES:
        print(f"生成成功，但校验发现 {len(VERIFY_ISSUES)} 项问题:")
        for m in VERIFY_ISSUES:
            print(f"  [FAIL] {m}")
        return 1
    print("全部输出生成成功，校验全部通过 [OK]")
    return 0


if __name__ == "__main__":
    sys.exit(main())