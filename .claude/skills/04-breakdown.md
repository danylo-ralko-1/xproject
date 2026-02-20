# Generate Breakdown & Estimates

**Reference docs:** Read `.claude/docs/json-schemas.md` for the exact `breakdown.json` format before writing.

**Trigger:** "create breakdown", "estimate the project", "generate stories", or when the user drops client answers and says something like "here are the answers, create the breakdown"

**Pre-checks:**
- Overview must exist (`output/overview.md`). If not: "I need to analyze the requirements first. Say 'generate overview' to start."
- If `answers/` folder has new files since last breakdown, mention: "I see new client answers. I'll factor those into the estimates."
- If overview was regenerated since last breakdown, warn about staleness.
- **Check if stories already exist in ADO** (`state.ado_pushed: true` in project.yaml). If yes → skip to **Phase B: Enrich Existing Stories**.

**If the user drops client answer files in the chat:**
1. Copy each file to `projects/<ProjectName>/answers/`
2. Confirm: "Saved the client answers. I'll factor them into the breakdown."
3. Proceed with breakdown — don't make them say "create breakdown" separately

---

## Phase A: Generate New Breakdown (stories NOT yet in ADO)

This skill runs ENTIRELY in conversation. You read files, generate the breakdown JSON, and save it. Then run a Python script only for Excel export.

### Step 1: Read Inputs

1. Read `projects/<ProjectName>/output/overview.md` — this is always the **primary source**. It contains the synthesized scope AND a **Source Reference** table at the end that maps topics to source files.
2. Read any files in `projects/<ProjectName>/answers/` (if they exist)
   - If no answers: use reasonable defaults and mark assumptions
3. **Targeted detail reads** — while generating the epic/feature/story structure and estimates, consult the Source Reference table in the overview whenever you need specifics the overview doesn't cover (exact field definitions, validation rules, workflow details). Then:
   - Look up the source filename in the Source Reference, find its `parsed_file` in the manifest's `files` array.
   - Read that file directly from `output/parsed/<parsed_file>`.
   - **Only read what you need.** Don't read all parsed files — the Source Reference tells you exactly which one has the detail for each topic.

### Step 2: Generate Epic/Feature/Story Structure

Analyze the requirements, overview, and client answers. Generate the hierarchy:

**Rules for structure:**
- Aim for 30-40 user stories total. If the project is complex, consolidate related work into broader stories rather than splitting into granular tasks.
- Epics group major functional areas (Authentication, Search, Content Management, etc.)
- Features are sub-areas within an epic (Login, Password Reset, SSO within Authentication)
- Stories are specific deliverable units within a feature
- Each story should be independently deliverable and testable
- First epic should always be "Technical Setup" with stories for dev environment, CI/CD, and database schema

### Step 3: Add Details and Estimates to Every Story

For each story, determine:
- `title`: clear, descriptive story title
- `acceptance_criteria`: brief scope-level AC (1-2 sentences — detailed AC is generated in push_ready.json)
- `skip_qa`: `true` if the story is purely technical with no end-user impact (e.g., environment setup, CI/CD, database migration, infrastructure changes). `false` (default) for anything a QA specialist can test — new functionality, business logic, UI changes, behavioral changes. When `false`, the push script creates `[QA][TD]` (with manual test cases in Description) and `[QA][TE]` (time-tracking placeholder) tasks.
- `fe_days`: frontend effort in days
- `be_days`: backend effort in days
- `devops_days`: DevOps effort in days (0 for most stories)
- `risks`: primary risk or concern
- `comments`: technical notes, dependencies, implementation hints
- `assumptions`: what we're assuming to be true for this estimate

**Estimation guidelines:**
- FE (days): UI components, state management, API integration, responsive behavior
- BE (days): API endpoints, business logic, data validation, database queries
- DevOps (days): Infrastructure, CI/CD, deployment config, monitoring. Most stories are 0.
- Minimum granularity is 0.5 days. A trivial task is 0.5, not 0.
- A "day" = ~6 productive hours
- Be realistic. A login form is not 5 days of FE work. A complex search with filters is not 0.5 days.
- Include stories for error handling, loading states, and edge cases — these are real work.

### Step 4: Estimation Validation Pass

Before saving, run a self-check on all generated estimates. Fix what you can automatically, flag the rest to the user.

#### 4a: Outlier Detection
- **Too small:** Any story with total effort (FE + BE + DevOps) < 1 day — is it really that trivial, or was work underestimated? Auto-bump to 1 day minimum unless it's genuinely a config change or copy update.
- **Too large:** Any story with total effort > 10 days — should it be split into smaller stories? Flag to the user but don't auto-split.
- **Within-feature variance:** If one story in a feature is 0.5 days and a sibling is 8+ days, flag the mismatch — similar features should have roughly similar complexity unless there's a clear reason.

