# Set Up New Project

**Trigger:** "new project", "set up a project", "create project", "start a new project", or when there are no existing projects and the user wants to begin

**What to do:**
1. Run `python3 ~/Downloads/xproject/xproject init` (or with project name if provided)
2. This walks through an interactive setup: project name, ADO credentials, Figma token
3. All fields have sensible defaults — the user can skip and fill in later
4. After creation, remind: "Drop your requirement files right here in the chat, or put them in the input/ folder, then say 'ingest requirements'"

**If the user doesn't know where to get credentials:**
- ADO PAT: "Go to dev.azure.com → click your profile icon (top right) → Personal Access Tokens → New Token. Give it Work Items read/write scope."
- Figma PAT: "Go to figma.com → click your profile → Settings → Personal Access Tokens → Generate new token."