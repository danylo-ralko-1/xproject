"""RTM command: generate Requirements Traceability Matrix wiki page in ADO.

Builds a story-centric traceability table showing which source documents
informed each user story. Uploads source files as wiki attachments so they
are downloadable directly from the page.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import click

from core.config import get_output_path, get_input_dir, get_answers_dir, get_changes_dir
from core import ado as ado_client
from core.usage import log_operation


def run(proj: dict) -> None:
    """Standalone entry point for `xproject rtm <project>`."""
    project_name = proj["project"]
    click.secho(f"\n  Generating RTM wiki page for '{project_name}'", bold=True)

    ado_client.reset_call_counter()

    push_data = _load_push_data(proj)
    if not push_data:
        return

    ado_mapping = _load_ado_mapping(proj)
    if not ado_mapping:
        return

    try:
        config = ado_client.from_project(proj)
    except ValueError as e:
        click.secho(f"  ✗ {e}", fg="red")
        return

    click.echo("  Testing ADO connection...")
    if not ado_client.test_connection(config):
        click.secho("  ✗ Failed to connect to ADO. Check credentials.", fg="red")
        return
    click.secho("  ✓ Connected to ADO", fg="green")

    _generate_and_publish(proj, config, push_data, ado_mapping)

    # Log usage
    stats = ado_client.get_call_stats()
    log_operation(proj, "rtm",
                  ado_api_calls=stats["count"],
                  duration_seconds=stats["total_seconds"],
                  details={"source": "standalone"})


def run_after_push(proj: dict, config: ado_client.AdoConfig) -> None:
    """Called from push.py Phase 8 — reuses existing ADO config.

    Note: ADO call counter is NOT reset here because the push command
    already tracks the combined count (push + RTM) in a single log entry.
    """
    click.echo("\n  Phase 8: Generating RTM wiki page...")

    push_data = _load_push_data(proj)
    if not push_data:
        return

    ado_mapping = _load_ado_mapping(proj)
    if not ado_mapping:
        return

    _generate_and_publish(proj, config, push_data, ado_mapping)


def _generate_and_publish(
    proj: dict,
    config: ado_client.AdoConfig,
    push_data: dict,
    ado_mapping: dict,
) -> None:
    """Core logic: build RTM data, upload attachments, render markdown, upsert wiki page."""
    project_name = proj["project"]

    # Scan source files on disk
    source_files = _scan_source_files(proj)
    click.echo(f"  Found {len(source_files)} source files on disk")

    # Build story-centric traceability data
    rtm_data = _build_rtm_data(
        push_data, ado_mapping, source_files,
        config.organization, config.project,
    )
    traced = rtm_data["total_stories"] - len(rtm_data["untraced_stories"])
    click.echo(f"  Coverage: {traced}/{rtm_data['total_stories']} stories traced")

    # Find or create wiki
    wiki_id = _find_or_create_wiki(config)
    if not wiki_id:
        click.secho("  ✗ Could not find or create a wiki", fg="red")
        return

    # Upload source files as wiki attachments
    attachment_links = _upload_attachments(config, wiki_id, source_files)

    # Render and publish
    content = _generate_wiki_markdown(rtm_data, project_name, attachment_links)
    _upsert_rtm_page(config, wiki_id, content)
    click.secho("  ✓ RTM wiki page published", fg="green")


# --- Data loading helpers ---

def _load_push_data(proj: dict) -> dict | None:
    """Load push_ready.json (or breakdown.json fallback)."""
    for filename in ("push_ready.json", "breakdown.json"):
        path = get_output_path(proj, filename)
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "epics" in data:
                    return data
            except (json.JSONDecodeError, KeyError):
                pass

    click.secho("  ✗ No push_ready.json or breakdown.json found.", fg="red")
    return None


def _load_ado_mapping(proj: dict) -> dict | None:
    """Load ado_mapping.json for local ID → ADO ID resolution."""
    path = get_output_path(proj, "ado_mapping.json")
    if not path.exists():
        click.secho("  ✗ ado_mapping.json not found. Push stories first.", fg="red")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, KeyError):
        click.secho("  ✗ Invalid ado_mapping.json", fg="red")
        return None


# --- Source file scanning ---

SKIP_FILES = {".ds_store", "thumbs.db", ".gitkeep"}


def _scan_source_files(proj: dict) -> dict[str, dict]:
    """Walk input/, answers/, changes/ and return {filename: {category, path}}.

    Skips hidden files and OS junk.
    """
    dirs = [
        (get_input_dir(proj), "Input"),
        (get_answers_dir(proj), "Answer"),
        (get_changes_dir(proj), "Change Request"),
    ]
    result: dict[str, dict] = {}
    for dir_path, category in dirs:
        if not dir_path.exists():
            continue
        for fpath in sorted(dir_path.rglob("*")):
            if not fpath.is_file():
                continue
            if fpath.name.startswith(".") or fpath.name.lower() in SKIP_FILES:
                continue
            result[fpath.name] = {"category": category, "path": str(fpath)}
    return result


# --- RTM data builder (story-centric) ---

def _build_rtm_data(
    push_data: dict,
    ado_mapping: dict,
    source_files: dict[str, dict],
    org: str,
    project: str,
) -> dict:
    """Build story-centric traceability data.

    Returns:
        {
            "stories": [{"id", "ado_id", "title", "sources": [filenames]}],
            "untraced_stories": [{"id", "ado_id", "title"}],
            "unreferenced_files": [{"filename", "category"}],
            "file_story_counts": {filename: int},
            "total_stories": int,
            "org": str,
            "project": str,
        }
    """
    # Build local ID → ADO ID lookup
    id_to_ado: dict[str, int] = {}
    for story_info in ado_mapping.get("stories", []):
        id_to_ado[story_info["id"]] = story_info["ado_id"]

    stories: list[dict] = []
    untraced: list[dict] = []
    referenced_files: set[str] = set()
    file_story_counts: dict[str, int] = {}

    for epic in push_data.get("epics", []):
        for feature in epic.get("features", []):
            for story in feature.get("stories", []):
                local_id = story.get("id", "")
                ado_id = id_to_ado.get(local_id)
                title = story.get("title", "Unknown")
                refs = story.get("reference_sources", [])

                entry = {
                    "id": local_id,
                    "ado_id": ado_id,
                    "title": title,
                    "sources": refs,
                }
                stories.append(entry)

                if not refs:
                    untraced.append(entry)
                else:
                    for ref in refs:
                        referenced_files.add(ref)
                        file_story_counts[ref] = file_story_counts.get(ref, 0) + 1

    # Unreferenced files
    unreferenced = []
    for filename, info in sorted(source_files.items()):
        if filename not in referenced_files:
            unreferenced.append({"filename": filename, "category": info["category"]})

    return {
        "stories": stories,
        "untraced_stories": untraced,
        "unreferenced_files": unreferenced,
        "file_story_counts": file_story_counts,
        "total_stories": len(stories),
        "org": org,
        "project": project,
    }


# --- Wiki attachment upload ---

def _upload_attachments(
    config: ado_client.AdoConfig,
    wiki_id: str,
    source_files: dict[str, dict],
) -> dict[str, str]:
    """Upload source files as wiki attachments. Returns {filename: wiki_path}."""
    links: dict[str, str] = {}
    for filename, info in sorted(source_files.items()):
        try:
            wiki_path = ado_client.upload_wiki_attachment(
                config, wiki_id, info["path"], filename,
            )
            links[filename] = wiki_path
        except Exception as e:
            click.secho(f"    ⚠ Failed to upload {filename}: {e}", fg="yellow")

    if links:
        click.echo(f"  Uploaded {len(links)} source files as wiki attachments")
    return links


# --- Wiki markdown renderer ---

def _generate_wiki_markdown(
    rtm_data: dict,
    project_name: str,
    attachment_links: dict[str, str],
) -> str:
    """Render the RTM wiki page with source overview and story-centric matrix."""
    org = rtm_data["org"]
    project = rtm_data["project"]
    total = rtm_data["total_stories"]
    traced = total - len(rtm_data["untraced_stories"])
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Requirements Traceability Matrix",
        "",
        f"**Project:** {project_name} | **Generated:** {now} | "
        f"**Coverage:** {traced}/{total} stories traced",
        "",
        "---",
        "",
    ]

    # --- Section 1: Source Documents overview ---
    lines.append("## Source Documents")
    lines.append("")

    file_counts = rtm_data["file_story_counts"]
    unreferenced = rtm_data["unreferenced_files"]

    # Collect all files: referenced + unreferenced
    all_files: list[tuple[str, str, int]] = []  # (filename, category, story_count)
    for filename, count in sorted(file_counts.items()):
        cat = "Input"
        if filename.lower().startswith("cr_") or "change" in filename.lower():
            cat = "Change Request"
        all_files.append((filename, cat, count))
    for f in unreferenced:
        all_files.append((f["filename"], f["category"], 0))

    lines.append("| # | Document | Type | Stories | Download |")
    lines.append("|---|----------|------|---------|----------|")
    for idx, (filename, category, count) in enumerate(all_files, 1):
        count_str = str(count) if count > 0 else "—"
        if filename in attachment_links:
            download = f"[Download]({attachment_links[filename]})"
        else:
            download = "—"
        lines.append(f"| {idx} | {filename} | {category} | {count_str} | {download} |")
    lines.append("")

    # --- Section 2: Story-centric traceability matrix ---
    lines.append("---")
    lines.append("")
    lines.append("## Traceability Matrix")
    lines.append("")

    stories = rtm_data["stories"]
    lines.append("| Story ID | Story Title | Source Documents |")
    lines.append("|----------|-------------|-----------------|")
    for s in stories:
        if s["ado_id"]:
            url = (
                f"https://dev.azure.com/{org}/{project}"
                f"/_workitems/edit/{s['ado_id']}"
            )
            title_cell = f"[{s['title']}]({url})"
        else:
            title_cell = s["title"]

        if s["sources"]:
            numbered = [f"{i}. {src}" for i, src in enumerate(s["sources"], 1)]
            sources_cell = "<br>".join(numbered)
        else:
            sources_cell = "⚠️ *Untraced*"

        lines.append(f"| {s['id']} | {title_cell} | {sources_cell} |")
    lines.append("")

    # --- Section 3: Coverage gaps (only if there are any) ---
    untraced = rtm_data["untraced_stories"]
    if untraced or unreferenced:
        lines.append("---")
        lines.append("")
        lines.append("## Coverage Gaps")
        lines.append("")

    if untraced:
        lines.append(f"### Untraced Stories ({len(untraced)})")
        lines.append("")
        lines.append("Stories with no reference sources — traceability unknown.")
        lines.append("")
        lines.append("| ID | Title | ADO Link |")
        lines.append("|----|-------|----------|")
        for s in untraced:
            if s["ado_id"]:
                url = (
                    f"https://dev.azure.com/{org}/{project}"
                    f"/_workitems/edit/{s['ado_id']}"
                )
                lines.append(f"| {s['id']} | {s['title']} | [#{s['ado_id']}]({url}) |")
            else:
                lines.append(f"| {s['id']} | {s['title']} | — |")
        lines.append("")

    if unreferenced:
        lines.append(f"### Unreferenced Documents ({len(unreferenced)})")
        lines.append("")
        lines.append("Source files not referenced by any story.")
        lines.append("")
        lines.append("| Filename | Type |")
        lines.append("|----------|------|")
        for f in unreferenced:
            lines.append(f"| {f['filename']} | {f['category']} |")
        lines.append("")

    return "\n".join(lines)


# --- Wiki helpers ---

def _find_or_create_wiki(config: ado_client.AdoConfig) -> str | None:
    """Find an existing wiki or create a project wiki. Returns wiki ID."""
    wikis = ado_client.get_wiki_list(config)

    for w in wikis:
        if w.get("type", "").lower() == "projectwiki":
            return w.get("id") or w.get("name")

    if wikis:
        return wikis[0].get("id") or wikis[0].get("name")

    click.echo("  No wiki found, creating project wiki...")
    try:
        wiki = ado_client.create_project_wiki(config)
        return wiki.get("id") or wiki.get("name")
    except Exception as e:
        click.secho(f"  ✗ Failed to create wiki: {e}", fg="red")
        click.echo("    Create a wiki manually in ADO, then re-run: xproject rtm")
        return None


def _upsert_rtm_page(
    config: ado_client.AdoConfig,
    wiki_id: str,
    content: str,
) -> None:
    """Create or update the RTM wiki page (idempotent)."""
    page_path = "/Requirements Traceability Matrix"

    existing = ado_client.get_wiki_page(config, wiki_id, page_path)

    etag = None
    if "etag" in existing and "error" not in existing:
        etag = existing["etag"]
        click.echo("  Updating existing RTM page...")
    else:
        click.echo("  Creating new RTM page...")

    ado_client.upsert_wiki_page(config, wiki_id, page_path, content, etag=etag)
