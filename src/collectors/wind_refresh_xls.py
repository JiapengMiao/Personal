# -*- coding: utf-8 -*-
"""
Excel数据刷新脚本

功能：
1. 遍历数据目录中的Excel文件，使用win32com打开并保存以刷新Wind RTD公式
2. 检查数据文件的新鲜度，提醒用户更新数据

注意：
- 此脚本只能刷新Excel中的RTD/链接公式，不能自动从Wind获取新数据
- Wind数据需要手动从Wind客户端导出，或使用Wind API（需要Wind终端登录）
"""

import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# 统一 Wind 数据目录
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data" / "wind"

# 需要排除的文件夹
EXCLUDE_FOLDERS = [
    "AG_基差图输出",
    "figure_output",
]

# 需要检查的关键数据文件及建议更新频率（小时）。
# 新结构只需要刷新一个工作簿；旧文件保留为数据读取回退，不再逐个刷新。
KEY_FILES = {
    "白银所有数据.xlsx": 24,
}


def check_data_freshness():
    """检查数据文件的新鲜度"""
    print("\n" + "=" * 60)
    print("数据新鲜度检查")
    print("=" * 60)

    now = datetime.now()
    stale_files = []
    missing_files = []

    for file_path, max_age_hours in KEY_FILES.items():
        full_path = DATA_DIR / file_path
        if not full_path.exists():
            missing_files.append(file_path)
            print(f"  ❌ 缺失: {file_path}")
            continue

        mtime = datetime.fromtimestamp(full_path.stat().st_mtime)
        age = now - mtime
        age_hours = age.total_seconds() / 3600

        if age_hours > max_age_hours:
            stale_files.append((file_path, age, max_age_hours))
            age_str = format_timedelta(age)
            print(f"  ⚠️  过期: {file_path} (最后更新: {age_str}前, 建议: {max_age_hours}小时内)")
        else:
            age_str = format_timedelta(age)
            print(f"  ✅ 正常: {file_path} (最后更新: {age_str}前)")

    print("\n" + "-" * 60)

    if missing_files:
        print(f"⚠️  缺失 {len(missing_files)} 个文件，需要从Wind导出")

    if stale_files:
        print(f"⚠️  {len(stale_files)} 个文件数据过期，建议从Wind更新")
        print("\n更新方法：")
        print("  1. 打开Wind终端")
        print("  2. 导出最新数据到对应文件")
        print("  3. 或使用Wind API自动导出（需要配置）")
    else:
        print("✅ 所有关键数据文件都是最新的")

    return len(stale_files) == 0 and len(missing_files) == 0


def format_timedelta(td):
    """格式化时间差为易读格式"""
    total_seconds = int(td.total_seconds())
    if total_seconds < 60:
        return f"{total_seconds}秒"
    elif total_seconds < 3600:
        minutes = total_seconds // 60
        return f"{minutes}分钟"
    elif total_seconds < 86400:
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}小时{minutes}分钟"
    else:
        days = total_seconds // 86400
        hours = (total_seconds % 86400) // 3600
        return f"{days}天{hours}小时"


def refresh_excel_files():
    """使用win32com刷新Excel文件"""
    try:
        import win32com.client as win32
    except ImportError:
        print("⚠️  未安装pywin32，跳过Excel刷新")
        print("   安装方法: pip install pywin32")
        return False

    print("\n" + "=" * 60)
    print("Excel文件刷新")
    print("=" * 60)

    base_dir = DATA_DIR
    print(f"处理文件夹：{base_dir}")

    # 不强制关闭用户正在使用的 Excel；刷新脚本自行打开目标工作簿。
    import subprocess

    total = 0
    success = 0

    try:
        file_path = DATA_DIR / "白银所有数据.xlsx"
        if not file_path.exists():
            print(f"  [MISSING] {file_path}")
            return False

        total = 1
        print(f"  [1] 处理: {file_path.relative_to(base_dir)}")
        try:
            script_path = Path(__file__).resolve().parent / "refresh_single_excel.py"
            result = subprocess.run(
                [sys.executable, str(script_path), str(file_path)],
                capture_output=True,
                text=True,
                timeout=120
            )
            if result.returncode == 0:
                success = 1
                print("      [OK] 保存成功")
            else:
                error_msg = result.stderr.strip() if result.stderr else "Unknown error"
                print(f"      [FAIL] 处理失败: {error_msg}")
        except subprocess.TimeoutExpired:
            print("      [WARN] 处理超时(120秒)，跳过")
        except Exception as e:
            print(f"      [FAIL] 处理失败: {e}")
    finally:
        pass

    print(f"\n处理完成。共 {total} 个文件，成功刷新 {success} 个。")
    return True


def main():
    """主函数"""
    print("=" * 60)
    print("AG日报数据刷新工具")
    print(f"数据目录: {DATA_DIR}")
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 检查数据新鲜度
    is_fresh = check_data_freshness()

    # 刷新Excel文件
    if "--check-only" not in sys.argv:
        refresh_excel_files()

    # 总结
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)

    if not is_fresh:
        print("⚠️  部分数据文件需要更新")
        print("   请从Wind客户端导出最新数据后再运行 run_all.py")
        print("\n   请打开并刷新 data/白银所有数据.xlsx 中的全部 Wind 工作表")
    else:
        print("✅ 数据文件正常，可以运行 run_all.py 生成最新图表")


if __name__ == "__main__":
    main()
