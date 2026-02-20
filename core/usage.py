"""Pipeline usage tracking — per-project cost and API call logging."""

import json
import math
from datetime import datetime, timezone
from pathlib import Path

from core.config import get_output_path

# Pricing: Claude API rates (USD per 1M tokens)
PRICING = {
    "opus_input_per_1m": 15.0,
    "opus_output_per_1m": 75.0,
}

USAGE_FILE = "pipeline_usage.json"


def estimate_tokens(text: str) -> int:
    """Estimate token count from text (~4 chars per token)."""
    return math.ceil(len(text) / 4)


def estimate_cost(input_tokens: int = 0, output_tokens: int = 0) -> float:
    """Calculate estimated cost in USD from token counts."""
    input_cost = (input_tokens / 1_000_000) * PRICING["opus_input_per_1m"]
    output_cost = (output_tokens / 1_000_000) * PRICING["opus_output_per_1m"]
    return round(input_cost + output_cost, 4)


def log_operation(
    proj: dict,
    operation: str,
    *,
    ado_api_calls: int = 0,
    duration_seconds: float | None = None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    details: dict | None = None,
) -> dict:
    """Append a usage entry to pipeline_usage.json.

    Args:
        proj: Project config dict
        operation: Operation name (e.g. "push", "discover", "feature_code_gen")
        ado_api_calls: Number of ADO API calls made
        duration_seconds: Wall-clock time for the operation
        input_tokens: Estimated input tokens (for conversational ops)
        output_tokens: Estimated output tokens (for conversational ops)
        details: Extra metadata (e.g. {"stories_created": 27})

    Returns:
        The entry that was appended.
    """
    cost = estimate_cost(input_tokens, output_tokens)

    entry = {
        "operation": operation,
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "duration_seconds": round(duration_seconds, 2) if duration_seconds is not None else None,
        "ado_api_calls": ado_api_calls,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "estimated_cost_usd": cost,
        "details": details or {},
    }

    # Load existing entries
    usage_path = get_output_path(proj, USAGE_FILE)
    entries = _load_entries(usage_path)
    entries.append(entry)

    # Write back
    usage_path.parent.mkdir(parents=True, exist_ok=True)
    with open(usage_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, indent=2)

    return entry


def get_usage_summary(proj: dict) -> dict:
    """Read pipeline_usage.json and return aggregated stats.

    Returns:
        {
            "total_operations": int,
            "total_ado_api_calls": int,
            "total_estimated_cost_usd": float,
            "by_operation": {
                "push": {"runs": int, "cost": float, "ado_calls": int},
                ...
            },
            "first_operation": str | None,
            "last_operation": str | None,
        }
    """
    usage_path = get_output_path(proj, USAGE_FILE)
    entries = _load_entries(usage_path)

    if not entries:
        return {
            "total_operations": 0,
            "total_ado_api_calls": 0,
            "total_estimated_cost_usd": 0.0,
            "by_operation": {},
            "first_operation": None,
            "last_operation": None,
        }

    total_ops = len(entries)
    total_ado = sum(e.get("ado_api_calls", 0) for e in entries)
    total_cost = sum(e.get("estimated_cost_usd", 0) for e in entries)

    by_op: dict[str, dict] = {}
    for e in entries:
        op = e.get("operation", "unknown")
        if op not in by_op:
            by_op[op] = {"runs": 0, "cost": 0.0, "ado_calls": 0}
        by_op[op]["runs"] += 1
        by_op[op]["cost"] += e.get("estimated_cost_usd", 0)
        by_op[op]["ado_calls"] += e.get("ado_api_calls", 0)

    # Round costs
    total_cost = round(total_cost, 2)
    for info in by_op.values():
        info["cost"] = round(info["cost"], 2)

    timestamps = [e.get("timestamp", "") for e in entries if e.get("timestamp")]
    first = min(timestamps) if timestamps else None
    last = max(timestamps) if timestamps else None

    return {
        "total_operations": total_ops,
        "total_ado_api_calls": total_ado,
        "total_estimated_cost_usd": total_cost,
        "by_operation": by_op,
        "first_operation": first,
        "last_operation": last,
    }


def _load_entries(path: Path) -> list[dict]:
    """Load usage entries from JSON file, returning empty list if missing/invalid."""
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
