# Generate Feature Code

**Reference docs:** Read `.claude/docs/ado-format.md` for story format (AC, Technical Context, relations) when reading stories from ADO.

**Trigger:** "generate code", "scaffold feature", "create feature branch", "generate feature code", "code from story"

**Pre-checks:**
- Project name must be known (to read ADO credentials from project.yaml). If not: "Which project should I use? Let me check what's available."
- ADO must be connected with stories present. If not: "I need ADO credentials configured and stories pushed before I can generate code. Want to set that up?"
- User must provide a **Story ID** — the ADO work item number. If not: "Which user story should I generate code for? Give me the ADO ID (e.g., #752)."
- User must provide the **target codebase path** — the actual product repo, NOT the xproject pipeline. If not: "Where is your product codebase? Give me the absolute path (e.g., ~/projects/my-app)."
- The target codebase must be a git repository. If not: "That folder isn't a git repo. Should I initialize one, or is the codebase somewhere else?"
- Optional: **Base branch** to branch from (default: `main`).

**What to do:**

This skill bridges pre-sales to development. It reads a user story from ADO, analyzes the target codebase's patterns (from `codebase-patterns.md` if available), applies the design system (from `design-system.md` if available), generates working starter code for the feature, runs a multi-agent code review to catch bugs and pattern violations, fixes issues automatically, produces an API contract for the backend developer, pushes it as a feature branch, and links it back in ADO. The frontend and backend developers each check out the branch and start from a reviewed, validated baseline.

**Figma is never used directly in this skill.** Design information enters only through the `design-system.md` file generated separately by the "extract design system" skill.

**This runs entirely in conversation.** YOU do all analysis and code generation. Python one-liners fetch/update ADO data. Git commands handle branching. Write/Edit tools create code files.

---

## Step 1: Gather Inputs

Collect from the user (ask for anything missing):

1. **Story ID** — which ADO story to implement (e.g., `752`)
2. **Target codebase path** — absolute path to the product repo
3. **Base branch** (optional) — defaults to `main`

## Step 2: Fetch Story from ADO

Use a Python one-liner to fetch the story with full details:

```bash
cd ~/Downloads/xproject && python3 -c "
from core.config import load_project
from core.ado import from_project, get_work_items_by_query
import json
p = load_project('<ProjectName>')
c = from_project(p)
wiql = 'SELECT [System.Id] FROM WorkItems WHERE [System.Id] = <StoryID>'
items = get_work_items_by_query(c, wiql)
print(json.dumps(items, indent=2, default=str))
"
```

Extract and note:
- **Title** — for branch naming and FEATURE.md
- **Description** — the user story statement (As a… I want… So that…)
- **Acceptance Criteria** — all AC groups with their bullet points (this drives code generation)
- **Technical Context block** — the structured section after the `<hr>` separator in the AC field. This contains Data Model, States, Interactions, Navigation, and API Hints that directly inform code generation. Parse each section and use it as your primary guide for:
  - **Data Model** → TypeScript interfaces/types, form field definitions, validation schemas
  - **States** → component state management, loading/error/empty UI variants
  - **Interactions** → event handlers, API calls, navigation logic, debounce/throttle
  - **Navigation** → route definitions, layout placement, link targets
  - **API Hints** → service layer functions, request/response types, hook definitions
- **Effort** — FE/BE split tells you what kind of code to generate
- **Tags** — for context
- **Parent Feature/Epic** — for understanding the broader context

If the story has only basic/lightweight AC with no Technical Context block, note: "This story has minimal acceptance criteria and no technical context. The generated code will be higher-level — based on what's currently in ADO."

## Step 2b: Read Related Story Branches (Predecessor + Similar Context)

Check the story's ADO relations for **Predecessor** and **Related** links. These provide critical context for code generation:

### 2b-i: Fetch the story's relations

