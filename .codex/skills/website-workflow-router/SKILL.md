---
name: website-workflow-router
description: "Route a website task to the right site-sense skill and act as the common entrypoint across projects for website strategy, product marketing, meanings, offer, sales angle, hero, structure, SEO, page copy, and copy review. Use whenever the user asks in broad or fuzzy language such as сайт, лендинг, смыслы сайта, оффер, позиционирование, продающий лендинг, маркетинг, продажи, упаковка, кому продаём, hero, структура сайта, тексты сайта, sitemap, IA, CTA, FAQ, copy, or when the agent is unsure which site-sense skill should run first."
---

# Website Workflow Router

Use this skill as the stable first hop for website work. Its job is not to do every stage itself, but to choose the right site-sense skill or chain and make sure the agent starts in the correct lane.

## Core rule

When a website task is broad, mixed, or underspecified, start here first.

Do not guess between product marketing, sales angle, strategy, IA, SEO, copy, and review. Route deliberately.

## Route map

Choose exactly one primary route first:

| User intent | Primary skill |
| --- | --- |
| Full website or landing workflow from scratch; several website tasks at once; user asks for site, landing, structure, messaging, and texts together | `website-strategy-orchestrator` |
| Need product context, market, audience, jobs, proof, sales context, or business framing before meanings or copy | `product-marketing-context` |
| Need meanings, positioning, offer, hero direction, sales angle, message hierarchy, objections, differentiation, or a stronger commercial promise | `meaning-positioning` |
| Need site structure, sitemap, navigation, URL map, taxonomy, breadcrumbs, or internal linking | `information-architecture` |
| Need content pillars, blog/resources plan, topic clusters, or editorial priorities | `content-strategy` |
| Need a specific SEO brief, search intent, metadata, outline, or must-answer questions for a page | `seo-content-brief` |
| Need final page text: homepage, landing, hero, sections, proof, FAQ, CTA, pricing copy, service page, product page | `page-copywriting` |
| Need critique or improvement of existing page copy, conversion strength, proof, objections, or CTA clarity | `conversion-copy-review` |
| Need only a final Russian polish pass: clearer, more natural, less generic, less bureaucratic | `russian-copy-polish` |

## Decision rules

1. If the user asks for several website outcomes at once, route to `website-strategy-orchestrator`.
2. If the user asks only for words like `смыслы`, `оффер`, `позиционирование`, `упаковка`, `как продавать`, or `hero`, route to `meaning-positioning`.
3. If the user already has the meaning and asks for finished text, route to `page-copywriting`.
4. If the user already has text and asks to improve it, route to `conversion-copy-review` first, then `russian-copy-polish` if needed.
5. If the user asks for structure before text, route to `information-architecture`.
6. If the user asks `кому продаём`, `какой сегмент`, `какой рынок`, `какая боль`, or `почему вообще это купят`, route to `product-marketing-context`.
7. If the project has real product, legal, or proof constraints, read project instructions first and keep them above generic website heuristics.

## Common chains

Use these chains when one skill is not enough:

- `product-marketing-context` -> `meaning-positioning`
- `meaning-positioning` -> `page-copywriting`
- `information-architecture` -> `seo-content-brief` -> `page-copywriting`
- `page-copywriting` -> `conversion-copy-review` -> `russian-copy-polish`
- Broad website project -> `website-strategy-orchestrator`

For commercial landing work, prefer:

- `product-marketing-context` -> `meaning-positioning` -> `page-copywriting`
- `meaning-positioning` -> `conversion-copy-review` when the problem is weak sales framing rather than grammar

Do not launch the whole chain by default when the user asked for one narrow artifact.

## Execution contract

When this router triggers:

1. Classify the task in one sentence.
2. Name the selected primary skill.
3. If a second step is clearly needed, name the next skill too.
4. Produce the next concrete artifact, not only advice.
5. If the user wants marketing or sales help, anchor the task in audience, buying trigger, proof, and safe commercial claims before writing copy.
6. If the task is blocked because the project lacks context, ask only the minimum questions or continue with explicit assumptions if the user prefers speed.

## Project reliability

This router is meant to make skill use more reliable across repositories, but it still depends on three conditions:

1. the `site-sense` plugin is installed and visible to the thread;
2. the thread started after plugin installation or update;
3. the project does not override the task into a narrower local workflow.

For project-level integration, read `references/project-snippet.md` and add its snippet to the repo's `AGENTS.md` when needed.
