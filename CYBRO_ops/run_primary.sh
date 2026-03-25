#!/usr/bin/env bash
set -euo pipefail
CYBRO_ROOT="/home/neprustrelny/Desktop/CYBRO/ultimate"
ENTRY=(python3 -m cybro.main)
USE_SUDO=false
if [[ ${1:-} == "--sudo" ]]; then
  USE_SUDO=true
  shift || true
fi
cd "$CYBRO_ROOT"
printf '🔷 Starting PRIMARY CYBRO DecisionLoop (%s)\n' "$CYBRO_ROOT"
if $USE_SUDO; then
  exec sudo "${ENTRY[@]}" "$@"
else
  exec "${ENTRY[@]}" "$@"
fi
