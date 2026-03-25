#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import os
import shlex
from typing import Dict, List, Set, Tuple

from ai_backend import get_backend
from data_access import (
    WHITELIST_ROOT,
    list_recent_artifacts,
    list_reports,
    read_text_file,
    sqlite_table_overview,
    tail_text_file,
    validate_artifact_path,
)


SYSTEM_PROMPT = (
    "Si CYBRO AI Analyst. Odpovedaj strucne, vecne a opatrne. "
    "Pracuj iba s explicitne poskytnutym kontextom z CYBRO artefaktov. "
    "Ak kontext nestaci, povedz to priamo a nehalucinuj."
)
MAX_CONTEXT_CHARS = 50_000
MAX_HISTORY_MESSAGES = 12
PRIMARY_AUDIT_LOG = WHITELIST_ROOT / "cybro_logs" / "ai_chat_audit.log"
FALLBACK_AUDIT_LOG = Path.home() / ".cache" / "cybro" / "ai_chat_audit.log"


def _is_writable_log_path(path: Path) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8"):
            pass
        return True
    except OSError:
        return False


def _resolve_audit_log_path() -> tuple[Path, bool]:
    try:
        PRIMARY_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        pass

    if PRIMARY_AUDIT_LOG.parent.is_dir() and os.access(PRIMARY_AUDIT_LOG.parent, os.W_OK):
        return PRIMARY_AUDIT_LOG, False
    FALLBACK_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    return FALLBACK_AUDIT_LOG, True


AUDIT_LOG, AUDIT_FALLBACK_USED = _resolve_audit_log_path()


def _append_audit(action: str, files_read: List[Tuple[str, int]], note: str = "") -> None:
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "files_read": [{"path": path, "bytes": size} for path, size in files_read],
        "note": note,
    }
    try:
        AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with AUDIT_LOG.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass


def _short_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.1f} KB"
    return f"{size / (1024 * 1024):.2f} MB"


def _print_help() -> None:
    print("Commands:")
    print("  /help                  Show this help")
    print("  /artifacts             List recent CYBRO artifacts")
    print("  /logs [path]           List log artifacts or tail selected log file")
    print("  /reports               List recent reports")
    print("  /db [path]             Show SQLite table overview")
    print("  /use <path>            Add artifact to context set")
    print("  /clear                 Clear selected context artifacts")
    print("  /quit                  Exit chat")


def _build_context(context_set: Set[str]) -> Tuple[str, List[Tuple[str, int]]]:
    remaining = MAX_CONTEXT_CHARS
    chunks: List[str] = []
    reads: List[Tuple[str, int]] = []

    for item in sorted(context_set):
        if remaining <= 0:
            break

        path = validate_artifact_path(item, allow_db=True)
        relative = str(path.relative_to(WHITELIST_ROOT))
        if path.suffix.lower() == ".db":
            overview = sqlite_table_overview(path)
            text = json.dumps(overview, ensure_ascii=False, indent=2)
        elif path.suffix.lower() in {".pcap", ".pcapng"}:
            text = f"[Binary capture metadata] path={relative}, size={path.stat().st_size} bytes"
        else:
            text = read_text_file(path, max_bytes=min(15_000, remaining))

        clipped = text[:remaining]
        section = f"\n### {relative}\n{clipped}\n"
        section = section[:remaining]
        chunks.append(section)
        used = len(clipped.encode("utf-8", errors="ignore"))
        reads.append((relative, used))
        remaining -= len(section)

    return "\n".join(chunks).strip(), reads


def _default_db_path() -> str | None:
    candidates = [
        WHITELIST_ROOT / "passive_devices.db",
        WHITELIST_ROOT / "cybro_watchdog.db",
        WHITELIST_ROOT / "ultimate" / "passive_devices.db",
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate.relative_to(WHITELIST_ROOT))
    return None


def _handle_logs(arg: str) -> None:
    if not arg:
        artifacts = list_recent_artifacts(limit=200)
        logs = [a for a in artifacts if "log" in a["path"].lower()]
        if not logs:
            print("No log files found in whitelist.")
            return
        print("Log files:")
        for item in logs[:20]:
            print(f"  {item['path']} ({_short_size(item['size'])})")
        print("Use: /logs <path>")
        return

    tail = tail_text_file(arg, lines=200)
    print(tail)
    _append_audit("tail_log", [(arg, len(tail.encode("utf-8", errors="ignore")))])


