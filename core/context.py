"""Dependency tracking and staleness detection for pipeline artifacts."""

import hashlib
import click
from pathlib import Path
from core.config import get_input_dir, get_output_path, get_answers_dir


# Dependency graph: command → list of (state_key, error_message)
DEPENDENCIES = {
    "ingest": [],
    "breakdown-export": [
        ("breakdown_generated", "Breakdown not generated. Generate it in conversation first."),
    ],
    "push": [
        ("breakdown_generated", "Breakdown not generated. Generate it in conversation first."),
    ],
    "enrich": [],  # Deprecated — enrichment removed from pipeline
    "validate": [
        ("ado_pushed", "Stories not pushed to ADO. Run: xproject push"),
    ],
    "specs-upload": [
        ("ado_pushed", "Stories not pushed to ADO. Run: xproject push"),
    ],
    "rtm": [
        ("ado_pushed", "Stories not pushed to ADO. Run: xproject push"),
    ],
}

# Invalidation graph: when a command runs, which downstream state flags become stale
INVALIDATION = {
    "ingest": [
        "breakdown_generated", "ado_pushed",
        "specs_generated", "validated",
    ],
    "push": [
        "specs_generated", "validated",
    ],
    "validate": [],
    "specs-upload": [],
    "breakdown-export": [],
    "rtm": [],
}


def get_dependencies(command: str) -> list[tuple[str, str]]:
    """Get dependency checks for a command."""
    return DEPENDENCIES.get(command, [])


def check_staleness(proj: dict) -> list[str]:
    """Check all staleness conditions and return warning messages."""
    warnings = []
    state = proj.get("state", {})

    # Check if requirements changed since last ingest
    if state.get("requirements_ingested"):
        current_hash = compute_input_hash(proj)
        stored_hash = state.get("requirements_hash", "")
        if current_hash and stored_hash and current_hash != stored_hash:
            warnings.append(
                "Input files changed since last ingest. Run: xproject ingest"
            )

    # Check if answers exist but haven't been incorporated
    if state.get("overview_generated") and not state.get("breakdown_generated"):
        ans_dir = get_answers_dir(proj)
        if ans_dir.exists() and any(ans_dir.iterdir()):
            warnings.append(
                "Client answers available but breakdown not yet generated. Run: xproject breakdown"
            )

    # Check if breakdown exists but not pushed
    if state.get("breakdown_generated") and not state.get("ado_pushed"):
        warnings.append(
            "Breakdown ready but not pushed to ADO. Run: xproject push"
        )

    return warnings


def invalidate_downstream(proj: dict, command: str) -> None:
    """Mark downstream artifacts as stale when an upstream command runs."""
    flags_to_clear = INVALIDATION.get(command, [])
    if not flags_to_clear:
        return

    state = proj.setdefault("state", {})
    cleared = []
    for flag in flags_to_clear:
        if state.get(flag):
            state[flag] = False
            cleared.append(flag)

    if cleared:
        from core.config import save_project
        save_project(proj)
        click.secho(
            f"  ↻ Invalidated downstream: {', '.join(cleared)}",
            fg="yellow",
        )


def compute_input_hash(proj: dict) -> str:
    """Compute a hash of all files in the input/ directory."""
    input_dir = get_input_dir(proj)
    if not input_dir.exists():
        return ""

    hasher = hashlib.md5()
    for fpath in sorted(input_dir.rglob("*")):
        if fpath.is_file():
            hasher.update(fpath.name.encode())
            hasher.update(str(fpath.stat().st_size).encode())
            hasher.update(str(fpath.stat().st_mtime).encode())

    return hasher.hexdigest()[:16]
