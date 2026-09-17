# tools 目录说明

这些脚本都是"开发时用一次"的辅助工具，不参与打包（PyInstaller 只收 `run.py` 和 `hr_hud/`）。

| 脚本 | 用途 |
|---|---|
| `preview_widget.py` | 把任务栏组件在各种心率/主题下的样子渲染成 PNG 到 `tools/_preview_*.png` |
| `preview_flyout.py` | 同上，渲染异常弹窗 |
| `preview_typography.py` | 字体/字号对比图，调排版时用 |
| `test_zones.py` | 心率区间与异常判定逻辑的自测（纯逻辑，不开窗） |
| `test_toast.py` | 发一条 Windows 通知，验证通知链路 |
| `test_rest.py` | 休息提醒的时段判定自测（结果写 `tools/_rest_*.json`） |
| `dump_taskbar.py` | 打印任务栏及其子窗口的类名/矩形，定位"组件贴哪儿"的问题 |
| `inspect_widget.py` | 运行时检查自己那个组件窗口的样式、父窗口、可见区域 |
| `make_icon.py` | 从爱心 SVG 生成 `assets/app.ico`（换图标时跑一次） |
| `packaging/qt_probe.py` | 两行冒烟测试：在打包环境里能不能 import 并初始化 QtWidgets |
| `packaging/dep_check.py` | 用 pefile 解析打包产物的导入表，找"缺 DLL / 缺符号"（需要 `pip install pefile`） |

预览图、临时 json 都是 `_` 开头，已被 `.gitignore` 忽略。
