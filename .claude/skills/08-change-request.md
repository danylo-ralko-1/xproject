# Process Change Request

**Reference docs:** Read `.claude/docs/ado-format.md` for modification rules, red/green markup, and Change Log format before updating stories.

**Trigger:** "change request", "client wants to change", "scope change", "the client sent this email", or when the user drops a file and mentions it's a change/update from the client

**Pre-checks:**
- ADO credentials must be configured and stories must exist in ADO. ADO is the single source of truth — the change request is compared against what's actually in ADO.
  - If no credentials: "I need ADO credentials to read the current stories. What's your organization, project, and PAT?"
  - If connected but no stories: "I connected to ADO but didn't find any user stories to compare against."

**If the user drops a file or pastes text:**
1. Save the file/text to `projects/<ProjectName>/changes/`
2. Confirm: "Got it — I'll analyze this change request against the current scope."
3. Proceed with analysis automatically

**What to do:**

This skill runs ENTIRELY in conversation. You do the analysis, then use Python only for ADO operations and file saves.

## Step 1: Get the Change Request

The user will paste text, share a file, or describe the change verbally.

## Step 2: Read Current Baseline from ADO

**ADO is the single source of truth.** Always read current state from ADO, never from breakdown.json.

1. Fetch all current stories from ADO:
   `python3 -c "from core.config import load_project; from core.ado import from_project, get_all_work_items; import json; p=load_project('<ProjectName>'); c=from_project(p); print(json.dumps(get_all_work_items(c), indent=2))"`
   This gives you the full current state: epics, features, stories with descriptions, AC, effort, and tags.
2. Read `projects/<ProjectName>/output/overview.md` for project context (optional — ADO stories should be self-sufficient).
3. Check `project.yaml` → `changes[]` for previous change requests.

## Step 3: Analyze Impact

Compare the change request against the existing scope. Determine:

- **Classification:** new_feature, scope_expansion, modification, clarification, or out_of_scope
- **Clarity:** Is the change clear enough to estimate, or does it need clarification?
- **What's new** vs what's already scoped
- **Which existing stories are affected** and how
- **Effort delta** (FE/BE/DevOps/Design days) for new and modified stories
- **Timeline impact**
- **Risk assessment**
- **Whether design updates are needed**
- **Story relations** for any new stories:
  - **Predecessors:** Which existing stories does the new story build on top of?
  - **Similar stories:** Which existing stories follow the same pattern/approach?

If the change is unclear, list specific questions for the client before proceeding.

## Step 4: Present Analysis

Present the analysis in this format:

```
═══════════════════════════════════════════════
Change Request: CR-XXX
Summary of the change
═══════════════════════════════════════════════

Classification: [type]
Requires design update: yes/no

New stories (N):
  + CR001-US-001: Story Title (Xd total)
    FE:Xd BE:Xd DevOps:Xd Design:Xd
    Predecessor: #XXX (Story Title) — builds on this
    Similar: #YYY (Story Title) — same pattern

Modified stories (N):
  ~ US-XXX: Original Story Title
    Change: what changes about this story
    Effort delta: +X.Xd

Impact:
  Total delta: X days
  Timeline: [impact description]
  Risk: Low/Medium/High

Recommendation: [accept/negotiate/defer and why]
```

**WAIT for user approval before making any changes.**

## Step 5: On Approval — Create Snapshot

Before applying changes, create a backup:

```bash
mkdir -p projects/<ProjectName>/snapshots/pre-CR-XXX/
cp projects/<ProjectName>/output/*.json projects/<ProjectName>/snapshots/pre-CR-XXX/
cp projects/<ProjectName>/output/*.md projects/<ProjectName>/snapshots/pre-CR-XXX/
```

## Step 6: On Approval — Update ADO (the source of truth)

If stories are pushed to ADO (`state.ado_pushed: true`):

### New stories
Use `core.ado` to create work items in ADO:
- Create User Story with description (user story text only), AC (no Change Log on creation), effort
- Tags: `Claude New Story` (no other tags)
- Create discipline Tasks as children (FE/BE/DevOps where effort > 0, plus [QA][TD] with manual test cases in Description and [QA][TE] time-tracking placeholder for testable stories)
- Link to appropriate Feature parent
- **Analyze relations** — for each new story, check ALL existing stories in ADO for:
  - **Predecessors:** Does this new story build on top of an existing story's output? If so, add a `System.LinkTypes.Dependency-Reverse` link.
  - **Similar stories:** Is there an existing story that follows the same pattern? If so, add a `System.LinkTypes.Related` link.
  - Use `core.ado.add_link()` to create the links after the story is created.
  - Show proposed relations to the user as part of the approval step (Step 4).

### Modified stories
Update existing ADO items following the **Modification Rules**:
- Look up ADO ID from `output/ado_mapping.json`
- **Never overwrite** existing content. Use red strikethrough for old, green for new:
  ```html
  <span style="color:red;text-decoration:line-through">old content</span>
  <span style="color:green">new content from CR-XXX</span>
  ```
- This applies to **any field** being changed (AC, Description user story text, effort justification, etc.)
- **Append a Change Log entry** to the end of the AC field:
  ```html
  <hr>
  <b>Change {N}:</b> {what changed}<br>
  <b>Date:</b> {YYYY-MM-DD}<br>
  <b>Reason:</b> CR-XXX: {reason}
  ```
- **Ask the user for a reason** if they haven't provided one. Use "Not specified" only if they explicitly decline.
- Add tag `Claude Modified Story` (preserve existing tags)
- **Update the `[QA][TD]` child task** — find the `[QA][TD]` task under the modified story and update its Description following the QA Test Design Modification Rules in `.claude/docs/ado-format.md`. Strikethrough outdated test cases in red, add new/replacement test cases in green. For minor step changes, apply red/green inline within the affected rows.

### Outdated stories
If a change request makes an existing story irrelevant:
- Add `<p><b>⚠️ OUTDATED</b> — Superseded by CR-XXX: {reason}.</p>` at the top of the Description
- Add an ADO link (`System.LinkTypes.Dependency-Forward` / Successor) to the replacement story
- The replacement story links back (`System.LinkTypes.Dependency-Reverse` / Predecessor)
- Append a Change Log entry to the AC field (next sequential number): "Marked outdated", Reason = "CR-XXX — replaced by ADO #{new_id}"
- Do NOT delete the old story — it must remain visible for audit trail

### Change Log in ADO
- Find or create a "Change Log — <ProjectName>" Epic with tag `changelog;<ProjectName>`
- Create a Feature under it for this CR with full impact details in the description
- Update the Epic description with a running summary table of all CRs
- Save the Change Log Epic ID in `project.yaml` under `_changelog_epic_id`

## Step 7: Save Change Record

Save the raw change request text to `projects/<ProjectName>/changes/CR-XXX.txt`

Save the analysis to `projects/<ProjectName>/output/change_analysis_CR-XXX.json`

Update `project.yaml`:
- Append to `changes[]` array:
  ```yaml
  - id: CR-001
    date: "2026-02-11"
    source: "inline" or filename
    summary: "Brief summary"
    classification: "new_feature"
    stories_added: ["CR001-US-001"]
    stories_modified: ["US-015"]
    effort_delta: {FE: 3, BE: 2, DevOps: 0, Design: 1}
    approved: true
  ```

## Step 8: Next Steps

Tell the user:
"Change request CR-XXX is processed. The new/modified stories are in ADO. You can:
1. **'generate code'** for any new or modified stories (includes API contract for backend)
2. Process another change request if there are more"

## Step 9: Auto-update Product Document

Regenerate the product document (see skill 10-product-document) to reflect the scope changes.