"""Azure DevOps REST API client for work item management."""

import json
import logging
import time
import base64
import urllib.parse
import urllib.request
import urllib.error
from dataclasses import dataclass

logger = logging.getLogger(__name__)


ADO_API_VERSION = "7.1"
RATE_LIMIT_DELAY = 0.3  # seconds between API calls to avoid throttling

# Module-level API call counter for usage tracking
_call_count = 0
_call_total_seconds = 0.0


def reset_call_counter() -> None:
    """Reset the API call counter and timer to zero."""
    global _call_count, _call_total_seconds
    _call_count = 0
    _call_total_seconds = 0.0


def get_call_stats() -> dict:
    """Return current API call count and total elapsed seconds."""
    return {"count": _call_count, "total_seconds": round(_call_total_seconds, 2)}


@dataclass
class AdoConfig:
    """ADO connection configuration."""
    organization: str
    project: str
    pat: str

    @property
    def base_url(self) -> str:
        proj = urllib.parse.quote(self.project, safe="")
        return f"https://dev.azure.com/{self.organization}/{proj}/_apis"

    @property
    def auth_header(self) -> str:
        token = base64.b64encode(f":{self.pat}".encode()).decode()
        return f"Basic {token}"


def from_project(proj: dict) -> AdoConfig:
    """Create AdoConfig from project config dict."""
    ado = proj.get("ado", {})
    org = ado.get("organization", "")
    project = ado.get("project", "")
    pat = ado.get("pat", "")
    if not all([org, project, pat]):
        raise ValueError(
            "ADO not configured. Ensure ado.organization, ado.project, and ado.pat "
            "are set in project.yaml"
        )
    return AdoConfig(organization=org, project=project, pat=pat)


def create_work_item(
    config: AdoConfig,
    work_item_type: str,
    title: str,
    description: str = "",
    tags: str = "",
    parent_id: int | None = None,
    extra_fields: dict | None = None,
) -> dict:
    """
    Create a work item in Azure DevOps.

    Args:
        config: ADO connection config
        work_item_type: "Epic", "Feature", or "User Story"
        title: Work item title
        description: HTML description
        tags: Semicolon-separated tags
        parent_id: Parent work item ID for hierarchy
        extra_fields: Additional field path → value pairs

    Returns:
        Created work item dict from ADO API
    """
    wit_encoded = urllib.parse.quote(work_item_type, safe="")
    url = f"{config.base_url}/wit/workitems/${wit_encoded}?api-version={ADO_API_VERSION}"

    # Build patch document
    patches = [
        {"op": "add", "path": "/fields/System.Title", "value": title},
    ]

    if description:
        patches.append({
            "op": "add",
            "path": "/fields/System.Description",
            "value": description,
        })

    if tags:
        patches.append({
            "op": "add",
            "path": "/fields/System.Tags",
            "value": tags,
        })

    if parent_id is not None:
        patches.append({
            "op": "add",
            "path": "/relations/-",
            "value": {
                "rel": "System.LinkTypes.Hierarchy-Reverse",
                "url": f"https://dev.azure.com/{config.organization}/_apis/wit/workItems/{parent_id}",
            },
        })

    if extra_fields:
        for field_path, value in extra_fields.items():
            if not field_path.startswith("/fields/"):
                field_path = f"/fields/{field_path}"
            patches.append({"op": "add", "path": field_path, "value": value})

    return _api_request(config, url, method="POST", body=patches,
                        content_type="application/json-patch+json")


def update_work_item(
    config: AdoConfig,
    work_item_id: int,
    fields: dict,
) -> dict:
    """
    Update fields on an existing work item.

    Args:
        config: ADO connection config
        work_item_id: ID of work item to update
        fields: field path → value pairs to update

    Returns:
        Updated work item dict
    """
    url = f"{config.base_url}/wit/workitems/{work_item_id}?api-version={ADO_API_VERSION}"

    patches = []
    for field_path, value in fields.items():
        if not field_path.startswith("/fields/"):
            field_path = f"/fields/{field_path}"
        patches.append({"op": "add", "path": field_path, "value": value})

    return _api_request(config, url, method="PATCH", body=patches,
                        content_type="application/json-patch+json")


