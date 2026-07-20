path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\src\build_dashboard_data.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# 1. Fix trading_calendar: use weekday filter instead of agtdClose, and include expiry dates
old_tc = '''        # ---- 交易日日历：仅保留 agtdClose 非空非零的日期（用于虚实比/持仓量 x 轴）
        _agtd_close_col = "上海金交所:收盘价:白银现货:Ag(T+D)"
        if _agtd_close_col in self.daily.columns:
            _ac = pd.to_numeric(self.daily[_agtd_close_col], errors="coerce")
            _mask = _ac.notna() & (_ac != 0)
            self.trading_calendar = pd.DatetimeIndex(self.daily.loc[_mask, "date"].values)
        else:
            self.trading_calendar = self._hist_calendar
        print(f"  trading_calendar: {len(self.trading_calendar)} days (from {len(self._hist_calendar)} hist rows)")'''

new_tc = '''        # ---- 交易日日历：排除周末 + 包含所有合约到期日（用于虚实比/持仓量 x 轴）
        _wd = self._hist_calendar.weekday
        _biz = self._hist_calendar[_wd < 5]  # Mon-Fri
        # 确保所有合约到期日都在日历中
        _exp_dates = pd.DatetimeIndex(list(self.expiry.values()))
        self.trading_calendar = _biz.union(_exp_dates).sort_values()
        print(f"  trading_calendar: {len(self.trading_calendar)} days (biz {len(_biz)} + expiry {len(_exp_dates)})")'''

src = src.replace(old_tc, new_tc, 1)

# 2. Fix _contract_points: extend expired contracts to x=0
old_cp = '''def _contract_points(code: str, y_func) -> list[dict]:
    """按交易日日历计算 x（距到期日的交易日序号差，到期日 x=0），保留 [-90, 0]。"""
    assert CTX is not None
    cal = CTX.trading_calendar
    exp = CTX.expiry.get(code, CTX.oi[code]["date"].max())
    exp_pos = int(cal.searchsorted(pd.Timestamp(exp)))
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
    return pts'''

new_cp = '''def _contract_points(code: str, y_func) -> list[dict]:
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
    return pts'''

src = src.replace(old_cp, new_cp, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("build_dashboard_data.py: fixed trading_calendar + expired contract extension")
