# Push to ADO

**Reference docs:** Read `.claude/docs/ado-format.md` for ADO HTML format and `.claude/docs/json-schemas.md` for the `push_ready.json` schema before starting.

**Trigger:** "push to ADO", "create work items", "push stories"

**Pre-checks:**
- Breakdown must exist (`output/breakdown.json`). If not: "I need a breakdown first. Say 'create breakdown'."
- ADO credentials must be configured in `project.yaml` (`ado.organization`, `ado.project`, `ado.pat`). If not: "I need ADO credentials. What's your organization name, project name, and Personal Access Token?"
- If breakdown changed since last push, warn.

**What to do:**

This skill has TWO phases: you generate the story details, then the Python script pushes to ADO.

## Phase 1: Generate push_ready.json (YOU do this)

Read `projects/<ProjectName>/output/breakdown.json` and `projects/<ProjectName>/output/overview.md`. The overview is the **primary source** — it contains the synthesized scope AND a **Source Reference** table mapping topics to source files.

Also read any files in `projects/<ProjectName>/answers/`.

### Targeted detail reads for AC generation

When generating detailed AC and technical context for each story, you will need specifics the overview doesn't cover (exact field definitions, enum values, validation rules, API shapes). **Use the Source Reference table** in the overview to identify which source file has the detail for each story's topic, then:

- Look up the source filename in the Source Reference, find its `parsed_file` in the manifest's `files` array.
- Read that file directly from `output/parsed/<parsed_file>`.
- **Read per story batch, not upfront.** Before generating AC for a batch of stories, identify the 2-3 source files relevant to those stories from the Source Reference, read them, then generate. This keeps context focused.
- **Don't re-read files already in context.** If two stories in the same batch need the same source file, read it once.

For EVERY story in the breakdown, generate:
- `user_story`: Three-line format — "As a [role],\nI want to [action],\nSo that [benefit]."
- `acceptance_criteria`: array of detailed AC groups, each with a `title` and `items` (bullet points)
- `technical_context`: structured block for Claude Code consumption during feature code generation (see format below)

**Rules for user story text:**
- Always three separate lines: "As a…", "I want to…", "So that…" — never a single inline sentence
- No italic formatting — regular text only
- The role should match the user roles identified in the overview
- The action should describe what the user does, not how it's built
- The benefit should tie to a business outcome

**Rules for detailed AC (dev-ready from initial push):**
- 4-7 AC groups per story — detailed enough for a developer to implement without further clarification
- Each group has a short descriptive title and 2-5 bullet points
- Cover: user flows, logical behavior, validation rules, error handling, edge cases, permissions
- Reference specific UI elements where inferable from requirements (field names, button labels, expected messages)
- Include empty states, loading states, and error scenarios — these are real implementation work
- No pixel-perfect details (font sizes, colors, spacing) — those come from design-system.md
- For backend/infra stories: specify data constraints, API behavior, error codes, performance expectations

**What to include (business requirements level):**
- **User flows:** what the user does step by step, what happens on each action
- **Logical behavior:** filtering logic, validation rules, state transitions
- **Edge cases:** empty states, no results, concurrent access, boundary conditions
- **Permissions:** which roles can do what, what happens when unauthorized
- **Data behavior:** required vs optional fields, default values, cascading effects

**What NOT to include (no pixel-perfect details):**
- No font weights, font sizes, or font families
- No exact pixel dimensions, padding, or margins
- No RGB/hex color values
- No CSS-level styling descriptions

**Rules for technical_context:**
- `data_model`: entities this story works with — field names, types, required/optional, constraints
- `states`: all UI states — default, loading, empty, error, success, etc. Brief description of each.
- `interactions`: event → action chains — click, type, submit, navigate. Use → arrows.
- `navigation`: route path, parent layout, links in/out
- `api_hints`: endpoints the frontend needs — method + path + params → response shape
- Omit sections that don't apply (e.g., pure backend story has no `states` or `navigation`)
- Don't include visual details (colors, fonts, spacing) — that's in design-system.md

