#!/usr/bin/env python3
"""
Non-destructive operational readiness checks for the CYBRO DecisionLoop build.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import List


@dataclass
class CheckResult:
    category: str
    item: str
    status: str  # PASS/WARN/FAIL
    detail: str = ""


REPO_ROOT = Path(__file__).resolve().parent
MAIN_FILE = REPO_ROOT / "main.py"


def check_file() -> CheckResult:
    return CheckResult(
        "filesystem",
        "main.py",
        "PASS" if MAIN_FILE.exists() else "FAIL",
        str(MAIN_FILE),
    )


def check_root() -> CheckResult:
    is_root = os.name != "posix" or os.geteuid() == 0  # type: ignore[attr-defined]
    return CheckResult(
        "privilege",
        "running_as_root",
        "WARN" if is_root else "PASS",
        "root session" if is_root else "standard user",
    )


def check_tool(name: str, required: bool) -> CheckResult:
    path = shutil.which(name)
    status = "PASS" if path else ("FAIL" if required else "WARN")
    return CheckResult(
        "external_tool",
        name,
        status,
        path or "not found",
    )


def check_import(module: str, required: bool) -> CheckResult:
    try:
        import_module(module)
        status = "PASS"
        detail = "import ok"
    except Exception as exc:  # pragma: no cover - diagnostics only
        status = "FAIL" if required else "WARN"
        detail = f"{exc.__class__.__name__}: {exc}"
    return CheckResult("python_dep", module, status, detail)


def main() -> None:
    print("=== CYBRO DecisionLoop Preflight ===")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version.split()[0]} ({platform.platform()})")

    results: List[CheckResult] = []
    results.append(check_file())
    results.append(check_root())

    required_tools = ["ip", "nmcli", "nmap"]
    optional_tools = ["iw", "airmon-ng", "tcpdump"]
    for tool in required_tools:
        results.append(check_tool(tool, required=True))
    for tool in optional_tools:
        results.append(check_tool(tool, required=False))

    required_modules = ["requests"]
    optional_modules = ["scapy", "bleak", "PIL", "pytesseract", "transformers", "torch"]

    for module in required_modules:
        results.append(check_import(module, required=True))
    for module in optional_modules:
        results.append(check_import(module, required=False))

    for result in results:
        print(f"[{result.status}] {result.category}:{result.item} -> {result.detail}")

    summary = {"PASS": 0, "WARN": 0, "FAIL": 0}
    for result in results:
        summary[result.status] += 1

    print("\n=== SUMMARY ===")
    print(
        f"PASS: {summary['PASS']} | WARN: {summary['WARN']} | FAIL: {summary['FAIL']}"
    )
    if summary["FAIL"]:
        overall = "FAIL"
    elif summary["WARN"]:
        overall = "WARN"
    else:
        overall = "PASS"
    print(f"Overall status: {overall}")
    if summary["WARN"]:
        print("Warnings indicate optional capabilities missing.")
    if summary["FAIL"]:
        print("Resolve FAIL items before launching CYBRO.")


if __name__ == "__main__":
    main()
