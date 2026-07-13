# Prompt Placement Matrix

Use the smallest surface that can reliably own the behavior.

| Prompt material | Codex placement | Why |
| --- | --- | --- |
| One-off task preference | Current user prompt | It should not become permanent behavior. |
| Repo rule or workflow gate | Project `AGENTS.md` | It must be visible before repository work starts. |
| Reusable workflow with clear trigger | `skills/<name>/SKILL.md` | Skills are discoverable and load only when relevant. |
| Long domain context or examples | `references/` | Keeps the skill compact while preserving detail. |
| Deterministic parsing or conversion | `scripts/` | Code is more testable than prose instructions. |
| Assets or templates used in output | `assets/` | Reuse beats re-creating fixed artifacts. |
| External API/tool capability | MCP server, app, connector, or plugin manifest | Instructions cannot create tools that do not exist. |
| Safety-critical enforcement | Permission, hook, CI, test, or review gate | A skill can guide behavior but cannot enforce security alone. |
| Current product facts | Official docs lookup skill or current source fetch | Facts drift; frozen prompt text becomes stale. |
| Personal preference | User settings or explicit user instruction | Avoid burying personal taste in a shared repo. |
| Dynamic conversation state | Current thread context | Do not store transient chat state in a reusable skill. |

Prefer multiple focused skills when a source prompt mixes unrelated jobs. A good split has clear triggers, clear boundaries, and independent verification.