The story data from Step 2 includes a `relations` array. Look for:
- **Predecessor links** (`System.LinkTypes.Dependency-Reverse`): stories whose code is WHERE this feature will be placed
- **Related links** (`System.LinkTypes.Related`): stories whose code shows HOW to implement a similar feature

Extract the target work item IDs from each relation URL (the last segment of the URL path).

### 2b-ii: For each predecessor story

Predecessor = WHERE context. This story's code physically lives inside or extends the predecessor's output.

1. Fetch the predecessor story from ADO (title, description, AC)
2. Check if it has a feature branch (look for a `Branch:` link in its Description field)
3. If a branch exists in the target codebase:
   - Read the branch's FEATURE.md to understand what files were generated
   - Read the key component files (main component, hooks, types) — these are the files your generated code will integrate with or extend
   - Note: import paths, component names, prop interfaces, state management approach, route structure
   - **This is the integration point.** Your generated code must work alongside these files — import from them, extend their types, nest inside their layouts, or add to their routes.
4. If no branch exists (story was implemented manually by developers):
   - The code lives on the main branch. Use Step 3's codebase analysis to find the relevant files based on the predecessor story's title and AC.

### 2b-iii: For each similar (related) story

Similar = HOW context. This story follows the same pattern as the related story.

1. Fetch the related story from ADO (title, AC, technical context)
2. Check if it has a feature branch
3. If a branch exists:
   - Read the branch's FEATURE.md to understand the implementation structure
   - Read the generated files — these serve as a **template** for your code
   - Note: the file structure, component decomposition, hook patterns, API integration approach
   - **This is your implementation template.** Follow the same structural decisions — same number of files, same hook extraction pattern, same state management approach — but adapt the data, labels, routes, and endpoints.
4. If no branch exists:
   - Find the similar feature's code on the main branch using title/AC matching.

### 2b-iv: Summarize context for code generation

Before proceeding to Step 3, summarize what you learned:

```
Related story context:

Predecessor: #752 "Glossary Terms Table Grid" (branch: feature/752-glossary-table)
  - Main component: src/features/glossary/GlossaryPage.tsx
  - Table component: src/features/glossary/components/TermsTable.tsx
  - Data hook: src/features/glossary/hooks/useGlossaryTerms.ts
  → Integration: My filtering UI will be added inside GlossaryPage.tsx, above TermsTable

Similar: #761 "FAQ Search and Filter" (branch: feature/761-faq-search-filter)
  - Pattern: SearchFilterBar component + useSearchFilter hook + API query params
  - Files: FaqSearchBar.tsx, useSearchFilter.ts, types.ts
  → Template: Follow the same decomposition but for Glossary data
```

**If no predecessor or similar stories exist** (no relations in ADO), skip this step and proceed to Step 3 normally. The code generation will work fine without it — relations are an enhancement, not a requirement.

## Step 3: Analyze the Target Codebase

Navigate to the target codebase and study its conventions. This is critical — generated code must look like it belongs.

### 3a: Detect the Tech Stack

Read `package.json` (or equivalent) to identify:
- **Framework:** React / Next.js / Vue / Angular / Svelte / other
- **Language:** TypeScript vs JavaScript
- **CSS approach:** Tailwind / CSS Modules / styled-components / Sass / vanilla
- **State management:** Redux / Zustand / Context / Pinia / other
- **Testing framework:** Jest / Vitest / Playwright / Cypress
- **Component library:** MUI / shadcn/ui / Radix / Chakra / Ant Design / custom

### 3b: Identify Folder Structure

Map the project layout by scanning `src/` or `app/`:
- Where do components live? (`src/components/`, `src/features/`, `app/(routes)/`)
- How are pages/routes organized?
- Where are shared hooks, utilities, types?
- Where does the API layer live? (`src/api/`, `src/services/`, `src/lib/`)
- Are there barrel exports (`index.ts` files)?

### 3c: Check for Codebase Patterns

