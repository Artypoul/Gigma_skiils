# Project AGENTS.md snippet

Add this block to a project's `AGENTS.md` when website tasks should reliably start from the shared site-sense workflow:

```md
## Website workflow

- If the task is about website meanings, offer, hero, landing structure, sitemap, page copy, CTA, FAQ, SEO brief, or a full landing/site workflow, start with `website-workflow-router`.
- `website-workflow-router` must choose the right site-sense skill:
  - `website-strategy-orchestrator` for a full website or several website tasks at once
  - `meaning-positioning` for meanings, positioning, offer, and hero direction
  - `information-architecture` for sitemap, navigation, URL map, and structure
  - `content-strategy` or `seo-content-brief` for search/content planning
  - `page-copywriting` for finished page text
  - `conversion-copy-review` for critique of existing text
  - `russian-copy-polish` for the final Russian polish pass
```

Use this when a repo has local frontend or product skills, so website-strategy tasks do not get swallowed by a narrower engineering workflow.
