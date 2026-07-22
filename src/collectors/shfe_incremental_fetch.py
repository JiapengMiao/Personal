"""
上期所白银 增量拉取
自动检测缺失日期并补充拉取，写入本项目统一数据目录。
"""
import sys, io, time, json, csv
from datetime import datetime, timedelta, date
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

EDGE_PATH   = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
BASE_URL    = "https://www.shfe.com.cn/data/tradedata/future/dailydata"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR  = PROJECT_ROOT / "data" / "shfe" / "ranking"
PRODUCT     = "ag"
PRODUCT_CN  = "白银"
DATE_START  = date(2026, 1, 1)
DATE_END    = date.today()
RETRY_MAX   = 3
RETRY_DELAY = 2
REQUEST_GAP = 0.5
WAF_WAIT    = 8


def weekdays_only(start, end):
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def pass_waf_and_get_cookies():
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
    print(f"  启动 Edge，过WAF ({WAF_WAIT}s)...")
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
    print(f"  WAF通过，cookies: {list(cookies.keys())}")
    return cookies


def fetch_dat(date_str, cookies):
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
    return [r for r in records if r.get("INSTRUMENTID", "").strip().lower().startswith(PRODUCT)]


def save_day_data(date_str, silver_records):
    day_dir = OUTPUT_DIR / date_str
    day_dir.mkdir(parents=True, exist_ok=True)

    json_path = day_dir / f"silver_ranking_{date_str}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(silver_records, f, ensure_ascii=False, indent=2)

    csv_path = day_dir / f"silver_ranking_{date_str}.csv"
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


def main():
    print("=" * 60)
    print(f"增量拉取 {PRODUCT_CN} {DATE_START} ~ {DATE_END}")
    print(f"输出路径: {OUTPUT_DIR}")
    print("=" * 60)

    # 日常增量只检查最新有效目录之后的日期，避免重复请求全年节假日。
    existing = sorted(
        d for d in OUTPUT_DIR.iterdir()
        if d.is_dir() and len(d.name) == 8 and d.name.isdigit()
    ) if OUTPUT_DIR.exists() else []
    scan_start = DATE_START
    if existing:
        scan_start = datetime.strptime(existing[-1].name, "%Y%m%d").date() + timedelta(days=1)
    workdays = list(weekdays_only(scan_start, DATE_END))

    if not workdays:
        print("\n所有日期已有数据，无需拉取。")
        return

    print(f"待拉取: {len(workdays)} 天")
    print("过WAF...")
    cookies = pass_waf_and_get_cookies()

    success = 0
    no_data = 0

    for i, d in enumerate(workdays):
        date_str = d.strftime("%Y%m%d")
        print(f"  [{i+1}/{len(workdays)}] {date_str} ... ", end="", flush=True)

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
        success += 1
        print(f"OK {len(silver)} 条")
        time.sleep(REQUEST_GAP)

    print(f"\n完成！ 成功={success}  无数据={no_data}")
    print(f"输出: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