**First**, check if `projects/<ProjectName>/codebase-patterns.md` exists (generated by the "scan codebase" skill). If it does:
- Read it and use it as the **primary reference** for all code generation decisions
- It contains actual code snippets from developer-built features showing: component structure, data fetching, state management, form handling, routing, styling, shared UI components, type conventions, error handling, auth patterns, testing patterns, and code style
- **Follow these patterns exactly** — import ordering, naming conventions, hook usage, file organization, everything
- **Staleness check:** Read the `**Commit:**` line and run `git rev-list <scan-hash>..HEAD --count`. If >30 commits since the scan, warn: "The codebase patterns file was scanned [N] commits ago. Conventions may have changed. Want me to re-scan before generating code?" If the scan hash is not found (rebased), warn and suggest re-scan.
- If the file has a Reference Implementations table, use it to find the most relevant existing feature to model after (e.g., for a list page, look at the reference list page)

**If no `codebase-patterns.md` exists**, fall back to scanning 2-3 existing feature components to understand:
- File naming convention (PascalCase? kebab-case? index.ts pattern?)
- Component structure (functional, hooks, prop destructuring style)
- Import ordering conventions
- Error handling patterns
- How data fetching is done (React Query, SWR, useEffect, server components)
- How forms are handled (react-hook-form, Formik, native)

If neither exists and the codebase is mostly empty, suggest: "This codebase has very few implemented features. I recommend developers manually implement 2-3 reference stories first, then run 'scan codebase' so I can learn the patterns. Want me to generate code anyway using framework defaults?"

### 3d: Check for Design System

**First**, check if `projects/<ProjectName>/design-system.md` exists (generated by the "extract design system" skill). If it does:
- Read it and use its color tokens, typography scale, spacing values, border/shadow definitions, and component patterns
- **Read the Screen Blueprints section carefully** — this documents the exact component structure of each page (what components exist, their arrangement top to bottom, custom/unique elements). Match the generated page structure to the blueprint:
  - If the blueprint says "dark header with tabs → search bar with mode toggles → A-Z strip → letter-grouped table", generate exactly that — not a generic header + flat table
  - If the blueprint lists custom components (alphabet nav, expandable rows, mode toggles), generate those specific components — don't substitute generic alternatives
  - If the blueprint specifies column order, grouping behavior, or visual hierarchy, follow it exactly
- This is the authoritative source for all styling AND structural decisions — prefer it over guessing from the codebase

**If no `design-system.md` exists**, fall back to what the codebase itself provides:
- Theme configuration (tailwind.config, theme.ts, tokens.css, variables.scss)
- Shared UI components (Button, Input, Modal, etc.)
- Layout primitives (Container, Stack, Grid, etc.)
- Icon system (which icon library, how icons are imported)

If neither a design-system.md nor an in-codebase theme exists, use sensible defaults that match the detected framework (e.g., Tailwind defaults, MUI theme defaults) and add a TODO comment: `// TODO: Review styling — no design system was available during generation`.

**Document what you find.** You'll reference it throughout code generation.

## Step 4: Create the Git Branch

In the target codebase:

```bash
cd <target_codebase_path>
git fetch origin
git checkout <base_branch>
git pull origin <base_branch>
git checkout -b feature/<story-id>-<kebab-case-short-name>
```

**Branch naming rules:**
- Prefix: `feature/`
- Story ID from ADO
- Kebab-case short name from story title (max 40 chars, meaningful)
- Example: `feature/752-glossary-search-filter`

## Step 5: Generate the Code

Generate working feature code that follows EXACTLY the patterns found in Step 3. Place files in the correct locations for the codebase.

**If predecessor context was found (Step 2b):** integrate with the predecessor's existing files. Import from their modules, extend their types, add your components into their layouts. Don't duplicate what already exists — build on it.

**If similar story context was found (Step 2b):** follow the same structural pattern — same file decomposition, same hook extraction, same state management approach. Adapt the data, labels, routes, and endpoints. The similar story is your template.

### What to generate

