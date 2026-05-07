<div align="center">

# NTE Auto-Fishing

[English](README.md) | [简体中文](docs/README_zh.md) | [日本語](docs/README_ja.md)

**A visual, configurable auto-fishing assistant built for responsive game control.**

Built with Python, OpenCV, MSS, PyDirectInput, and DearPyGui.

---

[![GitHub License](https://img.shields.io/github/license/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/blob/main/LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/releases)
[![Build Status](https://github.com/Chizukuo/NTE-auto-fish/actions/workflows/build.yml/badge.svg)](https://github.com/Chizukuo/NTE-auto-fish/actions)
[![GitHub Stars](https://img.shields.io/github/stars/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/stargazers)

</div>

## Highlights

- **Live control center**: Track bot state, fish count, session time, FPS, PID output, ROI data, and vision health in one GUI.
- **Safer controls**: The GUI starts paused, handles stop commands urgently, and releases held keys during pause, stop, recalibration, and shutdown.
- **Runtime tuning**: PID, HSV thresholds, timing, input keys, hotkeys, calibration, and debug options can be adjusted from the Settings tab.
- **Resolution adaptation**: Ratio-based ROI calibration with resolution-proportional fallback supports 1080p, 2K, 4K, and custom display sizes automatically.
- **Fast capture and input**: `mss` captures screen regions efficiently, while `PyDirectInput` sends game-friendly input events.
- **Portable builds**: GitHub Actions produces a single-file Windows EXE for GUI and a lightweight source package for CLI that auto-installs dependencies on first run.

## Project Structure

| Path | Description |
| :--- | :--- |
| `start_gui.py` | Recommended GUI entry point. |
| `main.py` | Headless entry point and core bot loop. |
| `config.py` | Runtime configuration for PID, HSV, keys, timing, and calibration. |
| `gui/` | DearPyGui control center, panels, and thread-safe bridge. |
| `modules/` | Capture, input, vision, and fishing logic modules. |
| `templates/` | Ratio data for automatic ROI calibration. |
| `tools/ratio_annotator.py` | Utility for creating ratio-based ROI JSON from screenshots. |

## Getting Started

### Option 1: Prebuilt Executable (GUI)

1. Download the latest `NTE-Auto-Fish.exe` from [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases).
2. Run it as Administrator so simulated input can reach the game.

### Option 2: CLI Package

1. Download `NTE-Auto-Fish-CLI.zip` from [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases) and extract it.
2. Double-click `run.bat` — it checks for Python, then auto-installs missing dependencies on first run.
3. For more options, run `python main.py --help` in a terminal. Available commands: `start`, `calibrate`, `config show/set`, `reset`.

### Option 3: Run From Source

```bash
git clone https://github.com/Chizukuo/NTE-auto-fish.git
cd NTE-auto-fish
pip install -r requirements.txt
```

Launch the GUI:

```bash
python start_gui.py
```

Launch headless mode:

```bash
python main.py
```

## Notes

- Run from an elevated terminal on Windows.
- Borderless window or windowed fullscreen usually gives the most reliable capture behavior.
- Hotkeys are configurable in the GUI and re-register after editing.
- Debug logging writes extra tracking data to `fishing_data.csv`.

## Known Issues

- **Dawn/dusk lighting**: During in-game sunrise and sunset, the warm yellow ambient lighting significantly interferes with HSV-based cursor detection, causing tracking failures and drastically reduced fishing success rates. This is an inherent limitation of the current color-based detection approach. If you encounter this, consider adjusting the cursor HSV thresholds in Settings to compensate for the shifted lighting conditions.

---

<div align="center">
Built for practical, low-friction automation.
</div>