#### 4b: Ratio Checks
- **FE-heavy with no BE:** Story title mentions data, API, integration, or CRUD but has 0 BE days → auto-add at least 0.5 BE days.
- **BE-heavy with no FE:** Story title mentions UI, page, form, dashboard, or screen but has 0 FE days → auto-add at least 0.5 FE days.
- **Uniform effort smell:** If more than 40% of stories have the exact same FE/BE values (e.g., all are 2/2/0), flag it — real projects have varied complexity. Re-examine each story individually.

#### 4c: Coverage Gaps
- **No DevOps stories:** If the project involves deployment, cloud, CI/CD, or infrastructure (check requirements/overview), flag: "No DevOps effort found — does this project need deployment setup?"
- **No auth/security stories:** If the requirements mention user roles, permissions, login, or access control, but no stories cover authentication or authorization, flag the gap.
- **No error/edge-case coverage:** If no stories address error handling, empty states, loading states, or data validation, flag: "Consider adding stories for error handling and edge cases."
- **Missing Technical Setup:** If the first epic isn't "Technical Setup", add it. This should always be present.

#### 4d: Title vs Effort Consistency
- Story title contains "simple", "basic", or "minor" but effort > 3 days → flag.
- Story title contains "complex", "advanced", "full", or "comprehensive" but effort < 2 days → flag.

#### 4e: Report and Fix

After running all checks, present a brief report:

```
Estimation validation:
- Auto-fixed: "User Profile Page" had 0 FE days → set to 1.5
- Auto-fixed: "API Integration" had 0 BE days → set to 1
- Warning: 5 stories all have identical 2/2/0 effort — re-examined and adjusted
- Gap: No auth stories found, but 3 user roles mentioned in requirements — added "User Authentication & Authorization" story
- OK: Effort distribution looks balanced, no major outliers
```

**Auto-fix silently:** Small corrections (adding missing 0.5 FE/BE, bumping sub-1-day totals) — apply them and mention in the report.
**Flag to user:** Large issues (stories > 10 days, missing entire categories, uniform effort smell) — ask before proceeding. If the user says "looks fine", proceed as-is.

After the user confirms (or if there are only auto-fixes), continue to Step 5.

### Step 5: Save breakdown.json

Write the result to `projects/<ProjectName>/output/breakdown.json` in EXACTLY this format:

```json
{
  "epics": [
    {
      "id": "EP-001",
      "name": "Technical Setup",
      "description": "Infrastructure and environment setup",
      "features": [
        {
          "id": "FT-001",
          "name": "Environment Setup",
          "stories": [
            {
              "id": "US-001",
              "title": "Development Environment Configuration",
              "acceptance_criteria": "Dev environment with hot reload, linting, and test runner configured for both FE and BE.",
              "fe_days": 1,
              "be_days": 1,
              "devops_days": 0.5,
              "risks": "Team may have different local setups",
              "comments": "Use Docker for consistency. Include README with setup instructions.",
              "assumptions": "Team uses VS Code or compatible IDE"
            }
          ]
        }
      ]
    }
  ]
}
```

**Critical:** The JSON must be valid and parseable. Use proper escaping for quotes in text fields.

### Step 6: Export to Excel

Run: `python3 ~/Downloads/xproject/xproject breakdown-export <ProjectName>`

This converts `breakdown.json` → `breakdown.xlsx` with formatting. If the command doesn't exist yet, skip this step and note it.

### Step 7: Update State

Update `projects/<ProjectName>/project.yaml`:
- Set `state.breakdown_generated: true`
- Set `status: "estimation"`

### Step 8: Show Summary

Present the summary to the user:

```
Breakdown complete:
- X epics, Y features, Z stories
- Total effort: N days
  - FE: X days
  - BE: X days
  - DevOps: X days

Top epics:
- Epic Name: X stories, Y days
- Epic Name: X stories, Y days
...
```

### Step 9: Next Steps

Tell the user:
"The breakdown is ready. You can:
1. **'push to ADO'** to create work items in Azure DevOps
2. Ask me to **adjust specific estimates** if anything looks off
3. Review the Excel file at `output/breakdown.xlsx`"

---

## Phase B: Enrich Existing Stories (stories already in ADO)

When stories already exist in ADO with basic/scope-level AC, do NOT regenerate them. Instead, read the existing stories from ADO and enrich the acceptance criteria to full detail.

**Why batches:** Generating detailed AC for all stories at once will hit token output limits. Process stories in batches of 3-5 to stay within limits. This is purely a technical constraint — no user review is needed between batches. Generate a batch, push it to ADO, move on to the next.

### Step 1: Fetch Stories from ADO

Use the Python ADO module to fetch all User Stories from the project:
```python
python3 -c "
from core.config import load_project
from core.ado import from_project, get_all_work_items
p = load_project('<ProjectName>')
c = from_project(p)
items = get_all_work_items(c)
# ... process items
"
```

