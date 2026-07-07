# Agent handoff

Use this block at the end of every skill output so the next skill can continue without re-asking the same questions.

```yaml
handoff:
  from_skill: ""
  next_skill: ""
  project_type: ""
  audience_primary: ""
  site_goal: ""
  primary_cta: ""
  decisions: []
  assumptions: []
  proof_available: []
  proof_gaps: []
  priority_pages: []
  files_created_or_updated: []
  open_questions: []
```

Rules:

- Put facts under `decisions` only when they came from the user, project files or reliable research.
- Put guesses under `assumptions`.
- Put unsupported claims under `proof_gaps`.
- Keep `open_questions` short and only include questions that change the result.