**For UI features** (story has frontend work):
- **Main component file(s)** — the primary feature component with layout, state, and event handlers
- **Sub-components** — break down complex UIs into logical child components
- **Types/interfaces** — TypeScript types for props, state, API responses
- **Styles** — using the project's CSS approach (Tailwind classes, CSS module, etc.)
- **Custom hooks** — extract reusable logic (data fetching, form handling, etc.)
- **API integration** — service functions or hooks for backend calls (with TODO for real endpoints)
- **Test stubs** — test file with describe blocks and placeholder test cases
- **API-CONTRACT.md** — documents every API endpoint the frontend calls, so the backend developer knows exactly what to build (see below)

**For API features** (story has backend work):
- **Route/controller** — endpoint handler with request validation
- **Service layer** — business logic separated from HTTP concerns
- **Types/schemas** — request/response types, validation schemas
- **Database queries/models** — if the story involves data persistence
- **Test stubs** — test file with placeholder cases for happy path and errors

### Code quality rules

1. **Match existing style exactly** — formatting, naming, indentation, import order
2. **Use the project's existing components** — import from the design system, don't recreate primitives
3. **Generate working code that renders** — not empty stubs. Fill in layout, state, handlers based on the AC
4. **Use design tokens AND screen blueprints** — if `design-system.md` exists, use its tokens for styling and its screen blueprints for page structure. The generated page must match the blueprint's component inventory — same components, same arrangement, same custom elements. Don't simplify or substitute.
5. **Add targeted TODO comments** where the developer needs to make decisions:
   ```typescript
   // TODO: Replace with actual API endpoint once backend is ready
   // TODO: Add proper error handling for [specific edge case from AC]
   // TODO: Confirm pagination page size with product team
   ```
6. **Import from existing modules** — don't add new packages unless the project already uses them
7. **Follow the AC precisely** — each AC group should map to identifiable code behavior
8. **Handle loading, empty, and error states** if mentioned in AC

### API-CONTRACT.md

When the story involves frontend work, **always** generate `API-CONTRACT.md` in the branch root alongside FEATURE.md. This is not backend code — it's a contract that tells the backend developer exactly what the frontend expects.

Derive the contract from:
1. The **generated frontend code** — look at every fetch/axios/API call, every service function, every data hook. Each one implies an endpoint.
2. The **acceptance criteria** — business rules that must be enforced server-side (validation, authorization, calculations).
3. The **TypeScript types** — request/response shapes already defined in the frontend code.

The frontend code and API-CONTRACT.md together give the backend developer everything they need to implement the API without guessing.

**Template:**

