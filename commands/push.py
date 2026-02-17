"""Push command: create work items in Azure DevOps from push_ready.json.

Reads pre-generated user stories and acceptance criteria from push_ready.json
(generated in conversation before running this command).
Falls back to breakdown.json if push_ready.json doesn't exist.
Creates Epics → Features → User Stories (with discipline Tasks) in ADO.

Reliability features:
- Resume: loads existing ado_mapping.json and skips already-created items
- Dedup: queries ADO for existing Epics/Features before creating new ones
- Incremental save: writes ado_mapping.json after each story creation
"""

import json
import click

from core.config import get_output_path, update_state
from core.context import invalidate_downstream
from core import ado as ado_client


def run(proj: dict, dry_run: bool = False) -> None:
    """Push stories to Azure DevOps from push_ready.json (or breakdown.json fallback)."""
    project_name = proj["project"]
    click.secho(f"\n  Pushing to Azure DevOps for '{project_name}'", bold=True)

    if dry_run:
        click.secho("  [DRY RUN — no changes will be made to ADO]\n", fg="yellow")

    # Load data source
    push_data, source_name = _load_data(proj)
    if not push_data:
        return
    click.echo(f"  Source: {source_name}")

    # Test ADO connection and fetch existing items for dedup
    config = None
    existing_items = {"epics": {}, "features": {}}
    if not dry_run:
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

        # Ensure Azure Repos repository exists for feature code generation
        click.echo("  Ensuring Azure Repos repository exists...")
        try:
            repo = ado_client.ensure_repository(config, project_name)
            repo_url = repo.get("remoteUrl", "")
            if repo_url:
                click.secho(f"  ✓ Repository ready: {repo_url}", fg="green")
            else:
                click.secho(f"  ✓ Repository '{project_name}' exists", fg="green")
        except Exception as e:
            click.secho(f"  ⚠ Could not create repository: {e}", fg="yellow")
            click.echo("    Feature code generation will need a repo later.")

        # Query existing Epics/Features to avoid creating duplicates
        click.echo("  Checking for existing work items...")
        existing_items = _fetch_existing_items(config)
        e_count = len(existing_items["epics"])
        f_count = len(existing_items["features"])
        if e_count or f_count:
            click.echo(f"    Found {e_count} epics, {f_count} features already in ADO")

    # Load existing mapping for resume support (survives partial failures)
    created = _load_existing_mapping(proj)
    created_story_ids = {s["id"] for s in created.get("stories", [])}

    # Count totals and determine what's already done
    total_stories = sum(
        len(feature.get("stories", []))
        for epic in push_data.get("epics", [])
        for feature in epic.get("features", [])
    )
    total_epics = len(push_data.get("epics", []))
    total_features = sum(len(e.get("features", [])) for e in push_data.get("epics", []))

    skip_count = sum(
        1 for epic in push_data.get("epics", [])
        for feature in epic.get("features", [])
        for story in feature.get("stories", [])
        if story.get("id", "") in created_story_ids
    )

    click.echo(f"\n  Total: {total_epics} epics, {total_features} features, {total_stories} stories")
    if skip_count:
        click.secho(
            f"  Resuming: {skip_count} stories already created, "
            f"{total_stories - skip_count} remaining",
            fg="yellow",
        )
    if not dry_run and not click.confirm("  Proceed?", default=True):
        return

    # Main creation loop
    story_index = 0
    new_story_count = 0

    for epic in push_data.get("epics", []):
        epic_name = epic.get("name", "Unknown Epic")
        epic_id_key = epic.get("id", epic_name)
        epic_desc = epic.get("description", "")

        feature_names = [f.get("name", "?") for f in epic.get("features", [])]
        epic_html = (
            f"<h3>{epic_name}</h3>"
            f"<p>{epic_desc}</p>"
            f"<p><b>Features:</b></p><ul>"
            + "".join(f"<li>{fn}</li>" for fn in feature_names)
            + "</ul>"
        )

        click.secho(f"\n  Epic: {epic_name}", fg="cyan", bold=True)

        # Resolve Epic: resume mapping → existing in ADO → create new
        epic_ado_id = created["epics"].get(epic_id_key)
        if epic_ado_id:
            click.echo(f"    ↩ Reusing Epic #{epic_ado_id} (from previous run)")
        elif dry_run:
            epic_ado_id = None
            click.echo(f"    [DRY RUN] Would create Epic: {epic_name}")
        elif epic_name in existing_items["epics"]:
            epic_ado_id = existing_items["epics"][epic_name]
            created["epics"][epic_id_key] = epic_ado_id
            click.echo(f"    ↩ Reusing existing ADO Epic #{epic_ado_id}")
        else:
            result = ado_client.create_work_item(
                config, "Epic", epic_name,
                description=epic_html,
                tags="Claude New Epic",
            )
            epic_ado_id = result.get("id")
            created["epics"][epic_id_key] = epic_ado_id
            click.echo(f"    ✓ Created Epic #{epic_ado_id}")

        for feature in epic.get("features", []):
            feat_name = feature.get("name", "Unknown Feature")
            feat_id_key = feature.get("id", feat_name)

            story_names = [s.get("title", "?") for s in feature.get("stories", [])]
            feat_html = (
                f"<h4>{feat_name}</h4>"
                f"<p><b>Stories:</b></p><ul>"
                + "".join(f"<li>{sn}</li>" for sn in story_names)
                + "</ul>"
            )

            click.echo(f"    Feature: {feat_name}")

            # Resolve Feature: resume mapping → existing in ADO → create new
            feat_ado_id = created["features"].get(feat_id_key)
            if feat_ado_id:
                click.echo(f"      ↩ Reusing Feature #{feat_ado_id} (from previous run)")
            elif dry_run:
                feat_ado_id = None
                click.echo(f"      [DRY RUN] Would create Feature: {feat_name}")
            elif feat_name in existing_items["features"]:
                feat_ado_id = existing_items["features"][feat_name]
                created["features"][feat_id_key] = feat_ado_id
                click.echo(f"      ↩ Reusing existing ADO Feature #{feat_ado_id}")
            else:
                result = ado_client.create_work_item(
                    config, "Feature", feat_name,
                    description=feat_html,
                    tags="Claude New Feature",
                    parent_id=epic_ado_id,
                )
                feat_ado_id = result.get("id")
                created["features"][feat_id_key] = feat_ado_id
                click.echo(f"      ✓ Created Feature #{feat_ado_id}")

            for story in feature.get("stories", []):
                story_index += 1
                story_title = story.get("title", "Unknown Story")
                story_id = story.get("id", f"US-{story_index:03d}")

                # Skip if already created (resume support)
                if story_id in created_story_ids:
                    click.echo(
                        f"      [{story_index}/{total_stories}] "
                        f"{story_title} — already created, skipping"
                    )
                    continue

                click.echo(f"      [{story_index}/{total_stories}] {story_title}")

                # Read user story and AC from push_ready.json fields;
                # fallback: breakdown.json has acceptance_criteria as a string
                user_story_text = story.get("user_story", f"As a user,\nI want to {story_title.lower()},\nSo that I can accomplish this goal.")
                ac_list = story.get("acceptance_criteria", [])

                # Effort
                fe = story.get("fe_days", 0)
                be = story.get("be_days", 0)
                devops = story.get("devops_days", 0)
                design = story.get("design_days", 0)
                total = fe + be + devops + design

                description_html = _build_story_description(
                    user_story_text, epic_name, feat_name
                )
                tech_ctx = story.get("technical_context", {})
                ac_html = _build_ac_html(ac_list, tech_ctx)

                if dry_run:
                    click.echo(f"        [DRY RUN] Would create User Story: {story_title}")
                    click.echo(f"        User story: {user_story_text[:100]}...")
                else:
                    result = ado_client.create_work_item(
                        config, "User Story", story_title,
                        description=description_html,
                        tags="Claude New Story",
                        parent_id=feat_ado_id,
                        extra_fields={
                            "Microsoft.VSTS.Scheduling.Effort": total,
                            "Microsoft.VSTS.Common.AcceptanceCriteria": ac_html,
                        },
                    )
                    story_ado_id = result.get("id")
                    click.secho(f"        ✓ Created Story #{story_ado_id}", fg="green")

                    # Create discipline tasks
                    _create_tasks(config, project_name, story_ado_id, story_title, story)

                    created["stories"].append({
                        "ado_id": story_ado_id,
                        "id": story_id,
                        "title": story_title,
                        "epic": epic_name,
                        "feature": feat_name,
                    })
                    created_story_ids.add(story_id)
                    new_story_count += 1

                    # Save mapping incrementally — progress survives failures
                    _save_mapping(proj, created)

    # Final mapping save (captures Epic/Feature-only changes from reuse)
    _save_mapping(proj, created)
    mapping_path = get_output_path(proj, "ado_mapping.json")

    # Create story relation links (predecessors + similar stories)
    if not dry_run:
        _create_relation_links(config, push_data, created)

    # Update state
    if not dry_run:
        invalidate_downstream(proj, "push")
        update_state(proj, ado_pushed=True)

    click.secho(f"\n  ✓ Push complete", fg="green", bold=True)
    click.echo(f"    Created: {new_story_count} new stories")
    if skip_count:
        click.echo(f"    Skipped: {skip_count} already-created stories")
    click.echo(f"    Mapping: {mapping_path}")
    click.echo(f"\n    Next: extract design system from Figma or generate feature code.")


