#!/usr/bin/env bash
set -euo pipefail
CYBRO_ROOT="/home/neprustrelny/Desktop/CYBRO"
ENTRY=(python3 cybro_watchdog_v7.py)
USE_SUDO=false
if [[ ${1:-} == "--sudo" ]]; then
  USE_SUDO=true
  shift || true
fi
cd "$CYBRO_ROOT"
printf '🔷 Starting SECONDARY CYBRO WatchDog v7 (%s)\n' "$CYBRO_ROOT"
if $USE_SUDO; then
  exec sudo "${ENTRY[@]}" "$@"
else
  exec "${ENTRY[@]}" "$@"
fi
