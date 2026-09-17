<#
.SYNOPSIS
    打包 MiBand-Heart-HUD（PyInstaller）。

.DESCRIPTION
    产物统一落在 packaging\out\ 下，仓库根目录只留源码：
      onedir  -> packaging\out\onedir\MiBandHeartHUD\     免安装绿色版（推荐分发形态）
      onefile -> packaging\out\onefile\MiBandHeartHUD.exe 单文件试用版
      debug   -> packaging\out\debug\MiBandHeartHUD_dbg.exe 带控制台排障版
      all     -> 三种都打

.EXAMPLE
    powershell -NoProfile -ExecutionPolicy Bypass -File packaging\pyinstaller\build.ps1 -Mode onedir
#>
[CmdletBinding()]
param(
    [ValidateSet('onedir', 'onefile', 'debug', 'all')]
    [string]$Mode = 'onedir',

    # 没装进 PATH 的 Python 可以用这个参数指定，例如
    # -Python "$env:LOCALAPPDATA\Programs\Python\Python314\python.exe"
    [string]$Python = '',

    [switch]$Clean
)

$ErrorActionPreference = 'Stop'

$here = Split-Path -Parent $MyInvocation.MyCommand.Path          # ...\packaging\pyinstaller
$repo = (Resolve-Path (Join-Path $here '..\..')).Path
$out  = Join-Path $repo 'packaging\out'

function Resolve-Python {
    param([string]$Explicit)
    if ($Explicit) {
        if (-not (Test-Path -LiteralPath $Explicit)) { throw "找不到 Python：$Explicit" }
        return (Resolve-Path -LiteralPath $Explicit).Path
    }
    $candidates = @()
    $candidates += (Get-Command python.exe -ErrorAction SilentlyContinue | Select-Object -First 1).Source
    $candidates += (Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe')
    $candidates += 'C:\Python314\python.exe'
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate)) { return (Resolve-Path -LiteralPath $candidate).Path }
    }
    throw "找不到 python.exe。装好 Python 3.10+ 后用 -Python <路径> 指定，或把它加进 PATH。"
}

$pythonExe = Resolve-Python -Explicit $Python
Write-Host "仓库：$repo"
Write-Host "Python：$pythonExe"

& $pythonExe -m PyInstaller --version 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "没装 PyInstaller。先执行：`"$pythonExe`" -m pip install -r `"$repo\requirements.txt`" pyinstaller"
}

# 版本资源：exe 的"属性 → 详细信息"里那几行，跟 hr_hud\__init__.py 保持同一个来源
& $pythonExe (Join-Path $here 'make_version_info.py')
if ($LASTEXITCODE -ne 0) { throw "生成版本资源失败" }

$modes = if ($Mode -eq 'all') { @('onedir', 'onefile', 'debug') } else { @($Mode) }

foreach ($m in $modes) {
    $spec = switch ($m) {
        'onedir'  { 'MiBandHeartHUD_od.spec' }
        'onefile' { 'MiBandHeartHUD.spec' }
        'debug'   { 'MiBandHeartHUD_dbg.spec' }
    }
    $distPath = Join-Path $out $m
    $workPath = Join-Path $out ('.work\' + $m)
    Write-Host ""
    Write-Host "==> 打包 $m（$spec）" -ForegroundColor Cyan
    if ($Clean) { Remove-Item -LiteralPath $distPath, $workPath -Recurse -Force -ErrorAction SilentlyContinue }

    $args = @(
        '-m', 'PyInstaller'
        '--noconfirm'
        '--distpath', $distPath
        '--workpath', $workPath
        (Join-Path $here $spec)
    )
    & $pythonExe @args
    if ($LASTEXITCODE -ne 0) { throw "打包 $m 失败" }
}

Write-Host ""
Write-Host "完成，产物在 $out ：" -ForegroundColor Green
Get-ChildItem -LiteralPath $out -Directory | Where-Object { $_.Name -notlike '.*' } | ForEach-Object {
    $size = (Get-ChildItem -LiteralPath $_.FullName -Recurse -File -ErrorAction SilentlyContinue |
             Measure-Object Length -Sum).Sum
    Write-Host ("  {0,-10} {1,8:N1} MB" -f $_.Name, ($size / 1MB))
}
