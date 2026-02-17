"""Azure DevOps MCP server — exposes ADO operations as Claude Code tools."""

import json
import os
import sys

# Add project root to path so we can import core.ado
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mcp.server.fastmcp import FastMCP

from core import ado
from core.ado import AdoConfig

server = FastMCP(
    "Azure DevOps",
    instructions=(
        "ADO tools for managing work items, wikis, and repositories. "
        "All tools read ADO_ORGANIZATION, ADO_PROJECT, ADO_PAT from environment."
    ),
)


def _get_config() -> AdoConfig:
    """Build AdoConfig from environment variables."""
    org = os.environ.get("ADO_ORGANIZATION", "")
    project = os.environ.get("ADO_PROJECT", "")
    pat = os.environ.get("ADO_PAT", "")
    if not all([org, project, pat]):
        raise ValueError(
            "Missing environment variables. Set ADO_ORGANIZATION, ADO_PROJECT, and ADO_PAT."
        )
    return AdoConfig(organization=org, project=project, pat=pat)


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------

@server.tool()
def ado_test_connection() -> dict:
    """Test ADO connectivity. Returns project info on success."""
    try:
        config = _get_config()
        import urllib.parse
        url = (
            f"https://dev.azure.com/{config.organization}/_apis/projects/"
            f"{urllib.parse.quote(config.project, safe='')}?api-version={ado.ADO_API_VERSION}"
        )
        result = ado._api_request(config, url, method="GET")
        return {"ok": True, "project": result.get("name"), "id": result.get("id")}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Work Items — Read
# ---------------------------------------------------------------------------

@server.tool()
def ado_get_work_item(work_item_id: int, expand: str = "relations") -> dict:
    """
    Fetch a single work item by ID with full field data and relations.

    Returns raw ADO response including fields, relations, and all HTML content
    with exact encoding preserved. Use this to inspect AC HTML before modifications.

    Args:
        work_item_id: The ADO work item ID (e.g. 1464)
        expand: Expansion — "relations" (default), "fields", "all", or "none"
    """
    try:
        config = _get_config()
        return ado.get_work_item(config, work_item_id, expand=expand)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def ado_query_work_items(wiql: str) -> dict:
    """
    Run a WIQL query and return matching work items with full details.

    Args:
        wiql: WIQL query string, e.g.
            "SELECT [System.Id] FROM WorkItems WHERE [System.WorkItemType] = 'User Story'"
    """
    try:
        config = _get_config()
        items = ado.get_work_items_by_query(config, wiql)
        return {"count": len(items), "items": items}
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def ado_get_child_work_items(parent_id: int) -> dict:
    """
    Get child work items (tasks) of a parent work item.

    Args:
        parent_id: ID of the parent work item
    """
    try:
        config = _get_config()
        children = ado.get_child_work_items(config, parent_id)
        return {"count": len(children), "items": children}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Work Items — Create & Update
# ---------------------------------------------------------------------------

@server.tool()
def ado_create_work_item(
    work_item_type: str,
    title: str,
    description: str = "",
    tags: str = "",
    parent_id: int | None = None,
    extra_fields: str = "{}",
) -> dict:
    """
    Create a new work item (Epic, Feature, User Story, or Task).

    Args:
        work_item_type: "Epic", "Feature", "User Story", or "Task"
        title: Work item title
        description: HTML description
        tags: Semicolon-separated tags (e.g. "Claude New Story")
        parent_id: Parent work item ID for hierarchy link
        extra_fields: JSON string of additional field path → value pairs, e.g.
            '{"Microsoft.VSTS.Common.AcceptanceCriteria": "<b>AC 1:</b>..."}'
    """
    try:
        config = _get_config()
        fields = json.loads(extra_fields) if extra_fields else {}
        result = ado.create_work_item(
            config,
            work_item_type=work_item_type,
            title=title,
            description=description,
            tags=tags,
            parent_id=parent_id,
            extra_fields=fields,
        )
        return result
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def ado_update_work_item_fields(work_item_id: int, fields: str) -> dict:
    """
    Update field values on an existing work item.

    Args:
        work_item_id: ID of the work item to update
        fields: JSON string of field path → value pairs, e.g.
            '{"System.Title": "New Title", "Microsoft.VSTS.Common.AcceptanceCriteria": "..."}'
    """
    try:
        config = _get_config()
        field_dict = json.loads(fields)
        return ado.update_work_item(config, work_item_id, field_dict)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def ado_update_work_item_raw(work_item_id: int, patches: str) -> dict:
    """
    Send a raw JSON Patch array to update a work item.

    Use this for complex updates that combine field changes and relation additions
    in a single API call. Accepts any valid JSON Patch operations.

    Args:
        work_item_id: ID of the work item to update
        patches: JSON string of patch operations array, e.g.
            '[{"op": "add", "path": "/fields/System.Title", "value": "New Title"},
              {"op": "add", "path": "/relations/-", "value": {"rel": "...", "url": "..."}}]'
    """
    try:
        config = _get_config()
        patch_list = json.loads(patches)
        return ado.update_work_item_raw(config, work_item_id, patch_list)
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Work Items — Links
# ---------------------------------------------------------------------------

