<div align="center">

# NTE Auto-Fishing

[English](README.md) | [简体中文](docs/README_zh.md) | [日本語](docs/README_ja.md)

**A visual, configurable auto-fishing assistant built for responsive game control.**

Built with Python, OpenCV, MSS, PyDirectInput, and DearPyGui.

---

[![GitHub License](https://img.shields.io/github/license/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/blob/main/LICENSE)
[![GitHub Release](https://img.shields.io/github/v/release/Chizukuo/NTE-auto-fish)](https://github.com/Chizukuo/NTE-auto-fish/releases)
[![Build Status](https://github.com/Chizukuo/NTE-auto-fish/actions/workflows/build.yml/badge.svg)](https://github.com/Chizukuo/NTE-auto-fish/actions)

</div>

## Highlights

- **Live control center**: Track bot state, fish count, session time, FPS, PID output, ROI data, and vision health in one GUI.
- **Safer controls**: The GUI starts paused, handles stop commands urgently, and releases held keys during pause, stop, recalibration, and shutdown.
- **Runtime tuning**: PID, HSV thresholds, timing, input keys, hotkeys, calibration, and debug options can be adjusted from the Settings tab.
- **Resolution adaptation**: Multi-scale template matching and ratio-based fallback support common 1080p, 2K, 4K, and custom display sizes.
- **Fast capture and input**: `mss` captures screen regions efficiently, while `PyDirectInput` sends game-friendly input events.
- **Portable builds**: GitHub Actions builds single-file Windows executables for GUI and CLI workflows.

## Project Structure

| Path | Description |
| :--- | :--- |
| `start_gui.py` | Recommended GUI entry point. |
| `main.py` | Headless entry point and core bot loop. |
| `config.py` | Runtime configuration for PID, HSV, keys, timing, and calibration. |
| `gui/` | DearPyGui control center, panels, and thread-safe bridge. |
| `modules/` | Capture, input, vision, and fishing logic modules. |
| `templates/` | Optional template and ratio data for calibration. |
| `tools/ratio_annotator.py` | Utility for creating ratio-based ROI JSON from screenshots. |

## Getting Started

### Option 1: Prebuilt Executable

1. Download the latest `NTE-Auto-Fish.exe` from [Releases](https://github.com/Chizukuo/NTE-auto-fish/releases).
2. Run it as Administrator so simulated input can reach the game.
3. Optional: place `button_f.png` and `bar_icon_left.png` in a `templates/` folder next to the executable for more precise calibration.

### Option 2: Run From Source

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

---

<div align="center">
Built for practical, low-friction automation.
</div>
