# PreSales Pipeline

Automated software pre-sales workflow powered by Claude Code. Handles requirements ingestion, story generation, Azure DevOps integration, Figma design validation, and change request management.

Claude Code does all the reasoning — Python scripts handle data I/O only.

## Prerequisites

- Python 3.10+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- Azure DevOps account with a Personal Access Token
- (Optional) Figma account with a Personal Access Token for design validation

## Setup

1. **Clone the repo:**

   ```bash
   git clone https://github.com/danylo-ralko-1/presales-pipeline.git
   cd presales-pipeline
   ```

2. **Install Python dependencies:**

   ```bash
   pip install pyyaml click openpyxl requests python-docx pdfplumber
   ```

3. **Configure credentials:**

   Copy the example env file and fill in your tokens:

   ```bash
   cp .env.example .env
   ```

   Edit `.env`:

   ```
   ADO_PAT=your_azure_devops_pat_here
   FIGMA_PAT=your_figma_personal_access_token_here
   ```

   - **ADO PAT:** dev.azure.com → User Settings → Personal Access Tokens (needs Work Items read/write scope)
   - **Figma PAT:** figma.com → Settings → Personal Access Tokens

4. **Make the CLI executable (macOS/Linux):**

   ```bash
   chmod +x presales
   ```

## Creating a New Project

```bash
python3 presales init MyProject
```

This creates `projects/MyProject/` with the required folder structure and a `project.yaml` config file. You'll be prompted for your ADO organization and project name.

Then drop your requirement files (PDF, DOCX, XLSX, TXT, images) into `projects/MyProject/input/` and start the pipeline:

```bash
python3 presales ingest MyProject
```

## Pipeline Commands

| Command | Description |
|---------|-------------|
| `presales init <project>` | Create a new project |
| `presales ingest <project>` | Parse requirements from input files |
| `presales breakdown-export <project>` | Export breakdown to Excel |
| `presales push <project>` | Push stories to Azure DevOps |
| `presales validate <project> --figma-link <url>` | Compare Figma designs against ADO stories |
| `presales enrich <project> --figma-link <url>` | Enrich story AC from Figma designs |
| `presales specs-upload <project>` | Upload spec files to ADO tasks |
| `presales status <project>` | Show project status and staleness |
| `presales list` | List all projects |

## Workflow

The typical flow inside a Claude Code conversation:

1. **Ingest** — parse requirement files into structured text
2. **Discover** — Claude reads requirements, generates overview and clarification questions
3. **Breakdown** — Claude generates epics/features/stories with estimates
4. **Push** — create work items in Azure DevOps
5. **Validate** — compare Figma designs against ADO stories, find gaps
6. **Enrich** — update story acceptance criteria from Figma designs
7. **Specs** — generate frontend/backend YAML specs per story

Use `/help` inside Claude Code for guided walkthroughs of each step.

## Project Structure

```
presales-pipeline/
├── presales              # CLI entrypoint
├── commands/             # Pipeline command implementations
├── core/                 # Config, ADO client, parser, context
├── .claude/skills/       # Claude Code skill definitions
├── projects/             # Project workspaces (gitignored)
│   └── <ProjectName>/
│       ├── project.yaml  # Config: ADO/Figma credentials, state
│       ├── input/        # Raw requirement files
│       ├── answers/      # Client answers to questions
│       ├── changes/      # Change request files
│       ├── output/       # Generated artifacts
│       └── snapshots/    # Versioned snapshots
├── .env                  # Credentials (gitignored)
├── .env.example          # Credential template
└── CLAUDE.md             # Claude Code instructions
```
