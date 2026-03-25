#!/usr/bin/env bash
set -euo pipefail
TOOLS_REQUIRED=(python3 ip nmcli nmap)
TOOLS_OPTIONAL=(iw airmon-ng tcpdump)
PY_MODULES=(requests scapy bleak PIL pytesseract transformers torch)
STATUS_PASS=0
STATUS_WARN=0
STATUS_FAIL=0
note() { printf '%s\n' "$1"; }
check_tool() {
  local name=$1
  local required=$2
  if command -v "$name" >/dev/null 2>&1; then
    note "[PASS] tool:$name"
    ((STATUS_PASS++))
  else
    if [[ $required == true ]]; then
      note "[FAIL] tool:$name not found"
      ((STATUS_FAIL++))
    else
      note "[WARN] tool:$name not found"
      ((STATUS_WARN++))
    fi
  fi
}
check_module() {
  local mod=$1
  if python3 -c "import $mod" >/dev/null 2>&1; then
    note "[PASS] module:$mod"
    ((STATUS_PASS++))
  else
    if [[ $mod == "requests" ]]; then
      note "[FAIL] module:$mod import failed"
      ((STATUS_FAIL++))
    else
      note "[WARN] module:$mod import failed"
      ((STATUS_WARN++))
    fi
  fi
}
note "Python: $(python3 --version 2>&1)"
for tool in "${TOOLS_REQUIRED[@]}"; do
  check_tool "$tool" true
done
for tool in "${TOOLS_OPTIONAL[@]}"; do
  check_tool "$tool" false
done
for mod in "${PY_MODULES[@]}"; do
  check_module "$mod"
done
note "SUMMARY -> PASS:$STATUS_PASS WARN:$STATUS_WARN FAIL:$STATUS_FAIL"
if (( STATUS_FAIL > 0 )); then
  exit 1
fi
