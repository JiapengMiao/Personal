"""
上期所白银成交及持仓排名 批量拉取脚本
────────────────────────────────────────
策略：
  1. 用 DrissionPage 启动 Edge，访问 shfe.com.cn 通过 Safeline WAF
  2. 提取 cookies
  3. 用 urllib + cookies 直接请求 .dat JSON 接口（比浏览器 JS 快得多）
  4. 筛选白银(ag)数据，按天保存 CSV + JSON

数据来源: https://www.shfe.com.cn/data/tradedata/future/dailydata/pm{YYYYMMDD}.dat
"""
import sys, os, time, json, csv
from datetime import datetime, timedelta, date
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = __import__("io").TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# ── 配置
EDGE_PATH   = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL    = "https://www.shfe.com.cn/data/tradedata/future/dailydata"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = PROJECT_ROOT / "data" / "shfe" / "ranking"
PRODUCT     = "ag"          # 白银合约前缀
PRODUCT_CN  = "白银"
DATE_START  = date(2026, 1, 1)
DATE_END    = date.today()
RETRY_MAX   = 3
RETRY_DELAY = 2
REQUEST_GAP = 0.5           # 请求间隔(秒)
WAF_WAIT    = 8


def weekdays_only(start, end):
    """只返回工作日"""
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def pass_waf_and_get_cookies():
    """启动浏览器，过WAF，返回cookies字典"""
    from DrissionPage import ChromiumPage, ChromiumOptions

    co = ChromiumOptions()
    co.set_browser_path(EDGE_PATH)
    co.headless(True)
    co.set_argument("--no-sandbox")
    co.set_argument("--disable-gpu")
    co.set_argument("--disable-dev-shm-usage")
    co.set_argument("--window-size=1920,1080")
    co.set_argument("--lang=zh-CN")
    co.set_timeouts(base=60, page_load=120)
    page = ChromiumPage(co)

    print(f"  启动 Edge 浏览器 (headless)...")
    print(f"  访问 shfe.com.cn 通过 WAF ({WAF_WAIT}s)...")
    page.get("https://www.shfe.com.cn/")
    time.sleep(WAF_WAIT)

    cookie_str = page.run_js("return document.cookie;")
    cookies = {}
    for pair in cookie_str.split(";"):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            cookies[k.strip()] = v.strip()

    page.quit()
    print(f"  WAF通过，获取到 {len(cookies)} 个cookies")
    return cookies


def fetch_dat(date_str, cookies):
    """用 urllib 请求 .dat 接口"""
    url = f"{BASE_URL}/pm{date_str}.dat?params={int(time.time()*1000)}"
    req = Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
    req.add_header("Referer", "https://www.shfe.com.cn/")
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        req.add_header("Cookie", cookie_header)

    for attempt in range(RETRY_MAX):
        try:
            resp = urlopen(req, timeout=30)
            data = resp.read()
            j = json.loads(data)
            if "o_cursor" in j:
                return j
            return None
        except HTTPError as e:
            if e.code == 404:
                return None
            if attempt < RETRY_MAX - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None
        except (URLError, json.JSONDecodeError):
            if attempt < RETRY_MAX - 1:
                time.sleep(RETRY_DELAY)
            else:
                return None
    return None


def filter_silver(records):
    """筛选白银数据：INSTRUMENTID 以 'ag' 开头"""
    return [r for r in records if r.get("INSTRUMENTID", "").strip().lower().startswith(PRODUCT)]