```markdown
# API Contract: [Story Title]

**ADO Story:** #[StoryID] — [Story Title]
**Generated:** [YYYY-MM-DD]
**Frontend branch:** feature/[story-id]-[short-name]

> This contract documents every API endpoint the frontend code in this
> branch calls. The backend developer should implement these endpoints
> so the frontend works as-is with no changes to API calls.

---

## Authentication & Authorization

- **Auth method:** [Bearer token / session cookie / API key — match what the codebase uses]
- **Required role(s):** [admin / user / public — derive from the AC]
- **Auth header:** `Authorization: Bearer <token>` [or whatever the codebase convention is]

---

## Endpoints

### [METHOD] [/api/v1/resource]

**Description:** [What this endpoint does — one sentence]

**Request:**
| Parameter | Location | Type | Required | Description |
|-----------|----------|------|----------|-------------|
| `id` | path | string (UUID) | yes | Resource identifier |
| `page` | query | integer | no | Page number (default: 1) |
| `search` | query | string | no | Search filter |

**Request body** (if POST/PUT/PATCH):
```json
{
  "field_name": "string — description and constraints",
  "other_field": "number — min: 0, max: 100"
}
```

**Success response:** `200 OK`
```json
{
  "id": "uuid",
  "field_name": "string",
  "created_at": "ISO 8601 timestamp",
  "updated_at": "ISO 8601 timestamp"
}
```

**Error responses:**
| Status | Condition | Response body |
|--------|-----------|---------------|
| 400 | Validation failed | `{ "error": "field_name is required" }` |
| 401 | Not authenticated | `{ "error": "Authentication required" }` |
| 403 | Insufficient permissions | `{ "error": "Admin role required" }` |
| 404 | Resource not found | `{ "error": "Resource not found" }` |
| 409 | Duplicate resource | `{ "error": "Resource already exists" }` |

**Called from:** `src/hooks/useResource.ts` line ~XX

---

[Repeat for each endpoint]

---

## Data Models

### [ModelName]

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `id` | UUID | yes | auto-generated | Primary key |
| `name` | string | yes | 1-255 chars | Display name |
| `email` | string | yes | valid email format | User email |
| `status` | enum | yes | "active" ∣ "inactive" ∣ "pending" | Current status |
| `created_at` | datetime | yes | auto-generated | Creation timestamp |

---

## Server-Side Business Logic

These rules MUST be enforced on the backend — the frontend does client-side
validation for UX but the backend is the source of truth.

### Validation Rules
- [field_name] must be [constraint] — frontend validates on blur, backend rejects on submit
- [field_name] must be unique within [scope] — backend checks before insert
- [compound rule, e.g., "end_date must be after start_date"]

### Calculations & Derived Fields
- [field] is calculated as [formula] — frontend displays it read-only, backend computes on save
- [aggregation, e.g., "total is sum of line_item amounts"]

### Side Effects
- When [event], the backend must [action] — e.g., "when order status changes to 'shipped', send notification email"
- [Audit logging, e.g., "log all changes to [resource] with user ID and timestamp"]
- [Cascading updates, e.g., "when parent is deleted, soft-delete all children"]

### Authorization Rules
- [role] can [action] on [resource] — e.g., "only admin can delete users"
- [row-level rule, e.g., "users can only edit their own profile"]

---

## Pagination Convention

- **Style:** [offset-based / cursor-based — match codebase convention]
- **Default page size:** [number]
- **Response envelope:**
```json
{
  "data": [...],
  "total": 142,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```
```

**Rules for API-CONTRACT.md:**
- **One endpoint per API call in the frontend code.** If the frontend calls `GET /api/terms` and `POST /api/terms`, both must be documented.
- **Match the frontend's expectations exactly.** The request/response shapes must match the TypeScript types used in the generated code.
- **Include every error the frontend handles.** If the frontend code has a catch block for 409 Conflict, the contract must document when 409 occurs.
- **Be specific about validation.** Don't just say "validate email" — say "must be valid email format, max 255 chars, unique per organization."
- **Server-side logic section is critical.** Anything the AC says "must happen" that can't be trusted to the client (uniqueness checks, authorization, calculations, side effects) goes here.
- **Skip this file** if the story is purely backend with no frontend work, or if the frontend makes zero API calls (e.g., a purely static UI component).

## Step 6: Review & Fix (Multi-Agent Code Review)

After generating all code files but BEFORE committing, run a multi-agent review to catch issues. This is adapted from Anthropic's code-review plugin pattern: parallel specialized agents review the code from different angles, findings are validated, and issues are fixed inline.

### 6a: Launch Parallel Review Agents

Launch **4 subagents in parallel** using the Task tool. Each agent receives:
- The full list of generated files (paths and contents)
- The story's Acceptance Criteria and Technical Context block
- The project context (tech stack, framework)

**Agent 1: AC Coverage Check** (subagent_type: general-purpose)
```
Review the generated code against these Acceptance Criteria:
[paste all AC groups with bullet points]

For EACH AC bullet point, determine:
- COVERED: code clearly implements this behavior (cite the file and function)
- PARTIAL: code has a placeholder/TODO where implementation should be
- MISSING: no code addresses this at all

Return a structured list:
- AC 1, bullet 1: COVERED — GlossaryPage.tsx:handleSearch()
- AC 1, bullet 2: PARTIAL — search debounce exists but hardcoded to 500ms, AC says 300ms
- AC 2, bullet 3: MISSING — no empty state component generated

Only flag PARTIAL and MISSING items.
```

**Agent 2: Pattern Compliance Check** (subagent_type: general-purpose)
```
Review the generated code against these codebase patterns:
[paste relevant sections from codebase-patterns.md — component patterns, data layer, styling, type patterns, code style]

Check EVERY generated file for:
- Import ordering matches the documented convention
- Component structure matches the documented template (arrow vs function, export style, hook ordering)
- Data fetching follows the documented pattern (React Query / SWR / useEffect — whichever the project uses)
- Types follow the documented naming convention (IUser vs User vs UserDTO)
- Styling follows the documented approach (Tailwind class ordering, CSS module naming, etc.)
- Error handling follows the documented pattern
- File naming matches the documented convention

Return ONLY clear violations where the generated code diverges from a documented pattern. For each:
- File and line
- What the code does
- What the pattern says it should do
- Suggested fix

Do NOT flag style preferences not documented in the patterns file. Only flag divergences from explicitly documented conventions.
```

**Agent 3: Bug & Build Check** (subagent_type: general-purpose)
```
Review the generated code for obvious bugs and build-breaking issues:
[paste all generated file contents]

Check for:
- Missing imports (component/hook/type used but not imported)
- Undefined variables or functions
- Type errors (mismatched prop types, wrong function signatures)
- Broken references (importing from files that don't exist)
- Logic errors (conditions that are always true/false, infinite loops, race conditions)
- Missing null checks where data could be undefined (API responses, optional props)
- Event handlers that reference wrong state variables
- Async errors (missing await, unhandled promise rejections)

Return ONLY issues where the code will definitely fail to compile, crash at runtime, or produce wrong results. Do NOT flag:
- Style/formatting issues
- Potential issues that depend on runtime state
- Missing features (that's Agent 1's job)
- Performance suggestions
```

**Agent 4: Design System Compliance** (subagent_type: general-purpose) — ONLY if design-system.md exists
```
Review the generated code against this design system:
[paste relevant sections from design-system.md — colors, typography, spacing, component patterns, screen blueprint for this page]

Check:
- Color values match design tokens (no hardcoded hex values that should be tokens)
- Typography uses the documented type scale (correct font sizes, weights, line heights)
- Spacing uses the documented spacing scale (no arbitrary pixel values)
- Component usage matches documented patterns (correct Button variant, Input style, etc.)
- Page structure matches the screen blueprint (correct component order, correct hierarchy)
- Custom components from the blueprint are present (not substituted with generic alternatives)

Return ONLY clear mismatches between the generated code and the design system. For each:
- File and line
- What the code uses
- What the design system specifies
- Suggested fix
```

### 6b: Collect and Validate Findings

After all 4 agents return, collect their findings into a single list. For each finding, assess:
- **Is it actionable?** Can you fix it right now without more information?
- **Is it a real issue?** Does it actually break something, or is the agent being overly cautious?

Discard findings that are:
- False positives (the code is actually correct, the agent misread it)
- Subjective suggestions rather than concrete problems
- Duplicates across agents (keep the most specific version)
- Issues that require information you don't have (e.g., "this API might not exist" — you already know it's a TODO)