**Example:**
```json
{
  "id": "US-003",
  "title": "User Login",
  "user_story": "As a registered user,\nI want to log in with my email and password,\nSo that I can access my dashboard.",
  "acceptance_criteria": [
    {
      "title": "Login form",
      "items": [
        "Email field (required) and password field (required, masked input)",
        "Submit button is disabled until both fields have content",
        "Form supports submission via Enter key"
      ]
    },
    {
      "title": "Authentication flow",
      "items": [
        "Valid credentials authenticate the user and redirect to /dashboard",
        "Invalid credentials show an inline error message without clearing the form",
        "Account locked after 5 consecutive failed attempts — show lockout message with retry timer"
      ]
    },
    {
      "title": "Session management",
      "items": [
        "Session persists across page refreshes until explicit logout or token expiry",
        "Already-authenticated users visiting /login are redirected to /dashboard"
      ]
    },
    {
      "title": "Loading and error states",
      "items": [
        "Submit button shows loading indicator during authentication request",
        "Network errors show a retry-able error message",
        "Form inputs are disabled during the authentication request"
      ]
    },
    {
      "title": "Navigation",
      "items": [
        "'Forgot password?' link navigates to password reset flow",
        "'Create account' link navigates to registration page"
      ]
    }
  ],
  "technical_context": {
    "data_model": [
      "LoginCredentials: { email: string (required, valid email), password: string (required, min 8 chars) }",
      "AuthSession: { token: JWT, user: User, expiresAt: datetime }"
    ],
    "states": [
      "Default: login form with email and password fields",
      "Loading: form disabled, submit button shows spinner",
      "Error: inline error message above form (invalid credentials / network error)",
      "Success: redirect to dashboard (no visible state)"
    ],
    "interactions": [
      "Fill form → click 'Log In' → POST /auth/login → on success redirect to /dashboard",
      "Invalid credentials → show error message → form stays filled → user can retry",
      "Click 'Forgot Password' → navigate to /auth/forgot-password"
    ],
    "navigation": [
      "Route: /auth/login",
      "Public route (no auth required)",
      "Redirect to /dashboard if already authenticated",
      "Links to: /auth/forgot-password, /auth/register"
    ],
    "api_hints": [
      "POST /auth/login { email, password } → { token, user }",
      "POST /auth/refresh { token } → { token }",
      "POST /auth/logout → 204"
    ]
  },
  "fe_days": 2,
  "be_days": 2,
  "devops_days": 0,
  "design_days": 1,
  "risks": "...",
  "comments": "...",
  "assumptions": "..."
}
```

Write the full structure to `projects/<ProjectName>/output/push_ready.json`. Same format as `breakdown.json` but with `user_story`, `acceptance_criteria` (detailed, as array of groups), and `technical_context` added to every story.

**Why batches:** Generating detailed AC + technical context for all stories at once may hit token output limits on large projects (30+ stories). If so, generate push_ready.json in batches — write a partial file, continue appending. The JSON must be complete and valid before running the push script.

## Phase 1b: Analyze Story Relations (YOU do this)

After generating push_ready.json and before running the push script, analyze ALL stories for inter-story relationships. This is done once — the relations are stored in push_ready.json and the push script creates the ADO links.

### What to analyze

For each story in push_ready.json, determine:

1. **Predecessors** — Does this story build ON TOP OF another story's output? Is there another story whose code is WHERE this feature will physically live?
   - Example: "Add filtering to Glossary table" → predecessor is "Glossary Terms Table Grid" (the table must exist first; filtering is added to it)
   - Example: "Term Detail Page" → predecessor is "Glossary Terms Table Grid" (clicking a row navigates to detail)
   - Ask: "If a developer implements this story, do they need to modify or extend something that another story creates?"

2. **Similar stories (Related)** — Is there another story that follows the same UI pattern or implementation approach but in a different context?
   - Example: "FAQ search and filter" → similar to "Glossary search and filter" (same pattern: search bar + filter dropdowns + table, different data)
   - Example: "Add Term modal" → similar to "Add FAQ modal" (same pattern: form in modal with validation)
   - Ask: "Is there another story that a developer could copy-paste and adapt to implement this one?"

### How to analyze

Read through all stories in push_ready.json and cross-reference:
- **Titles** — stories that reference the same page/feature are likely related
- **AC content** — stories with similar AC patterns (search, filter, table, form, modal) are candidates for "similar"
- **Technical Context** — stories sharing navigation routes (one links to another) indicate predecessor relationships
- **Feature grouping** — stories under the same Feature are more likely to have predecessor relationships

### Output

Add two fields to each story in push_ready.json:

```json
{
  "id": "US-005",
  "title": "Filter Glossary by Data Set",
  "predecessors": ["US-001"],
  "similar_stories": ["US-008"],
  ...
}
```

- `predecessors`: array of story IDs (from the same push_ready.json) that this story builds on. Empty array `[]` if none.
- `similar_stories`: array of story IDs that follow the same pattern. Empty array `[]` if none.

**Use the local IDs** from push_ready.json (e.g., `US-001`). The push script maps these to ADO IDs after creation and creates the links.

### Rules
- Don't force relations — if a story is standalone, leave both arrays empty.
- Prefer specificity — link to the most specific story, not to broad concepts.
- Keep it practical — a story should have at most 1-2 predecessors and 1-2 similar stories. More than that dilutes the signal.
- **Show the proposed relations to the user** before writing them:

```
Story Relations Analysis:

US-001: Glossary Terms Table Grid
  → No predecessors (standalone foundation)
  → No similar stories

US-003: Search and Filter Glossary
  → Predecessor: US-001 (Glossary Terms Table Grid) — search/filter is placed on the table
  → No similar stories

US-005: Filter Glossary by Data Set
  → Predecessor: US-001 (Glossary Terms Table Grid) — dropdown filter lives on the table
  → Similar: US-006 (Filter FAQ by Category) — same filter dropdown pattern

US-006: Filter FAQ by Category
  → Predecessor: US-002 (FAQ Table Grid) — dropdown filter lives on the table
  → Similar: US-005 (Filter Glossary by Data Set) — same filter dropdown pattern
```

