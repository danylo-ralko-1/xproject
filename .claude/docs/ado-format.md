# ADO Work Item Format

Read this before creating or modifying work items in Azure DevOps.

## Hierarchy (MANDATORY)

Every User Story **must** live inside the following hierarchy:

```
Epic → Feature → User Story → Tasks (FE/BE/DevOps)
```

**Before creating any User Story, always:**
1. **Fetch all existing open Epics and Features** from ADO.
2. **Match by content** — if an existing Epic or Feature logically covers the new story, use it as the parent. Do NOT create duplicates.
3. **Create new Epic/Feature only if no match exists.** When creating:
   - Epic: give it a broad domain name (e.g. "Glossary Application (Phase 1)")
   - Feature: give it a functional area name (e.g. "Terms Page", "FAQ Page")
   - Link the Feature to its parent Epic via `System.LinkTypes.Hierarchy-Reverse`
4. **Link the User Story** to its parent Feature via `System.LinkTypes.Hierarchy-Reverse`.

## Tagging (MANDATORY)

Every time you create or modify a work item in ADO, apply **only** the appropriate Claude tag via `System.Tags`:

- **`Claude New Story`** / **`Claude New Feature`** / **`Claude New Epic`** — when creating a brand-new work item from scratch
- **`Claude Modified Story`** / **`Claude Modified Feature`** / **`Claude Modified Epic`** — when updating an existing work item (e.g. enriching AC, changing title, modifying effort)

**Do NOT add any other tags** (no `xproject`, no project name, no epic/feature names). Only the Claude tags above.

Tags are additive — preserve any existing tags on the work item. Use semicolons to separate multiple tags (e.g. `"Existing Tag; Claude Modified Story"`).

## User Story

**Description field:**
```html
As a [role],<br>I want to [action],<br>So that [benefit].
```
Three lines separated by `<br>` only — no `<p>` wrapper, no extra newlines, no gaps between lines.

**Reference Sources** are appended below the user story text as a numbered list showing which input files were used to generate the story's requirements:
```html
As a [role],<br>I want to [action],<br>So that [benefit].<br><br><b>Reference Sources:</b><br><ol><li>RFP_document.pdf</li><li>Transcription_summary_12.08.2026.txt</li></ol>
```
Sources are the file names from `output/parsed/` (without the parsed path — use the original input file name). For compacted transcriptions, use the compacted summary file name with date. For change requests, use "Change request from DD.MM.YYYY".

The **Branch** link is added below the user story (before Reference Sources) when feature code is generated (see skill 12, Step 9). Before code generation, the branch line is absent. Epic/Feature are visible through ADO hierarchy links.

**Acceptance Criteria field** (`Microsoft.VSTS.Common.AcceptanceCriteria`):
```html
<b>AC 1:</b> Search behavior<br>
<ul>
<li>Search field is visible on the glossary page</li>
<li>Filtering starts only after the user types at least 2 characters</li>
<li>Results update as the user continues typing</li>
</ul>

<b>AC 2:</b> No results handling<br>
<ul>
<li>If no terms match the search, display "No results found" message</li>
<li>The message disappears when the user modifies the search</li>
</ul>
```

Each AC group has a **bold numbered title** (`AC 1: Title`) followed by **bullet points** (`<ul><li>`) listing the specific criteria.

**Change Log** is NOT added during initial story creation. The initial push generates detailed, dev-ready AC from the start — no enrichment step needed. The Change Log only appears when an actual **change request** or **scope revision** modifies a previously-completed story. See Modification Rules below for the format.

**Effort field** (`Microsoft.VSTS.Scheduling.Effort`): total days across all disciplines.

**Rules for AC:**
- 4-7 AC groups, each with a short descriptive title
- Each group covers a logical area of related behaviors
- Bullet points within each group — specific, testable criteria
- No Given/When/Then — write like developer notes
- Reference shadcn/ui components from the shared design system when relevant (e.g., "use DataTable with sorting", "display in a Dialog")
- Stories have detailed, dev-ready AC from the initial push — no enrichment step needed

**Technical Context block** (appended after AC groups, separated by `<hr>`):

A structured block consumed by Claude Code during feature code generation. It provides the information code gen needs to produce complete, working code without guessing. The push script renders it automatically from the `technical_context` field in push_ready.json.

