"""Change utilities: snapshot, save source, push changes to ADO.

This is a utility module with importable functions — not a CLI command.
The change analysis itself happens in conversation. These functions handle
the data I/O: snapshotting, saving files, pushing to ADO, updating the changelog.
"""

import json
import shutil
import click
from pathlib import Path
from datetime import datetime, timezone

from core.config import (
    get_output_path, get_changes_dir, get_snapshots_dir,
    add_change_record, save_project,
)
from core import ado as ado_client


def create_snapshot(proj: dict, cr_id: str) -> Path:
    """Snapshot current output/ before applying changes.

    Args:
        proj: Project config dict
        cr_id: Change request identifier (e.g. "CR-001")

    Returns:
        Path to the snapshot directory.
    """
    snap_dir = get_snapshots_dir(proj) / f"pre-{cr_id}"
    snap_dir.mkdir(parents=True, exist_ok=True)

    output_dir = Path(proj["path"]) / "output"
    copied = 0
    for f in output_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, snap_dir / f.name)
            copied += 1

    click.secho(f"  ✓ Snapshot saved: {snap_dir} ({copied} files)", fg="green")
    return snap_dir


def save_change_source(proj: dict, text: str, cr_id: str) -> Path:
    """Save the raw change request text to changes/ directory.

    Args:
        proj: Project config dict
        text: Raw change request text
        cr_id: Change request identifier (e.g. "CR-001")

    Returns:
        Path to the saved file.
    """
    changes_dir = get_changes_dir(proj)
    changes_dir.mkdir(parents=True, exist_ok=True)
    path = changes_dir / f"{cr_id}.txt"
    path.write_text(text, encoding="utf-8")
    click.echo(f"  Saved change source: {path}")
    return path


def push_new_stories_to_ado(proj: dict, stories: list[dict]) -> list[dict]:
    """Create new user stories in ADO from change request analysis.

    Args:
        proj: Project config dict
        stories: List of story dicts, each with:
            title, user_story, acceptance_criteria (list), epic, feature,
            fe_days, be_days, devops_days, design_days

    Returns:
        List of created stories with ado_id added.
    """
    try:
        config = ado_client.from_project(proj)
    except ValueError as e:
        click.secho(f"  ✗ ADO not configured: {e}", fg="red")
        return []

    project_name = proj["project"]
    created = []

    for story in stories:
        title = story.get("title", "")
        user_story_text = story.get("user_story", f"As a user,\nI want to {title.lower()},\nSo that I can accomplish this goal.")
        ac_list = story.get("acceptance_criteria", [])

        fe = story.get("fe_days", 0)
        be = story.get("be_days", 0)
        dv = story.get("devops_days", 0)
        ds = story.get("design_days", 0)
        total = fe + be + dv + ds

        cr_id = story.get("cr_id", "CR")
        epic = story.get("epic", "")
        feature = story.get("feature", "")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Three-line format, no italic
        html_text = user_story_text.replace("\n", "<br>\n")
        desc = f"<p>{html_text}</p>"

        changelog = (
            f"<br><b>Change Log:</b><br><br>"
            f"<b>Change 1:</b> Story created<br>"
            f"<b>Date:</b> {today}<br>"
            f"<b>Reason:</b> {cr_id}"
        )
        ac_parts = []
        if ac_list:
            for i, ac in enumerate(ac_list, 1):
                if isinstance(ac, dict):
                    title = ac.get("title", f"Criterion {i}")
                    items_html = "".join(
                        f"<li>{item}</li>" for item in ac.get("items", [])
                    )
                    ac_parts.append(f"<b>AC {i}:</b> {title}<br><ul>{items_html}</ul>")
                else:
                    ac_parts.append(f"<b>AC {i}:</b> {ac}<br><ul><li>{ac}</li></ul>")
        ac_html = "".join(ac_parts) + changelog

        try:
            result = ado_client.create_work_item(
                config, "User Story", title,
                description=desc,
                tags=f"xproject;change-request;{cr_id};{project_name}",
                extra_fields={
                    "Microsoft.VSTS.Scheduling.Effort": total,
                    "Microsoft.VSTS.Common.AcceptanceCriteria": ac_html,
                },
            )
            ado_id = result.get("id")
            click.secho(f"  ✓ Created ADO #{ado_id}: {title}", fg="green")
            story["ado_id"] = ado_id
            created.append(story)
        except Exception as e:
            click.secho(f"  ✗ Failed to create '{title}': {e}", fg="red")

    return created


