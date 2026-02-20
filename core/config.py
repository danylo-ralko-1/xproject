"""Project configuration and state management for xProject pipeline."""

import os
import yaml
from pathlib import Path
from datetime import datetime, timezone


# Base directory: projects/ lives next to the xproject script
BASE_DIR = Path(__file__).resolve().parent.parent
PROJECTS_DIR = BASE_DIR / "projects"

# Project folder structure
PROJECT_DIRS = [
    "input",        # Raw requirements (any format)
    "answers",      # Client answers to questions
    "changes",      # Change request source files
    "output",       # Generated artifacts
    "output/specs", # YAML specs per story
    "snapshots",    # Versioned snapshots before changes
]

# Default rate cards ($/day)
DEFAULT_RATES = {
    "FE": 650,
    "BE": 700,
    "DevOps": 750,
    "Design": 600,
}

# Pipeline phases and valid statuses
STATUSES = ["init", "discovery", "design", "estimation", "ready", "active"]

# Default state tracking
DEFAULT_STATE = {
    "requirements_hash": None,
    "requirements_ingested": False,
    "breakdown_generated": False,
    "ado_pushed": False,
    "validated": False,
    "enriched": False,
    "specs_generated": False,
}


def get_projects_dir() -> Path:
    """Return the projects directory, creating if needed."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    return PROJECTS_DIR


def get_project_dir(name: str) -> Path:
    """Return path to a specific project directory."""
    return get_projects_dir() / name


def list_projects() -> list[str]:
    """List all project names."""
    d = get_projects_dir()
    return sorted([
        p.name for p in d.iterdir()
        if p.is_dir() and (p / "project.yaml").exists()
    ])


def init_project(
    name: str,
    ado: dict | None = None,
    rate_cards: dict | None = None,
) -> dict:
    """
    Initialize a new project with folder structure and project.yaml.

    Returns the project config dict with 'path' added.
    Raises FileExistsError if project already exists.
    """
    proj_dir = get_project_dir(name)
    if proj_dir.exists():
        raise FileExistsError(f"Project directory already exists: {proj_dir}")

    # Create folder structure
    for d in PROJECT_DIRS:
        (proj_dir / d).mkdir(parents=True, exist_ok=True)

    # Build config
    config = {
        "project": name,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "status": "init",
        "ado": ado or {"organization": "", "project": "", "pat": ""},
        "rate_cards": rate_cards or DEFAULT_RATES.copy(),
        "state": DEFAULT_STATE.copy(),
        "changes": [],
    }

    # Write project.yaml
    _save_yaml(proj_dir / "project.yaml", config)

    # Add a .gitignore to keep sensitive data out
    gitignore = proj_dir / ".gitignore"
    gitignore.write_text("project.yaml\nsnapshots/\n")

    config["path"] = str(proj_dir)
    return config


def load_project(name: str) -> dict:
    """
    Load project config from project.yaml.

    Returns config dict with 'path' added.
    Raises FileNotFoundError if project doesn't exist.
    """
    proj_dir = get_project_dir(name)
    yaml_path = proj_dir / "project.yaml"

    if not yaml_path.exists():
        raise FileNotFoundError(f"No project.yaml found at {yaml_path}")

    config = _load_yaml(yaml_path)

    # Ensure all state keys exist (forward compatibility)
    for k, v in DEFAULT_STATE.items():
        if k not in config.get("state", {}):
            config.setdefault("state", {})[k] = v

    # Ensure changes list exists
    config.setdefault("changes", [])

    config["path"] = str(proj_dir)

    # Env var fallback for credentials
    ado = config.get("ado", {})
    if not ado.get("pat"):
        ado["pat"] = os.environ.get("ADO_PAT", "")
        config["ado"] = ado

    figma = config.get("figma", {})
    if not figma.get("pat"):
        figma["pat"] = os.environ.get("FIGMA_PAT", "")
        config["figma"] = figma

    return config


def save_project(proj: dict) -> None:
    """Save project config back to project.yaml."""
    proj_dir = Path(proj["path"])
    config = {k: v for k, v in proj.items() if k != "path"}
    _save_yaml(proj_dir / "project.yaml", config)


def update_state(proj: dict, **kwargs) -> None:
    """Update state fields and save."""
    for k, v in kwargs.items():
        if k not in DEFAULT_STATE:
            raise ValueError(f"Unknown state key: {k}")
        proj["state"][k] = v
    save_project(proj)


def update_status(proj: dict, status: str) -> None:
    """Update project phase status and save."""
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}. Must be one of {STATUSES}")
    proj["status"] = status
    save_project(proj)


def add_change_record(proj: dict, record: dict) -> None:
    """Append a change request record and save."""
    proj["changes"].append(record)
    save_project(proj)


def get_output_path(proj: dict, filename: str) -> Path:
    """Get path to an output file."""
    return Path(proj["path"]) / "output" / filename


def get_input_dir(proj: dict) -> Path:
    """Get path to the input directory."""
    return Path(proj["path"]) / "input"


def get_answers_dir(proj: dict) -> Path:
    """Get path to the answers directory."""
    return Path(proj["path"]) / "answers"


def get_changes_dir(proj: dict) -> Path:
    """Get path to the changes directory."""
    return Path(proj["path"]) / "changes"


def get_snapshots_dir(proj: dict) -> Path:
    """Get path to the snapshots directory."""
    return Path(proj["path"]) / "snapshots"


def get_specs_dir(proj: dict) -> Path:
    """Get path to the specs output directory."""
    return Path(proj["path"]) / "output" / "specs"


# --- Internal helpers ---

def _load_yaml(path: Path) -> dict:
    """Load a YAML file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _save_yaml(path: Path, data: dict) -> None:
    """Save a dict to YAML with clean formatting."""
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(
            data, f,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
            width=120,
        )
