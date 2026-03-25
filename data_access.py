from __future__ import annotations

from collections import deque
from datetime import datetime
from pathlib import Path
import os
import sqlite3
from typing import Any, Dict, Iterable, List


WHITELIST_ROOT = Path("/home/neprustrelny/Desktop/CYBRO").resolve()
ALLOWED_SUBDIRECTORIES = {"cybro_logs", "logs", "security_reports", "packet_captures"}
ALLOWED_FILES = {"cybro_config.json", "cybro_watchdog.db", "passive_devices.db"}
DEFAULT_MAX_BYTES = 200_000


def resolve_whitelisted_path(path: str | Path) -> Path:
    candidate = Path(path)
    if not candidate.is_absolute():
        candidate = WHITELIST_ROOT / candidate
    resolved = candidate.resolve()

    try:
        resolved.relative_to(WHITELIST_ROOT)
    except ValueError as exc:
        raise PermissionError(f"Path outside whitelist root: {path}") from exc
    return resolved


def _is_under(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def _allowed_dir_roots() -> List[Path]:
    roots: List[Path] = []
    for base in (WHITELIST_ROOT, WHITELIST_ROOT / "ultimate"):
        for dirname in sorted(ALLOWED_SUBDIRECTORIES):
            roots.append((base / dirname).resolve())
    return roots


def _is_allowed_file(path: Path) -> bool:
    if path.name in ALLOWED_FILES and _is_under(path, WHITELIST_ROOT):
        return True
    return any(_is_under(path, root) for root in _allowed_dir_roots())


def _validate_readable_path(path: str | Path, *, allow_db: bool = False) -> Path:
    resolved = resolve_whitelisted_path(path)
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(f"File not found: {resolved}")
    if not _is_allowed_file(resolved):
        raise PermissionError(f"Path is not in allowed scope: {resolved}")
    if resolved.suffix.lower() == ".db" and not allow_db:
        raise PermissionError("DB files are only allowed via sqlite_table_overview().")
    return resolved


def validate_artifact_path(path: str | Path, *, allow_db: bool = True) -> Path:
    return _validate_readable_path(path, allow_db=allow_db)


def _is_binary_file(path: Path, sample_bytes: int = 4096) -> bool:
    with path.open("rb") as handle:
        sample = handle.read(sample_bytes)
    if b"\x00" in sample:
        return True
    try:
        sample.decode("utf-8")
    except UnicodeDecodeError:
        return True
    return False


def _iter_files_limited(base: Path, max_depth: int = 4) -> Iterable[Path]:
    if not base.exists() or not base.is_dir():
        return
    base_depth = len(base.parts)
    for current_root, dirs, files in os.walk(base):
        current = Path(current_root)
        if len(current.parts) - base_depth >= max_depth:
            dirs[:] = []
        for name in files:
            yield current / name


def _format_artifact(path: Path) -> Dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.relative_to(WHITELIST_ROOT)),
        "size": stat.st_size,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
    }


def list_recent_artifacts(limit: int = 20) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    found: List[Path] = []

    for base in _allowed_dir_roots():
        if base.exists():
            found.extend(_iter_files_limited(base, max_depth=4))

    for filename in sorted(ALLOWED_FILES):
        for candidate in (WHITELIST_ROOT / filename, WHITELIST_ROOT / "ultimate" / filename):
            if candidate.exists() and candidate.is_file():
                found.append(candidate.resolve())

    dedup = {path.resolve(): path.resolve() for path in found}
    ordered = sorted(
        dedup.values(),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return [_format_artifact(p) for p in ordered[:safe_limit]]


def tail_text_file(path: str | Path, lines: int = 200) -> str:
    safe_lines = max(1, min(lines, 2000))
    target = _validate_readable_path(path)
    if _is_binary_file(target):
        raise ValueError(f"Binary file is not readable as text: {target}")

    buffer: deque[str] = deque(maxlen=safe_lines)
    with target.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            buffer.append(line.rstrip("\n"))
    return "\n".join(buffer)


def read_text_file(path: str | Path, max_bytes: int = DEFAULT_MAX_BYTES) -> str:
    safe_max = max(1, min(max_bytes, 2_000_000))
    target = _validate_readable_path(path)
    if _is_binary_file(target):
        raise ValueError(f"Binary file is not readable as text: {target}")

    with target.open("rb") as handle:
        payload = handle.read(safe_max + 1)
    truncated = len(payload) > safe_max
    if truncated:
        payload = payload[:safe_max]

    text = payload.decode("utf-8", errors="replace")
    if truncated:
        text += "\n\n[TRUNCATED]"
    return text


def list_reports(limit: int = 20) -> List[Dict[str, Any]]:
    safe_limit = max(1, min(limit, 200))
    reports: List[Path] = []
    for base in _allowed_dir_roots():
        if base.name == "security_reports" and base.exists():
            reports.extend(_iter_files_limited(base, max_depth=3))
    ordered = sorted(reports, key=lambda p: p.stat().st_mtime, reverse=True)
    return [_format_artifact(p) for p in ordered[:safe_limit]]


def list_captures(limit: int = 20) -> List[str]:
    safe_limit = max(1, min(limit, 200))
    captures: List[Path] = []
    for base in _allowed_dir_roots():
        if base.name == "packet_captures" and base.exists():
            captures.extend(_iter_files_limited(base, max_depth=3))
    ordered = sorted(captures, key=lambda p: p.stat().st_mtime, reverse=True)
    return [p.name for p in ordered[:safe_limit]]


def sqlite_table_overview(db_path: str | Path, max_tables: int = 25) -> Dict[str, Any]:
    safe_tables = max(1, min(max_tables, 200))
    target = _validate_readable_path(db_path, allow_db=True)
    if target.suffix.lower() != ".db" or target.name not in ALLOWED_FILES:
        raise PermissionError(f"DB path not allowed: {target}")

    query = (
        "SELECT name FROM sqlite_master "
        "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name LIMIT ?"
    )
    overview: List[Dict[str, Any]] = []

    conn = sqlite3.connect(f"file:{target}?mode=ro", uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute(query, (safe_tables,))
        tables = [row[0] for row in cursor.fetchall()]

        for table in tables:
            safe_table = table.replace('"', '""')
            cursor.execute(f'PRAGMA table_info("{safe_table}")')
            columns = cursor.fetchall()
            col_names = [col[1] for col in columns]

            row_count = None
            try:
                cursor.execute(f'SELECT COUNT(1) FROM "{safe_table}"')
                row_count = int(cursor.fetchone()[0])
            except sqlite3.DatabaseError:
                row_count = None

            overview.append(
                {
                    "table": table,
                    "columns": len(col_names),
                    "column_names": col_names[:30],
                    "rows": row_count,
                }
            )
    finally:
        conn.close()

    return {
        "db_path": str(target.relative_to(WHITELIST_ROOT)),
        "db_size": target.stat().st_size,
        "tables": overview,
    }
