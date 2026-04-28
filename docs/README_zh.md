<div align="center">

# 🎣 NTE 自动钓鱼

[English](../README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md)

**专为现代游戏设计的高性能、智能化自动钓鱼脚本。**

基于 Python、OpenCV、MSS 和 DearPyGui 构建。

---

[![GitHub License](https://img.shields.io/github/license/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/blob/main/LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/releases)
[![Build Status](https://github.com/Chizukuo/NTE-auto-fish/actions/workflows/build.yml/badge.svg)](https://github.com/Chizukuo/NTE-auto-fish/actions)

</div>

## 🌟 项目亮点

- **可视化控制面板 (GUI)**：通过精美的 DearPyGui 界面进行实时状态监控、PID 参数微调及 HSV 颜色阈值设置。
- **持久化配置**：支持在 GUI 中保存和加载设置，启动时自动应用上次的配置。
- **智能分辨率适配**：支持多尺度模板匹配，并在匹配失败时自动回退至基于分辨率的坐标估算。完美适配 1080p、2K、4K 等多种分辨率。
- **性能优化**：使用 `mss` 实现超快截屏，并通过 `PyDirectInput` 进行精准的键鼠模拟。
- **便携性**：提供单文件可执行程序，无需安装 Python 环境或解压即可运行。

## 📁 项目结构

| 文件/文件夹 | 描述 |
| :--- | :--- |
| `start_gui.py` | GUI 模式的推荐启动入口。 |
| `main.py` | 无界面模式启动入口及核心逻辑。 |
| `config.py` | 全局配置管理（PID、HSV 等）。 |
| `gui/` | 交互式仪表盘与设置面板。 |
| `modules/` | 核心功能模块：IO、视觉及逻辑处理。 |

## 🚀 快速开始

### 方式一：使用预编译程序（推荐）
1. 从 [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases) 页面下载最新的 `NTE-Auto-Fish.exe`。
2. **以管理员身份运行**（模拟输入必须）。
3. （可选）在 EXE 同级目录下创建 `templates/` 文件夹并放入 `button_f.png` 和 `bar_icon_left.png` 以提升匹配精度。

### 方式二：从源码运行
1. **克隆并安装**：
   ```bash
   git clone https://github.com/Chizukuo/NTE-auto-fish.git
   cd NTE-auto-fish
   pip install -r requirements.txt
   ```
2. **准备模板**：将匹配模板放入 `templates/` 目录。
3. **启动**：
   ```bash
   # 启动 GUI
   python start_gui.py
   
   # 启动无界面模式
   python main.py
   ```
   *注意：请始终使用管理员权限的终端。*

## ⚙️ 核心功能

- **仪表盘 (Dashboard)**：实时显示成功次数、运行时间及处理频率等遥测数据。
- **PID 微调**：动态调整 `Kp` 和 `Ki` 参数，以获得最完美的拉杆响应。
- **HSV 校准**：支持针对青色（安全区）、黄色（游标）及蓝色（咬钩）进行颜色识别校准。
- **实时日志**：集成的日志控制台，方便进行实时诊断。

## ⚠️ 注意事项

- **权限要求**：必须以管理员权限运行，否则无法与游戏窗口交互。
- **显示设置**：建议使用**无边框窗口**或**窗口化全屏**模式，以确保截屏的稳定性。
- **自动化**：通过 GitHub Actions 实现代码推送后的自动构建。

---

<div align="center">
高性能、高可靠性的自动钓鱼工具。
</div>
