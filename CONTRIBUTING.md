# Contributing to NTE Auto-Fish

Thanks for your interest in contributing! This guide will help you get started.

## Prerequisites

- **Windows** (required — uses `pydirectinput` and `ctypes.windll`)
- **Python 3.11+**
- **Elevated terminal** (administrator privileges for input simulation)
- A running copy of the game for manual testing

## Setup

```bash
git clone https://github.com/Chizukuo/NTE-auto-fish.git
cd NTE-auto-fish
pip install -r requirements.txt
```

Run the bot:

```bash
python start_gui.py   # GUI mode (recommended)
python main.py        # Headless / CLI mode
```

## Project Architecture

The bot is a 4-state finite state machine: **IDLE → WAITING → STRUGGLING → RESULT → IDLE**

| Layer | Files | Responsibility |
|---|---|---|
| Vision | `modules/vision.py` | HSV centroid detection, blue pixel threshold, error region analysis |
| I/O | `modules/io_module.py` | Screen capture (`mss`), keyboard input (`pydirectinput`) |
| Logic | `modules/logic.py` | State machine, PID controller |
| Config | `config.py` | Dataclass config, atomic JSON persistence |
| GUI | `gui/` | DearPyGui with sidebar navigation, dashboard, settings, logs |

## Code Style

- **flake8** with `max-line-length = 120`
- **mypy** with `ignore_missing_imports = true`
- Follow existing patterns in the codebase

Install dev tools (not included in `requirements.txt`):

```bash
pip install flake8 mypy
```

Run linting locally:

```bash
flake8 .
mypy .
```

## Commit Convention

All commits must follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add multi-cast support
fix: reset error counter on resume
docs: update calibration instructions
ci: add commitlint workflow
```

This is enforced by commitlint in CI and required for release-please to generate changelogs.

## Development Tools

- `tools/ratio_annotator.py` — Standalone Tkinter utility for creating ratio-based ROI JSON from screenshots. Use this when calibrating screen regions for new resolutions.

## Running Tests

```bash
python -m unittest discover -s tests -v
```

Vision tests use real screenshots in `tests/vision/data/`. When adding vision features, include test screenshots.

## Submitting a Pull Request

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes with clear, conventional commits
4. Run tests and ensure they pass
5. Open a PR against `main`
6. Fill in the PR template

## Reporting Bugs

Use the [Bug Report](https://github.com/Chizukuo/NTE-auto-fish/issues/new?template=bug_report.md) issue template. Include your `settings.json`, screen resolution, and steps to reproduce.
