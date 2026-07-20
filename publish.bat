@echo off
chcp 65001 >nul
REM 白银数据看板 - 每日一键发布
REM 流程: 更新数据 JSON → 提取现货基差 → 构建前端 → 同步产物到 docs → 提交并推送
cd /d "%~dp0"

echo [1/6] 更新看板数据...
"C:\Users\56558\AppData\Local\Programs\Python\Python312\python.exe" src\build_dashboard_data.py
if errorlevel 1 ( echo [错误] 数据构建失败 & pause & exit /b 1 )

echo [2/6] 提取现货基差报价...
"C:\Users\56558\AppData\Local\Programs\Python\Python312\python.exe" src\extract_spot_quotes.py
if errorlevel 1 ( echo [错误] 现货基差提取失败 & pause & exit /b 1 )

echo [3/6] 构建前端...
cd web
"C:\Users\56558\.workbuddy\binaries\node\versions\22.22.2\node.exe" node_modules\vite\bin\vite.js build --emptyOutDir false --logLevel warn
if errorlevel 1 ( echo [错误] 前端构建失败 & pause & exit /b 1 )
cd ..

echo [4/6] 同步产物到 docs（GitHub Pages 源目录）...
if exist docs rmdir /s /q docs
mkdir docs
xcopy web\dist\* docs\ /E /I /Q >nul
if exist "docs\白银五项固定监测看板_20260719.xlsx" del /q "docs\白银五项固定监测看板_20260719.xlsx"

echo [5/6] 提交更新...
git add -A
git diff --cached --quiet && ( echo 无数据变化,跳过推送 & goto :end )
for /f "tokens=1-3 delims=/" %%a in ("%date%") do set TODAY=%%a-%%b-%%c
git commit -m "data: %TODAY% 每日数据更新"

echo [6/6] 推送到 GitHub...
git push origin main
if errorlevel 1 ( echo [提示] 推送失败,可能是网络问题,稍后重跑本脚本即可 )

:end
echo 完成。线上地址: https://jiapengmiao.github.io/Personal/
pause