def push_modified_stories_to_ado(proj: dict, modifications: list[dict]) -> None:
    """Update existing ADO stories based on change request analysis.

    Args:
        proj: Project config dict
        modifications: List of dicts, each with:
            ado_id (int), fields (dict of field_path → value)
    """
    try:
        config = ado_client.from_project(proj)
    except ValueError as e:
        click.secho(f"  ✗ ADO not configured: {e}", fg="red")
        return

    for mod in modifications:
        ado_id = mod.get("ado_id")
        fields = mod.get("fields", {})
        title = mod.get("title", f"#{ado_id}")

        if not ado_id or not fields:
            continue

        try:
            ado_client.update_work_item(config, ado_id, fields)
            click.secho(f"  ✓ Updated ADO #{ado_id}: {title}", fg="green")
        except Exception as e:
            click.secho(f"  ✗ Failed to update #{ado_id}: {e}", fg="red")


def update_ado_changelog(proj: dict, analysis: dict, change_text: str, cr_id: str) -> None:
    """Create/update a Change Log in ADO: parent Epic + child Feature per CR.

    Args:
        proj: Project config dict
        analysis: Change analysis dict with keys:
            summary, classification, impact, new_stories, modified_stories, recommendation
        change_text: Raw change request text
        cr_id: Change request identifier (e.g. "CR-001")
    """
    try:
        config = ado_client.from_project(proj)
    except ValueError as e:
        click.secho(f"  ⚠ ADO not configured, skipping changelog: {e}", fg="yellow")
        return

    project_name = proj.get("project", "")
    impact = analysis.get("impact", {})
    new_stories = analysis.get("new_stories", [])
    mod_stories = analysis.get("modified_stories", [])

    # Find or create the Change Log epic
    changelog_epic_id = proj.get("_changelog_epic_id")
    if not changelog_epic_id:
        try:
            items = ado_client.get_work_items_by_query(
                config,
                "SELECT [System.Id] FROM WorkItems "
                "WHERE [System.WorkItemType] = 'Epic' "
                f"AND [System.Title] = 'Change Log — {project_name}' "
                "AND [System.State] <> 'Removed'"
            )
            if items:
                changelog_epic_id = items[0].get("id")
        except Exception:
            pass

    if not changelog_epic_id:
        try:
            result = ado_client.create_work_item(
                config, "Epic",
                f"Change Log — {project_name}",
                description=(
                    f"<h3>Change Log for {project_name}</h3>"
                    "<p>Each child item represents a change request with full impact analysis.</p>"
                ),
                tags=f"changelog;{project_name}",
            )
            changelog_epic_id = result.get("id")
            click.secho(f"  ✓ Created Change Log epic #{changelog_epic_id}", fg="green")
        except Exception as e:
            click.secho(f"  ⚠ Failed to create Change Log epic: {e}", fg="yellow")
            return

    proj["_changelog_epic_id"] = changelog_epic_id
    save_project(proj)

    # Build CR description HTML
    delta_days = impact.get("total_delta_days", 0)
    delta_cost = impact.get("total_delta_cost", 0)

    new_html = ""
    if new_stories:
        rows = "".join(
            f"<tr><td>{s.get('id','?')}</td><td>{s.get('title','?')}</td>"
            f"<td>{s.get('fe_days',0)}</td><td>{s.get('be_days',0)}</td>"
            f"<td>{s.get('devops_days',0)}</td><td>{s.get('design_days',0)}</td></tr>"
            for s in new_stories
        )
        new_html = (
            "<h4>New Stories</h4>"
            "<table><tr><th>ID</th><th>Title</th><th>FE</th><th>BE</th>"
            f"<th>DevOps</th><th>Design</th></tr>{rows}</table>"
        )

    mod_html = ""
    if mod_stories:
        rows = "".join(
            f"<tr><td>{s.get('original_id','?')}</td>"
            f"<td>{s.get('original_title','?')}</td>"
            f"<td>{s.get('change_description','')}</td></tr>"
            for s in mod_stories
        )
        mod_html = (
            "<h4>Modified Stories</h4>"
            f"<table><tr><th>ID</th><th>Title</th><th>Change</th></tr>{rows}</table>"
        )

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    cr_description = f"""
<h3>{cr_id}: {analysis.get('summary', 'Change request')}</h3>
<p><b>Date:</b> {now}</p>
<p><b>Classification:</b> {analysis.get('classification', 'unknown')}</p>
<p><b>Risk:</b> {impact.get('risk_assessment', 'Unknown')}</p>

<h4>Impact</h4>
<table>
<tr><td><b>Effort delta</b></td><td>{delta_days} days</td></tr>
<tr><td><b>Cost delta</b></td><td>${delta_cost:+,.0f}</td></tr>
<tr><td><b>Timeline</b></td><td>{impact.get('timeline_impact', 'Unknown')}</td></tr>
</table>

{new_html}
{mod_html}

<h4>Original Request</h4>
<blockquote>{change_text[:500]}{'...' if len(change_text) > 500 else ''}</blockquote>

<p><b>Recommendation:</b> {analysis.get('recommendation', '')}</p>
""".strip()

    try:
        result = ado_client.create_work_item(
            config, "Feature",
            f"{cr_id}: {analysis.get('summary', 'Change request')}",
            description=cr_description,
            tags=f"change-request;{cr_id};{project_name}",
            parent_id=changelog_epic_id,
            extra_fields={
                "Microsoft.VSTS.Scheduling.Effort": delta_days,
            },
        )
        click.secho(f"  ✓ Created CR item #{result.get('id')} under Change Log epic", fg="green")
    except Exception as e:
        click.secho(f"  ⚠ Failed to create CR item: {e}", fg="yellow")

    # Update epic summary
    _update_changelog_epic_summary(config, changelog_epic_id, proj, analysis)
    click.secho("  ✓ Changelog updated", fg="green")


