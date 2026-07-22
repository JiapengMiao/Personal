#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单个Excel文件刷新脚本
用法: python refresh_single_excel.py <excel_file_path>
"""

import sys
import pythoncom
import win32com.client as win32

def refresh_excel(file_path):
    """刷新单个Excel文件"""
    pythoncom.CoInitialize()
    excel = None
    try:
        excel = win32.DispatchEx("Excel.Application")
        excel.Visible = False
        excel.DisplayAlerts = False
        
        # 直接打开文件，不使用多线程
        wb = excel.Workbooks.Open(file_path)
        import time
        time.sleep(3)  # 等待RTD公式刷新
        wb.Save()
        wb.Close()
        return True
    except Exception as e:
        import traceback
        print(f"Error: {str(e)}\n{traceback.format_exc()}")
        return False
    finally:
        if excel:
            try:
                excel.Quit()
            except:
                pass
        pythoncom.CoUninitialize()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python refresh_single_excel.py <excel_file_path>")
        sys.exit(1)
    
    file_path = sys.argv[1]
    success = refresh_excel(file_path)
    sys.exit(0 if success else 1)