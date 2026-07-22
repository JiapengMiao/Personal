@echo off
chcp 65001 >nul
REM 白银数据看板 - 一键更新并发布
REM 流程: 统一数据管道 → 校验/构建 → 同步docs → 提交 → 推送
cd /d "%~dp0"

echo [1/4] 运行统一更新流程...
"C:\Users\56558\AppData\Local\Programs\Python\Python312\python.exe" src\update_all.py
if errorlevel 1 ( echo [错误] 统一更新失败，未提交也未推送 & pause & exit /b 1 )

echo [2/4] 提交更新...
git add -A
git diff --cached --quiet && ( echo 无数据变化,跳过推送 & goto :end )
for /f "tokens=1-3 delims=/" %%a in ("%date%") do set TODAY=%%a-%%b-%%c
git commit -m "data: %TODAY% 每日数据更新"
if errorlevel 1 ( echo [错误] 提交失败 & pause & exit /b 1 )

echo [3/4] 推送到 GitHub...
git push origin main
if errorlevel 1 ( echo [提示] 推送失败,可能是网络问题,稍后重跑本脚本即可 )

:end
echo [4/4] 完成
echo 完成。线上地址: https://jiapengmiao.github.io/Personal/
pause
