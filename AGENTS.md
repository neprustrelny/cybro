# CYBRO – Codex rules (local-only)

## Scope
- Work ONLY inside: /home/neprustrelny/Desktop/CYBRO
- No GitHub, no network actions, no external auth flows.
- Prefer read-only discovery unless explicitly asked to modify code.

## Safety / Anti-chaos
- Avoid wide scans across ~ or /
- Max scan depth: 6
- Exclude: venv, .venv, __pycache__, node_modules, .git, ai_env, llama.cpp, dist, build, *.tar.gz, *.zip
- Prefer a single python helper for trees/import maps when possible.

## Default outputs I like
- Tree view (depth<=6)
- Entrypoint identification
- Module grouping: Core / UI / Network-WatchDog / Sensors / AI / Config