def add_link(
    config: AdoConfig,
    source_id: int,
    target_id: int,
    link_type: str,
    comment: str = "",
) -> dict:
    """
    Add a relation link between two work items.

    Args:
        config: ADO connection config
        source_id: ID of the work item to add the link to
        target_id: ID of the work item to link to
        link_type: ADO link type, e.g.:
            - "System.LinkTypes.Dependency-Reverse" (Predecessor)
            - "System.LinkTypes.Dependency-Forward" (Successor)
            - "System.LinkTypes.Related" (Related)
        comment: Optional comment describing the relationship

    Returns:
        Updated work item dict
    """
    url = f"{config.base_url}/wit/workitems/{source_id}?api-version={ADO_API_VERSION}"

    link_value = {
        "rel": link_type,
        "url": f"https://dev.azure.com/{config.organization}/_apis/wit/workItems/{target_id}",
    }
    if comment:
        link_value["attributes"] = {"comment": comment}

    patches = [
        {"op": "add", "path": "/relations/-", "value": link_value},
    ]

    return _api_request(config, url, method="PATCH", body=patches,
                        content_type="application/json-patch+json")


def get_work_items_by_query(config: AdoConfig, wiql: str) -> list[dict]:
    """
    Query work items using WIQL (Work Item Query Language).

    Args:
        config: ADO connection config
        wiql: WIQL query string

    Returns:
        List of work item dicts with full details
    """
    url = f"{config.base_url}/wit/wiql?api-version={ADO_API_VERSION}"
    result = _api_request(config, url, method="POST", body={"query": wiql})

    work_items = result.get("workItems", [])
    if not work_items:
        return []

    # Fetch full details in batches of 200
    ids = [wi["id"] for wi in work_items]
    detailed = []
    for i in range(0, len(ids), 200):
        batch = ids[i:i + 200]
        id_str = ",".join(str(x) for x in batch)
        detail_url = (
            f"{config.base_url}/wit/workitems?ids={id_str}"
            f"&$expand=relations&api-version={ADO_API_VERSION}"
        )
        batch_result = _api_request(config, detail_url, method="GET")
        detailed.extend(batch_result.get("value", []))

    return detailed


def get_all_stories(config: AdoConfig, tag_filter: str | None = None) -> list[dict]:
    """Get all user stories, optionally filtered by tag."""
    wiql = (
        "SELECT [System.Id], [System.Title], [System.Description], "
        "[System.Tags], [System.State] "
        "FROM WorkItems WHERE [System.WorkItemType] = 'User Story'"
    )
    if tag_filter:
        wiql += f" AND [System.Tags] CONTAINS '{tag_filter}'"
    wiql += " ORDER BY [System.Id] ASC"

    return get_work_items_by_query(config, wiql)


def get_all_work_items(config: AdoConfig) -> dict:
    """
    Get all epics, features, and stories organized hierarchically.

    Returns:
        {
            "epics": [{"id": ..., "title": ..., "features": [...]}],
            "features": [...],
            "stories": [...]
        }
    """
    wiql = (
        "SELECT [System.Id], [System.Title], [System.WorkItemType], "
        "[System.Description], [System.Tags], [System.State] "
        "FROM WorkItems WHERE [System.WorkItemType] IN ('Epic', 'Feature', 'User Story') "
        "ORDER BY [System.WorkItemType] ASC, [System.Id] ASC"
    )
    items = get_work_items_by_query(config, wiql)

    epics = []
    features = []
    stories = []

    for item in items:
        fields = item.get("fields", {})
        wit = fields.get("System.WorkItemType", "")
        entry = {
            "id": item.get("id"),
            "title": fields.get("System.Title", ""),
            "description": fields.get("System.Description", ""),
            "tags": fields.get("System.Tags", ""),
            "state": fields.get("System.State", ""),
            "type": wit,
        }
        if wit == "Epic":
            epics.append(entry)
        elif wit == "Feature":
            features.append(entry)
        elif wit == "User Story":
            stories.append(entry)

    return {"epics": epics, "features": features, "stories": stories}