def _handle_db(arg: str) -> None:
    selected = arg.strip() or _default_db_path()
    if not selected:
        print("No known DB file found.")
        return

    overview = sqlite_table_overview(selected)
    print(f"DB: {overview['db_path']} ({_short_size(overview['db_size'])})")
    tables = overview.get("tables", [])
    if not tables:
        print("No tables detected.")
    for table in tables:
        print(
            f"  - {table['table']}: columns={table['columns']}, rows={table['rows']}"
        )
    db_bytes = int(overview["db_size"])
    _append_audit("db_overview", [(str(selected), db_bytes)])


def _print_artifacts() -> None:
    artifacts = list_recent_artifacts(limit=20)
    if not artifacts:
        print("No artifacts found.")
        return
    for item in artifacts:
        print(f"{item['modified']}  {_short_size(item['size']):>10}  {item['path']}")


def _print_reports() -> None:
    reports = list_reports(limit=20)
    if not reports:
        print("No reports found.")
        return
    for item in reports:
        print(f"{item['modified']}  {_short_size(item['size']):>10}  {item['path']}")


def main() -> None:
    backend = get_backend()
    print("LOCAL-ONLY MODE: Data never leaves this machine. External backends are disabled.")
    print("CYBRO AI Chat")
    print(f"Backend: {backend.name} ({backend.describe()})")
    if backend.is_available():
        print("Status: READY")
    else:
        print("Status: NOT AVAILABLE")
        print(f"Reason: {backend.status()}")
        print("Tip: check backend config/dependencies and restart.")
    print(f"Audit log -> {AUDIT_LOG}")

    _print_help()
    context_set: Set[str] = set()
    history: List[Dict[str, str]] = []

    while True:
        try:
            raw = input("\ncybro-ai> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not raw:
            continue
        if raw == "/quit":
            print("Bye.")
            break
        if raw == "/help":
            _print_help()
            continue
        if raw == "/artifacts":
            _print_artifacts()
            continue
        if raw.startswith("/logs"):
            arg = raw[len("/logs") :].strip()
            try:
                _handle_logs(arg)
            except Exception as exc:
                print(f"Error: {exc}")
            continue
        if raw == "/reports":
            _print_reports()
            continue
        if raw.startswith("/db"):
            arg = raw[len("/db") :].strip()
            try:
                _handle_db(arg)
            except Exception as exc:
                print(f"Error: {exc}")
            continue
        if raw.startswith("/use "):
            try:
                path_arg = shlex.split(raw)[1]
                resolved = validate_artifact_path(path_arg, allow_db=True)
                rel = str(resolved.relative_to(WHITELIST_ROOT))
                context_set.add(rel)
                print(f"Context added: {rel}")
            except Exception as exc:
                print(f"Error: {exc}")
            continue
        if raw == "/clear":
            context_set.clear()
            print("Context cleared.")
            continue

        if not backend.is_available():
            print("Backend is not available. Fix backend and retry.")
            continue

        try:
            context_blob, reads = _build_context(context_set)
            user_payload = (
                f"User question:\n{raw}\n\n"
                f"Context artifacts:\n{context_blob or '[none selected]'}"
            )
            messages: List[Dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(history[-MAX_HISTORY_MESSAGES:])
            messages.append({"role": "user", "content": user_payload})

            print("Čakám na odpoveď AI... (prvý beh môže trvať 30–90 sekúnd, kým sa model načíta do pamäte)")
            answer = backend.chat(messages, timeout=300)
            print(f"\nAI> {answer}")

            history.append({"role": "user", "content": raw})
            history.append({"role": "assistant", "content": answer})
            history[:] = history[-MAX_HISTORY_MESSAGES:]
            _append_audit("chat", reads, note=f"context_items={len(context_set)}")
        except Exception as exc:
            print(f"AI error: {exc}")


if __name__ == "__main__":
    main()
