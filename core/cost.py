"""Per-project cost tracking — reads Claude Code JSONL transcripts for exact token counts."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from core.config import get_output_path

COST_LOG_FILE = "cost_log.json"

# Claude API pricing (USD per 1M tokens) — updated 2026-02
# https://www.anthropic.com/pricing
MODEL_PRICING = {
    "claude-opus-4-6": {
        "input": 15.0,
        "output": 75.0,
        "cache_create": 18.75,
        "cache_read": 1.50,
    },
    "claude-sonnet-4-6": {
        "input": 3.0,
        "output": 15.0,
        "cache_create": 3.75,
        "cache_read": 0.30,
    },
    "claude-sonnet-4-5": {
        "input": 3.0,
        "output": 15.0,
        "cache_create": 3.75,
        "cache_read": 0.30,
    },
    "claude-haiku-4-5": {
        "input": 0.80,
        "output": 4.0,
        "cache_create": 1.0,
        "cache_read": 0.08,
    },
}

# Fallback pricing if model not recognized
DEFAULT_PRICING = {
    "input": 15.0,
    "output": 75.0,
    "cache_create": 18.75,
    "cache_read": 1.50,
}


def _get_claude_projects_dir() -> Path:
    """Find the Claude Code projects directory."""
    home = Path.home()
    for candidate in [
        home / ".claude" / "projects",
        home / ".config" / "claude" / "projects",
    ]:
        if candidate.exists():
            return candidate
    return home / ".claude" / "projects"


def _match_model(model_str: str) -> dict:
    """Match a model string to pricing. Handles partial matches."""
    if not model_str:
        return DEFAULT_PRICING
    model_lower = model_str.lower()
    for key, pricing in MODEL_PRICING.items():
        if key in model_lower or key.replace("-", "") in model_lower.replace("-", ""):
            return pricing
    # Try partial matches
    if "opus" in model_lower:
        return MODEL_PRICING["claude-opus-4-6"]
    if "sonnet" in model_lower:
        return MODEL_PRICING["claude-sonnet-4-5"]
    if "haiku" in model_lower:
        return MODEL_PRICING["claude-haiku-4-5"]
    return DEFAULT_PRICING


def _calc_message_cost(usage: dict, model: str) -> float:
    """Calculate cost for a single message's usage data."""
    pricing = _match_model(model)
    input_tokens = usage.get("input_tokens", 0)
    output_tokens = usage.get("output_tokens", 0)
    cache_create = usage.get("cache_creation_input_tokens", 0)
    cache_read = usage.get("cache_read_input_tokens", 0)

    cost = (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
        + (cache_create / 1_000_000) * pricing["cache_create"]
        + (cache_read / 1_000_000) * pricing["cache_read"]
    )
    return cost


def read_session_cost(session_id: str) -> dict | None:
    """Read a specific Claude Code session JSONL and calculate total cost.

    Returns:
        {
            "session_id": str,
            "total_cost_usd": float,
            "input_tokens": int,
            "output_tokens": int,
            "cache_create_tokens": int,
            "cache_read_tokens": int,
            "total_tokens": int,
            "models_used": list[str],
            "message_count": int,
        }
    """
    projects_dir = _get_claude_projects_dir()
    jsonl_path = None

    # Search all project dirs for the session JSONL
    for proj_dir in projects_dir.iterdir():
        if not proj_dir.is_dir():
            continue
        candidate = proj_dir / f"{session_id}.jsonl"
        if candidate.exists():
            jsonl_path = candidate
            break

    if not jsonl_path:
        return None

    return _parse_jsonl(jsonl_path, session_id)


def read_all_sessions_for_cwd() -> list[dict]:
    """Read all sessions from the current working directory's Claude project folder.

    Claude Code stores sessions under ~/.claude/projects/<encoded-cwd>/
    where the cwd path has / replaced with - (e.g. /Users/foo → -Users-foo).
    Also checks the old project name (presales-pipeline → xproject rename).
    """
    cwd = os.getcwd()
    projects_dir = _get_claude_projects_dir()

    # Claude encodes the cwd by replacing / with -
    encoded = cwd.replace("/", "-")

    # Collect all matching directories (current name + legacy names)
    candidate_dirs = [projects_dir / encoded]
    # Also check presales-pipeline (legacy name before rename)
    if "xproject" in encoded:
        legacy = encoded.replace("xproject", "presales-pipeline")
        candidate_dirs.append(projects_dir / legacy)

    sessions = []
    seen_ids = set()
    for session_dir in candidate_dirs:
        if not session_dir.exists():
            continue
        for f in sorted(session_dir.glob("*.jsonl")):
            session_id = f.stem
            if session_id in seen_ids:
                continue
            seen_ids.add(session_id)
            result = _parse_jsonl(f, session_id)
            if result and result["message_count"] > 0:
                sessions.append(result)

    return sessions