```html
<hr>
<b>Technical Context</b><br><br>
<b>Data Model:</b><br>
<ul>
<li>Term: { id: UUID, name: string (required, max 100), description: string (optional), category: enum [General, Technical, Legal], createdAt: datetime, updatedBy: User }</li>
</ul>
<b>States:</b><br>
<ul>
<li>Default: table with paginated terms</li>
<li>Loading: skeleton rows</li>
<li>Empty: illustration + "No terms yet" + CTA to add first term</li>
<li>Error: inline error banner with retry action</li>
</ul>
<b>Interactions:</b><br>
<ul>
<li>Click "Add Term" → modal opens → fill form → submit → table refreshes with new row</li>
<li>Click row → navigate to /terms/{id}</li>
<li>Type in search → 300ms debounce → GET /terms?q={query} → update table</li>
</ul>
<b>Navigation:</b><br>
<ul>
<li>Route: /glossary/terms</li>
<li>Parent: Glossary section in sidebar</li>
<li>Links to: /glossary/terms/{id} (detail), /glossary/categories (related)</li>
</ul>
<b>API Hints:</b><br>
<ul>
<li>GET /terms?q=&amp;page=&amp;sort=&amp;category= → { items: Term[], total: number }</li>
<li>POST /terms → Term</li>
<li>PATCH /terms/{id} → Term</li>
<li>DELETE /terms/{id} → 204</li>
</ul>
```

**Rules for Technical Context:**
- **Data Model:** List each entity the story works with. Include field names, types, required/optional, constraints (max length, enums). Use inline object notation.
- **States:** Every UI state the component can be in: default, loading, empty, error, success, search-active, etc. Brief description of what each looks like.
- **Interactions:** Event → action chains. Include debounce, navigation, modal triggers, form submissions. Use → arrows for flow.
- **Navigation:** Route path, parent layout/section, what pages link here, where this page links to.
- **API Hints:** Endpoints this feature needs. Method + path + key query params → response shape. Don't design the full API — just hint at what the frontend expects.
- **Omit sections that don't apply** (e.g., a pure backend story has no States or Navigation).
- **Don't duplicate design-system.md** — no component names or UI library details. Only functional/data context.

## Modification Rules (MANDATORY — applies to ALL ADO updates)

When modifying **any** existing User Story field (Description, Acceptance Criteria, or any other content field), follow these rules:

**1. Never overwrite original text.** Show the old text with red strikethrough and the new text in green:
```html
<span style="color:red;text-decoration:line-through">old text being replaced</span>
<span style="color:green">new text replacing it</span>
```
This applies to **any field** being changed — Description, Acceptance Criteria, or others. The reader must always be able to see what changed.

**2. Add a Change Log only for change requests.** The Change Log lives at the **end of the Acceptance Criteria field**. It is **NOT added during initial story creation.** It only appears when an actual change request or scope revision modifies a story. When modifying a story via change request, append a Change Log section (if not already present) and add a numbered entry:
```html
<br><b>Change Log:</b><br><br>
<b>Change {N}:</b> {what changed}<br>
<b>Date:</b> {YYYY-MM-DD}<br>
<b>Reason:</b> {why it changed}
```
Number entries sequentially (Change 1, Change 2, Change 3...). Separate entries with `<hr>`. New entries go at the **end** so the history reads chronologically. If the AC field doesn't yet have a Change Log (first modification), append one starting at Change 1.

**2b. Always ask for a reason.** When a user requests a modification but does not provide a reason for the change, **ask them for one** before updating ADO. If the user says they don't know or want to skip, set the Reason to `Not specified`.

**3. Outdated stories.** If a story becomes irrelevant after a change request or scope revision:
- Add a visible warning at the top of the Description: `<p><b>⚠️ OUTDATED</b> — {reason why this story is no longer relevant}.</p>`
- If a replacement story exists (or is being created), add an ADO link of type `System.LinkTypes.Related` or `System.LinkTypes.Dependency-Forward` (Successor) pointing to the new story
- The new story should link back to the old one as well (`System.LinkTypes.Dependency-Reverse` / Predecessor)
- Add a Change Log entry (next sequential number) to the AC field: "Marked outdated", Date, Reason = reason + reference to replacement story ID

## Tasks (MANDATORY child items under User Story)

