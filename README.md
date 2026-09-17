# 小米手环心率 · Windows 任务栏组件

> 任务栏组件 + 异常提醒：把小米手环的实时心率放进 Windows 任务栏，
> 打游戏时任务栏被盖住就以弹窗提醒（照 FluentFlyout 的弹窗形态做的）。

**任务栏组件**（紧跟 FluentFlyout 组件右侧；底色取任务栏自身颜色，没有白底）

![任务栏组件](docs/preview-taskbar.png)

**异常弹窗**（任务栏正上方，20px 位移 + 淡入，300ms）

![弹窗](docs/preview-flyout.png)

> 目标：在 Windows 桌面上放一个极小的、置顶的、不抢鼠标的窗口，实时显示小米手环的心率，
> 打游戏时能瞄一眼（尤其恐怖游戏 / 高心率场景），但完全不干扰操作。
>
> 状态：**全链路已验证通过**（2026-09-17）。
> 型号：**小米手环 10 NFC**（广播名形如 `Xiaomi Smart Band 10 xxxx`）。
>
> 实测结论：手环开启「心率广播」后，**不需要配对**，PC 端直接连上就能读到标准心率数据
> （19 个采样：78–84 BPM，平均 82）。任务栏组件、Windows 11 通知、弹窗均已实机跑通。
>
> **项目状态：已归档**（2026-09-17）。目标功能全部完成、代码已整理，不再继续开发。
> 原先计划的 MSIX 安装包（照 FluentFlyout 的安装方式）没有做，现成的打包脚本见
> [`packaging/README.md`](packaging/README.md)。

---

## 目录结构

```
hr_hud/        程序本体：ble(蓝牙) / taskbar(任务栏组件) / flyout(弹窗) / tray(托盘)
               toast(通知) / zones(心率区间判定) / rest(休息提醒) / win32 / widget_render
run.py         入口：python run.py [--demo | --scan | --test-alert | --address | --diag]
probe.py       链路验证：扫描手环、把心率打在控制台
assets/        图标（Fluent UI System Icons）+ 生成好的 app.ico
scripts/       源码方式启动的小脚本（用 pythonw，不弹控制台）
tools/         开发辅助：界面预览、逻辑自测、任务栏排障（见 tools/README.md）
packaging/     PyInstaller 打包（见 packaging/README.md）
docs/          预览图
```

## 快速使用

```powershell
# 1) 手环上打开：设置 → 心率广播 → 开启（不开连不上，这是硬件开关）

# 2) 先验证链路：扫描 + 打印心率
python probe.py

# 3) 正常启动（自动连接上次记住的手环）
python run.py

# 其它
python run.py --scan         # 只扫描附近设备
python run.py --demo         # 演示模式：模拟心率，不需要手环
python run.py --test-alert   # 启动后立刻发一条测试提醒

# 源码方式后台启动（不弹控制台窗口）：scripts\启动（无控制台）.bat

# 不用手环也能自查：判定逻辑 / 休息时段 / 界面渲染
python tools\test_zones.py
python tools\test_rest.py
python tools\preview_widget.py
```

启动后：

- **任务栏组件**：贴在系统托盘左边，显示实时心率和心脏颜色（绿=正常 / 橙=偏高 / 红=过高 / 蓝=偏低）
- **异常提醒**：超过 150（可调）持续 10 秒 → Windows 11 通知 + 任务栏上方的 FluentFlyout 风格弹窗
- **托盘图标**：右键菜单里可以开关组件、开关通知、改阈值、退出

配置文件：`%LOCALAPPDATA%\MiBandHeartHUD\config.json`
日志文件：`%LOCALAPPDATA%\MiBandHeartHUD\logs\app.log`

### 界面设计

- **图标**：统一用微软官方 **Fluent UI System Icons**（MIT），源文件在 `assets/icons/`，
  渲染前替换 SVG 里的填充色，所以同一个文件能出任意颜色的图标。
- **任务栏组件**：默认贴在任务栏**左侧**，紧跟 FluentFlyout 的任务栏组件右边，
  每次刷新都会重新读取它的位置自动避让，两边不会重叠。
  组件宽度跟着数字长度走（两位数 59px、三位数 72px），不会空一大截。
  想挪回系统托盘左边，把配置里的 `widget_side` 改成 `"right"`。