# --- Resume and dedup helpers ---

def _fetch_existing_items(config) -> dict:
    """Fetch existing Epics and Features from ADO for duplicate detection.

    Only queries the current project to avoid cross-project matches.
    Returns {"epics": {title: ado_id}, "features": {title: ado_id}}.
    """
    project = config.project
    wiql = (
        "SELECT [System.Id], [System.Title], [System.WorkItemType] "
        "FROM WorkItems WHERE [System.WorkItemType] IN ('Epic', 'Feature') "
        "AND [System.State] <> 'Removed' "
        f"AND [System.TeamProject] = '{project}' "
        "ORDER BY [System.Id] ASC"
    )
    try:
        items = ado_client.get_work_items_by_query(config, wiql)
    except Exception as e:
        click.secho(f"    ⚠ Could not query existing items: {e}", fg="yellow")
        return {"epics": {}, "features": {}}

    epics = {}
    features = {}
    for item in items:
        fields = item.get("fields", {})
        wit = fields.get("System.WorkItemType", "")
        title = fields.get("System.Title", "")
        ado_id = item.get("id")
        if wit == "Epic":
            epics[title] = ado_id
        elif wit == "Feature":
            features[title] = ado_id

    return {"epics": epics, "features": features}


def _load_existing_mapping(proj: dict) -> dict:
    """Load existing ado_mapping.json for resume support.

    If the file exists and is valid, returns its contents so the push
    can skip already-created items. Otherwise returns an empty mapping.
    """
    mapping_path = get_output_path(proj, "ado_mapping.json")
    if mapping_path.exists():
        try:
            with open(mapping_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            # Validate structure
            if (isinstance(data.get("epics"), dict)
                    and isinstance(data.get("features"), dict)
                    and isinstance(data.get("stories"), list)):
                return data
        except (json.JSONDecodeError, KeyError):
            pass
    return {"epics": {}, "features": {}, "stories": []}


def _save_mapping(proj: dict, created: dict) -> None:
    """Save ado_mapping.json incrementally after each story creation."""
    mapping_path = get_output_path(proj, "ado_mapping.json")
    with open(mapping_path, "w", encoding="utf-8") as f:
        json.dump(created, f, indent=2)


# --- Task and relation helpers ---

def _create_tasks(config, project_name: str, parent_id: int,
                   story_title: str, story: dict) -> None:
    """Create FE / BE / DevOps tasks as children of the user story."""
    disciplines = [
        ("fe_days", "FE"),
        ("be_days", "BE"),
        ("devops_days", "DevOps"),
    ]
    for field, prefix in disciplines:
        days = story.get(field, 0)
        if days and days > 0:
            task_title = f"[{prefix}] {story_title}"
            try:
                ado_client.create_work_item(
                    config, "Task", task_title,
                    parent_id=parent_id,
                    tags="Claude New Story",
                    extra_fields={
                        "Microsoft.VSTS.Scheduling.Effort": days,
                    },
                )
            except Exception as e:
                click.secho(f"          ⚠ Failed to create {prefix} task: {e}", fg="yellow")


def _create_relation_links(config, push_data: dict, created: dict) -> None:
    """Create predecessor and similar-story links between ADO work items.

    Reads 'predecessors' and 'similar_stories' arrays from each story in
    push_data, maps local IDs (e.g. US-001) to ADO IDs using the created
    mapping, and creates the appropriate ADO links.
    """
    # Build local ID → ADO ID mapping
    id_to_ado = {}
    for story_info in created.get("stories", []):
        id_to_ado[story_info["id"]] = story_info["ado_id"]

    link_count = 0

    for epic in push_data.get("epics", []):
        for feature in epic.get("features", []):
            for story in feature.get("stories", []):
                story_local_id = story.get("id", "")
                story_ado_id = id_to_ado.get(story_local_id)
                if not story_ado_id:
                    continue

                # Predecessor links
                for pred_id in story.get("predecessors", []):
                    pred_ado_id = id_to_ado.get(pred_id)
                    if pred_ado_id:
                        try:
                            ado_client.add_link(
                                config, story_ado_id, pred_ado_id,
                                "System.LinkTypes.Dependency-Reverse",
                                comment="Predecessor: feature builds on this story's output",
                            )
                            link_count += 1
                        except Exception as e:
                            click.secho(
                                f"    ⚠ Failed to link {story_local_id} → predecessor {pred_id}: {e}",
                                fg="yellow",
                            )

                # Similar story links
                for sim_id in story.get("similar_stories", []):
                    sim_ado_id = id_to_ado.get(sim_id)
                    if sim_ado_id:
                        try:
                            ado_client.add_link(
                                config, story_ado_id, sim_ado_id,
                                "System.LinkTypes.Related",
                                comment="Similar: same pattern/approach as this story",
                            )
                            link_count += 1
                        except Exception as e:
                            click.secho(
                                f"    ⚠ Failed to link {story_local_id} → similar {sim_id}: {e}",
                                fg="yellow",
                            )

    if link_count > 0:
        click.secho(f"    ✓ Created {link_count} story relation links", fg="green")


# --- HTML builders ---

def _build_story_description(user_story: str, epic: str, feature: str) -> str:
    """Build HTML description — user story text only, three lines, no italic."""
    # Convert newlines to <br> for three-line display — no extra \n or <p> wrapper
    # to avoid ADO rendering extra gaps between lines
    html_text = user_story.replace("\n", "<br>")
    return html_text


def _build_ac_html(ac_list, technical_context: dict | None = None) -> str:
    """Build HTML for acceptance criteria + optional technical context block.

    No Change Log is added on initial creation — it only appears
    when the story is later modified (change request, scope revision, etc.).

    Accepts two formats:
    - New: list of dicts with 'title' and 'items' keys
    - Legacy: list of strings or a single string
    """
    if isinstance(ac_list, str):
        ac_html = f"<p>{ac_list}</p>"
    elif isinstance(ac_list, list) and ac_list:
        # New structured format: list of {title, items}
        if isinstance(ac_list[0], dict):
            parts = []
            for i, group in enumerate(ac_list, 1):
                title = group.get("title", f"Criterion {i}")
                items_html = "".join(
                    f"<li>{item}</li>" for item in group.get("items", [])
                )
                parts.append(
                    f"<b>AC {i}:</b> {title}<br><ul>{items_html}</ul>"
                )
            ac_html = "".join(parts)
        else:
            # Legacy format: list of strings
            parts = []
            for i, ac in enumerate(ac_list, 1):
                if ac:
                    parts.append(f"<b>AC {i}:</b> {ac}<br><ul><li>{ac}</li></ul>")
            ac_html = "".join(parts)
    else:
        ac_html = "<p>To be defined when designs are ready.</p>"

    # Append technical context block if present
    if technical_context:
        ac_html += _build_technical_context_html(technical_context)

    return ac_html


def _build_technical_context_html(ctx: dict) -> str:
    """Build HTML for the Technical Context block appended after AC groups.

    This structured block is consumed by Claude Code during feature code
    generation. It provides data model, states, interactions, navigation,
    and API hints so the generated code is complete from the start.
    """
    sections = [
        ("Data Model", ctx.get("data_model", [])),
        ("States", ctx.get("states", [])),
        ("Interactions", ctx.get("interactions", [])),
        ("Navigation", ctx.get("navigation", [])),
        ("API Hints", ctx.get("api_hints", [])),
    ]

    # Skip if all sections are empty
    if not any(items for _, items in sections):
        return ""

    parts = ['<hr><b>Technical Context</b><br><br>']
    for title, items in sections:
        if items:
            items_html = "".join(f"<li>{item}</li>" for item in items)
            parts.append(f"<b>{title}:</b><br><ul>{items_html}</ul>")

    return "".join(parts)


# --- Data loading ---

def _load_data(proj: dict) -> tuple[dict | None, str]:
    """Load push_ready.json, falling back to breakdown.json."""
    # Try push_ready.json first
    pr_path = get_output_path(proj, "push_ready.json")
    if pr_path.exists():
        try:
            with open(pr_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "epics" in data:
                return data, "push_ready.json"
        except json.JSONDecodeError as e:
            click.secho(f"  ⚠ Failed to parse push_ready.json: {e}", fg="yellow")

    # Fallback to breakdown.json
    bd_path = get_output_path(proj, "breakdown.json")
    if bd_path.exists():
        try:
            with open(bd_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "epics" in data:
                click.secho("  ℹ Using breakdown.json (push_ready.json not found)", fg="yellow")
                return data, "breakdown.json"
        except json.JSONDecodeError as e:
            click.secho(f"  ✗ Failed to parse breakdown.json: {e}", fg="red")

    click.secho("  ✗ No data source found.", fg="red")
    click.echo("    Generate push_ready.json in conversation, or ensure breakdown.json exists.")
    return None, ""