### 6c: Fix Validated Issues

For each validated finding, fix it immediately:

1. **MISSING AC items** → Generate the missing code. If the AC item requires backend work you can't implement, add a meaningful TODO with the specific AC reference.
2. **Pattern violations** → Rewrite to match the documented pattern. This is a mechanical fix — change the import order, rename the type, restructure the component.
3. **Bugs** → Fix the bug. Missing import → add it. Type error → correct the type. Logic error → fix the logic.
4. **Design system mismatches** → Replace hardcoded values with tokens. Restructure to match the blueprint.

### 6d: Quick Verification Pass

After fixing, do ONE more quick scan (not full parallel agents — just you reviewing your fixes):
- Did each fix actually resolve the finding?
- Did any fix introduce a new issue (e.g., fixing an import broke another reference)?
- Are all files still internally consistent?

If you find new issues from the fixes, fix those too. **Maximum 2 fix cycles** — after that, note any remaining issues in FEATURE.md's "What the Developer Needs to Do" section rather than looping forever.

### 6e: Build Verification (if available)

If the target codebase has a build/lint/type-check command, run it:

```bash
cd <target_codebase_path>
# Try in order — use whichever exists
npx tsc --noEmit 2>&1 || true          # TypeScript type check
npm run lint -- --quiet 2>&1 || true    # Linter
npm run build 2>&1 || true              # Full build
```

