"""
log_parser.py — Parses uploaded log files (TXT, JSON, CSV) into a normalized format.
"""

import json
import csv
import io
import re
from typing import List, Dict


def parse_log_file(content: str, filename: str = "") -> str:
    """
    Parses a log file content string into a normalized JSON array string.
    Supports JSON, CSV, and plain-text log formats.

    Args:
        content: Raw file content as a string.
        filename: Original filename (used to detect format).

    Returns:
        A JSON string (array of log entry dicts) for the agent to process.
    """
    ext = filename.lower().split(".")[-1] if "." in filename else ""

    # Try JSON first
    if ext == "json" or content.strip().startswith("["):
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return json.dumps(_normalize_entries(data), indent=2)
        except json.JSONDecodeError:
            pass

    # Try CSV
    if ext == "csv":
        try:
            reader = csv.DictReader(io.StringIO(content))
            entries = [row for row in reader]
            return json.dumps(_normalize_entries(entries), indent=2)
        except Exception:
            pass

    # Fallback: parse plain text logs
    return _parse_plain_text(content)


def _normalize_entries(entries: List[Dict]) -> List[Dict]:
    """Normalizes log entry dicts to have consistent keys."""
    normalized = []
    for entry in entries:
        # Normalize common field name variations
        normalized.append({
            "timestamp": entry.get("timestamp") or entry.get("time") or entry.get("ts") or "",
            "service": entry.get("service") or entry.get("service_name") or entry.get("component") or "unknown",
            "level": (entry.get("level") or entry.get("severity") or entry.get("log_level") or "INFO").upper(),
            "message": entry.get("message") or entry.get("msg") or entry.get("log") or str(entry),
        })
    return normalized


def _parse_plain_text(content: str) -> str:
    """
    Parses common plain-text log formats into normalized JSON.
    Handles formats like:
      [2024-01-01T12:00:00Z] [ERROR] [service-name] Message here
      2024-01-01 12:00:00 ERROR service-name: Message here
    """
    entries = []
    level_pattern = re.compile(
        r'\b(CRITICAL|ALERT|FATAL|ERROR|WARN|WARNING|INFO|DEBUG|TRACE)\b',
        re.IGNORECASE
    )
    ts_pattern = re.compile(
        r'(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)'
    )

    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue

        ts_match = ts_pattern.search(line)
        timestamp = ts_match.group(1) if ts_match else ""

        level_match = level_pattern.search(line)
        level = level_match.group(1).upper() if level_match else "INFO"

        entries.append({
            "timestamp": timestamp,
            "service": "parsed-from-text",
            "level": level,
            "message": line,
        })

    return json.dumps(entries, indent=2)