def test_connection(config: AdoConfig) -> bool:
    """Test ADO connection by fetching project info."""
    try:
        url = (
            f"https://dev.azure.com/{config.organization}/_apis/projects/"
            f"{urllib.parse.quote(config.project, safe='')}?api-version={ADO_API_VERSION}"
        )
        result = _api_request(config, url, method="GET")
        return "id" in result
    except Exception:
        return False


def upload_attachment(
    config: AdoConfig,
    work_item_id: int,
    file_path: str,
    filename: str | None = None,
    comment: str = "",
) -> dict:
    """
    Upload a file as an attachment to an ADO work item.

    Two-step process:
    1. Upload the file to get an attachment URL
    2. Link the attachment to the work item

    Args:
        config: ADO connection config
        work_item_id: ID of the work item to attach to
        file_path: Local path to the file
        filename: Display name (defaults to basename of file_path)
        comment: Optional comment for the attachment

    Returns:
        Attachment metadata dict from ADO API
    """
    from pathlib import Path
    fp = Path(file_path)
    if not fp.exists():
        raise FileNotFoundError(f"Attachment file not found: {file_path}")

    if not filename:
        filename = fp.name

    # Step 1: Upload the file blob
    encoded_name = urllib.parse.quote(filename, safe="")
    upload_url = (
        f"https://dev.azure.com/{config.organization}/{urllib.parse.quote(config.project, safe='')}/"
        f"_apis/wit/attachments?fileName={encoded_name}&api-version={ADO_API_VERSION}"
    )

    file_data = fp.read_bytes()
    headers = {
        "Authorization": config.auth_header,
        "Content-Type": "application/octet-stream",
    }
    req = urllib.request.Request(upload_url, data=file_data, headers=headers, method="POST")

    time.sleep(RATE_LIMIT_DELAY)
    with urllib.request.urlopen(req) as resp:
        upload_result = json.loads(resp.read().decode("utf-8"))

    attachment_url = upload_result.get("url", "")

    # Step 2: Link the attachment to the work item
    patches = [{
        "op": "add",
        "path": "/relations/-",
        "value": {
            "rel": "AttachedFile",
            "url": attachment_url,
            "attributes": {"comment": comment or filename},
        },
    }]

    wi_url = f"{config.base_url}/wit/workitems/{work_item_id}?api-version={ADO_API_VERSION}"
    return _api_request(config, wi_url, method="PATCH", body=patches,
                        content_type="application/json-patch+json")


def upload_file_blob(config: AdoConfig, file_path: str, filename: str | None = None) -> str:
    """Upload a file blob to ADO and return the attachment URL.

    This is step 1 of the attachment process — uploads the raw bytes.
    Use link_attachment() to then link this URL to one or more work items.
    """
    from pathlib import Path
    fp = Path(file_path)
    if not fp.exists():
        raise FileNotFoundError(f"Attachment file not found: {file_path}")

    if not filename:
        filename = fp.name

    encoded_name = urllib.parse.quote(filename, safe="")
    upload_url = (
        f"https://dev.azure.com/{config.organization}/{urllib.parse.quote(config.project, safe='')}/"
        f"_apis/wit/attachments?fileName={encoded_name}&api-version={ADO_API_VERSION}"
    )

    file_data = fp.read_bytes()
    headers = {
        "Authorization": config.auth_header,
        "Content-Type": "application/octet-stream",
    }
    req = urllib.request.Request(upload_url, data=file_data, headers=headers, method="POST")

    time.sleep(RATE_LIMIT_DELAY)
    with urllib.request.urlopen(req) as resp:
        upload_result = json.loads(resp.read().decode("utf-8"))

    return upload_result.get("url", "")


def link_attachment(config: AdoConfig, work_item_id: int, attachment_url: str,
                    comment: str = "") -> dict:
    """Link an already-uploaded attachment URL to a work item."""
    patches = [{
        "op": "add",
        "path": "/relations/-",
        "value": {
            "rel": "AttachedFile",
            "url": attachment_url,
            "attributes": {"comment": comment},
        },
    }]
    wi_url = f"{config.base_url}/wit/workitems/{work_item_id}?api-version={ADO_API_VERSION}"
    return _api_request(config, wi_url, method="PATCH", body=patches,
                        content_type="application/json-patch+json")


