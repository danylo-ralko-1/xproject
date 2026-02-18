# Generate Overview & Questions

**Trigger:** "generate overview", "analyze requirements", "create client questions", "what should we ask the client"

**Pre-checks:**
- Requirements must be ingested. If not: "I need to ingest requirements first. Drop the files here in the chat or put them in the input folder."
- If requirements were re-ingested since last overview, warn about staleness.

**What to do:**

## Step 0: Check context strategy
Read `output/requirements_manifest.json` and check `summary.context_strategy`:

- **`"full"`** (or missing field — backwards compat): proceed to Step 1 normally, read `requirements_context.md` as a single file.
- **`"sectioned"`**: the combined context exceeds the token window. Instead of reading `requirements_context.md` in one go:
  1. Read the `sections` array from the manifest to get the list of sections with their `start_line` and `end_line` offsets.
  2. Read each section from `requirements_context.md` one at a time using `Read(offset=start_line, limit=end_line - start_line + 1)`.
  3. After reading each section, take brief notes (key topics, entities, requirements, unknowns).
  4. After all sections are read, synthesize the notes into the overview and questions (Steps 1-2).

This ensures large document sets are processed incrementally without exceeding context limits. All content lives in one file (`requirements_context.md`) — the manifest just stores line offsets so each section can be read independently.

## Step 1: Generate overview.md
Read `requirements_context.md` (if strategy is `"full"`) or use notes from section-by-section reading (if strategy is `"sectioned"`) and generate a structured scope summary covering:
- Business problem and desired solution
- Functional scope (grouped by feature area)
- User roles and permissions
- Data model / term fields
- Non-functional requirements
- Timeline, deliverables, risks & dependencies
- Items marked TBD or uncertain

### Source Reference (MANDATORY — always append at end of overview)

After the main overview content, append a `## Source Reference` section that maps **topics to source files**. This index tells downstream skills (breakdown, push) exactly which file to re-read when they need specific detail — no guessing.

Build the index while reading the sources. For each file, note what kind of detail it contains. Group by topic, not by file.

**Format:**
```markdown
## Source Reference

| Topic | Detail available | Source file(s) |
|-------|-----------------|----------------|
| Data model — Term fields | Field names, types, max lengths, required/optional | Data-Model.xlsx, RFP.pdf (pp. 12-15) |
| Data model — User/roles | Role names, permission matrix | Security-Spec.pdf, Transcript-Jan20.md |
| Workflow — Term lifecycle | Draft → Review → Published states, approval rules | RFP.pdf (pp. 22-24), Client-Email-Feb3.md |
| Authentication | SSO requirements, session behavior | Security-Spec.pdf |
| Search & filtering | Search fields, filter options, expected behavior | Transcript-Jan20.md, RFP.pdf (p. 18) |
| Integration — External APIs | Third-party systems, data sync requirements | Technical-Spec.docx (section 4) |
| Non-functional | Performance targets, accessibility, browser support | RFP.pdf (pp. 30-32) |
```

**Rules for the source reference:**
- One row per topic/sub-topic — granular enough that a developer generating AC for "Term CRUD" can find the right file in one look
- "Detail available" column describes what specifics that file has (not a summary — a hint about what you'd find if you read it)
- Multiple files per topic is fine — list all that contribute
- Include page numbers or section names when known (helps with large PDFs)
- If a topic appears in only one file, still list it — the index must be complete
- The index covers ALL source files — every file must appear in at least one row

Save to `projects/<ProjectName>/output/overview.md`.

## Step 2: Generate questions.txt (client-ready email)

Generate clarification questions formatted as a **ready-to-send email** — not a technical document.

### Rules:

1. **Maximum 15 questions.** Prioritize questions that have the biggest impact on:
   - Architecture decisions (affects how the system is built)
   - Effort estimation (could swing the estimate significantly)
   - Timeline (blocks progress if unanswered)

   Skip nice-to-have questions that can be figured out later during development.

2. **Email format.** Structure the output like this:
   - **Greeting** — 1-2 sentences: what document we reviewed, what we're asking for
   - **Questions** — grouped into 3-4 simple, non-technical categories (e.g., "How the app should work", "Users & permissions", "Data & migration", "Technical setup"). NOT labels like "NFRs" or "Auth & SSO"
   - **Closing** — friendly note offering to jump on a quick call to go through the questions together

3. **Tone & language:**
   - Friendly, professional — write for a business stakeholder, not a developer
   - Each question should be short and clear (1-2 sentences max)
   - No sub-options (a/b/c/d) unless absolutely necessary for clarity
   - Avoid technical jargon. Examples:
     - Instead of "Is WCAG AA a hard requirement?" → "How important is accessibility for users with disabilities — is this a must-have for launch?"
     - Instead of "Confirm Azure AD / Entra ID for SSO" → "Can your IT team set up single sign-on so employees log in with their existing company accounts?"
     - Instead of "Should Sub-domains have a parent-child relationship with Domains?" → "When someone picks a domain (like Finance), should the sub-domain list automatically narrow down to match, or are they independent choices?"

4. **Overflow:** If there are more than 15 important questions, pick the top 15 for the email and save the rest in `projects/<ProjectName>/output/additional-questions.md` with a note that these are lower-priority items for internal tracking.

Save the email to `projects/<ProjectName>/output/questions.txt`.

## Step 3: Present results
1. Show a brief summary of the overview
2. Show the full questions email
3. If additional-questions.md was created, mention it
4. **Next steps:** "Two things to do now: (1) Review the overview — does it match your understanding? (2) Send the questions to the client. When you get answers, drop the response here in the chat or save it in `projects/<ProjectName>/answers/`. Then say 'create breakdown'."
