# CYBRO Agent Briefing

## Project Intent
CYBRO is an ethical defensive cyber-operations suite. The DecisionLoop build couples a hacker-themed Tkinter UI with modular sensors, AI debate, and audit logging to help blue-team operators detect, analyze, and report network activity without crossing legal or ethical lines.

## Variant Policy
- **PRIMARY:** `ultimate/cybro` (DecisionLoop build you are in now).
- **SECONDARY:** `/home/neprustrelny/Desktop/CYBRO/cybro_watchdog_v7.py` (legacy monolith retained for reference/testing).
- Treat PRIMARY as the production baseline; SECONDARY stays untouched unless leadership asks for parity fixes or forensic comparisons.

## Observe-First Default
- Launch as a normal user and stay on dashboard/reporting panes by default.
- Promote to sudo only after scope approval and just before running scans that truly need privileged interfaces.

## Do-Not-Refactor Rule
- No structural refactors, merges, or “cleanup” unless the explicit ticket says so.
- Favor drop-in modules, scripts, or docs that keep behavior stable and reversible.

## Safe Operations
- Every sudo command or high-impact subprocess must be justified (monitor mode, `nmap`, `nmcli`, etc.). Use the DecisionLoop hooks already in place.
- Pentest or packet-capture tools run only within approved scopes, with logging enabled, and with clear stop conditions (proof-of-access → halt).
- Never run destructive payloads, password sprays, or exploits from this workspace.
