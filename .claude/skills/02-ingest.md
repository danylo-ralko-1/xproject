# Ingest Requirements

**Trigger:** "ingest requirements", "process these files", "parse the RFP", or when the user drops/adds files to the conversation

**Pre-checks:**
- Confirm files exist in `projects/<ProjectName>/input/`
- If empty: "I don't see any files in the input folder. You can drag and drop files right here in the chat, or put them in `projects/<ProjectName>/input/`."

**If the user drops files directly in the chat:**
1. Copy each file to `projects/<ProjectName>/input/` using `cp`
2. Confirm: "I've saved 3 files to the project input folder: RFP.pdf, Requirements.docx, Wireframes.png"
3. Then proceed with ingestion automatically — don't make them say "ingest" separately

**What to do:**
1. Run `python3 ~/Downloads/xproject/xproject ingest <ProjectName>`
2. Report what was parsed and any errors
3. **Next steps:** "Requirements are ingested. Next, say 'generate overview' and I'll analyze them and prepare questions for the client."