def _parse_jsonl(path: Path, session_id: str) -> dict:
    """Parse a JSONL transcript and extract token usage."""
    total_input = 0
    total_output = 0
    total_cache_create = 0
    total_cache_read = 0
    total_cost = 0.0
    models = set()
    msg_count = 0
    first_ts = None
    last_ts = None

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue

            # Track timestamps
            ts = msg.get("timestamp")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts

            # Usage can be at top level or nested under message.usage
            usage = msg.get("usage")
            inner = msg.get("message", {})
            if not usage and isinstance(inner, dict):
                usage = inner.get("usage")

            if not usage:
                continue

            msg_count += 1

            # Model can be at top level or nested under message.model
            model = msg.get("model", "") or inner.get("model", "")
            if model:
                models.add(model)

            inp = usage.get("input_tokens", 0)
            out = usage.get("output_tokens", 0)
            cc = usage.get("cache_creation_input_tokens", 0)
            cr = usage.get("cache_read_input_tokens", 0)

            total_input += inp
            total_output += out
            total_cache_create += cc
            total_cache_read += cr
            total_cost += _calc_message_cost(usage, model)

    return {
        "session_id": session_id,
        "total_cost_usd": round(total_cost, 2),
        "input_tokens": total_input,
        "output_tokens": total_output,
        "cache_create_tokens": total_cache_create,
        "cache_read_tokens": total_cache_read,
        "total_tokens": total_input + total_output + total_cache_create + total_cache_read,
        "models_used": sorted(models),
        "message_count": msg_count,
        "first_activity": first_ts,
        "last_activity": last_ts,
    }


# --- Cost log management ---

def log_session(
    proj: dict,
    *,
    cost_usd: float,
    description: str,
    session_id: str = "",
    tokens: int = 0,
    details: dict | None = None,
) -> dict:
    """Append a session cost entry to the project's cost_log.json.

    Called by Claude during conversation after completing work on a project.

    Args:
        proj: Project config dict
        cost_usd: Session cost in USD
        description: What was done (e.g. "Generated breakdown + pushed to ADO")
        session_id: Claude Code session ID (optional)
        tokens: Total tokens used (optional)
        details: Extra metadata (optional)

    Returns:
        The entry that was appended.
    """
    entry = {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session_id": session_id,
        "description": description,
        "cost_usd": round(cost_usd, 2),
        "tokens": tokens,
        "details": details or {},
    }

    log_path = get_output_path(proj, COST_LOG_FILE)
    entries = _load_cost_log(log_path)
    entries.append(entry)

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    return entry


def get_cost_summary(proj: dict) -> dict:
    """Read cost_log.json and return aggregated stats.

    Returns:
        {
            "total_sessions": int,
            "total_cost_usd": float,
            "total_tokens": int,
            "entries": list[dict],
            "first_date": str | None,
            "last_date": str | None,
        }
    """
    log_path = get_output_path(proj, COST_LOG_FILE)
    entries = _load_cost_log(log_path)

    if not entries:
        return {
            "total_sessions": 0,
            "total_cost_usd": 0.0,
            "total_tokens": 0,
            "entries": [],
            "first_date": None,
            "last_date": None,
        }

    total_cost = sum(e.get("cost_usd", 0) for e in entries)
    total_tokens = sum(e.get("tokens", 0) for e in entries)
    dates = [e.get("date", "") for e in entries if e.get("date")]

    return {
        "total_sessions": len(entries),
        "total_cost_usd": round(total_cost, 2),
        "total_tokens": total_tokens,
        "entries": entries,
        "first_date": min(dates) if dates else None,
        "last_date": max(dates) if dates else None,
    }


def _load_cost_log(path: Path) -> list[dict]:
    """Load cost log entries from JSON file."""
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, OSError):
        pass
    return []