- **弹窗**：极简版——爱心图标 + "心率" + 数值。没有底色块、没有单位、没有副标题，
  数值按心率区间变色（绿=正常 / 红=过高 / 蓝=偏低）。
- **颜色**：深浅色跟随系统主题（运行中也会跟，每 10 秒检查一次）；
  爱心统一用固定红色（配置里的 `heart_color` 可改），心率数值保留功能色。

### ⚠️ 游戏里能不能看到

任务栏在**独占全屏 / 无边框全屏**下会被游戏盖住，所以打游戏时**任务栏组件看不见**。
这是任务栏方案的天花板，不是 bug。想游戏内可见需要另加一个"角落悬浮窗"（见 §6.5）。

---

## 0. 一句话结论

链路本身是成熟的：手环开「心率广播」→ 走标准 BLE 心率服务 `0x180D / 0x2A37` → PC 端订阅通知 → 悬浮窗显示。

自研一个这样的窗口大约 **半天到一天**，技术栈本机已验证可用（Python 3.14 + bleak + PySide6 全部有对应轮子）。
另外 GitHub 上已经有几款现成的同类工具，**建议先花 10 分钟用手环实测链路，再决定是直接用现成工具还是自研**。

最大的不确定性不在 PC 端，而在**手环型号/固件是否真的开放了标准广播**（见 §8 风险 R1、R2）。

---

## 1. 需求与验收标准

| 编号 | 需求 | 验收方式 |
|---|---|---|
| N1 | 显示实时心率（BPM），大字可读 | 数值随活动变化，延迟 ≤ 2 秒 |
| N2 | 窗口极小，只在角落占一点地方 | 默认 ≈ 120×64 px，可调字号 |
| N3 | 不挡鼠标操作 | 点击穿透开启后，鼠标点窗口位置能直接落到游戏上 |
| N4 | 不被游戏盖住（非独占全屏时） | 游戏无边框窗口化模式下，悬浮窗始终可见 |
| N5 | 不抢焦点、不误触 Alt+Tab | 不出现在任务栏/Alt+Tab 列表，点击不激活 |
| N6 | 对游戏帧率影响可忽略 | 更新频率 ~1 Hz，CPU 占用 ≈ 0 |
| N7 | 掉线能自愈 | 手环走远/熄屏后自动重连，界面显示灰色 `--` |
| N8 | 记得住设置 | 位置、字号、颜色、上次连接的设备持久化到 json |
| N9 | 一键开关 | 托盘图标 + 全局热键显示/隐藏、切换穿透 |

**明确不做**（高风险、易被反作弊盯上）：不注入游戏进程、不做 DirectX/Vulkan Hook 覆盖层。
「置顶的普通窗口」这一做法本身是安全的。

---

## 2. 环境勘察（本机实测结果）

| 项目 | 实测 | 对方案的影响 |
|---|---|---|
| Windows | 11，Build **22000.2538**（21H2） | 支持 `Windows.Devices.Bluetooth` WinRT API，无阻碍 |
| Python | **3.14.0**，`C:\Users\Administrator\AppData\Local\Programs\Python\Python314\python.exe`，pip 25.2 可用 | 主推语言 |
| bleak（BLE 库） | PyPI 3.0.2，纯 Python，`>=3.10` | ✅ 可装 |
| winrt-Windows.Devices.Bluetooth | PyPI 3.2.1，**有 cp314 win_amd64 轮子** | ✅ BLE 后端可用，不用降级 Python |
| PySide6 | PyPI 6.11.2，**cp310-abi3 win_amd64 轮子**（abi3 向上兼容 3.14） | ✅ 透明/穿透窗口有专业控件 |
| tkinter | 3.14 自带 | 备用零依赖 UI |
| Node / npm | v26.4.0 / 11.17.0 | 不推荐（Electron 太重，违背"不干扰游戏"） |
| .NET | 只有 **运行时** 6.0 / 8.0，**没有 SDK** | 走 C# 路线需先 `winget install Microsoft.DotNet.SDK.8` |
| gh CLI | 已装但 token 失效 | 联网走 curl/Invoke-RestMethod 即可 |

---

## 3. 数据链路

```
小米手环                    PC（Windows）
┌──────────┐    BLE 广播    ┌─────────────────────────────┐
│ 设置 →    │ ────────────→ │ bleak 扫描 0x180D           │
│ 心率广播  │               │   └ 订阅 0x2A37 notify      │
│ 开启      │               │        └ BPM ──→ 悬浮窗渲染  │
└──────────┘   约 1 次/秒   └─────────────────────────────┘
```

