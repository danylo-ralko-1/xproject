# Generate Overview & Questions

**Trigger:** "generate overview", "analyze requirements", "create client questions", "what should we ask the client"

**Pre-checks:**
- Requirements must be ingested. If not: "I need to ingest requirements first. Drop the files here in the chat or put them in the input folder."
- If requirements were re-ingested since last overview, warn about staleness.

**What to do:**

## Step 0: Check for incremental changes
Read `output/requirements_manifest.json` and check `summary.new_files`, `summary.changed_files`, and `summary.removed_files`:

- **If `overview.md` does NOT exist yet** (first run): do a **full discovery** — read all parsed files from `output/parsed/` one by one, take notes on each, then synthesize into overview and questions.
- **If `overview.md` exists AND `new_files` + `changed_files` lists are non-empty**: do an **incremental discovery**:
  1. Read the existing `overview.md` (including the Source Reference table).
  2. Read ONLY the parsed files for new/changed sources from `output/parsed/` (the manifest's `files` array has the `parsed_file` field with the filename).
  3. Update the overview to incorporate the new/changed information — add new topics, revise affected sections, update the Source Reference table with new rows or modified entries.
  4. If files were removed (`summary.removed_files`), remove their references from the Source Reference and flag any overview sections that relied solely on those files.
  5. Regenerate `questions.txt` only if the new information raises new questions.
- **If `overview.md` exists AND no new/changed/removed files**: skip discovery entirely — tell the user "Requirements haven't changed since last overview."

For full discovery with many files, read each file from `output/parsed/` one at a time, take brief notes (key topics, entities, requirements, unknowns), then synthesize after all are read. This handles large document sets naturally — each file is its own small read.

## Step 1: Generate overview.md
Use notes from reading parsed files (full discovery) or update the existing overview (incremental) to generate a structured scope summary covering:
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
