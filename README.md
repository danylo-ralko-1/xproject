# xProject

An AI-powered project assistant that lives in your terminal. Open Claude Code, describe what you need in plain English, and it handles requirements analysis, Azure DevOps stories, product documentation, and feature code generation for you.

**You don't need to memorize any commands.** Just chat with Claude like you would with a colleague.

## How It Works

Open your terminal and type:

```bash
xproject
```

This launches Claude Code in the pipeline folder with all instructions loaded automatically. Then just tell it what you want. Here are some real examples:

### Starting a new project

> "Create a new project called Glossary"

Claude will set up the folder structure, ask for your Azure DevOps org and project name, and get everything ready. The ADO project is created with the Agile process template.

### Processing requirements

Just drag and drop your files (PDF, DOCX, XLSX, images) directly into the Claude Code chat. No need to manually copy anything into folders — Claude will place them in the right location automatically and start processing.

> *drop files into chat*
>
> "These are the requirements for the project. Read them and give me an overview."

Claude will save the files, parse them, extract the requirements, and generate a summary with clarification questions for the client (max 15 questions, formatted as a ready-to-send email).

**Meeting transcriptions:** If you drop a call recording transcript, Claude will ask whether to compact it down to just the key requirements, decisions, and open questions before saving — raw transcriptions have very low information density (~10% signal), so compacting produces a much better overview.

**Large document sets (20+ files):** Each input file is parsed into its own `.md` file in `output/parsed/` — no combined mega-file. Claude reads each parsed file one at a time during discovery and synthesizes everything into an overview with a Source Reference table. Downstream steps use the overview as the primary source and do targeted reads of only the relevant parsed files when detail is needed. Incremental re-ingestion only processes new or changed files.

### Generating stories

> "Break down these requirements into user stories with estimates"

Claude will create a structured breakdown with epics, features, stories, and effort estimates (FE/BE/DevOps/Design) — grouped into multiple domain-specific epics, ordered by development sequence (infrastructure first, core features next, nice-to-haves last). Both `breakdown.json` and `breakdown.xlsx` are generated.

### Pushing to Azure DevOps

> "Push these stories to ADO"

Claude will create the full hierarchy in Azure DevOps:

- **Epics** grouped by functional domain (never a single mega-epic)
- **Features** under each epic
- **User Stories** with detailed acceptance criteria, technical context (data model, states, interactions, navigation, API hints), and reference sources listing which input files informed each story
- **Tasks** — FE, BE, DevOps discipline tasks plus QA tasks ([QA][TD] for test design, [QA][TE] for test execution) for every testable story
- **Relations** — predecessor and similar-story links between stories
- **Attachments** — original source files (PDF, DOCX, etc.) are uploaded and attached to each story that references them
- **Azure Repository** created automatically in the ADO project
- **Wiki pages** — Product Overview and Change Requests pages generated in ADO

Stories include resume support — if the push is interrupted, re-running picks up where it left off.

### Generating feature code

> "Generate code for story #1464"

Claude will read the story from ADO, check predecessor and related story branches for context (to understand WHERE to place the code and HOW to implement it), analyze the shared design system and codebase patterns, generate working starter code using shadcn/ui components, push it as a feature branch (`feature/US-{id}-{kebab-title}`), and link the branch back to the ADO story (both as a description link and an ADO artifact link in the Development section). Frontend and backend developers check out the branch and start from a working baseline.

Code generation strictly implements only what the story's acceptance criteria says — no scope bleed from sibling stories.

### Generating tests

> "Generate tests for story #1464"

Claude will read the developer-edited feature code on the branch, cross-reference with the story's AC from ADO, generate comprehensive tests, and commit them to the feature branch.

### Handling change requests

> "I got a change request from the client — they want to add a new filter."
>
> *drop the file into chat*

Claude will ask whether to create a formal Change Request or just edit the affected stories directly. For a full CR:

- Creates a CR work item in ADO (with AC, technical context, and child tasks)
- Updates affected stories with red/green markup showing exactly what changed across all fields (AC, Technical Context, Description)
- Adds a Change Log entry with a link to the CR
- Creates successor links from affected stories to the CR
- Updates the Change Requests wiki page
- Creates a source file in `changes/` and attaches it to the CR in ADO
- Updates `overview.md` to reflect the new project state

**Verbal change requests** are also tracked — Claude creates a `.txt` file capturing the essence of the request (date, reason, affected stories, summary) so every CR has a traceable source document even without a dropped file.