If any command fails due to generated code:
- Fix the specific errors (don't fix pre-existing errors in the codebase)
- Re-run to confirm the fix worked
- If unfixable (e.g., depends on a module you didn't generate), note in FEATURE.md

**Do NOT block on build errors caused by code outside your generated files.** Only fix issues in files you created.

---

## Step 7: Create FEATURE.md

Create `FEATURE.md` in the branch root (target codebase root):

```markdown
# Feature: [Story Title]

**ADO Story:** #[StoryID] — [Story Title]
**Branch:** feature/[story-id]-[short-name]
**Generated:** [YYYY-MM-DD]

## What Was Generated

| File | Purpose |
|------|---------|
| `src/components/Feature/FeatureName.tsx` | Main component with [brief description] |
| `src/components/Feature/SubComponent.tsx` | [brief description] |
| `src/hooks/useFeatureName.ts` | Custom hook for [brief description] |
| `src/components/Feature/FeatureName.test.tsx` | Test stubs |
| `API-CONTRACT.md` | Backend contract — endpoints, data models, server-side logic |
| ... | ... |

## Acceptance Criteria Coverage

- ✅ **AC 1: [Title]** — [how it's implemented]
- ✅ **AC 2: [Title]** — [how it's implemented]
- ⬜ **AC 3: [Title]** — stub only, needs [what's missing]
- ...

## What the Developer Needs to Do

**Frontend developer:**
1. [ ] Review component structure and adjust naming/organization if needed
2. [ ] Connect API calls to real endpoints once backend is ready (see TODO comments)
3. [ ] Replace mock/placeholder data with actual data sources
4. [ ] Complete test cases (stubs and describe blocks provided)
5. [ ] Verify responsive behavior and cross-browser compatibility

**Backend developer:**
6. [ ] Read `API-CONTRACT.md` — implement all documented endpoints
7. [ ] Implement server-side validation and business logic rules
8. [ ] Ensure response shapes match the contract exactly (frontend types depend on them)
9. [ ] [Any other story-specific items]

## Code Review Summary

**Review agents ran:** [4/4 or 3/4 if no design-system.md]
**Issues found:** [N] total → [M] validated → [M] fixed
**Build check:** [PASS / FAIL with details / SKIPPED — no build command available]

Issues fixed during review:
- [Brief description of each fix — e.g., "Added missing import for useCallback in GlossaryPage.tsx"]
- [...]

Remaining items (could not auto-fix):
- [Any issues noted but not fixed — e.g., "AC 3 bullet 4 requires backend endpoint that doesn't exist yet"]

## Story Relations Context

- **Predecessor:** [#ID — Title — what was used from it, or "None"]
- **Similar story:** [#ID — Title — what was used as template, or "None"]

## Design System

- **Source:** [design-system.md if used, or "No design system — used codebase defaults"]
- **Design notes:** [Any styling decisions made during generation]

## Tech Stack Used

- Framework: [detected framework]
- Styling: [detected CSS approach]
- State: [detected state management]
- Testing: [detected test framework]
```

## Step 8: Commit and Push

**Show the user what will be committed before proceeding.**

List all new/modified files and their purposes. Then ask: "Ready to commit and push this branch?"

**WAIT for approval.**

On approval:

```bash
cd <target_codebase_path>
git add -A
git commit -m "$(cat <<'EOF'
feat(#<StoryID>): scaffold <feature-name>

Generated feature code from ADO story #<StoryID>.
See FEATURE.md for what was generated and what needs review.
See API-CONTRACT.md for backend endpoint specifications.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
git push -u origin feature/<story-id>-<kebab-case-short-name>
```

Record the remote URL for the branch (extract from `git remote get-url origin`).

## Step 9: Update ADO Story

After the branch is pushed, update the ADO story to link to it.

**Add the Branch link** to the Description field. The branch link lives directly after the user story statement as a standard part of the description (not a "change" — no green/strikethrough needed):

```html
<p>As a [role],<br>
I want to [action],<br>
So that [benefit].</p>

<p><b>Branch:</b> <a href="<repo-url>/tree/feature/<story-id>-<short-name>">feature/<story-id>-<short-name></a></p>
```

If the description already has a Branch line (e.g., from a previous generation), **replace the URL** — don't duplicate it.

**Append** a Change Log entry to the AC field:

```html
<hr>
<b>Change {N}:</b> Feature code scaffolded<br>
<b>Date:</b> {YYYY-MM-DD}<br>
<b>Reason:</b> Generated starter code from acceptance criteria; branch pushed for developer handoff
```

**Add tag:** `Claude Modified Story` (additive to existing tags).

Use Python one-liner with `core.ado.update_work_item` to apply both updates:

```bash
cd ~/Downloads/xproject && python3 -c "
from core.config import load_project
from core.ado import from_project, update_work_item
p = load_project('<ProjectName>')
c = from_project(p)
update_work_item(c, <StoryID>, {
    'System.Description': '<updated description HTML>',
    'Microsoft.VSTS.Common.AcceptanceCriteria': '<updated AC HTML with changelog>',
    'System.Tags': '<existing tags>; Claude Modified Story'
})
print('ADO updated')
"
```

**Never use raw curl for ADO calls.**

## Step 10: Next Steps

Tell the user:

"Feature branch `feature/[story-id]-[short-name]` is ready.

- **Pushed to:** [remote URL]/tree/feature/[branch-name]
- **Linked in:** ADO story #[StoryID]
- **Files generated:** [count] files — see FEATURE.md for the full list
- **API contract:** API-CONTRACT.md documents all endpoints the frontend expects

The frontend developer checks out the branch and starts coding. The backend developer reads API-CONTRACT.md and implements the endpoints. You can:
1. **Generate code for another story** — give me another Story ID
2. **Create a pull request** — I can draft a PR for this branch
3. **Review the generated code** — I can walk through what was generated and why"

---

## Incremental Mode

If the branch already exists (e.g., new AC was added to the story, or the developer needs more code):

1. Check out the existing feature branch (don't create a new one)
2. Fetch the latest story data from ADO
3. Identify what's new or changed in the AC
4. Generate only the new/changed code
5. Run the review agents (Step 6) on the new/changed files only — same 4-agent parallel review, but scoped to the incremental changes
6. Fix any issues found
7. Commit as a separate commit: `feat(#<StoryID>): add <what changed>`
8. Update FEATURE.md with the additions
9. Push to the same branch

---

## Why One Story at a Time

**Always generate feature code one story at a time.** Do NOT batch-generate multiple stories in parallel or in quick succession.

Each generated feature — once reviewed by the developer and merged — becomes part of the codebase that the next generation can reference. This creates a compounding quality effect:
- **Story 1:** generated from codebase patterns + design system alone
- **Story 2:** sees Story 1's actual implementation → better imports, consistent types, realistic integration
- **Story 5:** sees 4 real features → code quality approaches hand-written level

The recommended workflow:
1. Generate code for one story → push branch
2. Developer reviews, adjusts, merges to main
3. Generate code for the next story (now the codebase has more real code to learn from)

If the user asks to generate multiple stories at once, explain this and suggest prioritizing by dependency order — predecessor stories first, then stories that build on them. The story relations (Step 2b) help determine the right order.
