<div align="center">

# NTE 自动钓鱼

[English](../README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md)

**面向实时游戏控制的可视化、可调校自动钓鱼助手。**

基于 Python、OpenCV、MSS、PyDirectInput 和 DearPyGui 构建。

---

[![GitHub License](https://img.shields.io/github/license/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/blob/main/LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/releases)
[![Build Status](https://github.com/Chizukuo/NTE-auto-fish/actions/workflows/build.yml/badge.svg)](https://github.com/Chizukuo/NTE-auto-fish/actions)

</div>

## 项目亮点

- **实时控制台**：在 GUI 中查看状态、钓获数、会话时长、FPS、PID 输出、ROI 数据和视觉追踪健康度。
- **更安全的控制流程**：界面启动后默认暂停；停止命令优先处理；暂停、停止、校准和退出时会释放已按住的按键。
- **运行时调参**：PID、HSV 阈值、时序、输入按键、全局热键、校准和调试选项都可以在设置页调整。
- **分辨率自适应**：结合多尺度模板匹配与比例回退数据，适配 1080p、2K、4K 以及更多自定义分辨率。
- **高效截图与输入**：使用 `mss` 捕获屏幕区域，使用 `PyDirectInput` 发送更适合游戏环境的输入事件。
- **便携构建**：GitHub Actions 会生成 GUI 和 CLI 两个单文件 Windows 可执行程序。

## 项目结构

| 路径 | 说明 |
| :--- | :--- |
| `start_gui.py` | 推荐的 GUI 启动入口。 |
| `main.py` | 无界面入口和核心运行循环。 |
| `config.py` | PID、HSV、按键、时序和校准配置。 |
| `gui/` | DearPyGui 控制中心、面板和线程安全桥接。 |
| `modules/` | 截图、输入、视觉识别和钓鱼逻辑模块。 |
| `templates/` | 可选模板和比例数据，用于校准。 |
| `tools/ratio_annotator.py` | 从截图标注比例 ROI 的辅助工具。 |

## 快速开始

### 方式一：使用预构建程序

1. 从 [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases) 下载最新的 `NTE-Auto-Fish.exe`。
2. 以管理员身份运行，确保模拟输入可以进入游戏。
3. 可选：在 EXE 同级目录创建 `templates/` 文件夹，并放入 `button_f.png` 与 `bar_icon_left.png`，以提高校准精度。

### 方式二：从源码运行

```bash
git clone https://github.com/Chizukuo/NTE-auto-fish.git
cd NTE-auto-fish
pip install -r requirements.txt
```

启动 GUI：

```bash
python start_gui.py
```

启动无界面模式：

```bash
python main.py
```

## 注意事项

- Windows 下建议在管理员终端中运行。
- 无边框窗口或窗口化全屏通常具有更稳定的截图效果。
- 全局热键可以在 GUI 中修改，编辑后会重新注册。
- 调试日志会把额外追踪数据写入 `fishing_data.csv`。

## 已知问题

- **黄昏/日出光照干扰**：游戏内日出和日落时段的暖黄色环境光会严重干扰基于 HSV 的光标检测，导致追踪失败、钓鱼成功率大幅下降。这是当前颜色检测方案的固有局限。如遇此情况，可尝试在设置中调整光标 HSV 阈值以适配偏移后的光照条件。
