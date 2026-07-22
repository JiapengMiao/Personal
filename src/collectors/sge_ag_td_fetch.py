"""
上海黄金交易所 Ag(T+D) 每日持仓量拉取
数据源：https://www.sge.com.cn/sjzx/quotation_daily_new
按天查询，避免分页问题，写入本项目统一数据目录。
"""
import sys, io, time, re, csv, json
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_URL = "https://www.sge.com.cn/sjzx/quotation_daily_new"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "data" / "sge"
CONTRACT = "Ag(T+D)"

# Ag(T+D) 行的正则
ROW_PATTERN = re.compile(
    r'<td[^>]*>\s*(\d{4}-\d{2}-\d{2})\s*</td>\s*'
    r'<td[^>]*>\s*Ag\(T\+D\)\s*</td>\s*'
    r'<td[^>]*>\s*([\d,.]+|-)\s*</td>\s*'   # 开盘价
    r'<td[^>]*>\s*([\d,.]+|-)\s*</td>\s*'   # 最高价
    r'<td[^>]*>\s*([\d,.]+|-)\s*</td>\s*'   # 最低价
    r'<td[^>]*>\s*([\d,.]+|-)\s*</td>\s*'   # 收盘价
    r'<td[^>]*>\s*([-\d,.]+)\s*</td>\s*'    # 涨跌
    r'<td[^>]*>\s*([-\d,.]+%?)\s*</td>\s*'  # 涨跌幅
    r'<td[^>]*>\s*([\d,.]+|-)\s*</td>\s*'   # 加权平均价
    r'<td[^>]*>\s*([\d,.]+)\s*</td>\s*'     # 成交量
    r'<td[^>]*>\s*([\d,.]+)\s*</td>\s*'     # 成交金额
    r'<td[^>]*>\s*([\d,.]+|-)\s*</td>',     # 市场持仓
    re.DOTALL
)


def weekdays_in_range(start, end):
    """生成日期范围内的工作日"""
    d = start
    while d <= end:
        if d.weekday() < 5:
            yield d
        d += timedelta(days=1)


def fetch_day(d):
    """拉取指定日期的数据"""
    date_str = d.strftime("%Y-%m-%d")
    url = f"{BASE_URL}?start_date={date_str}&end_date={date_str}"
    req = Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')

    for attempt in range(3):
        try:
            resp = urlopen(req, timeout=30)
            html = resp.read().decode('utf-8')
            return html
        except (URLError, HTTPError) as e:
            if attempt < 2:
                time.sleep(2)
            else:
                return None
    return None


def parse_ag_td(html):
    """从HTML中提取Ag(T+D)数据"""
    match = ROW_PATTERN.search(html)
    if not match:
        return None

    def to_num(s):
        if s == '-' or s is None:
            return ''
        return s.replace(',', '')

    return {
        'date': match.group(1),
        'open': to_num(match.group(2)),
        'high': to_num(match.group(3)),
        'low': to_num(match.group(4)),
        'close': to_num(match.group(5)),
        'change': to_num(match.group(6)),
        'change_pct': match.group(7).strip(),
        'avg_price': to_num(match.group(8)),
        'volume_kg': to_num(match.group(9)),
        'turnover_yuan': to_num(match.group(10)),
        'open_interest': to_num(match.group(11)),
    }


def main():
    print("=" * 60)
    print(f"拉取 {CONTRACT} 2026年每日持仓量数据")
    print(f"输出路径: {OUTPUT_DIR}")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 读取已有数据，跳过已拉取的日期
    csv_path = OUTPUT_DIR / "ag_td_daily_2026.csv"
    existing_dates = set()
    existing_records = []
    if csv_path.exists():
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                existing_dates.add(row['date'])
                existing_records.append(row)
        print(f"已有 {len(existing_dates)} 天数据，增量拉取")

    # 增量模式只检查最新有效记录之后的日期，避免每天重复请求全年节假日。
    # 历史缺口如需回补，应由单独的 backfill 流程处理。
    start = date(2026, 1, 1)
    if existing_dates:
        start = date.fromisoformat(max(existing_dates)) + timedelta(days=1)
    today = date.today()

    workdays = [d for d in weekdays_in_range(start, today) if d.strftime("%Y-%m-%d") not in existing_dates]

    if not workdays:
        print("\n所有工作日数据已存在，无需拉取。")
        return

    print(f"待拉取: {len(workdays)} 个工作日\n")

    new_records = []
    success = 0
    no_data = 0

    for i, d in enumerate(workdays):
        date_str = d.strftime("%Y-%m-%d")
        print(f"  [{i+1}/{len(workdays)}] {date_str} ... ", end="", flush=True)

        html = fetch_day(d)
        if html is None:
            print("请求失败")
            no_data += 1
            time.sleep(0.5)
            continue

        record = parse_ag_td(html)
        if record is None:
            print("无数据(休市?)")
            no_data += 1
        else:
            new_records.append(record)
            oi = record['open_interest']
            if oi:
                oi = f"{int(float(oi)):,}"
            print(f"OK  持仓={oi}")
            success += 1

        time.sleep(0.5)

    # 合并新旧数据
    all_records = existing_records + new_records
    all_records.sort(key=lambda r: r['date'])

    # 去重
    seen = set()
    unique = []
    for r in all_records:
        if r['date'] not in seen:
            seen.add(r['date'])
            unique.append(r)
    all_records = unique

    # 保存CSV
    fields = ['date', 'open', 'high', 'low', 'close', 'change', 'change_pct',
              'avg_price', 'volume_kg', 'turnover_yuan', 'open_interest']
    with open(csv_path, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(all_records)

    # 保存JSON
    json_path = OUTPUT_DIR / "ag_td_daily_2026.json"
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*60}")
    print(f"完成！ 新增={success}  无数据={no_data}  总计={len(all_records)} 个交易日")
    print(f"CSV: {csv_path}")
    print(f"JSON: {json_path}")

    # 打印最新几天
    print(f"\n最新5天数据：")
    print(f"{'日期':<12} {'收盘价':>10} {'涨跌':>8} {'市场持仓(手)':>14}")
    print("-" * 50)
    for r in all_records[-5:]:
        oi = r['open_interest']
        if oi:
            oi = f"{int(float(oi)):,}"
        chg = r['change']
        print(f"{r['date']:<12} {r['close']:>10} {chg:>8} {oi:>14}")


if __name__ == "__main__":
    main()