def summarize_breakdown(breakdown: dict) -> str:
    """Create compact text summary of a breakdown for change analysis."""
    lines = []
    for epic in breakdown.get("epics", []):
        lines.append(f"\nEPIC: {epic.get('name', '?')}")
        for feature in epic.get("features", []):
            lines.append(f"  FEATURE: {feature.get('name', '?')}")
            for story in feature.get("stories", []):
                sid = story.get("id", "?")
                title = story.get("title", "?")
                fe = story.get("fe_days", 0)
                be = story.get("be_days", 0)
                ac = story.get("acceptance_criteria", "")
                if isinstance(ac, list):
                    ac = "; ".join(ac)
                ac = ac[:80]
                lines.append(f"    {sid}: {title} (FE:{fe}d BE:{be}d) — {ac}")
    return "\n".join(lines)


def _update_changelog_epic_summary(config, epic_id: int, proj: dict, latest: dict) -> None:
    """Update the Change Log epic description with a running summary table."""
    changes = proj.get("changes", [])
    all_changes = changes + [{
        "id": latest.get("id", "?"),
        "summary": latest.get("summary", ""),
        "cost_delta": latest.get("impact", {}).get("total_delta_cost", 0),
        "approved": True,
    }]

    rows = ""
    total_cost = 0
    for cr in all_changes:
        cost = cr.get("cost_delta", 0)
        total_cost += cost
        status = "Approved" if cr.get("approved") else "Pending"
        rows += (
            f"<tr><td>{status}</td><td>{cr.get('id', '?')}</td>"
            f"<td>{cr.get('summary', '')[:60]}</td>"
            f"<td>${cost:+,.0f}</td></tr>"
        )

    summary_html = f"""
<h3>Change Log Summary — {proj.get('project', '')}</h3>
<p><b>Total change requests:</b> {len(all_changes)}</p>
<p><b>Total cost impact:</b> ${total_cost:+,.0f}</p>

<table>
<tr><th>Status</th><th>ID</th><th>Summary</th><th>Cost Impact</th></tr>
{rows}
<tr><td colspan="3"><b>Total</b></td><td><b>${total_cost:+,.0f}</b></td></tr>
</table>
""".strip()

    try:
        ado_client.update_work_item(
            config, epic_id,
            {"System.Description": summary_html},
        )
    except Exception:
        pass  # Non-critical