要点：

1. 手环必须**主动开启「心率广播」**（手环设置里，不是 App；不同型号路径略有差异：设置 → 心率广播 → 开启）。
   这是硬件开关，不开一律连不上。
2. 广播内容就是标准 GATT 心率服务：service `0x180D`、characteristic `0x2A37`（Heart Rate Measurement）。
   大部分设备 1 Hz 上报一次，完全够用，也决定了悬浮窗不需要高频刷新。
3. 开启广播期间，手环**自身不再记录心率/血氧等数据**，且持续广播会明显耗电 —— 不用时记得关。
4. 广播可以与手机 App（小米运动健康）同时连接，互不挤占。

---

## 4. 现成方案（已按项目约定先查 GitHub）

| 项目 | 星 | 技术 | 形态 | 对本需求的适配 |
|---|---|---|---|---|
| [HoshinoSuzumi/HeartBeatCat](https://github.com/HoshinoSuzumi/HeartBeatCat) | 123 | Tauri/Rust | Windows 安装包，悬浮窗 + OBS 插件 | 生态最成熟，但 README 实测表明确写着「**小米手环全系列 ❌ 有加密**」，主要支持华为/三星/佳明 |
| [Tnze/miband-heart-rate](https://github.com/Tnze/miband-heart-rate) | 143 | Rust | 命令行 / OBS Demo，**无悬浮窗** | 明确支持**小米手环 10（含 NFC）**，可作链路验证参考；issue #5 记录了手环 9 在 Linux 上 `ATT 0x0e`（加密/需配对）的坑 |
| [HardToThinkAUsername/band-heart-rate-display](https://github.com/HardToThinkAUsername/band-heart-rate-display) | 0 | Python + bleak + PySide6 | **透明数字 HUD + 点击穿透 + 托盘，有 exe 发布**（MIT） | 形态和需求几乎一模一样，可直接拿来验证/急用；但 0 星新项目，建议先读源码再运行 |
| [GenmetsuWenxuePress/miband-heartbeat-hud](https://github.com/GenmetsuWenxuePress/miband-heartbeat-hud) | 0 | Python + PyQt6 | 悬浮卡片 + 心电波形 + 阈值闪烁 + 便携 exe（GPL-3.0） | 功能最全，README 甚至专门提到"打恐怖游戏"；同样 0 星，注意来源 |
| [ChaYeWuu/Hyper-Heartrate](https://github.com/ChaYeWuu/Hyper-Heartrate) | 3 | Java | Minecraft Fabric Mod | 只做 MC 内显示，不通用 |
| [PaysNatal/pulsecast](https://github.com/PaysNatal/pulsecast) | 0 | Rust + Tauri | 桌面端采集 + 推流 OBS/手机 | 偏直播推流，非游戏内轻量悬浮 |
| [Rexios80/hds_overlay](https://github.com/Rexios80/hds_overlay) | 151 | Dart | OBS 浏览器源 | 数据源是 Apple Watch，不适配手环 |

**结论**：现成工具里没有"既支持小米手环 10 系广播、又是游戏用轻量悬浮窗"的成熟项目。
0 星的那两个形态最贴合需求但来路不明，123 星的 HeartBeatCat 对手环支持存疑。

---

## 5. 三条技术路线

| | 路线 A：Python 自研（推荐） | 路线 B：C# / .NET 8 WPF | 路线 C：直接用现成 exe |
|---|---|---|---|
| 依赖 | `pip install bleak PySide6`（约 150 MB） | 先装 .NET 8 SDK（约 200 MB） | 无 |
| 代码量 | ~250 行 | ~400 行 | 0 |
| 上手时间 | 半天～1 天 | 1～2 天 | 10 分钟 |
| 悬浮窗能力 | PySide6 原生支持逐像素透明 + `WindowTransparentForInput` + `WindowDoesNotAcceptFocus` | Win32 扩展样式，最可控（`WS_EX_TRANSPARENT/NOACTIVATE/TOOLWINDOW/LAYERED`） | 看作者实现 |
| 体积/内存 | exe 打包后较大（PyInstaller），源码运行约 60 MB 内存 | 单文件 exe 约 10～20 MB，内存小 | — |
| 可维护/可改造 | 高（我们自己的代码，随便加功能） | 最高 | 最低（改不了，只能提 issue） |
| 风险 | 中等（依赖包版本） | 低 | **不明来源的 exe 有安全风险** |

**推荐：先用路线 C 里的任一工具做 10 分钟链路验证（只验证，不长期用），链路确认后走路线 A 自研。**
理由：这类工具的核心难点就是"能否连上你的手环"，先用手边现成的验证最省时间；
但长期要"完全不干扰游戏"需要一个我们能随时调参数、随时改行为的自己人版本。

---

## 6. 推荐路线 A 的详细设计

### 6.1 窗口形态

```
┌─────────────────────────────┐  ← 游戏画面（无边框窗口化）
│                             │
│                    ╭──────╮ │
│                    │  86  │ │  ← 悬浮窗：仅一个大字 + 小爱心
│                    ╰─❤────╯ │     半透明深色圆角底，≈120×64
│                             │     默认贴在屏幕右上角
└─────────────────────────────┘
```

- 无边框（`FramelessWindowHint`）、置顶（`WindowStaysOnTopHint`）、不进任务栏（`Qt.Tool`）
- 不抢焦点（`WindowDoesNotAcceptFocus` + `WS_EX_NOACTIVATE`），点击穿透可切换（`WindowTransparentForInput` + `WS_EX_TRANSPARENT`）
- 背景为半透明深色（可设 0% = 纯数字悬浮），数字颜色按心率分级：绿 <140 / 橙 140-169 / 红 ≥170 / 蓝过低
- 断连时显示灰色 `--`，重连中显示闪烁 `…`
- 拖动：穿透开启时按 `Alt` 拖动，或用托盘菜单选四个角落，位置写进配置

### 6.2 "不干扰游戏"对策清单（核心）

| 干扰源 | 对策 |
|---|---|
| 窗口抢鼠标点击 | 默认开启点击穿透，鼠标事件直达游戏 |
| 窗口抢键盘焦点 / 打断游戏输入 | `WS_EX_NOACTIVATE` + `WindowDoesNotAcceptFocus`，全程不激活 |
| 误触 Alt+Tab 切出游戏 | 窗口不进任务栏、不进 Alt+Tab（`WS_EX_TOOLWINDOW`） |
| 全屏被游戏盖住 | 游戏设「无边框窗口化 / 窗口化」。**独占全屏下任何非注入覆盖层都看不见**，这是 Windows 限制 |
| 掉帧 / 卡顿 | 只在 BPM 变化时重绘；UI 定时器 200 ms，数据源 ~1 Hz；进程不设高优先级 |
| 被反作弊判定 | 纯顶层窗口，不注入、不 Hook、不改游戏内存；不做 DirectX overlay |
| HDR 下颜色发灰 | 游戏开 HDR 时 SDR 覆盖层颜色会被映射，建议用高对比白色，或游戏内关 HDR |
| 多显示器位置错乱 | 记住"屏幕序号 + 相对坐标"，换分辨率时钳制回可见区域 |
| 忘记关闭、白耗手环电 | 托盘一键断开；退出程序时提示"请顺手关闭手环心率广播" |

### 6.3 连接与容错

- 扫描时按 service UUID 过滤，同时列出**所有**广播 `0x180D` 的设备（避免只认设备名前缀）
- 首次连接成功后保存设备地址，下次直接定向重连（比全量扫描快很多）
- **静默看门狗**：8 秒没收到通知 → 判定掉线 → 指数退避重连（1s/2s/4s/8s…，上限 30s）
- 若连接报错 `ATT 0x0e`（认证不足）或多设备排队：提示"请在 Windows 蓝牙设置中先配对/移除该设备后重试"
- 不要在扫描阶段反复"连接测试"设备（会打断手环的广播状态，这是已知坑）
- 写日志到 `%LOCALAPPDATA%\MiBandHeartHUD\logs`，连不上时有据可查

### 6.4 配置与自启

配置文件 `%LOCALAPPDATA%\MiBandHeartHUD\config.json`：

```json
{
  "device_address": "XX:XX:XX:XX:XX:XX",
  "device_name": "Xiaomi Smart Band 10",
  "screen": 0, "x": 1750, "y": 40,
  "font_size": 56, "opacity": 0.85,
  "click_through": true, "color_mode": "auto",
  "hotkey_toggle": "Ctrl+Alt+H", "hotkey_clickthrough": "Ctrl+Alt+C"
}
```

开机自启：快捷方式放进 `shell:startup`（可选），并带 `--tray` 静默启动不出窗口。

### 6.5 显示形态：角落悬浮窗 / 任务栏组件 / 托盘图标

三种落点可以同时做进同一个程序，用一个热键轮流切换。

**① 游戏内角落悬浮窗**（§6.1 的方案）—— 唯一能在全屏游戏里被看见的形态。

**② 任务栏组件**（= FluentFlyout 的 "Taskbar widget" 做法）

先讲一个事实：Windows 11 已经砍掉了自定义任务栏工具栏（DeskBand），所以"官方方式"没有。
FluentFlyout 用的是**把窗口认领成任务栏的子窗口**这个办法（我读了它的 `TaskbarWindow.xaml.cs`，流程如下）：

1. `FindWindow("Shell_TrayWnd")` 找到主任务栏窗口（多显示器用 `Shell_SecondaryTrayWnd` 或枚举找）
2. 把自己窗口的样式从 `WS_POPUP` 改成 `WS_CHILD`
3. `SetParent(自己的 hwnd, 任务栏 hwnd)` —— 成为任务栏的子窗口，跟任务栏一起移动/隐藏
4. 在任务栏客户区里计算位置，并用 `SetWindowRgn` 裁剪成想要的形状
5. 1.5 秒轮询自愈：Explorer 重启、DPI 变化、任务栏句柄变化时重新挂载
   （它还专门屏蔽了 `WM_GETOBJECT` / `WM_NCCALCSIZE` 等消息，防止拖累整个任务栏卡死）

Python 侧用 ctypes 调 `SetParent` / `SetWindowLongPtr` / `SetWindowPos` / `CreateRectRgn` 就能复刻同一套流程。
代价：比悬浮窗脆弱一些 —— Explorer 重启或系统大版本更新后可能失效，需要自愈逻辑和托盘兜底。

**③ 托盘图标直接显示心率** —— 把 BPM 渲染成图标（16/24/32 px），颜色按区间变（绿/橙/红），鼠标悬停显示精确数值。
最稳、零技巧、永远不干扰任何东西。缺点：100% 缩放下托盘图标只有 16 px，两位数勉强清晰、三位数就糊了，
所以建议用"颜色表达区间 + 悬停看精确值"。

> ⚠️ **打游戏时能不能看见，这是关键区别**：
> 独占全屏和无边框全屏下，任务栏和托盘都会被游戏盖住或隐藏，**②③ 都看不见，只有 ① 能看见**。
> 所以推荐组合：**平时挂在任务栏/托盘当常驻信息，打游戏时切到角落悬浮窗**（同一进程、热键切换）。

---

## 7. 分阶段实施计划

### M0 · 链路验证（30 分钟，**必须先做**）

写一个 30 行的 `probe.py`（bleak）：扫描并打印所有含 `0x180D` 的设备 → 连上 → 订阅 `0x2A37` → 控制台持续打印 BPM。

验收：
- 能看到自己的手环出现在列表里（名称 + 地址）
- 控制台数值随活动变化，静止 60~90 BPM、活动后升高

如果这一步失败 → 直接跳到 §8 风险 R1/R2，不要继续写 UI。

### M1 · 悬浮窗 MVP（半天）

PySide6 悬浮窗：大字 BPM + 置顶 + 无边框 + 半透明 + 可拖动 + 位置记忆 + 点击穿透开关 + 托盘菜单（显示/隐藏/退出）。

验收：N1 N2 N3 N4 N5。

### M2 · 打磨（半天）

不抢焦点、进不了 Alt+Tab、全局热键、心率颜色分级、断连灰显 + 自动重连、阈值闪烁提醒、日志。

验收：N6 N7 N8 N9 + 实机打一局游戏全流程体验无感。

### M3 · 可选增强

- PyInstaller 打包单文件 exe + 开机自启
- 本地 HTTP/WebSocket 接口（给 OBS 浏览器源、手机看）
- 心率历史曲线与简单统计（当局最高/平均）
- 阈值语音/系统通知提醒

---

## 8. 已知风险与预案

| 编号 | 风险 | 证据/来源 | 预案 |
|---|---|---|---|
| R1 | **手环型号/固件不支持标准广播** | 型号已确认：**小米手环 10 NFC**；[Tnze/miband-heart-rate](https://github.com/Tnze/miband-heart-rate) 明确标注 "Tested on MiBand10/NFC" ✅ | 风险已大幅下降，仍以 M0 实测为准（HeartBeatCat 那张"小米全系 ❌ 有加密"的表大概率是 10 代之前的结论） |
| R2 | 手环需要配对/加密，PC 端连上但读不到数据 | Tnze issue #5：手环 9 在 Linux 上 `ATT error 0x0e` | 先在 Windows 设置→蓝牙里**配对**该设备；仍失败则删除设备重配；这类错误 M0 就会暴露 |
| R3 | 开启广播后手环不再记录心率数据、耗电快 | band-heart-rate-display 使用说明 | 只在打游戏时开；用完随手关 |
| R4 | 独占全屏游戏里看不到 | miband-heartbeat-hud README 明确说明 | 游戏改「无边框窗口化」；多数现代游戏本来就是 |
| R5 | 现成 0 星 exe 安全风险 | 两个最贴合的项目均 0 星 | 只用于 M0 验证，或先读源码；长期用自研版本 |
| R6 | 蓝牙被手机 App / 其他软件抢占 | 社区 FAQ | 保持单实例；必要时先断开手机 App 再连 PC |
| R7 | 多显示器/分辨率变化导致窗口跑到屏幕外 | 通用 | 启动时钳制到主屏可见区域 + 托盘"重置位置" |
| R8 | 任务栏组件在 Explorer 重启/系统更新后失效 | FluentFlyout 源码里为此专门写了重新挂载与自愈逻辑 | 1.5 秒轮询 + 句柄变化检测重新挂载；托盘图标作为兜底显示 |

---

## 9. 待确认

1. ~~手环型号~~ **已确认：小米手环 10 NFC** —— 对应 M0 大概率一次通过。
2. 手环上**是否已经能打开「心率广播」开关**（设置 → 心率广播）。
3. 显示偏好（可多选）：任务栏组件 / 角落悬浮窗 / 托盘图标数字。
4. 打游戏时只要数字，还是也要阈值闪烁提醒和心电小波形？（影响 M1 的 UI 复杂度）

---

## 10. 参考链接

- bleak（Python BLE 库）：https://github.com/hbldh/bleak
- Bluetooth SIG 心率服务规范（0x180D / 0x2A37）：https://www.bluetooth.com/specifications/specs/heart-rate-service-1-0/
- HeartBeatCat：https://github.com/HoshinoSuzumi/HeartBeatCat
- Tnze/miband-heart-rate（小米手环 10 广播 Demo）：https://github.com/Tnze/miband-heart-rate
- band-heart-rate-display（透明数字 HUD）：https://github.com/HardToThinkAUsername/band-heart-rate-display
- miband-heartbeat-hud（悬浮卡片）：https://github.com/GenmetsuWenxuePress/miband-heartbeat-hud

---

## 11. 协议与致谢

本项目以 **GPL-3.0-or-later** 发布（见 [LICENSE](LICENSE)），
与 [FluentFlyout](https://github.com/unchihugo/FluentFlyout) 保持同一协议。

需要说明的是，任务栏组件的实现参考了 FluentFlyout 的做法，因此按同一协议开源是应有的做法：

- **窗口嵌入方式**：先按顶层窗口创建，再 `SetParent` 到 `Shell_TrayWnd` 并把 `WS_POPUP` 换成 `WS_CHILD`
  （直接以 `WS_CHILD` + 外部父窗口创建会导致鼠标输入不投递到本窗口）
- **需要吞掉的消息**：`WM_GETOBJECT` / `WM_SHOWWINDOW` / `WM_WINDOWPOSCHANGING` / `WM_NCCALCSIZE` /
  `WM_IME_SETCONTEXT` / `WM_IME_NOTIFY`，否则辅助功能工具会拖死整个任务栏
- **弹窗动画参数**：位移 20px + 透明度，300ms（其 1x 档位），进场 CubicEase EaseOut、出场 EaseIn
- **位置**：任务栏正上方、与任务栏组件水平居中

FluentFlyout 版权归 The FluentFlyout Authors 所有（GPL-3.0-or-later）。

爱心图标来自微软官方的 [Fluent UI System Icons](https://github.com/microsoft/fluentui-system-icons)（MIT），
详见 [assets/icons/NOTES.md](assets/icons/NOTES.md)。

其它依赖：bleak（MIT）、PySide6（LGPL-3.0）、winrt（MIT）、Windows 11 通知 API。
