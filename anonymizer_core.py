import re
import hashlib
import datetime
import json


BASE_PATTERNS = {
    "emails": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    "phones": r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
    "ips": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    "macs": r"([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})",
    "credit_cards": r"\b\d{4}[- ]?\d{4}[- ]?\d{4}[- ]?\d{4}\b",
    "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
    "iban": r"[A-Z]{2}\d{2}[\s-]?[A-Z\d]{4}[\s-]?[A-Z\d]{4}[\s-]?[A-Z\d]{4}[\s-]?[A-Z\d]{0,20}",
    "btc": r"[13][a-km-zA-HJ-NP-Z1-9]{25,34}",
    "coordinates": r"[-+]?([1-8]?\d(\.\d+)?|90(\.0+)?)\s*[-+,]?\s*[-+]?(180(\.0+)?|((1[0-7]\d)|([1-9]?\d))(\.\d+)?)",
}

BASE_SEQUENCE = [
    ("emails", BASE_PATTERNS["emails"], None),
    ("phones", BASE_PATTERNS["phones"], None),
    ("ips", BASE_PATTERNS["ips"], None),
    ("macs", BASE_PATTERNS["macs"], None),
    ("credit_cards", BASE_PATTERNS["credit_cards"], None),
    ("ssn", BASE_PATTERNS["ssn"], None),
    ("iban", BASE_PATTERNS["iban"], None),
    ("btc", BASE_PATTERNS["btc"], None),
    ("coordinates", BASE_PATTERNS["coordinates"], None),
]

CLOUD_SEQUENCE = [
    ("linux_paths", r"/home/[^\s\"'<>]+", None),
    ("linux_system_paths", r"/(?:etc|var/log|proc|sys)/[^\s\"'<>]+", None),
    ("windows_paths", r"[A-Za-z]:\\[^\s\"'<>]+", None),
    ("timestamps", r"\b\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?\b", None),
    ("ipv6", r"\b(?:[A-Fa-f0-9]{1,4}:){2,7}[A-Fa-f0-9]{1,4}\b", None),
    ("bearer_tokens", r"\bBearer\s+[A-Za-z0-9._~+/=-]{8,}\b", None),
    ("authorization_values", r"(?i)(Authorization\s*:\s*)([^\r\n]+)", 2),
    ("api_tokens", r"(?i)\b(?:api[_-]?key|token|secret|access[_-]?token|refresh[_-]?token)\b\s*[:=]\s*([^\s,;]+)", 1),
    ("url_credentials", r"(?i)\b([a-z]+://)([^@\s/]+)@", 2),
    ("url_hosts", r"(?i)\b(https?://)([^/\s:?#]+)", 2),
    ("ssid", r"(?i)\b(SSID\s*[:=]\s*)([^\r\n,;]+)", 2),
    ("hostname", r"(?i)\b(hostname\s*[:=]\s*|host\s*[:=]\s*)([A-Za-z0-9._-]+)", 2),
]


def _placeholder(name, value):
    digest = hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()[:10]
    return f"[{name.upper()}_{digest}]"


def _normalize_match(match):
    if isinstance(match, tuple):
        return "".join(str(part) for part in match if part is not None)
    return str(match)


def _apply_pattern(text, name, pattern, group_index, mapping, replace_counts):
    compiled = re.compile(pattern)

    def repl(match):
        original = match.group(group_index) if group_index else match.group(0)
        original = _normalize_match(original)
        if not original:
            return match.group(0)
        token = mapping.setdefault(original, _placeholder(name, original))
        replace_counts[name] = replace_counts.get(name, 0) + 1
        if group_index:
            start, end = match.span(group_index)
            base_start, base_end = match.span(0)
            whole = match.group(0)
            rel_start = start - base_start
            rel_end = end - base_start
            return whole[:rel_start] + token + whole[rel_end:]
        return token

    return compiled.sub(repl, text)


def anonymize_payload(text: str, mode: str = "cloud", custom_patterns: list[tuple[str, str]] | None = None):
    if not isinstance(text, str):
        raise TypeError("text must be a string")

    selected_mode = (mode or "cloud").strip().lower()
    if selected_mode not in {"cloud", "basic", "scan"}:
        raise ValueError("mode must be one of: cloud, basic, scan")

    stats = {}
    mapping = {}
    replace_counts = {}
    redacted_text = text
    custom_patterns = custom_patterns or []

    pattern_sequence = list(BASE_SEQUENCE)
    if selected_mode == "cloud":
        pattern_sequence.extend(CLOUD_SEQUENCE)

    for name, pattern, group_index in pattern_sequence:
        matches = re.findall(pattern, text)
        if matches:
            stats[name] = len(matches)
        if selected_mode != "scan":
            redacted_text = _apply_pattern(redacted_text, name, pattern, group_index, mapping, replace_counts)

    for custom_name, custom_pattern in custom_patterns:
        matches = re.findall(custom_pattern, text)
        if matches:
            stats[custom_name] = len(matches)
        if selected_mode != "scan":
            redacted_text = _apply_pattern(redacted_text, custom_name, custom_pattern, None, mapping, replace_counts)

    report = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "mode": selected_mode,
        "original_length": len(text),
        "redacted_length": len(redacted_text),
        "replacements": sum(replace_counts.values()),
        "unique_mappings": len(mapping),
        "stats": stats,
        "replace_counts": replace_counts,
        "custom_patterns": [name for name, _ in custom_patterns],
        "pattern_catalog": json.loads(json.dumps(sorted(stats.keys()))),
    }
    return redacted_text, report, mapping
