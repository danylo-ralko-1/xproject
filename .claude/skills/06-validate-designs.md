# Validate Designs Against Requirements

> **OPTIONAL — STANDALONE SKILL.** This is NOT part of the standard pipeline flow. It is available for manual invocation when a user explicitly asks to compare Figma designs against ADO stories. Do NOT suggest this as a next step from other skills, and do NOT list it as a required pipeline stage.

**Trigger:** "validate designs", "compare Figma with ADO", "check designs against requirements", "find gaps in designs"

**Pre-checks:**
- ADO credentials must be configured in `project.yaml` (`ado.organization`, `ado.project`, `ado.pat`). Test the connection and confirm stories exist. If no credentials: "I need ADO credentials to read the stories. What's your organization name, project name, and Personal Access Token?" If connected but no stories found: "I connected to ADO but didn't find any user stories. Are they in a different project?"
- Figma PAT must be configured in `project.yaml` (`figma.pat`). If not: "I need your Figma access token. Go to figma.com → Settings → Personal Access Tokens → Generate new token. What's the token?"
- Figma link must be provided. If not: "What's the Figma file URL? It looks like https://www.figma.com/design/ABC123/ProjectName"

**What to do:**

This skill uses the **screenshot-based approach**: Python fetches all screenshots in 2 API calls, you analyze them with vision. No MCP node crawling.

## Step 1: Gather Data (Python)

Run: `python3 ~/Downloads/xproject/xproject validate <ProjectName> --figma-link <url>`

This does:
- 1 API call to get Figma file structure (pages and frames)
- 1 batch API call to export all screen screenshots via Figma REST API (`/v1/images/{file_key}`)
- Downloads screenshots to `output/screenshots/`
- Fetches all ADO stories with current AC
- Saves everything to `output/validation_bundle.json`

The bundle contains:
```json
{
  "screens": [
    {
      "name": "Login Page",
      "node_id": "123:456",
      "screenshot_path": "output/screenshots/login-page.png",
      "page": "Authentication"
    }
  ],
  "stories": [
    {
      "ado_id": 720,
      "title": "User Login",
      "description": "...",
      "acceptance_criteria": "...",
      "tags": "...",
      "state": "New"
    }
  ],
  "figma_file_key": "xo7gE69nspbRI8yDMo1waf"
}
```

## Step 2: Analyze Screenshots with Vision (YOU do this)

Read `output/validation_bundle.json` to get the list of screens and stories.

For each screenshot in `output/screenshots/`:
1. Look at the image to identify all visible UI elements: fields, buttons, labels, headings, navigation, states
2. Match it to ADO stories based on content
3. Check if all acceptance criteria elements are present in what you see
4. Note anything visible in the design that has no corresponding story

**Process screens in batches of 3-5** — include multiple images in one analysis pass to save time.

## Step 3: Cross-Reference

For each ADO story:
- Find matching screenshot(s)
- If no screenshot and story needs UI → gap
- If backend-only story → skip

For each screenshot:
- Find matching story/stories
- Check every AC element against what's visible
- Note elements with no corresponding AC

## Step 4: Generate Report

Organize findings into these categories:

### ✅ Fully Matched
Screens that cover all AC for their matching stories.

### 🔴 Missing Designs
Stories that need UI but have no Figma screen. For each: ADO ID, title, what screen is expected.

### 🟡 Incomplete Designs
Screens that exist but are missing elements from AC. For each: screen name, ADO ID, specific missing elements or states.

### 🟠 Inconsistencies
Both exist but don't match — wrong labels, missing fields, incorrect flow, missing states. For each: what AC says vs what Figma shows.

### 🔵 Untracked Design Elements
Visible in screenshots but no ADO story. Should they be added as stories, removed from Figma, or ignored?

### Summary Table
| Category | Count |
|---|---|
| Fully matched | X |
| Missing designs | X |
| Incomplete | X |
| Inconsistencies | X |
| Untracked | X |

### Proposed New Stories
For any gaps that need new stories:
- Title, Epic/Feature, brief AC, estimated effort (FE/BE/DevOps days)

### Proposed Modifications
For stories that need AC updates:
- ADO ID, title, what to change, effort impact

## Step 5: Wait for Approval

**WAIT for the user to review and approve before making any ADO changes.**

## Step 6: On Approval — Update ADO

### New stories
Create in ADO using `core.ado`:
- User Story with description (user story text only), AC (no Change Log on creation), effort
- Discipline Tasks as children (FE/BE/DevOps where effort > 0)
- Tags: `Claude New Story` (no other tags)
- Link to appropriate Feature parent

### Modified stories
Update existing stories following the **Modification Rules**:
- **Never overwrite** existing AC text. Use red strikethrough for old content, green for new:
  ```html
  <span style="color:red;text-decoration:line-through">old AC text</span>
  <span style="color:green">new AC text from design validation</span>
  ```
- **Change Log:** Only add a Change Log entry if the modification is a **genuine scope change** (e.g., validation reveals the design contradicts the AC, or a feature works differently than specified). Do NOT add a Change Log for minor AC refinements or clarifications that don't change what the story delivers.
- Add tag `Claude Modified Story` (preserve existing tags)

### Outdated stories
If validation reveals a story is no longer relevant (e.g. the design shows a completely different approach):
- Add `<p><b>⚠️ OUTDATED</b> — Design validation shows this functionality was replaced by [description].</p>` at the top of the Description
- If a replacement story is being created, add an ADO link (`System.LinkTypes.Dependency-Forward`) to the new story, and link the new story back (`System.LinkTypes.Dependency-Reverse`)
- Append a Change Log entry to the AC field (next sequential number): "Marked outdated", Reason = "Replaced by ADO #{new_id}"

### Mapping update
Update `output/ado_mapping.json` with any new story IDs

## Step 7: Next Steps

Tell the user:
"Validation is done. The report shows what matches, what's missing, and what conflicts between Figma and ADO."

## Step 8: Auto-update Product Document

Regenerate the product document (see skill 10-product-document) to reflect any new or modified stories.

---

**If you need more detail on a specific screen:** Use the Figma MCP `get_design_context` for that one node ID (available in the bundle). Don't crawl the whole tree — only drill in when the screenshot isn't enough.