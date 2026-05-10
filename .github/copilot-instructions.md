# Copilot Instructions for NTE-auto-fish

## Project Summary

NTE-auto-fish is a visual auto-fishing bot for a game. It captures screen regions, uses OpenCV HSV color detection to identify game elements (cursor, safe zone bar, bite-trigger button), and sends simulated keyboard input via PyDirectInput to automatically catch fish. The bot operates as a 4-state finite state machine: **IDLE -> WAITING -> STRUGGLING -> RESULT -> IDLE**.

- **Language**: Python 3.11+ (CI uses 3.11, type hints use `float | None` union syntax)
- **Platform**: Windows-only (pydirectinput, ctypes.windll)
- **GUI**: DearPyGui with glassmorphism dark theme
- **Entry points**: `start_gui.py` (GUI), `main.py` (headless CLI with subcommands)
- **Config**: `config.py` — nested dataclasses persisted as atomic JSON to `settings.json`

## Architecture

| Layer | Key Files | Responsibility |
|-------|-----------|----------------|
| Vision | `modules/vision.py` | HSV centroid detection, multi-scale template matching, blue pixel trigger, error region check |
| I/O | `modules/io_module.py` | Screen capture (mss), keyboard input (pydirectinput) with held-key tracking |
| Logic | `modules/logic.py` | FishingState enum, PIDController (adaptive gain, EMA derivative, anti-windup), FishingStateMachine |
| Config | `config.py` | All runtime config dataclasses (HSV, PID, ROI, Timing, Humanization, Keys, Hotkeys). Atomic JSON persistence. |
| GUI | `gui/app.py`, `gui/bridge.py` | DearPyGui shell, thread-safe queue bridge (status/log/command queues) between bot and GUI |
| GUI Pages | `gui/pages/dashboard.py`, `gui/pages/settings.py`, `gui/pages/logs.py` | Dashboard (stat cards, PID plot, visual tracker), Settings (6 category panels), Logs (filter/search) |
| GUI Theme | `gui/theme.py`, `gui/components.py` | Design system, glassmorphism widgets, styled buttons |
| Bot Core | `main.py` (~990 lines) | NTEFishingBot class, FSM loop, calibration, CLI args, DPI awareness, auto-deps |
| Tools | `tools/ratio_annotator.py` | Standalone utility for creating ratio-based ROI JSON from screenshots |

## Code Conventions

- **Linting**: flake8 with `max-line-length = 120`, extends-ignore E203/E221/E241/E272 (see `.flake8`)
- **Type checking**: mypy with `ignore_missing_imports = True` (see `mypy.ini`)
- **Commits**: Must follow [Conventional Commits](https://www.conventionalcommits.org/) — enforced by commitlint in CI. Allowed types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `ci`, `build`, `chore`, `revert`. Subject max length: 100.
- **No co-author lines** in commits
- **Never commit `CLAUDE.md`** — leave it untracked

## Key Patterns to Watch in PRs

### Thread Safety
The bot runs in a daemon thread, GUI on the main thread. Communication goes through `gui/bridge.py` using thread-safe queues (status, log, command). The stop command is urgent and drains stale commands. When reviewing changes to bot or GUI code, verify that cross-thread communication uses the bridge, not direct shared state.

### Config Dataclasses
All runtime config lives in `config.py` as nested dataclasses (`AppConfig`). Changes are persisted atomically (write to `.tmp`, then `os.replace`). If a PR adds new settings, they must follow this pattern and be added to the correct sub-dataclass.

### Vision Module
`modules/vision.py` contains static methods for computer vision. Tests in `tests/vision/` use real screenshot fixtures in `tests/vision/data/`. When reviewing vision changes, check that corresponding test fixtures exist.

### GUI Error Handling
Never use `print()` for user-visible errors in the GUI. Errors must be proxied through `gui/bridge.py` so the user sees notifications in the GUI.

### Humanization
The bot includes configurable humanization (`HumanizationConfig` in config.py) with `jitter()`, `sample_reaction()`, and `sample_noise()` helpers. Timing values use natural variation to appear more human-like.

## Testing

```bash
python -m unittest discover -s tests -v
```

This is the command CI runs. Tests cover vision pipeline outcomes using screenshot fixtures. When adding vision features, include test screenshots in `tests/vision/data/`.

## CI Pipelines

1. **build.yml** — "Release and Build": Runs on PRs and pushes to main. Executes tests, builds PyInstaller EXE, packages CLI ZIP. Uses release-please for automated releases from `version.txt`.
2. **commitlint.yml** — "Lint Commit Messages": Runs on PRs. Lints commit messages against Conventional Commits using Node.js 20.

## PyInstaller Build

The CI builds the GUI EXE with this command (authoritative — match it exactly):

```bash
pyinstaller --noconfirm --onefile --windowed --icon=NONE \
  --add-data "templates;templates" \
  --add-data "version.txt;." \
  --exclude-module tkinter --exclude-module unittest --exclude-module test \
  --exclude-module email --exclude-module http --exclude-module xml \
  --exclude-module pydoc --exclude-module multiprocessing --exclude-module asyncio \
  --exclude-module sqlite3 --exclude-module lib2to3 --exclude-module distutils \
  --exclude-module setuptools --exclude-module _decimal --exclude-module _lzma \
  --exclude-module _bz2 \
  --name NTE-Auto-Fish start_gui.py
```

## Review Checklist

When reviewing PRs, verify:
- Commit messages follow Conventional Commits
- New config fields follow the dataclass pattern in `config.py`
- GUI errors go through `gui/bridge.py`, not `print()`
- Vision changes have corresponding test fixtures in `tests/vision/data/`
- Cross-thread code uses the bridge queues
- No breaking changes without documentation
