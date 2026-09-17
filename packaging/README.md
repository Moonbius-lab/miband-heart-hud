# 打包（PyInstaller）

构建产物统一落在 `packaging/out/`（已 gitignore），仓库根目录只留源码。

| 形态 | 命令 | 产物 | 用途 |
|---|---|---|---|
| 免安装目录 | `packaging\pyinstaller\build.ps1 -Mode onedir` | `packaging/out/onedir/MiBandHeartHUD/` | 绿色版，整个目录拷走就能跑 |
| 单文件 exe | `packaging\pyinstaller\build.ps1 -Mode onefile` | `packaging/out/onefile/MiBandHeartHUD.exe` | 试用、随手分发 |
| 排障 exe | `packaging\pyinstaller\build.ps1 -Mode debug` | `packaging/out/debug/MiBandHeartHUD_dbg.exe` | 带控制台，装了没反应时看输出 |

前置：`pip install -r requirements.txt pyinstaller`。也可以直接双击 `packaging\pyinstaller\build.bat`（默认打目录版）。

```
packaging/
├── pyinstaller/    .spec × 3 + 统一入口 build.ps1 + 版本资源生成
├── cxfreeze/       cx_Freeze 备用配置，用于交叉验证"是代码还是打包器的问题"
└── out/            构建产物
```

## 版本号

只有一个来源：`hr_hud/__init__.py` 里的 `__version__`。`build.ps1` 会先跑
`make_version_info.py`，把它写成 exe 的版本资源（右键 → 属性 → 详细信息）。

## 已知坑：别让外来的 ICU DLL 混进包里

冻结后的 exe 启动时报
`无法定位程序输入点 ucnv_open 于动态链接库 ...\PySide6\Qt6Core.dll 上`，
基本都是**打包那台机器的 PATH 上有另一套 ICU**（装了 poppler / GTK / 某些 Python
图形库时很常见）：PyInstaller 顺着 `Qt6Core.dll → icuuc.dll` 的依赖，把**别人家的**
`icuuc.dll` + `icudt*.dll` 一起收进了包，跟 Qt 需要的那套对不上。

处理办法：打包前把这类目录从 PATH 里摘掉再打；打完检查
`packaging/out/onedir/MiBandHeartHUD/_internal/` 里有没有 `icuuc.dll` / `icudt*.dll`，
并用 `tools/packaging/dep_check.py` 核对导入表（`python tools/packaging/dep_check.py <_internal 目录> <某个 DLL>`）。