When creating a User Story, **always** create discipline tasks as children:

- **Frontend:** Title = `[FE] <User Story Title>`, Effort = fe_days — create if the story has any frontend work (UI, components, styling, client-side logic)
- **Backend:** Title = `[BE] <User Story Title>`, Effort = be_days — create if the story has any backend work (API, database, integrations, server-side logic)
- **DevOps:** Title = `[DevOps] <User Story Title>`, Effort = devops_days — create only if explicit DevOps work is needed
- **Design tasks are NOT created**
- **QA Test Design:** Title = `[QA][TD] <User Story Title>`, no effort — Description contains **manual test cases** derived from the story's AC (see format below)
- **QA Test Execution:** Title = `[QA][TE] <User Story Title>`, no effort, no description — time-tracking placeholder for QA execution

Link each Task to its parent User Story via `System.LinkTypes.Hierarchy-Reverse`.

**QA tasks are only created for testable stories** — stories with user-facing functionality, business logic changes, or behavioral changes that a QA specialist can verify. They are **skipped** for purely technical stories that have no end-user impact (e.g., environment setup, CI/CD pipeline, database migrations). Claude sets `skip_qa: true` on such stories during generation; the push script reads this flag.

If effort values are not yet assigned, still create the tasks (with effort = 0) so the hierarchy is complete. Effort can be updated later during estimation.

### QA Test Design Description Format

The `[QA][TD]` task Description field contains manual test cases derived from the parent story's AC. Claude generates these when creating the story — QA can start testing immediately.

**HTML structure:**
```html
<b>Preconditions:</b>
<ul>
  <li>[Shared precondition — user role, existing data, system state]</li>
</ul>

<b>Test Data:</b>
<ul>
  <li>[Specific values to use in tests — names, emails, boundary strings]</li>
</ul>

<b>Environment:</b> [Browser requirements, viewport sizes if responsive testing needed]
<br><br>

<hr>
<h4>AC 1: [AC Group Title]</h4>

<b>TC-001: [Descriptive test case title]</b> [P1]
<br><i>[Type] — [One-line description]</i>
<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse; width:100%;">
  <tr style="background-color:#f0f0f0;">
    <th style="width:5%;">#</th>
    <th style="width:50%;">Step</th>
    <th style="width:45%;">Expected Result</th>
  </tr>
  <tr>
    <td>1</td>
    <td>[Action the tester performs]</td>
    <td>[What they should observe — specific text, values, behavior]</td>
  </tr>
</table>
```

**Rules for generating test cases:**

- **Group by AC** — test cases under `<h4>AC N: Title</h4>` headings, plus a "Cross-Cutting" section at the end for implicit tests
- **Numbering:** `TC-001` through `TC-NNN`, sequential within the task
- **Priority tags:** `[P1]` must test (happy path + key negative), `[P2]` should test (edge/boundary), `[P3]` nice to test (a11y, polish)
- **Type labels:** Happy path, Negative, Edge case, Boundary, Authorization, Implicit
- **Per AC bullet, generate:**
  - 1 happy path test (always)
  - 1 negative test (always for user inputs, API calls, conditional logic)
  - 0-1 boundary test (when limits/ranges are mentioned in AC)
  - 0-1 edge case (empty states, cancel flows)
- **No cross-cutting / implicit tests** — do not add generic tests for page load, keyboard accessibility, or similar. Only generate test cases directly derived from the story's AC bullets
- **Detail level:** describe WHAT to interact with and WHAT data to enter — not HOW to operate a mouse. A QA engineer knows how to click; they need to know *which* element and *what value*
- **Expected results must be observable and specific** — exact message text, exact values, exact UI state. Never "it works correctly"
- **Test data must be explicit** — "enter `test@example.com`", not "enter a valid email"
- **Preconditions:** shared at top, TC-specific only when a TC needs additional setup
- **Typical count:** 15-30 test cases per story (2-4 per AC bullet)

### QA Test Design Modification Rules

When a user story's AC changes (via change request or direct modification), the `[QA][TD]` task Description **must also be updated** to reflect the changes. Follow the same modification rules as user stories:

1. **Never delete outdated test cases.** Mark them with red strikethrough:
```html
<span style="color:red;text-decoration:line-through"><b>TC-005: Verify "All" button clears letter filter</b> [P1]
<br><i>Happy path — verifies All option</i>
<table>...</table></span>
```

