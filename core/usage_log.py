"""
usage_log.py — Logs each resume generation for audit trail and metrics.

Logs are stored in a local JSON-lines file (one JSON object per line).
Each entry records: timestamp, username, candidate name, latency,
token usage, and estimated cost.

No resume-specific details (level, industry, layout) are stored.
"""

import json
import os
from datetime import datetime

LOG_DIR = os.path.join(os.path.dirname(__file__), '..', 'logs')
LOG_FILE = os.path.join(LOG_DIR, 'generation_log.jsonl')


def log_generation(username: str, candidate_name: str, latency: float, usage: dict):
    """Append a generation event to the log file."""
    os.makedirs(LOG_DIR, exist_ok=True)

    input_tokens = usage.get('inputTokens', 0)
    output_tokens = usage.get('outputTokens', 0)
    estimated_cost = (input_tokens * 0.0000008) + (output_tokens * 0.0000032)

    entry = {
        'timestamp': datetime.now().isoformat(),
        'username': username,
        'candidate_name': candidate_name,
        'latency_seconds': round(latency, 2),
        'input_tokens': input_tokens,
        'output_tokens': output_tokens,
        'estimated_cost_usd': round(estimated_cost, 6),
    }

    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(entry) + '\n')


def get_log_entries(limit=50):
    """Read the most recent log entries."""
    if not os.path.exists(LOG_FILE):
        return []

    with open(LOG_FILE, 'r') as f:
        lines = f.readlines()

    entries = []
    for line in lines[-limit:]:
        try:
            entries.append(json.loads(line.strip()))
        except json.JSONDecodeError:
            continue

    return list(reversed(entries))


def get_stats():
    """Return summary statistics from the log."""
    entries = get_log_entries(limit=10000)
    if not entries:
        return None

    total = len(entries)
    total_cost = sum(e.get('estimated_cost_usd', 0) for e in entries)
    avg_latency = sum(e.get('latency_seconds', 0) for e in entries) / total
    levels = {}
    for e in entries:
        lvl = e.get('resume_level', 'Unknown')
        levels[lvl] = levels.get(lvl, 0) + 1

    return {
        'total_resumes': total,
        'total_cost_usd': round(total_cost, 4),
        'avg_latency_seconds': round(avg_latency, 2),
        'resumes_by_level': levels,
    }
