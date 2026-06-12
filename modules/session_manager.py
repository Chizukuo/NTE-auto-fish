"""Per-session fish catch logging with index-backed session management."""
from __future__ import annotations

import csv
import json
import logging
import os
import time
from dataclasses import asdict, dataclass
from typing import Optional

log = logging.getLogger("NTEFish")

_INDEX_FILENAME = "index.json"
_CSV_HEADER = ["timestamp", "fish_name", "weight_g"]


@dataclass
class SessionMeta:
    id: str
    start: str
    fish_count: int
    filename: str


class SessionManager:
    def __init__(self, sessions_dir: str) -> None:
        self._dir = sessions_dir
        os.makedirs(self._dir, exist_ok=True)
        self._active_meta: Optional[SessionMeta] = None
        self._csv_handle = None
        self._csv_writer = None

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def start_session(self) -> SessionMeta:
        """Create a new session file and register it in the index."""
        if self._csv_handle is not None:
            self.end_session()

        session_id = "session_" + time.strftime("%Y%m%d_%H%M%S") + "_" + os.urandom(3).hex()
        filename = f"{session_id}.csv"
        start_str = time.strftime("%Y-%m-%d %H:%M:%S")

        path = os.path.join(self._dir, filename)
        self._csv_handle = open(path, "w", newline="", encoding="utf-8")
        self._csv_writer = csv.writer(self._csv_handle)
        self._csv_writer.writerow(_CSV_HEADER)
        self._csv_handle.flush()

        meta = SessionMeta(id=session_id, start=start_str, fish_count=0, filename=filename)
        self._active_meta = meta

        sessions = self._read_index()
        sessions.append(meta)
        self._write_index(sessions)

        return meta

    def append_catch(self, name: str, weight_g: str) -> None:
        """Append a catch row to the active session and update the index."""
        if self._active_meta is None or self._csv_writer is None:
            log.debug("append_catch called with no active session — ignored.")
            return

        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        self._csv_writer.writerow([ts, name, weight_g])
        self._csv_handle.flush()

        self._active_meta.fish_count += 1
        sessions = self._read_index()
        for s in sessions:
            if s.id == self._active_meta.id:
                s.fish_count = self._active_meta.fish_count
                break
        else:
            # Index was missing or corrupt; re-insert the active session.
            sessions.append(SessionMeta(
                id=self._active_meta.id,
                start=self._active_meta.start,
                fish_count=self._active_meta.fish_count,
                filename=self._active_meta.filename,
            ))
        self._write_index(sessions)

    def end_session(self) -> None:
        """Flush and close the active session file."""
        if self._csv_handle is None:
            return
        try:
            self._csv_handle.flush()
            self._csv_handle.close()
        except Exception:
            log.debug("Failed to close session CSV.", exc_info=True)
        finally:
            self._csv_handle = None
            self._csv_writer = None
            self._active_meta = None

    # ------------------------------------------------------------------
    # Query / management
    # ------------------------------------------------------------------

    def load_sessions(self) -> list[SessionMeta]:
        """Return all sessions, newest last. Rebuilds from files if index is missing/corrupt."""
        sessions = self._read_index()
        if not sessions:
            sessions = self._rebuild_index()
        return sessions

    def delete_session(self, session_id: str) -> None:
        """Remove a session's CSV file and its index entry."""
        if session_id == self.active_session_id():
            self.end_session()

        sessions = self._read_index()
        to_delete = next((s for s in sessions if s.id == session_id), None)
        if to_delete:
            path = os.path.join(self._dir, to_delete.filename)
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                log.debug("Failed to delete session file: %s", path, exc_info=True)
            sessions = [s for s in sessions if s.id != session_id]
            self._write_index(sessions)

    def export_session(self, session_id: str, dest_path: str, fmt: str) -> None:
        """Export a session to dest_path in fmt ('csv', 'json', or 'xlsx')."""
        sessions = self._read_index()
        meta = next((s for s in sessions if s.id == session_id), None)
        if meta is None:
            raise ValueError(f"Session not found: {session_id}")

        if self._active_meta and self._active_meta.id == session_id and self._csv_handle:
            self._csv_handle.flush()

        rows = self._read_session_rows(meta.filename)

        if fmt == "csv":
            self._export_csv(rows, dest_path)
        elif fmt == "json":
            self._export_json(rows, dest_path)
        elif fmt == "xlsx":
            self._export_xlsx(rows, dest_path)
        else:
            raise ValueError(f"Unknown export format: {fmt}")

    def active_fish_count(self) -> int:
        """Return fish count for the current active session (0 if none)."""
        if self._active_meta is None:
            return 0
        return self._active_meta.fish_count

    def active_session_start(self) -> str:
        """Return the start timestamp of the active session, or empty string if none."""
        if self._active_meta is None:
            return ""
        return self._active_meta.start

    def active_session_id(self) -> Optional[str]:
        """Return the ID of the currently active session, or None."""
        if self._active_meta is None:
            return None
        return self._active_meta.id

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _index_path(self) -> str:
        return os.path.join(self._dir, _INDEX_FILENAME)

    def _read_index(self) -> list[SessionMeta]:
        path = self._index_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [SessionMeta(**entry) for entry in data]
        except Exception:
            log.debug("Failed to read session index; will rebuild.", exc_info=True)
            return []

    def _write_index(self, sessions: list[SessionMeta]) -> None:
        tmp = self._index_path() + ".tmp"
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump([asdict(s) for s in sessions], f, indent=2)
            os.replace(tmp, self._index_path())
        except Exception:
            log.debug("Failed to write session index.", exc_info=True)

    def _rebuild_index(self) -> list[SessionMeta]:
        """Scan the sessions folder and rebuild the index from CSV files."""
        sessions: list[SessionMeta] = []
        try:
            for fname in sorted(os.listdir(self._dir)):
                if not fname.startswith("session_") or not fname.endswith(".csv"):
                    continue
                session_id = fname[:-4]
                rows = self._read_session_rows(fname)
                # Parse start time from session_YYYYMMDD_HHMMSS_hex.csv
                try:
                    ts_part = session_id[len("session_"):][:15]
                    start_str = time.strftime(
                        "%Y-%m-%d %H:%M:%S",
                        time.strptime(ts_part, "%Y%m%d_%H%M%S"),
                    )
                except Exception:
                    start_str = rows[0]["timestamp"] if rows else "unknown"
                sessions.append(SessionMeta(
                    id=session_id,
                    start=start_str,
                    fish_count=len(rows),
                    filename=fname,
                ))
        except Exception:
            log.debug("Failed to rebuild session index.", exc_info=True)
        if sessions:
            self._write_index(sessions)
        return sessions

    def _read_session_rows(self, filename: str) -> list[dict]:
        path = os.path.join(self._dir, filename)
        if not os.path.exists(path):
            return []
        try:
            with open(path, newline="", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        except Exception:
            log.debug("Failed to read session CSV: %s", filename, exc_info=True)
            return []

    def _export_csv(self, rows: list[dict], dest_path: str) -> None:
        with open(dest_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=_CSV_HEADER)
            writer.writeheader()
            writer.writerows(rows)

    def _export_json(self, rows: list[dict], dest_path: str) -> None:
        with open(dest_path, "w", encoding="utf-8") as f:
            json.dump(rows, f, indent=2)

    def _export_xlsx(self, rows: list[dict], dest_path: str) -> None:
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(_CSV_HEADER)
        for row in rows:
            ws.append([row.get(col, "") for col in _CSV_HEADER])
        wb.save(dest_path)