@server.tool()
def ado_add_link(
    source_id: int,
    target_id: int,
    link_type: str,
    comment: str = "",
) -> dict:
    """
    Add a relation link between two work items.

    Args:
        source_id: ID of the work item to add the link to
        target_id: ID of the work item to link to
        link_type: ADO link type, e.g.
            "System.LinkTypes.Hierarchy-Reverse" (parent)
            "System.LinkTypes.Dependency-Reverse" (predecessor)
            "System.LinkTypes.Dependency-Forward" (successor)
            "System.LinkTypes.Related" (related)
        comment: Optional comment describing the relationship
    """
    try:
        config = _get_config()
        return ado.add_link(config, source_id, target_id, link_type, comment)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def ado_add_artifact_link(
    work_item_id: int,
    artifact_uri: str,
    name: str = "Branch",
    comment: str = "",
) -> dict:
    """
    Add an ArtifactLink (branch link) to a work item's Development section.

    Args:
        work_item_id: ID of the work item
        artifact_uri: vstfs:///Git/Ref/{projectId}%2F{repoId}%2FGB{urlEncodedBranch}
        name: Link name, typically "Branch"
        comment: Optional comment
    """
    try:
        config = _get_config()
        return ado.add_artifact_link(config, work_item_id, artifact_uri, name, comment)
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

@server.tool()
def ado_list_repositories() -> dict:
    """List all Git repositories in the ADO project."""
    try:
        config = _get_config()
        repos = ado.list_repositories(config)
        return {"count": len(repos), "repositories": repos}
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def ado_ensure_repository(repo_name: str) -> dict:
    """
    Ensure a Git repository exists in the ADO project. Creates it if missing.

    Args:
        repo_name: Name of the repository to ensure exists
    """
    try:
        config = _get_config()
        return ado.ensure_repository(config, repo_name)
    except Exception as e:
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Wiki
# ---------------------------------------------------------------------------

@server.tool()
def ado_get_wiki_page(wiki_id: str, path: str) -> dict:
    """
    Read a wiki page's content and ETag.

    Returns {"content": "...", "etag": "..."} on success,
    or {"error": "Page not found", "status": 404} if the page doesn't exist.

    Args:
        wiki_id: Wiki identifier (name or ID)
        path: Page path, e.g. "/Product Overview"
    """
    try:
        config = _get_config()
        return ado.get_wiki_page(config, wiki_id, path)
    except Exception as e:
        return {"error": str(e)}


@server.tool()
def ado_upsert_wiki_page(
    wiki_id: str,
    path: str,
    content: str,
    etag: str = "",
) -> dict:
    """
    Create or update a wiki page.

    For updates, provide the etag from a previous ado_get_wiki_page call.
    For new pages, omit etag or pass empty string.

    Args:
        wiki_id: Wiki identifier (name or ID)
        path: Page path, e.g. "/Product Overview"
        content: Markdown content for the page
        etag: ETag for updates (from ado_get_wiki_page). Empty = create new.
    """
    try:
        config = _get_config()
        return ado.upsert_wiki_page(
            config, wiki_id, path, content,
            etag=etag if etag else None,
        )
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    server.run()