def ensure_repository(config: AdoConfig, repo_name: str) -> dict:
    """Ensure a Git repository exists in the ADO project.

    Checks if a repo with the given name already exists. If not, creates it.
    Returns the repo metadata dict (with 'id', 'name', 'remoteUrl', etc.).
    """
    proj = urllib.parse.quote(config.project, safe="")

    # List existing repos
    list_url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/git/repositories?api-version={ADO_API_VERSION}"
    )
    result = _api_request(config, list_url, method="GET")
    for repo in result.get("value", []):
        if repo.get("name", "").lower() == repo_name.lower():
            return repo

    # Create new repo
    create_url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/git/repositories?api-version={ADO_API_VERSION}"
    )
    body = {"name": repo_name}
    return _api_request(config, create_url, method="POST", body=body)


def get_child_work_items(config: AdoConfig, parent_id: int) -> list[dict]:
    """Get child work items (tasks) of a parent work item."""
    wiql = (
        f"SELECT [System.Id], [System.Title], [System.WorkItemType] "
        f"FROM WorkItemLinks "
        f"WHERE ([Source].[System.Id] = {parent_id}) "
        f"AND ([System.Links.LinkType] = 'System.LinkTypes.Hierarchy-Forward') "
        f"MODE (MustContain)"
    )
    url = f"{config.base_url}/wit/wiql?api-version={ADO_API_VERSION}"
    result = _api_request(config, url, method="POST", body={"query": wiql})

    # Extract target (child) IDs — skip the source itself
    child_ids = []
    for relation in result.get("workItemRelations", []):
        target = relation.get("target", {})
        tid = target.get("id")
        if tid and tid != parent_id:
            child_ids.append(tid)

    if not child_ids:
        return []

    # Fetch details
    id_str = ",".join(str(x) for x in child_ids)
    detail_url = (
        f"{config.base_url}/wit/workitems?ids={id_str}"
        f"&api-version={ADO_API_VERSION}"
    )
    batch_result = _api_request(config, detail_url, method="GET")
    return batch_result.get("value", [])


def get_work_item(
    config: AdoConfig,
    work_item_id: int,
    expand: str = "relations",
) -> dict:
    """
    Fetch a single work item by ID with full field data.

    Args:
        config: ADO connection config
        work_item_id: ID of the work item
        expand: Expansion option — "relations", "fields", "all", or "none"

    Returns:
        Work item dict with fields, relations, etc.
    """
    url = (
        f"{config.base_url}/wit/workitems/{work_item_id}"
        f"?$expand={expand}&api-version={ADO_API_VERSION}"
    )
    return _api_request(config, url, method="GET")


def update_work_item_raw(
    config: AdoConfig,
    work_item_id: int,
    patches: list[dict],
) -> dict:
    """
    Send a raw JSON Patch array to update a work item.

    Unlike update_work_item() which only handles field updates, this accepts
    any valid JSON Patch operations including relations, removals, etc.

    Args:
        config: ADO connection config
        work_item_id: ID of work item to update
        patches: List of JSON Patch operations, e.g.:
            [{"op": "add", "path": "/fields/System.Title", "value": "New Title"},
             {"op": "add", "path": "/relations/-", "value": {...}}]

    Returns:
        Updated work item dict
    """
    url = f"{config.base_url}/wit/workitems/{work_item_id}?api-version={ADO_API_VERSION}"
    return _api_request(config, url, method="PATCH", body=patches,
                        content_type="application/json-patch+json")


