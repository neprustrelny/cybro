# CYBRO Map (Local)

## AI Chat
- Entrypoint: `python3 cybro_ai_chat.py`
- Backends:
  - `ollama` (default): uses `CYBRO_OLLAMA_URL` and `CYBRO_OLLAMA_MODEL`
  - `openai` (optional): enabled when `CYBRO_AI_BACKEND=openai` and `OPENAI_API_KEY` exists
- Controlled data access is enforced by `data_access.py`:
  - Allowed dirs: `cybro_logs`, `logs`, `security_reports`, `packet_captures`
  - Allowed files: `cybro_config.json`, `cybro_watchdog.db`, `passive_devices.db`
- Audit log: `cybro_logs/ai_chat_audit.log`

