#!/usr/bin/env python3
"""拉取香港政府统计处 HS 7106 白银全量进出口数据（2012-2026.05）"""
import json, urllib.request, time, csv, os, http.cookiejar

BASE = "https://tradeidds.censtatd.gov.hk/api/get"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(OUT_DIR, "hk_silver_trade.csv")

# 内存 cookie（跟随 302 会话）
_cj = http.cookiejar.CookieJar()
_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(_cj))

def fetch(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    for attempt in range(3):
        try:
            resp = _opener.open(req, timeout=60)
            return json.loads(resp.read().decode())
        except Exception as e:
            if attempt == 2:
                raise
            time.sleep(3)

def query(params):
    url = BASE + "?" + "&".join(f"{k}={v}" for k, v in params.items())
    return fetch(url)

# 拉取函数
def pull_qty(code, ttype, period):
    """6位月度数量（千克）"""
    d = query({"lang":"EN","sv":"QCm","freq":"M","period":period,"ttype":ttype,"codeclass":"HKHS6","code":code})
    return {r["period"]: int(r["figure"]) for r in d.get("dataSet", [])}

def pull_val(code, ttype, period):
    """4位月度货值（千港元）"""
    d = query({"lang":"EN","sv":"VCm","freq":"M","period":period,"ttype":ttype,"codeclass":"HKHS4","code":code})
    return {r["period"]: int(r["figure"]) for r in d.get("dataSet", [])}

print("拉取中...")

# 1. 6位数量（千克）：三个子编码 × 三种贸易类型
qty_data = {}  # {period: {label: kg}}
codes_6 = ["710610", "710691", "710692"]
ttypes = {"1": "进口", "3": "转口", "4": "出口总额"}
period = "201201,202605"

for code in codes_6:
    for tt, label in ttypes.items():
        result = pull_qty(code, tt, period)
        for p, v in result.items():
            qty_data.setdefault(p, {})
            key = f"{label}_{code}"
            qty_data[p][key] = qty_data[p].get(key, 0) + v
        print(f"  QCm {code} ttype={tt}: {len(result)} 条")
        time.sleep(0.3)

# 2. 4位货值（千港元）：7106 × 三种贸易类型
val_data = {}  # {period: {label: 千港元}}
for tt, label in ttypes.items():
    result = pull_val("7106", tt, period)
    for p, v in result.items():
        val_data.setdefault(p, {})[label] = v
    print(f"  VCm 7106 ttype={tt}: {len(result)} 条")
    time.sleep(0.3)

# 3. 汇总所有月份
all_periods = sorted(set(list(qty_data.keys()) + list(val_data.keys())))
print(f"\n共 {len(all_periods)} 个月份: {all_periods[0]} ~ {all_periods[-1]}")

# 4. 写 CSV
USDHKD = 7.8
with open(OUT, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow([
        "月份",
        "进口数量(吨)", "转口数量(吨)", "出口总额数量(吨)",
        "进口货值(千港元)", "转口货值(千港元)", "出口总额货值(千港元)",
        "进口货值(亿美元)", "出口总额货值(亿美元)",
        "净流入数量(吨)", "净流入货值(千港元)",
        "进口隐含单价(美元/kg)", "出口隐含单价(美元/kg)",
    ])
    for p in all_periods:
        q = qty_data.get(p, {})
        v = val_data.get(p, {})
        # 数量（千克→吨）
        imp_q = sum(q.get(f"进口_{c}", 0) for c in codes_6) / 1000
        reexp_q = sum(q.get(f"转口_{c}", 0) for c in codes_6) / 1000
        exp_q = sum(q.get(f"出口总额_{c}", 0) for c in codes_6) / 1000
        net_q = imp_q - exp_q
        # 货值（千港元）
        imp_v = v.get("进口", 0)
        reexp_v = v.get("转口", 0)
        exp_v = v.get("出口总额", 0)
        net_v = imp_v - exp_v
        # 折亿美元
        imp_usd = imp_v / 1e6 / USDHKD if imp_v else 0
        exp_usd = exp_v / 1e6 / USDHKD if exp_v else 0
        # 隐含单价（美元/kg）= 货值(港元) / 数量(kg) / 7.8
        imp_price = (imp_v * 1000 / USDHKD) / (imp_q * 1000) if imp_q > 0 else 0
        exp_price = (exp_v * 1000 / USDHKD) / (exp_q * 1000) if exp_q > 0 else 0
        w.writerow([
            p,
            f"{imp_q:.1f}", f"{reexp_q:.1f}", f"{exp_q:.1f}",
            imp_v, reexp_v, exp_v,
            f"{imp_usd:.2f}", f"{exp_usd:.2f}",
            f"{net_q:+.1f}", net_v,
            f"{imp_price:.2f}", f"{exp_price:.2f}",
        ])

print(f"\n已保存: {OUT}")
print(f"数据范围: {all_periods[0]} ~ {all_periods[-1]}")