**WAIT for approval before writing the relations into push_ready.json.**

## Phase 1c: Generate QA Test Design Descriptions (YOU do this)

For each story that has `skip_qa: false`, generate a `qa_td_description` field containing manual test cases in HTML format. These go into the `[QA][TD]` task's Description field so QA can start testing immediately.

**Read `.claude/docs/ado-format.md` section "QA Test Design Description Format"** for the exact HTML structure and rules.

**Derivation process per story:**
1. Read the story's `acceptance_criteria` array — each AC group becomes a test case section
2. For each AC bullet, generate:
   - 1 happy path test case `[P1]` (always)
   - 1 negative test case `[P1]` (for inputs, API calls, conditional logic)
   - 0-1 boundary test `[P2]` (when limits/ranges mentioned)
   - 0-1 edge case `[P2]` (empty states, cancel flows)
3. Read the `technical_context` to derive:
   - **Preconditions** from data model (what data must exist)
   - **Test data** with specific values matching the data model types/constraints
   - **State-based tests** from the states section (loading, empty, error)
4. Add implicit cross-cutting tests at the end: page load, empty state, cancel/back, error recovery, keyboard accessibility
5. Number all test cases sequentially: `TC-001` through `TC-NNN`

**Write the HTML string into each story's `qa_td_description` field in push_ready.json.** The push script reads this field and passes it as the Description when creating the `[QA][TD]` task.

Stories with `skip_qa: true` do not get this field (no QA tasks created).

## Phase 2: Push to ADO (Python script)

Run: `python3 ~/Downloads/xproject/xproject push <ProjectName>`

The script reads `push_ready.json` and creates the following hierarchy in ADO:
- **Epics** → **Features** → **User Stories** (with the AC you generated)
- **Tasks** under each User Story for each required discipline:
  - `[FE] <Story Title>` — if the story has frontend effort > 0
  - `[BE] <Story Title>` — if the story has backend effort > 0
  - `[DevOps] <Story Title>` — if the story has DevOps effort > 0
  - `[QA][TD] <Story Title>` — Test Design with manual test cases in Description (derived from AC, see `.claude/docs/ado-format.md` for format)
  - `[QA][TE] <Story Title>` — Test Execution time-tracking placeholder (no effort, no description)
  - QA tasks are skipped when the story has `skip_qa: true` (set by Claude for purely technical stories with no end-user impact)
  - Design tasks are NOT created
- **Story relation links** — after all stories are created, the script reads `predecessors` and `similar_stories` arrays, maps local IDs to ADO IDs, and creates:
  - `System.LinkTypes.Dependency-Reverse` (Predecessor) links for each predecessor
  - `System.LinkTypes.Related` links for each similar story

**Story Description format** (the script builds this):
```html
<p>As a [role],<br>
I want to [action],<br>
So that [benefit].</p>
```
Three separate lines, no italic. Description contains only the user story statement.

**AC format** (the script builds this from the structured array — NO Change Log on creation):
```html
<b>AC 1:</b> Login form<br>
<ul>
<li>Email field (required) and password field (required, masked input)</li>
<li>Submit button is disabled until both fields have content</li>
<li>Form supports submission via Enter key</li>
</ul>

<b>AC 2:</b> Authentication flow<br>
<ul>
<li>Valid credentials authenticate the user and redirect to /dashboard</li>
<li>Invalid credentials show an inline error message without clearing the form</li>
<li>Account locked after 5 consecutive failed attempts</li>
</ul>

...additional AC groups...

<hr>
<b>Technical Context</b><br><br>
<b>Data Model:</b><br>
<ul><li>LoginCredentials: { email: string (required), password: string (required, min 8) }</li></ul>
<b>States:</b><br>
<ul><li>Default: form with email and password</li><li>Loading: submit disabled, spinner</li><li>Error: inline message</li></ul>
...
```

Each AC group gets a bold numbered title + bullet list. After the AC groups, the script appends a **Technical Context** block (separated by `<hr>`) with Data Model, States, Interactions, Navigation, and API Hints — structured information consumed by Claude Code during feature code generation.

**No Change Log is added on initial creation.** The Change Log section only appears when a story is later modified by a change request or scope revision. At that point, a Change Log header is appended and entries are numbered sequentially (Change 1, Change 2, etc.) separated by `<hr>`.

**Effort:** `Microsoft.VSTS.Scheduling.Effort` = total days (FE + BE + DevOps + Design)

The script saves `output/ado_mapping.json` mapping local IDs to ADO IDs. This mapping is saved incrementally (after each item) so progress isn't lost on failure.

## Phase 3: Report & Next Steps

After the script completes, report what was created (epics, features, stories, tasks).

Tell the user:
"Stories are in ADO with detailed acceptance criteria and technical context — they're ready for code generation. You can:
1. **'extract design system'** — capture your Figma design tokens so generated code matches the designs
2. **'generate code'** — scaffold feature code from a story into a feature branch (includes API contract for backend)
3. **'handle a change request'** — if the client sends scope changes"

## Phase 4: Auto-update Product Document

After successful push, regenerate the product document (see skill 10-product-document) to reflect the new stories.