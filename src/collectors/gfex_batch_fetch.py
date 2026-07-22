"""
批量拉取广期所铂钯仓单数据（2026-05-06 至今）
"""
import requests
import csv
import time
from datetime import datetime, timedelta
from pathlib import Path

WAREHOUSE_API = "http://www.gfex.com.cn/u/interfacesWebTdWbillWeeklyQuotes/loadList"
VARIETIES = [("pt", "铂"), ("pd", "钯")]
START_DATE = "20260506"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "gfex"

def get_trading_days(start, end):
    """生成交易日列表（跳过周末）"""
    days = []
    current = datetime.strptime(start, "%Y%m%d")
    end_dt = datetime.strptime(end, "%Y%m%d")
    while current <= end_dt:
        if current.weekday() < 5:
            days.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    return days

def fetch_data(session, date_str, variety_code):
    """通过已建立session的请求获取仓单数据"""
    try:
        r = session.post(WAREHOUSE_API, data={"gen_date": date_str, "variety": variety_code}, timeout=15)
        result = r.json()
        if result.get("code") == "0" and result.get("data"):
            return result["data"]
    except Exception as e:
        print(f"  [错误] {date_str} {variety_code}: {e}")
    return []

def parse_records(raw_data, variety_name):
    """解析仓单记录，跳过总计/小计行"""
    records = []
    for item in raw_data:
        if item.get("variety") in ["总计", "小计"] or not item.get("genDate"):
            continue
        records.append({
            "品种": variety_name,
            "日期": item.get("genDate", ""),
            "仓库代码": item.get("whCodeOrder", ""),
            "仓库名称": item.get("whAbbr", ""),
            "昨日仓单": item.get("lastWbillQty", 0),
            "今日注册": item.get("regWbillQty", 0),
            "今日注销": item.get("logoutWbillQty", 0),
            "今日仓单": item.get("wbillQty", 0),
            "增减": item.get("diff", 0),
        })
    return records

def save_csv(records, filename):
    """保存CSV"""
    if not records:
        return
    fields = ["品种", "日期", "仓库代码", "仓库名称", "昨日仓单", "今日注册", "今日注销", "今日仓单", "增减"]
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(records)
    print(f"已保存: {filename} ({len(records)} 条)")

def main():
    today = datetime.now().strftime("%Y%m%d")
    trading_days = get_trading_days(START_DATE, today)
    print(f"日期范围: {START_DATE} ~ {today}, 共 {len(trading_days)} 个交易日")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    })
    # 先访问主页建立session
    session.get("http://www.gfex.com.cn", timeout=15)
    print("Session 已建立\n")

    all_records = []
    empty_days = []

    for i, day in enumerate(trading_days, 1):
        day_has_data = False
        for code, name in VARIETIES:
            raw = fetch_data(session, day, code)
            records = parse_records(raw, name)
            if records:
                all_records.extend(records)
                day_has_data = True
        status = "有数据" if day_has_data else "无数据"
        if not day_has_data:
            empty_days.append(day)
        print(f"[{i}/{len(trading_days)}] {day[:4]}-{day[4:6]}-{day[6:]} {status}")
        time.sleep(0.5)

    # 保存到统一 data/gfex 目录
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    save_csv(all_records, DATA_DIR / f"铂钯仓单数据_{START_DATE}_{today}_{ts}.csv")

    # 摘要
    pt_count = len([r for r in all_records if r["品种"] == "铂"])
    pd_count = len([r for r in all_records if r["品种"] == "钯"])
    print(f"\n{'='*50}")
    print(f"拉取完成!")
    print(f"铂: {pt_count} 条, 钯: {pd_count} 条, 总计: {len(all_records)} 条")
    print(f"有数据交易日: {len(trading_days) - len(empty_days)} 天")
    if empty_days:
        print(f"无数据交易日 ({len(empty_days)} 天): {', '.join(empty_days[:10])}{'...' if len(empty_days)>10 else ''}")

if __name__ == "__main__":
    main()
