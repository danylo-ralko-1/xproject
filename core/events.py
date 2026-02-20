"""Lightweight event logging for the xproject pipeline.

Appends timestamped events to projects/<Name>/output/events.json.
The viewer app reads this file to render the project timeline.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from core.config import get_output_path


def append_event(proj: dict, event_type: str, **data) -> None:
    """Append an event to the project's events.json.

    Args:
        proj: project config dict (from load_project)
        event_type: e.g. "files_ingested", "overview_generated", "pushed_to_ado"
        **data: arbitrary key-value pairs stored in the event's "data" field
    """
    events_path = get_output_path(proj, "events.json")

    events = []
    if events_path.exists():
        try:
            with open(events_path, "r", encoding="utf-8") as f:
                events = json.load(f)
        except (json.JSONDecodeError, ValueError):
            events = []

    events.append({
        "type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": data,
    })

    events_path.parent.mkdir(parents=True, exist_ok=True)
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(events, f, indent=2)
