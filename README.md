<div align="center">

# 🎣 NTE Auto-Fishing

[English](README.md) | [简体中文](docs/README_zh.md) | [日本語](docs/README_ja.md)

**A high-performance, intelligent automatic fishing bot for modern games.**

Built with Python, OpenCV, MSS, and DearPyGui.

---

[![GitHub License](https://img.shields.io/github/license/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/blob/main/LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/releases)
[![Build Status](https://github.com/Chizukuo/NTE-auto-fish/actions/workflows/build.yml/badge.svg)](https://github.com/Chizukuo/NTE-auto-fish/actions)

</div>

## 🌟 Highlights

- **Visual Control Panel (GUI)**: Real-time monitoring, PID tuning, and HSV threshold adjustment via a sleek DearPyGui interface.
- **Persistence**: Save and load settings effortlessly from the GUI; configurations are automatically applied on launch.
- **Intelligent Resolution Adaptation**: Multi-scale template matching with fallback to resolution-based coordinate estimation. Supports 1080p, 2K, 4K, and more.
- **Performance Optimized**: Ultra-fast screen capture using `mss` and precise input simulation via `PyDirectInput`.
- **Portable**: Available as a single-file executable—no Python environment or extraction required.

## 📁 Project Structure

| File/Folder | Description |
| :--- | :--- |
| `start_gui.py` | Recommended entry point for the GUI version. |
| `main.py` | Headless mode entry point and core bot logic. |
| `config.py` | Global configuration management (PID, HSV, etc.). |
| `gui/` | Interactive dashboard and setting panels. |
| `modules/` | Core functional modules: IO, Vision, and Logic. |

## 🚀 Getting Started

### Option 1: Prebuilt Executable (Recommended)
1. Download the latest `NTE-Auto-Fish.exe` from [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases).
2. **Run as Administrator** (required for input simulation).
3. (Optional) Enhance precision by placing `button_f.png` and `bar_icon_left.png` in a `templates/` folder next to the EXE.

### Option 2: Run from Source
1. **Clone & Install**:
   ```bash
   git clone https://github.com/Chizukuo/NTE-auto-fish.git
   cd NTE-auto-fish
   pip install -r requirements.txt
   ```
2. **Templates**: Place your matching templates in the `templates/` directory.
3. **Run**:
   ```bash
   # Launch GUI
   python start_gui.py
   
   # Launch Headless
   python main.py
   ```
   *Note: Always use an elevated terminal (Administrator).*

## ⚙️ Key Features

- **Dashboard**: Live telemetry including success count, runtime, and processing frequency.
- **PID Tuning**: Dynamically adjust `Kp` and `Ki` to perfect the reeling response.
- **HSV Calibration**: Calibrate color detection for Cyan (Safe Area), Yellow (Cursor), and Blue (Bite) to suit any lighting.
- **Live Logs**: Integrated logging console for real-time diagnostics.

## ⚠️ Requirements & Notes

- **Privileges**: Must run with Administrator privileges to interact with game windows.
- **Display**: Use **Borderless Window** or **Windowed Fullscreen** for optimal capture reliability.
- **CI/CD**: Fully automated builds via GitHub Actions.

---

<div align="center">
Built with high performance and reliability.
</div>