def add_artifact_link(
    config: AdoConfig,
    work_item_id: int,
    artifact_uri: str,
    name: str = "Branch",
    comment: str = "",
) -> dict:
    """
    Add an ArtifactLink (e.g. branch link) to a work item.

    This makes the link appear in the Development section of the ADO UI.

    Args:
        config: ADO connection config
        work_item_id: ID of the work item
        artifact_uri: vstfs:///Git/Ref/{projectId}%2F{repoId}%2FGB{branch}
        name: Link name, typically "Branch"
        comment: Optional comment

    Returns:
        Updated work item dict
    """
    url = f"{config.base_url}/wit/workitems/{work_item_id}?api-version={ADO_API_VERSION}"
    link_value = {
        "rel": "ArtifactLink",
        "url": artifact_uri,
        "attributes": {
            "name": name,
        },
    }
    if comment:
        link_value["attributes"]["comment"] = comment

    patches = [{"op": "add", "path": "/relations/-", "value": link_value}]
    return _api_request(config, url, method="PATCH", body=patches,
                        content_type="application/json-patch+json")


def get_wiki_list(config: AdoConfig) -> list[dict]:
    """
    List all wikis in the ADO project.

    Returns:
        List of wiki dicts with id, name, type, etc.
    """
    proj = urllib.parse.quote(config.project, safe="")
    url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/wiki/wikis?api-version={ADO_API_VERSION}"
    )
    result = _api_request(config, url, method="GET")
    return result.get("value", [])


def get_wiki_page(
    config: AdoConfig,
    wiki_id: str,
    path: str,
) -> dict:
    """
    Read a wiki page's content and ETag.

    Args:
        config: ADO connection config
        wiki_id: Wiki identifier (name or ID)
        path: Page path, e.g. "/Product Overview"

    Returns:
        {"content": str, "etag": str} or {"error": str} if not found
    """
    proj = urllib.parse.quote(config.project, safe="")
    encoded_wiki = urllib.parse.quote(wiki_id, safe="")
    encoded_path = urllib.parse.quote(path, safe="/")
    url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/wiki/wikis/{encoded_wiki}/pages?path={encoded_path}"
        f"&includeContent=true&api-version={ADO_API_VERSION}"
    )

    headers = {
        "Authorization": config.auth_header,
        "Content-Type": "application/json",
    }
    req = urllib.request.Request(url, headers=headers, method="GET")

    try:
        time.sleep(RATE_LIMIT_DELAY)
        with urllib.request.urlopen(req) as resp:
            etag = resp.headers.get("ETag", "")
            body = json.loads(resp.read().decode("utf-8"))
            return {"content": body.get("content", ""), "etag": etag}
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {"error": "Page not found", "status": 404}
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(
            f"Wiki page GET error {e.code}: {e.reason}\nResponse: {body_text[:500]}"
        )


def upsert_wiki_page(
    config: AdoConfig,
    wiki_id: str,
    path: str,
    content: str,
    etag: str | None = None,
) -> dict:
    """
    Create or update a wiki page.

    Args:
        config: ADO connection config
        wiki_id: Wiki identifier (name or ID)
        path: Page path, e.g. "/Product Overview"
        content: Markdown content for the page
        etag: If provided, updates existing page (required for updates).
              If None, creates a new page.

    Returns:
        Page metadata dict from ADO API
    """
    proj = urllib.parse.quote(config.project, safe="")
    encoded_wiki = urllib.parse.quote(wiki_id, safe="")
    encoded_path = urllib.parse.quote(path, safe="/")
    url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/wiki/wikis/{encoded_wiki}/pages?path={encoded_path}"
        f"&api-version={ADO_API_VERSION}"
    )

    headers = {
        "Authorization": config.auth_header,
        "Content-Type": "application/json",
    }
    if etag:
        headers["If-Match"] = etag

    body = json.dumps({"content": content}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="PUT")

    try:
        time.sleep(RATE_LIMIT_DELAY)
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8")
        except Exception:
            pass
        raise RuntimeError(
            f"Wiki page PUT error {e.code}: {e.reason}\nResponse: {body_text[:500]}"
        )