### Generating product documentation

> "Create a product overview from the ADO stories"

Claude will fetch all stories from ADO and generate wiki pages covering vision, problem statement, solution summary, user roles, key functional areas, data model overview, technical environment, and key risks & assumptions. The wiki is automatically updated when major changes happen (new pages, new roles, new epics).

## One-Time Setup

### 1. Clone and install

```bash
git clone https://github.com/danylo-ralko-1/xproject.git
cd xproject
pip install pyyaml click openpyxl requests python-docx pdfplumber
chmod +x xproject
```

### 2. Install MCP dependencies (optional, for ADO MCP server)

```bash
pip install -r requirements-mcp.txt
```

### 3. Set up the `xproject` alias

Add this to your `~/.zshrc` (or `~/.bashrc`):

```bash
alias xproject="cd ~/Downloads/xproject && claude"
```

Then reload your shell:

```bash
source ~/.zshrc
```

### 4. Start chatting

```bash
xproject
```

That's it. This opens Claude Code in the pipeline folder with all instructions loaded automatically. Credentials (ADO PAT) are configured per-project in `project.yaml` when you create a new project — Claude will ask you for them.

**Where to get your ADO PAT:** dev.azure.com → User Settings → Personal Access Tokens (needs Work Items read/write, Code read/write, Wiki read/write)

## What You Can Ask Claude To Do

### Main Pipeline

| What you want | Just say something like... |
|---|---|
| Set up a new project | "Create a new project called ClientName" |
| Read requirement files | *(drop files into chat)* "These are the requirements" |
| Get a requirements overview | "Summarize the requirements and give me questions for the client" |
| Break down into stories | "Generate a breakdown with estimates" |
| Export to Excel | "Export the breakdown to an Excel file" |
| Push stories to ADO | "Push these stories to Azure DevOps" |
| Generate product documentation | "Create a product overview from the ADO stories" |
| Generate feature code | "Generate code for story #1464" |
| Generate tests | "Generate tests for story #1464" |
| Scan codebase patterns | "Scan the codebase and extract conventions" |
| Handle a change request | "Analyze this change request" *(drop file)* |
| Handle a verbal change | "The client wants to rename Domain to Category" |
| Check project status | "What's the status of the Glossary project?" |

## Pipeline Flow

```
Ingest requirements → Breakdown into stories → Push to ADO + Generate wiki pages → Generate feature code → Generate tests
```

Each step builds on the previous one. ADO becomes the single source of truth once stories are pushed — all downstream operations (change requests, feature code, product docs, tests) read from ADO.

Optionally, if the target repo already has code:
```
→ Scan existing codebase for patterns (improves code generation accuracy)
```

Change requests can happen at any point after push:
```
→ CR analyzed → ADO stories updated → overview.md updated → wiki updated
```

## Project Structure

```
xproject/
├── xproject              # CLI entrypoint (used by Claude behind the scenes)
├── commands/             # Pipeline command implementations
├── core/                 # Config, ADO client, parser, context, events
├── ado_mcp/              # ADO MCP server for work item management
├── design-system.md      # Shared shadcn/ui component catalog (used by all projects)
├── projects/             # Your project workspaces (gitignored)
│   └── <ProjectName>/
│       ├── project.yaml  # Config: ADO credentials, pipeline state
│       ├── codebase-patterns.md  # Extracted conventions from target codebase (optional)
│       ├── input/        # Drop your requirement files here
│       ├── answers/      # Client answers to clarification questions
│       ├── changes/      # Change request source files (also ingested for discovery)
│       ├── output/       # Everything Claude generates
│       └── snapshots/    # Auto-snapshots before change requests
└── CLAUDE.md             # Instructions Claude follows automatically
```

## Prerequisites

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Azure DevOps account with a Personal Access Token

---

<details>
<summary><b>CLI Command Reference (advanced)</b></summary>

These are the Python commands that Claude runs behind the scenes. You don't need to use them directly — Claude will call them for you. But if you prefer running things manually:

| Command | Description |
|---------|-------------|
| `python3 xproject init <project>` | Create a new project |
| `python3 xproject ingest <project>` | Parse requirements from input/ and changes/ |
| `python3 xproject breakdown-export <project>` | Export breakdown to Excel |
| `python3 xproject push <project>` | Push stories to Azure DevOps |
| `python3 xproject status <project>` | Show project status |
| `python3 xproject list` | List all projects |

</details>
