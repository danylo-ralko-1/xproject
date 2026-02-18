# PreSales Pipeline

An AI-powered pre-sales assistant that lives in your terminal. Open Claude Code, describe what you need in plain English, and it handles requirements analysis, Azure DevOps stories, product documentation, and feature code generation for you.

**You don't need to memorize any commands.** Just chat with Claude like you would with a colleague.

## How It Works

Open your terminal and type:

```bash
presales
```

This launches Claude Code in the pipeline folder with all instructions loaded automatically. Then just tell it what you want. Here are some real examples:

### Starting a new project

> "Create a new presales project called Glossary"

Claude will set up the folder structure, ask for your Azure DevOps org and project name, and get everything ready.

### Processing requirements

Just drag and drop your files (PDF, DOCX, XLSX, images) directly into the Claude Code chat. No need to manually copy anything into folders — Claude will place them in the right location automatically and start processing.

> *drop files into chat*
>
> "These are the requirements for the project. Read them and give me an overview."

Claude will save the files, parse them, extract the requirements, and generate a summary with clarification questions for the client.

**Large document sets (20+ files):** If the combined requirements exceed Claude's context window, the system automatically splits them into per-file sections and builds a Source Reference index mapping topics to source files. Downstream steps use the overview as the primary source and do targeted reads of only the specific files needed for each story — no detail is lost, and the full context is never re-read unnecessarily.

### Generating stories

> "Break down these requirements into user stories with estimates"

Claude will create a structured breakdown with epics, features, stories, and effort estimates (FE/BE/DevOps/Design) — grouped by domain, ordered by development sequence.

### Pushing to Azure DevOps

> "Push these stories to ADO"

Claude will create the full hierarchy in Azure DevOps — Epics, Features, User Stories with detailed acceptance criteria and technical context, FE/BE/DevOps tasks — all properly linked. It also creates an Azure Repository and generates Product Overview and Change Requests wiki pages automatically.

### Generating feature code

> "Generate code for story #1464"

Claude will read the story from ADO, check predecessor and related story branches for context, analyze the shared design system, generate working starter code using shadcn/ui components, push it as a feature branch, and link the branch back to the ADO story. Frontend and backend developers check out the branch and start from a working baseline.

### Handling change requests

> "I got a change request from the client — they want to add a new filter."
>
> *drop the file into chat*

Claude will analyze the impact, identify affected stories, create a CR work item in ADO, update affected stories with red/green markup showing what changed, and update the Change Requests wiki page.

### Generating product documentation

> "Create a product overview from the ADO stories"

Claude will fetch all stories from ADO and generate wiki pages covering vision, problem statement, solution summary, user roles, key functional areas, data model overview, and technical environment.

## One-Time Setup

### 1. Clone and install

```bash
git clone https://github.com/danylo-ralko-1/presales-pipeline.git
cd presales-pipeline
pip install pyyaml click openpyxl requests python-docx pdfplumber
chmod +x presales
```

### 2. Install MCP dependencies (optional, for ADO MCP server)

```bash
pip install -r requirements-mcp.txt
```

### 3. Set up the `presales` alias

Add this to your `~/.zshrc` (or `~/.bashrc`):

```bash
alias presales="cd ~/Downloads/presales-pipeline && claude"
```

Then reload your shell:

```bash
source ~/.zshrc
```

### 4. Start chatting

```bash
presales
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
| Scan codebase patterns | "Scan the codebase and extract conventions" |
| Handle a change request | "Analyze this change request" *(drop file)* |
| Check project status | "What's the status of the Glossary project?" |

## Pipeline Flow

```
Ingest requirements → Breakdown into stories → Push to ADO + Generate wiki pages → Generate feature code
```

Each step builds on the previous one. ADO becomes the single source of truth once stories are pushed — all downstream operations (change requests, feature code, product docs) read from ADO.

Optionally, if the target repo already has code:
```
→ Scan existing codebase for patterns (improves code generation accuracy)
```

## Project Structure

```
presales-pipeline/
├── presales              # CLI entrypoint (used by Claude behind the scenes)
├── commands/             # Pipeline command implementations
├── core/                 # Config, ADO client, parser, context
├── ado_mcp/              # ADO MCP server for work item management
├── design-system.md      # Shared shadcn/ui component catalog (used by all projects)
├── projects/             # Your project workspaces (gitignored)
│   └── <ProjectName>/
│       ├── project.yaml  # Config: ADO credentials, pipeline state
│       ├── codebase-patterns.md  # Extracted conventions from target codebase (optional)
│       ├── input/        # Drop your requirement files here
│       ├── answers/      # Client answers to clarification questions
│       ├── changes/      # Change request files
│       ├── output/       # Everything Claude generates (incl. requirements_sections/ for large projects)
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
| `python3 presales init <project>` | Create a new project |
| `python3 presales ingest <project>` | Parse requirements from input files |
| `python3 presales breakdown-export <project>` | Export breakdown to Excel |
| `python3 presales push <project>` | Push stories to Azure DevOps |
| `python3 presales status <project>` | Show project status |
| `python3 presales list` | List all projects |

</details>
