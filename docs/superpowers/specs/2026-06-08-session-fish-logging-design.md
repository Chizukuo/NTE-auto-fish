# Session Fish Logging — Design Spec
**Date:** 2026-06-08

## Overview
Split the existing flat `catch_log.csv` into per-session files and add a scrollable session manager UI in the Fish Logging section of the Vision & Detection settings tab. Each session corresponds to one Start → Stop bot cycle.

---

## Data Layer

### Storage layout
```
APP_DIR/
  sessions/
    index.json
    session_20260608_143205.csv
    session_20260608_151042.csv
    ...
```

### `index.json` schema
```json
[
  {
    "id": "session_20260608_143205",
    "start": "2026-06-08 14:32:05",
    "fish_count": 12,
    "filename": "session_20260608_143205.csv"
  }
]
```
Most-recent session is last. The index is rebuilt from disk files if it is missing or corrupt.

### Session CSV columns
`timestamp, fish_name, weight_g` — same as the existing `catch_log.csv`.

### Lifecycle
| Event | Action |
|---|---|
| Bot `Start` | Create `sessions/session_<YYYYMMDD_HHMMSS>.csv`, add entry to index with `fish_count: 0`, save index |
| Each catch | Append row to active CSV; increment `fish_count` in active index entry; save index |
| Bot `Stop` | Flush + close active CSV file handle |

### Backwards compatibility
The old flat `catch_log.csv` is left untouched; no migration required.

---

## New module: `modules/session_manager.py`

Responsibilities:
- `SessionManager` class owns the sessions folder, index file, and the active session's open file handle + writer
- `start_session() -> SessionMeta` — creates the file, updates index, returns metadata
- `append_catch(name, weight_g)` — writes row, increments fish_count, saves index
- `end_session()` — flushes and closes file handle
- `load_sessions() -> list[SessionMeta]` — reads index, rebuilds from files if needed
- `delete_session(session_id)` — removes CSV file and index entry
- `export_session(session_id, path, fmt)` — writes CSV / JSON / XLSX at `path`

`SessionMeta` is a small dataclass: `id`, `start`, `fish_count`, `filename`.

XLSX export uses `openpyxl`. Added to `requirements.txt`.

---

## UI changes (`gui/pages/settings.py`)

### Fish Logging section additions (inside `_build_vision_settings`)
Below the existing checkbox and button, add:
- Section label "Sessions"
- `dpg.child_window` (scrollable, fixed height `~180px`, tag `session_list_window`) containing one row per session
- Each row: label `"● YYYY-MM-DD HH:MM · N fish"` (bullet only for active session) + `[Delete]` (danger) + `[Export ▾]` (neutral)

### Export flow
Export button opens a small DPG modal with three buttons: **CSV**, **JSON**, **XLSX**. Picking one opens `tkinter.filedialog.asksaveasfilename` (in a daemon thread), then writes the file via `SessionManager.export_session`.

### Refresh trigger
`_rebuild_session_list()` — clears and repopulates `session_list_window`. Called:
- When the Vision & Detection tab is shown
- After any delete
- During `update_settings_ui` to update the active session's fish count label (only when the bot is running)

---

## `main.py` changes

- Instantiate `SessionManager` in `NTEFishingBot.__init__`
- In `prepare_for_run`: call `session_manager.start_session()`
- In `_append_catch`: delegate to `session_manager.append_catch(name, weight_g)` instead of writing to `catch_log.csv` directly (keep existing `_last_fish_name`/`_last_fish_weight_g` cache updates)
- In `request_stop`: call `session_manager.end_session()`

---

## Dependencies
- `openpyxl` — add to `requirements.txt` for XLSX export
