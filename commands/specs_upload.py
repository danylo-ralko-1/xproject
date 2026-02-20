"""Specs upload command: upload YAML spec files to ADO tasks as attachments.

Reads YAML files from output/specs/fe/ and output/specs/be/.
Reads ado_mapping.json to find story ADO IDs.
Looks up [FE] and [BE] child tasks of each story.
Uploads each spec as an attachment to the matching task.
"""

import json
import click
from pathlib import Path

from core.config import get_output_path, get_specs_dir
from core import ado as ado_client


def run(proj: dict) -> None:
    """Upload FE and BE spec files to corresponding ADO tasks."""
    project_name = proj["project"]
    click.secho(f"\n  Uploading specs to ADO for '{project_name}'", bold=True)

    # Load ADO mapping
    mapping = _load_mapping(proj)
    if mapping is None:
        return

    # Check ADO connection
    try:
        config = ado_client.from_project(proj)
    except ValueError as e:
        click.secho(f"  ✗ {e}", fg="red")
        return

    click.echo("  Testing ADO connection...")
    if not ado_client.test_connection(config):
        click.secho("  ✗ Failed to connect to ADO. Check credentials.", fg="red")
        return
    click.secho("  ✓ Connected to ADO\n", fg="green")

    specs_dir = get_specs_dir(proj)
    fe_dir = specs_dir / "fe"
    be_dir = specs_dir / "be"

    # Collect spec files
    fe_specs = list(fe_dir.glob("*.yaml")) + list(fe_dir.glob("*.yml")) if fe_dir.exists() else []
    be_specs = list(be_dir.glob("*.yaml")) + list(be_dir.glob("*.yml")) if be_dir.exists() else []

    if not fe_specs and not be_specs:
        click.secho("  ✗ No spec files found in output/specs/fe/ or output/specs/be/", fg="red")
        click.echo("    Generate specs in conversation first, then save them there.")
        return

    click.echo(f"  Found {len(fe_specs)} FE specs, {len(be_specs)} BE specs")

    # Build a lookup of story title/id → ADO story ID
    story_lookup = {}
    for story in mapping.get("stories", []):
        ado_id = story.get("ado_id")
        title = story.get("title", "")
        sid = story.get("id", "")
        if ado_id:
            story_lookup[title.lower()] = ado_id
            story_lookup[sid.lower()] = ado_id

    # Cache for child tasks: story_ado_id → {prefix → task_ado_id}
    task_cache = {}

    uploaded = 0
    errors = 0

    # Upload FE specs
    for spec_path in sorted(fe_specs):
        ok = _upload_spec(config, spec_path, "FE", story_lookup, task_cache)
        if ok:
            uploaded += 1
        else:
            errors += 1

    # Upload BE specs
    for spec_path in sorted(be_specs):
        ok = _upload_spec(config, spec_path, "BE", story_lookup, task_cache)
        if ok:
            uploaded += 1
        else:
            errors += 1

    click.secho(f"\n  ✓ Upload complete", fg="green", bold=True)
    click.echo(f"    Uploaded: {uploaded}")
    if errors:
        click.secho(f"    Errors: {errors}", fg="yellow")


def _upload_spec(config, spec_path: Path, prefix: str,
                  story_lookup: dict, task_cache: dict) -> bool:
    """Upload a single spec file to the matching ADO task.

    Returns True on success, False on failure.
    """
    filename = spec_path.stem  # e.g. "US-001_Login_Page"

    # Try to match spec filename to a story
    story_ado_id = _match_spec_to_story(filename, story_lookup)
    if not story_ado_id:
        click.secho(f"  ⚠ [{prefix}] No ADO story match for {spec_path.name}", fg="yellow")
        return False

    # Find the discipline task under the story
    task_id = _find_task(config, story_ado_id, prefix, task_cache)
    if not task_id:
        click.secho(f"  ⚠ [{prefix}] No [{prefix}] task found under story #{story_ado_id}", fg="yellow")
        return False

    # Upload
    try:
        ado_client.upload_attachment(
            config, task_id, str(spec_path),
            filename=spec_path.name,
            comment=f"{prefix} spec for story #{story_ado_id}",
        )
        click.secho(f"  ✓ [{prefix}] {spec_path.name} → task #{task_id}", fg="green")
        return True
    except Exception as e:
        click.secho(f"  ✗ [{prefix}] Failed to upload {spec_path.name}: {e}", fg="red")
        return False


def _match_spec_to_story(filename: str, story_lookup: dict) -> int | None:
    """Try to match a spec filename to a story ADO ID.

    Spec filenames are expected to contain the story ID (e.g. "US-001")
    or the story title (e.g. "Login_Page").
    """
    name_lower = filename.lower().replace("_", " ").replace("-", " ")

    # Try exact key match on parts of the filename
    for key, ado_id in story_lookup.items():
        if key in name_lower:
            return ado_id

    return None


def _find_task(config, story_ado_id: int, prefix: str, cache: dict) -> int | None:
    """Find the [FE] or [BE] task under a story, with caching."""
    cache_key = story_ado_id
    if cache_key not in cache:
        try:
            children = ado_client.get_child_work_items(config, story_ado_id)
            tasks = {}
            for child in children:
                fields = child.get("fields", {})
                title = fields.get("System.Title", "")
                cid = child.get("id")
                if title.startswith("[FE]"):
                    tasks["FE"] = cid
                elif title.startswith("[BE]"):
                    tasks["BE"] = cid
                elif title.startswith("[DevOps]"):
                    tasks["DevOps"] = cid
            cache[cache_key] = tasks
        except Exception:
            cache[cache_key] = {}

    return cache.get(cache_key, {}).get(prefix)


def _load_mapping(proj: dict) -> dict | None:
    """Load ado_mapping.json."""
    path = get_output_path(proj, "ado_mapping.json")
    if not path.exists():
        click.secho("  ✗ ado_mapping.json not found.", fg="red")
        click.echo("    Run: xproject push first to create the ADO mapping.")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        click.secho(f"  ✗ Failed to parse ado_mapping.json: {e}", fg="red")
        return None
