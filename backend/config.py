"""Runtime config. Every threshold is editable at runtime via PUT /api/config so we can
retune live in front of a judge -- nothing says "this is real" like that.
"""
from __future__ import annotations
import json, os, threading
from pathlib import Path

DEFAULTS = json.loads((Path(__file__).parent.parent / "contracts" / "fixtures" / "config.json").read_text())
_STATE = json.loads(json.dumps(DEFAULTS))
_LOCK = threading.Lock()


def get() -> dict:
    with _LOCK:
        return json.loads(json.dumps(_STATE))


def update(patch: dict) -> dict:
    with _LOCK:
        _deep(_STATE, patch)
        return json.loads(json.dumps(_STATE))


def reset() -> dict:
    global _STATE
    with _LOCK:
        _STATE = json.loads(json.dumps(DEFAULTS))
        return json.loads(json.dumps(_STATE))


def _deep(dst: dict, src: dict):
    for k, v in src.items():
        if isinstance(v, dict) and isinstance(dst.get(k), dict):
            _deep(dst[k], v)
        else:
            dst[k] = v


def _pick_db_path() -> str:
    """Choose a SQLite path that actually works here.

    SQLite needs POSIX file locking, which FUSE mounts, network drives, OneDrive-synced
    folders and WSL's /mnt/c do NOT provide -- you get "disk I/O error" on the first
    CREATE TABLE. Found the hard way on day 0. Probe, then fall back.
    """
    override = os.getenv("SATYAVAANI_DB")
    if override:
        return override

    import sqlite3, tempfile
    from pathlib import Path

    candidates = [
        Path.cwd() / "satyavaani.db",
        Path.home() / ".satyavaani" / "satyavaani.db",
        Path(tempfile.gettempdir()) / "satyavaani.db",
    ]
    for c in candidates:
        try:
            c.parent.mkdir(parents=True, exist_ok=True)
            con = sqlite3.connect(str(c))
            con.execute("CREATE TABLE IF NOT EXISTS _probe (a INTEGER)")
            con.execute("DROP TABLE _probe")
            con.commit(); con.close()
            if c != candidates[0]:
                print(f"[db] {candidates[0].parent} cannot host SQLite "
                      f"(mounted/network drive?) -- using {c}")
            return f"sqlite:///{c}"
        except Exception:
            continue
    return "sqlite:///:memory:"


DB_URL = _pick_db_path()
