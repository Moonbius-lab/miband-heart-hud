@echo off
rem 兼容入口：双击就能用。真正的逻辑在 build.ps1。
rem 默认打目录版（packaging\out\onedir\MiBandHeartHUD\）。
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0build.ps1" %*