def save_day_data(date_str, silver_records):
    """保存一天的白银数据为 CSV + JSON"""
    day_dir = OUTPUT_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    json_path = day_dir / f"silver_ranking_{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(silver_records, f, ensure_ascii=False, indent=2)

    csv_path = day_dir / f"silver_ranking_{date_str}.csv"
    if not silver_records:
        return json_path, csv_path

    fields = [
        "INSTRUMENTID", "RANK",
        "PARTICIPANTABBR1", "CJ1", "CJ1_CHG",
        "PARTICIPANTABBR2", "CJ2", "CJ2_CHG",
        "PARTICIPANTABBR3", "CJ3", "CJ3_CHG",
        "PRODUCTNAME",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["DATE"] + fields, extrasaction="ignore")
        writer.writeheader()
        for r in silver_records:
            row = {"DATE": date_str}
            row.update({k: r.get(k, "") for k in fields})
            writer.writerow(row)

    return json_path, csv_path


def save_combined_csv(all_data):
    """保存所有日期合并的CSV"""
    csv_path = OUTPUT_DIR / f"silver_ranking_all_{DATE_START}_{DATE_END}.csv"
    fields = [
        "DATE", "INSTRUMENTID", "RANK",
        "PARTICIPANTABBR1", "CJ1", "CJ1_CHG",
        "PARTICIPANTABBR2", "CJ2", "CJ2_CHG",
        "PARTICIPANTABBR3", "CJ3", "CJ3_CHG",
        "PRODUCTNAME",
    ]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for date_str in sorted(all_data.keys()):
            for r in all_data[date_str]:
                row = {"DATE": date_str}
                row.update({k: r.get(k, "") for k in fields if k != "DATE"})
                writer.writerow(row)

    total = sum(len(v) for v in all_data.values())
    print(f"\n  合并CSV: {csv_path} ({total} 条记录)")


def main():
    today = date.today()
    actual_end = min(DATE_END, today)

    print("=" * 60)
    print(f"上期所{PRODUCT_CN} 成交及持仓排名 批量拉取")
    print(f"日期范围: {DATE_START} ~ {actual_end}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    # Step 1: 过WAF
    print("\n[Step 1] 过WAF...")
    cookies = pass_waf_and_get_cookies()

    # Step 2: 生成交易日列表
    workdays = list(weekdays_only(DATE_START, actual_end))
    print(f"\n[Step 2] 待拉取工作日: {len(workdays)} 天")

    # Step 3: 逐日拉取
    print(f"\n[Step 3] 开始批量拉取...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    all_data = {}
    success = 0
    no_data = 0
    failed = 0

    for i, d in enumerate(workdays):
        date_str = d.strftime("%Y%m%d")
        status = f"[{i+1}/{len(workdays)}] {date_str} ({d.strftime('%a')})"
        print(f"  {status} ... ", end="", flush=True)

        jdata = fetch_dat(date_str, cookies)
        if jdata is None:
            print("无数据")
            no_data += 1
            time.sleep(REQUEST_GAP)
            continue

        records = jdata.get("o_cursor", [])
        silver = filter_silver(records)

        if not silver:
            print(f"无{PRODUCT_CN}数据")
            no_data += 1
            time.sleep(REQUEST_GAP)
            continue

        save_day_data(date_str, silver)
        all_data[date_str] = silver
        success += 1
        print(f"OK {len(silver)} 条 (全部{len(records)}条)")

        time.sleep(REQUEST_GAP)

    # Step 4: 合并CSV
    if all_data:
        print(f"\n[Step 4] 生成合并CSV...")
        save_combined_csv(all_data)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"完成！ 成功={success}  无数据={no_data}  失败={failed}")
    print(f"输出: {OUTPUT_DIR}")
    print(f"{'=' * 60}")

    # 拉取报告
    report = {
        "date_range": f"{DATE_START} ~ {actual_end}",
        "product": PRODUCT_CN,
        "workdays_total": len(workdays),
        "success": success,
        "no_data": no_data,
        "failed": failed,
        "output_dir": str(OUTPUT_DIR),
        "fetch_time": datetime.now().isoformat(),
        "dates_with_data": sorted(all_data.keys()),
    }
    report_path = OUTPUT_DIR / "fetch_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  拉取报告: {report_path}")


if __name__ == "__main__":
    main()