2. **Add new or replacement test cases in green:**
```html
<span style="color:green"><b>TC-016: Verify clicking active letter clears the filter</b> [P1]
<br><i>Happy path — replaces TC-005 (All button removed per CR #1553)</i>
<table>...</table></span>
```

3. **For modified steps within an existing test case**, apply red/green inline to the changed step or expected result — don't strikethrough the entire TC if only one step changed:
```html
<tr>
<td>2</td>
<td><span style="color:red;text-decoration:line-through">Click the "All" button</span> <span style="color:green">Click the active letter "B" again</span></td>
<td><span style="color:red;text-decoration:line-through">All terms are shown, no letter is highlighted</span> <span style="color:green">Filter is cleared, "B" returns to default style, all terms shown</span></td>
</tr>
```

4. **New test cases** added due to AC changes get the next sequential number (TC-016, TC-017, etc.) — never reuse numbers from struck-through test cases.

5. **Update preconditions and test data** if the AC change affects them (e.g., new role, new field, removed feature). Apply red/green markup to changed items.

## Story Relations (MANDATORY)

Every User Story should have its **inter-story relationships** identified and stored as ADO links. Relations are analyzed once during push (or when creating/modifying stories via change requests) and then consumed by code generation for context.

**Two link types:**

| Link Type | ADO Relation | Meaning | Code Gen Use |
|-----------|-------------|---------|--------------|
| **Predecessor** | `System.LinkTypes.Dependency-Reverse` | This story builds ON TOP OF another story's output. The predecessor's code is WHERE the new feature will be placed. | Read the predecessor's feature branch to understand the existing component structure, layout, and integration points. |
| **Related (Similar)** | `System.LinkTypes.Related` | This story is structurally similar to another story — same pattern, different data/context. | Read the similar story's feature branch as a template for HOW to implement this feature. |

**Examples:**
- Story "Add filtering to Glossary table" -> **Predecessor:** "Glossary Terms Table Grid" (the table already exists; filtering goes ON it)
- Story "Add filtering to FAQ table" -> **Related:** "Add filtering to Glossary table" (same filtering pattern, different page)
- Story "Term Detail Page" -> **Predecessor:** "Glossary Terms Table Grid" (row click navigates to detail; need to know the table's route and row structure)

**When to create relations:**
1. **During push (skill 05)** — after generating push_ready.json, analyze ALL stories for predecessor and similarity relationships. Add `predecessors` and `similar_stories` fields to each story. The push script creates the ADO links.
2. **During change requests (skill 08)** — when creating new stories or modifying existing ones, always check for relations against all existing stories in ADO.
3. **During any story creation/modification** — if you create or change a story for any reason, check if it has predecessors or similar stories.

**Rules for identifying relations:**
- **Predecessor:** Story A is a predecessor of Story B if Story B's feature physically lives inside or extends Story A's output. Ask: "Does this story modify or add to something that another story creates?" If yes, the other story is the predecessor.
- **Related (Similar):** Story A is related to Story B if they follow the same UI pattern or implementation approach but on different data/pages. Ask: "Is there another story that does essentially the same thing but in a different context?" If yes, they are related.
- **A story can have 0-N predecessors and 0-N related stories.** Most stories will have 0-1 predecessors and 0-2 related stories.
- **Relations are bidirectional in ADO** — when you link A->B as predecessor, ADO automatically shows B->A as successor. When you link A<->B as related, both sides see it.
- **Don't force relations.** If a story is truly standalone with no dependencies or similar patterns, leave it without relations.
- **Prefer specificity.** Link to the most specific story, not the broadest. Link "Add filtering to Glossary table" to "Glossary Terms Table Grid" (specific), not to "Glossary Application" (too broad — that's the Epic).

**ADO link format** (JSON patch for creating links on an existing work item):
```json
{
  "op": "add",
  "path": "/relations/-",
  "value": {
    "rel": "System.LinkTypes.Dependency-Reverse",
    "url": "https://dev.azure.com/{org}/_apis/wit/workItems/{predecessorId}",
    "attributes": { "comment": "Predecessor: feature builds on this story's output" }
  }
}
```

For Related links, use `"rel": "System.LinkTypes.Related"` with comment `"Similar: same pattern/approach as this story"`.
