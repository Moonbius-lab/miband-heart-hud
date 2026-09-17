@echo off
rem 源码方式启动：用 pythonw 跑，不弹黑色控制台窗口。
rem 日志在 %LOCALAPPDATA%\MiBandHeartHUD\logs\app.log
rem 打包好的 exe 不需要这个脚本，双击 exe 即可。
setlocal
where pythonw >nul 2>nul
if errorlevel 1 (
  echo 找不到 pythonw，请先安装 Python 3.10 或更高版本，并把它加入 PATH。
  pause
  exit /b 1
)
start "" pythonw "%~dp0..\run.py"
endlocal
