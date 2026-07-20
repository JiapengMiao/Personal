path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\src\build_dashboard_data.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Move trading_calendar construction to AFTER calendar extension
# 1. Remove the current trading_calendar block (before calendar extension)
old_tc = '''        # ---- 交易日日历：排除周末 + 包含所有合约到期日（用于虚实比/持仓量 x 轴）
        _wd = self._hist_calendar.weekday
        _biz = self._hist_calendar[_wd < 5]  # Mon-Fri
        # 确保所有合约到期日都在日历中
        _exp_dates = pd.DatetimeIndex(list(self.expiry.values()))
        self.trading_calendar = _biz.union(_exp_dates).sort_values()
        print(f"  trading_calendar: {len(self.trading_calendar)} days (biz {len(_biz)} + expiry {len(_exp_dates)})")

        # ---- 虚实比数据'''

new_tc = '''        # ---- 虚实比数据'''
src = src.replace(old_tc, new_tc, 1)

# 2. Add trading_calendar AFTER calendar extension (after the calendar print line)
old_cal_print = '''        print(f"  calendar: {len(self.calendar)} days (hist {len(self._hist_calendar)} + future {len(self.calendar)-len(self._hist_calendar)})")'''

new_cal_print = '''        print(f"  calendar: {len(self.calendar)} days (hist {len(self._hist_calendar)} + future {len(self.calendar)-len(self._hist_calendar)})")

        # ---- 交易日日历：从扩展后的 calendar 排除周末 + 包含所有合约到期日
        _wd = self.calendar.weekday
        _biz = self.calendar[_wd < 5]  # Mon-Fri
        _exp_dates = pd.DatetimeIndex(list(self.expiry.values()))
        self.trading_calendar = _biz.union(_exp_dates).sort_values()
        print(f"  trading_calendar: {len(self.trading_calendar)} days (biz {len(_biz)} + expiry {len(_exp_dates)})")'''

src = src.replace(old_cal_print, new_cal_print, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Fixed: trading_calendar now built from extended calendar")
