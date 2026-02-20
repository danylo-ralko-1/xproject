# JSON Schemas

Read this before generating `breakdown.json` or `push_ready.json`.

## breakdown.json

When generating the breakdown, output EXACTLY this structure:
```json
{
  "epics": [
    {
      "id": "EP-001",
      "name": "Epic Name",
      "description": "What this epic covers",
      "features": [
        {
          "id": "FT-001",
          "name": "Feature Name",
          "stories": [
            {
              "id": "US-001",
              "title": "Story Title",
              "acceptance_criteria": "Brief scope-level AC",
              "skip_qa": false,
              "fe_days": 0,
              "be_days": 0,
              "devops_days": 0,
              "design_days": 0,
              "risks": "Primary risk",
              "comments": "Technical notes",
              "assumptions": "What we assume"
            }
          ]
        }
      ]
    }
  ]
}
```

## push_ready.json

Before running `xproject push`, generate this file with full story details:
```json
{
  "epics": [
    {
      "id": "EP-001",
      "name": "Epic Name",
      "description": "Epic description",
      "features": [
        {
          "id": "FT-001",
          "name": "Feature Name",
          "stories": [
            {
              "id": "US-001",
              "title": "Story Title",
              "user_story": "As a [role],\nI want to [action],\nSo that [benefit].",
              "acceptance_criteria": [
                {
                  "title": "Search behavior",
                  "items": [
                    "Search field is visible on the page",
                    "Filtering starts after 2 characters"
                  ]
                },
                {
                  "title": "No results handling",
                  "items": [
                    "Display 'No results found' message when no match"
                  ]
                }
              ],
              "technical_context": {
                "data_model": [
                  "Term: { id: UUID, name: string (required, max 100), description: string (optional), category: enum [General, Technical, Legal] }"
                ],
                "states": [
                  "Default: table with paginated terms",
                  "Loading: skeleton rows",
                  "Empty: 'No terms yet' message with CTA",
                  "Error: inline error banner with retry"
                ],
                "interactions": [
                  "Click 'Add Term' → modal opens → fill form → submit → table refreshes",
                  "Type in search → 300ms debounce → GET /terms?q={query} → update table",
                  "Click column header → toggle sort asc/desc"
                ],
                "navigation": [
                  "Route: /glossary/terms",
                  "Parent: Glossary section in sidebar",
                  "Links to: /terms/{id} (detail)"
                ],
                "api_hints": [
                  "GET /terms?q=&page=&sort= → { items: Term[], total: number }",
                  "POST /terms → Term",
                  "PATCH /terms/{id} → Term",
                  "DELETE /terms/{id} → 204"
                ]
              },
              "reference_sources": [
                "RFP_document.pdf",
                "Transcription_summary_12.08.2026.txt"
              ],
              "predecessors": ["US-003"],
              "similar_stories": ["US-007"],
              "qa_td_description": "<b>Preconditions:</b><ul><li>User logged in as admin</li></ul><b>Test Data:</b><ul><li>...</li></ul><b>Environment:</b> Chrome 120+<br><br><hr><h4>AC 1: Search behavior</h4><b>TC-001: Verify search filters results</b> [P1]<br><i>Happy path</i><table border=\"1\" cellpadding=\"6\" cellspacing=\"0\" style=\"border-collapse:collapse; width:100%;\"><tr style=\"background-color:#f0f0f0;\"><th style=\"width:5%;\">#</th><th style=\"width:50%;\">Step</th><th style=\"width:45%;\">Expected Result</th></tr><tr><td>1</td><td>Type 'Term' in search field</td><td>Table filters to show only matching terms</td></tr></table>",
              "skip_qa": false,
              "fe_days": 2,
              "be_days": 3,
              "devops_days": 0,
              "design_days": 1,
              "risks": "Risk description",
              "comments": "Notes",
              "assumptions": "Assumptions"
            }
          ]
        }
      ]
    }
  ]
}
```
