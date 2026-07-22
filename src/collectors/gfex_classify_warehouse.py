"""
仓单数据分类处理：将仓库分为「仓库」和「厂库」两类并聚合
"""
import csv
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "gfex"

# 仓库分类定义
PT_WAREHOUSES = {"中工美上海虹桥", "外运华东上海虹桥", "深圳威豹"}
PD_WAREHOUSES = {"中储吴淞", "中工美上海虹桥", "外运华东上海虹桥", "深圳威豹"}

def classify(variety, warehouse_name):
    """判断仓库类型"""
    if variety == "铂":
        return "仓库" if warehouse_name in PT_WAREHOUSES else "厂库"
    elif variety == "钯":
        return "仓库" if warehouse_name in PD_WAREHOUSES else "厂库"
    return "厂库"

def process(input_csv):
    """读取原始数据，添加分类列，输出明细+聚合两个文件"""
    with open(input_csv, encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))

    # 1. 添加「仓库类型」列，写明细文件
    detail_rows = []
    for r in rows:
        r["仓库类型"] = classify(r["品种"], r["仓库名称"])
        detail_rows.append(r)

    detail_fields = ["品种", "日期", "仓库类型", "仓库代码", "仓库名称",
                     "昨日仓单", "今日注册", "今日注销", "今日仓单", "增减"]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    detail_path = DATA_DIR / "铂钯仓单明细_分类.csv"
    with open(detail_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=detail_fields)
        w.writeheader()
        w.writerows(detail_rows)
    print(f"明细文件: {detail_path} ({len(detail_rows)} 条)")

    # 2. 按 日期+品种+仓库类型 聚合
    agg = {}
    for r in detail_rows:
        key = (r["日期"], r["品种"], r["仓库类型"])
        if key not in agg:
            agg[key] = {"昨日仓单": 0, "今日注册": 0, "今日注销": 0, "今日仓单": 0, "增减": 0}
        for field in ["昨日仓单", "今日注册", "今日注销", "今日仓单", "增减"]:
            agg[key][field] += int(r[field])

    agg_rows = []
    for (date, variety, wh_type), vals in sorted(agg.items()):
        agg_rows.append({
            "日期": date,
            "品种": variety,
            "仓库类型": wh_type,
            "昨日仓单": vals["昨日仓单"],
            "今日注册": vals["今日注册"],
            "今日注销": vals["今日注销"],
            "今日仓单": vals["今日仓单"],
            "增减": vals["增减"],
        })

    agg_fields = ["日期", "品种", "仓库类型", "昨日仓单", "今日注册", "今日注销", "今日仓单", "增减"]
    agg_path = DATA_DIR / "铂钯仓单聚合_仓库类型.csv"
    with open(agg_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=agg_fields)
        w.writeheader()
        w.writerows(agg_rows)
    print(f"聚合文件: {agg_path} ({len(agg_rows)} 条)")

    # 3. 打印摘要
    print("\n" + "=" * 60)
    print("分类统计摘要")
    print("=" * 60)
    for variety in ["铂", "钯"]:
        wh_rows = [r for r in detail_rows if r["品种"] == variety and r["仓库类型"] == "仓库"]
        fw_rows = [r for r in detail_rows if r["品种"] == variety and r["仓库类型"] == "厂库"]
        wh_names = sorted(set(r["仓库名称"] for r in wh_rows))
        fw_names = sorted(set(r["仓库名称"] for r in fw_rows))
        print(f"\n{variety}:")
        print(f"  仓库 ({len(wh_names)}个): {', '.join(wh_names)}")
        print(f"  厂库 ({len(fw_names)}个): {', '.join(fw_names)}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        csv_file = Path(sys.argv[1])
    else:
        candidates = sorted(DATA_DIR.glob("铂钯仓单数据_*.csv"))
        if not candidates:
            raise FileNotFoundError(f"未找到广期所仓单原始 CSV: {DATA_DIR}")
        csv_file = candidates[-1]
    process(csv_file)
