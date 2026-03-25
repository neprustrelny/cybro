from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List


class AuditLogger:
    """Structured audit log for decisions, actions, and AI debates."""

    def __init__(self, log_dir: Path | None = None) -> None:
        primary_dir = log_dir or Path.cwd() / "logs"
        target_dir = self._ensure_writable_directory(primary_dir)
        if target_dir is None:
            fallback_dir = Path.home() / ".local" / "state" / "cybro" / "logs"
            target_dir = self._ensure_writable_directory(fallback_dir, warn=True)
        if target_dir is None:
            raise PermissionError("Unable to create a writable audit log directory.")

        self.log_file = target_dir / "cybro_decisions.log"
        logging.basicConfig(
            filename=self.log_file,
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(message)s",
        )
        self._bias_log: List[Dict[str, Any]] = []

    def _ensure_writable_directory(
        self, directory: Path, warn: bool = False
    ) -> Optional[Path]:
        try:
            directory.mkdir(parents=True, exist_ok=True)
            test_file = directory / ".cybro_write_test"
            with test_file.open("w") as handle:
                handle.write("")
            test_file.unlink(missing_ok=True)
            return directory
        except PermissionError:
            if warn:
                print(
                    "[WARN] Audit log path not writable, falling back to user state directory"
                )
        except OSError:
            pass
        return None

    def log_decision(self, payload: Dict[str, Any]) -> None:
        payload = dict(payload)
        payload["timestamp"] = datetime.utcnow().isoformat()
        logging.info(json.dumps(payload, default=str))

    def log_bias(self, bias_report: Dict[str, Any]) -> None:
        bias_report["timestamp"] = datetime.utcnow().isoformat()
        self._bias_log.append(bias_report)
        logging.warning(json.dumps({"bias": bias_report}))

    def recent_biases(self) -> List[Dict[str, Any]]:
        return list(self._bias_log[-20:])