def create_project_wiki(config: AdoConfig) -> dict:
    """
    Create a project wiki in the ADO project.

    Only needed when no wiki exists yet. Creates a wiki of type 'projectWiki'.

    Returns:
        Wiki metadata dict from ADO API (id, name, type, etc.)
    """
    proj = urllib.parse.quote(config.project, safe="")
    url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/wiki/wikis?api-version={ADO_API_VERSION}"
    )

    # Fetch the project ID needed for the wiki creation payload
    project_url = (
        f"https://dev.azure.com/{config.organization}/_apis/projects/"
        f"{proj}?api-version={ADO_API_VERSION}"
    )
    project_info = _api_request(config, project_url, method="GET")
    project_id = project_info.get("id", "")

    body = {
        "type": "projectWiki",
        "name": f"{config.project}.wiki",
        "projectId": project_id,
    }
    return _api_request(config, url, method="POST", body=body)


def upload_wiki_attachment(
    config: AdoConfig,
    wiki_id: str,
    file_path: str,
    filename: str | None = None,
) -> str:
    """
    Upload a file attachment to an ADO wiki.

    ADO wiki attachments require the file content to be base64-encoded
    and sent as application/octet-stream.

    Args:
        config: ADO connection config
        wiki_id: Wiki identifier (name or ID)
        file_path: Local path to the file to upload
        filename: Display name (defaults to basename of file_path)

    Returns:
        The wiki-relative path to the attachment (for use in markdown links)
    """
    from pathlib import Path as _Path
    fp = _Path(file_path)
    if not fp.exists():
        raise FileNotFoundError(f"Attachment file not found: {file_path}")

    if not filename:
        filename = fp.name

    proj = urllib.parse.quote(config.project, safe="")
    encoded_wiki = urllib.parse.quote(wiki_id, safe="")
    encoded_name = urllib.parse.quote(filename, safe="")
    url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/wiki/wikis/{encoded_wiki}/attachments?name={encoded_name}"
        f"&api-version={ADO_API_VERSION}"
    )

    default_path = f"/.attachments/{filename}"

    file_data = base64.b64encode(fp.read_bytes())
    headers = {
        "Authorization": config.auth_header,
        "Content-Type": "application/octet-stream",
    }
    req = urllib.request.Request(url, data=file_data, headers=headers, method="PUT")

    try:
        time.sleep(RATE_LIMIT_DELAY)
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        return result.get("path", default_path)
    except urllib.error.HTTPError as e:
        # 500 with "already exists" or 409 Conflict — attachment was uploaded before
        if e.code in (409, 500):
            return default_path
        raise


def list_repositories(config: AdoConfig) -> list[dict]:
    """
    List all Git repositories in the ADO project.

    Returns:
        List of repo dicts with id, name, remoteUrl, etc.
    """
    proj = urllib.parse.quote(config.project, safe="")
    url = (
        f"https://dev.azure.com/{config.organization}/{proj}"
        f"/_apis/git/repositories?api-version={ADO_API_VERSION}"
    )
    result = _api_request(config, url, method="GET")
    return result.get("value", [])


# --- Internal helpers ---

def _api_request(
    config: AdoConfig,
    url: str,
    method: str = "GET",
    body: dict | list | None = None,
    content_type: str = "application/json",
) -> dict:
    """Make an authenticated API request to ADO."""
    headers = {
        "Authorization": config.auth_header,
        "Content-Type": content_type,
    }

    data = None
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=headers, method=method)

    global _call_count, _call_total_seconds

    retries = 3
    for attempt in range(retries):
        try:
            time.sleep(RATE_LIMIT_DELAY)
            t0 = time.monotonic()
            with urllib.request.urlopen(req) as resp:
                resp_body = resp.read().decode("utf-8")
                _call_total_seconds += time.monotonic() - t0
                _call_count += 1
                return json.loads(resp_body) if resp_body else {}
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8")
            except Exception:
                pass

            if e.code == 429:  # Rate limited
                delay = 2 ** (attempt + 1)
                logger.warning("Rate limited, waiting %ds...", delay)
                time.sleep(delay)
                continue
            elif e.code >= 500 and attempt < retries - 1:
                delay = 2 ** attempt
                time.sleep(delay)
                continue
            else:
                raise RuntimeError(
                    f"ADO API error {e.code}: {e.reason}\n"
                    f"URL: {url}\n"
                    f"Response: {body_text[:500]}"
                )

    raise RuntimeError(f"ADO API request failed after {retries} retries: {url}")
