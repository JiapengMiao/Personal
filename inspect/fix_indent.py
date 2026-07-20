path = r"C:\Users\56558\Nutstore\1\我的坚果云\agent\Project-002-白银数据网页可视化\src\build_dashboard_data.py"
with open(path, "r", encoding="utf-8") as f:
    src = f.read()

# Fix indentation: the trading_calendar block should be at 8-space indent (same level as the print above it)
old_block = '''        print(f"  calendar: {len(self.calendar)} days (hist {len(self._hist_calendar)} + future {len(self.calendar)-len(self._hist_calendar)})")

          # ---- 交易日日历：仅保留 agtdClose 非空非零的日期（用于虚实比/持仓量 x 轴）
          _agtd_close_col = "上海金交所:收盘价:白银现货:Ag(T+D)"
          if _agtd_close_col in self.daily.columns:
              _ac = pd.to_numeric(self.daily[_agtd_close_col], errors="coerce")
              _mask = _ac.notna() & (_ac != 0)
              self.trading_calendar = pd.DatetimeIndex(self.daily.loc[_mask, "date"].values)
          else:
              self.trading_calendar = self._hist_calendar
          print(f"  trading_calendar: {len(self.trading_calendar)} days (from {len(self._hist_calendar)} hist rows)")'''

new_block = '''        print(f"  calendar: {len(self.calendar)} days (hist {len(self._hist_calendar)} + future {len(self.calendar)-len(self._hist_calendar)})")

        # ---- 交易日日历：仅保留 agtdClose 非空非零的日期（用于虚实比/持仓量 x 轴）
        _agtd_close_col = "上海金交所:收盘价:白银现货:Ag(T+D)"
        if _agtd_close_col in self.daily.columns:
            _ac = pd.to_numeric(self.daily[_agtd_close_col], errors="coerce")
            _mask = _ac.notna() & (_ac != 0)
            self.trading_calendar = pd.DatetimeIndex(self.daily.loc[_mask, "date"].values)
        else:
            self.trading_calendar = self._hist_calendar
        print(f"  trading_calendar: {len(self.trading_calendar)} days (from {len(self._hist_calendar)} hist rows)")'''

src = src.replace(old_block, new_block, 1)

with open(path, "w", encoding="utf-8") as f:
    f.write(src)
print("Indentation fixed")
