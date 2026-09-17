@echo off
rem 用 pythonw 启动，不弹黑色控制台窗口；日志在 %LOCALAPPDATA%\MiBandHeartHUD\logs\app.log
setlocal
where pythonw >nul 2>nul
if errorlevel 1 (
  echo 找不到 pythonw，请先安装 Python 3.10 或更高版本，并把它加入 PATH。
  pause
  exit /b 1
)
start "" pythonw "%~dp0run.py"
endlocal