Read the overview, requirements context, and client answers for enrichment context.

### Step 2: Identify Stories Needing Enrichment

A story needs enrichment if its AC is:
- A single sentence or brief paragraph (scope-level)
- Has only 1-2 AC groups with minimal bullet points
- Missing behavioral detail a developer would need

Skip stories that already have 4+ detailed AC groups — they're already enriched.

Tell the user: "I found X stories that need detailed AC. I'll enrich them in batches of 3-5."

### Step 3: Enrich and Push in Batches of 3-5 Stories

For each batch:
1. Generate detailed AC + Technical Context for 3-5 stories
2. Push each to ADO immediately
3. Report briefly: "Batch X done (stories #A, #B, #C). Moving to next batch."
4. Continue to the next batch — **do not wait for user input between batches**

**Generate detailed AC** following these rules:

#### What to include (business requirements level):
- **User flows:** what the user does step by step, what happens on each action
- **Logical behavior:** filtering logic, validation rules, state transitions, error handling
- **Edge cases:** empty states, no results, concurrent access, boundary conditions
- **Permissions:** which roles can do what, what happens when unauthorized
- **Data behavior:** required vs optional fields, default values, cascading effects

#### What NOT to include (no pixel-perfect details):
- No font weights, font sizes, or font families
- No exact pixel dimensions, padding, or margins
- No RGB/hex color values
- No specific element sizes or spacing measurements
- No CSS-level styling descriptions

**Think of it as:** "more detailed than a sentence, less detailed than a Figma spec." A developer should understand WHAT to build and HOW it should behave, but not be constrained by exact visual measurements.

#### AC format:
- 4-7 AC groups per story, each with a short descriptive title
- Each group covers a logical area of related behaviors
- Bullet points within each group — specific, testable criteria
- No Given/When/Then — write like developer notes

**Good example:**
```
AC 1: Search behavior
- Search bar supports three modes: All, Term only, Description only
- Results update as the user types with a debounce delay
- Minimum 2 characters before search triggers
- Search is case-insensitive

AC 2: No results state
- If no terms match, display a clear "no results" message
- Message suggests broadening the search or clearing filters
- The empty state disappears as soon as the user modifies the query

AC 3: Performance
- Search returns results within 2 seconds under normal load
- Results are paginated (server-side) to handle 10k+ terms
```

**Bad example (too pixel-perfect):**
```
AC 1: Search bar
- Search input is 48px tall with 16px padding and a 14px Inter Regular placeholder
- Border is 1px solid #E2E8F0, border-radius 8px
- Search icon is 20x20px positioned 12px from the left edge
```

#### Technical Context block

After the AC groups, generate a **Technical Context** block for each story. This structured data is consumed by Claude Code during feature code generation.

Derive from the story's AC, overview, and requirements context:
- **Data Model:** entities this story works with — field names, types, required/optional, constraints
- **States:** all UI states — default, loading, empty, error, success. Brief description of each.
- **Interactions:** event → action chains — click, type, submit, navigate. Use → arrows.
- **Navigation:** route path, parent layout, links in/out
- **API Hints:** endpoints the frontend needs — method + path + params → response shape

Omit sections that don't apply. Don't include visual details (that's in design-system.md).

Format as HTML appended after the AC groups:
```html
<hr>
<b>Technical Context</b><br><br>
<b>Data Model:</b><br>
<ul><li>Term: { id: UUID, name: string (required), ... }</li></ul>
<b>States:</b><br>
<ul><li>Default: table with paginated terms</li><li>Loading: skeleton rows</li></ul>
<b>Interactions:</b><br>
<ul><li>Click "Add" → modal opens → fill form → submit → table refreshes</li></ul>
<b>Navigation:</b><br>
<ul><li>Route: /glossary/terms</li></ul>
<b>API Hints:</b><br>
<ul><li>GET /terms?q=&page= → { items: Term[], total: number }</li></ul>
```

### Step 4: Update ADO Per Batch

For each story in the batch, update ADO using `core.ado`:

- **Replace the AC field** with the new detailed AC + Technical Context block (since this is enrichment of initial scope-level AC, not a change request — no red/green strikethrough needed)
- **Do NOT add a Change Log.** Enrichment is part of initial requirements generation, not a change request. The Change Log section only appears when a story is later modified by a change request.
- **Add tag:** `Claude Modified Story` (preserve existing tags)
- Do NOT modify the Description field or effort values

### Step 5: Summary & Next Steps

After all batches are complete:

```
Enrichment complete:
- X stories enriched with detailed AC
- Y stories skipped (already detailed)
```

Tell the user:
"All stories now have detailed acceptance criteria in ADO. You can:
1. **'extract design system'** if you have Figma designs to capture visual tokens
2. **'generate code'** to scaffold feature branches for developers
3. **'handle a change request'** if the client sends scope changes"
