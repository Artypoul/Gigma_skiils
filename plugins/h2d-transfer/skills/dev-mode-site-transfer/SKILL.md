---
name: dev-mode-site-transfer
description: "Transfer a live website or page block by block from browser dev mode into clean HTML, Tailwind, or React when the source is a public URL or existing frontend rather than a .h2d snapshot. Use when the user asks to copy a site from dev mode, inspect a live page, rebuild a WordPress/Elementor or legacy marketing site section by section, extract layout/assets/styles from DOM and CSS, or recreate a website quickly without dragging legacy markup into the new codebase. Prefer this skill over `h2d-pixel-perfect-transfer` when speed and clean reconstruction matter more than formal H2D proof gates, and switch back to H2D when the task requires strict pixel-proof, complex runtime motion, canvas/WebGL, or source-intake evidence."
---

# Dev Mode Site Transfer

Use this skill when the source of truth is a live site and the practical move is:

1. confirm the page opens and you can inspect it in browser dev mode;
2. inventory blocks, assets, and layout tokens;
3. rebuild the page cleanly in new code;
4. verify that the result is faithful enough for the requested level.

This is not the H2D proof pipeline. Do not call the result `pixel-perfect` unless the user only asked for a close transfer or you later validate it with stricter diff methods.

If you cannot open the live page, inspect the final rendered DOM/CSS, or access the meaningful states needed for transfer, stop and report `blocked`.

If the user says the transfer is wrong, off-spec, not from the source, or nothing changed, stop the previous fix path, rebuild the source-of-truth map for the complained-about block, and only then continue.

## Agent Stance

Work like a reconstruction agent, not like a stylist.

- rebuild from inspected evidence;
- keep the source and the candidate mentally separate;
- do not compensate one wrong block by globally scaling or nudging the whole page;
- do not report success from memory after a complaint; re-open the block and prove it again.

## Recovery Protocol

After complaint-driven feedback:

1. stop the previous fix path;
2. re-read the latest user message;
3. lock the winning source for the complained-about block;
4. name the exact delta in one line;
5. fix only that block first;
6. rerun the comparison at the judged width before claiming improvement.

## Choose the route first

Use this skill when most of these are true:

- source is a public URL, existing landing page, WordPress/Elementor site, Tilda/Webflow-like marketing page, or legacy static site;
- the page is mostly normal DOM/CSS/images/video embeds;
- the goal is to transfer blocks into cleaner code, not preserve every wrapper or plugin artifact;
- speed and practical fidelity matter more than formal proof gates.

Use `h2d-pixel-perfect-transfer` instead when any of these are true:

- user explicitly wants proof-gated pixel-perfect transfer;
- source is already a `.h2d` snapshot;
- the page depends on canvas, WebGL, heavy motion, scroll-linked choreography, or runtime-only states;
- you need formal geometry / live diff / behavior / liveness evidence before saying `ready`.

If unsure, read `references/dev-mode-transfer-checklist.md` and decide honestly.

## Quick workflow

1. Run a preflight: confirm the live page opens and dev-mode inspection is actually available.
2. Lock the source of truth.
3. Identify the stack.
4. Build a block inventory.
5. Extract visual tokens and assets from dev mode.
6. Rebuild each block in clean markup/components.
7. Verify desktop and mobile behavior and keep lightweight evidence.
8. Report the true status with canonical labels: `clean-transfer`, `close-match`, `needs-polish`, `changed-source`, or `blocked`.

## Lock the source of truth

Before rebuilding, decide what actually wins:

- live site only;
- live site + a specific screenshot/crop;
- live site visuals + a separate behavior donor;
- another explicit source the user named.

Record that decision in a small working map:

```text
block | winning source | desktop width | mobile width | key behavior | allowed deviation
```

Do not silently mix donor, Figma, screenshots, and current local code into one blended interpretation.

## 1. Identify the stack

Before copying anything, determine what you are looking at:

- generator/CMS/framework: WordPress, Elementor, Tilda, Webflow, custom React, legacy jQuery;
- whether the page is mostly server-rendered DOM or hydrated runtime UI;
- whether layout is simple marketing content or complex app behavior;
- whether images/video embeds/icons/fonts are directly reusable.

Use browser dev mode, page source, loaded CSS/JS URLs, and generator meta tags when available.

Do not assume the raw DOM is worth preserving. On builder sites, the DOM often contains many wrappers that should not survive the rebuild.

If browser inspection is unavailable, the page is auth-gated, or the visible state cannot be reached safely, stop early with `blocked` instead of inventing the missing source data.

## 2. Build a block inventory

Work page-by-page and block-by-block, not as one giant paste.

For each block capture:

- purpose: hero, social proof, gallery, pricing, CTA, contacts, FAQ, footer;
- visible text content;
- asset dependencies;
- desktop layout pattern;
- mobile layout pattern;
- interaction, if any;
- which source proves the block is correct.

Name blocks by role, not by source CSS class. Good names:

- `hero`
- `service-cards`
- `video-gallery`
- `contact-cta`
- `footer-contacts`

Bad names:

- `elementor-section-42`
- `vc_row_7`
- `wp-block-group-3`

## 3. Extract only the useful source material

From browser dev mode, pull the useful pieces:

- text content;
- image and video URLs;
- font family, weight, size, line-height;
- colors, gradients, shadows, borders;
- container widths, grid/flex patterns, gaps, padding, margin;
- breakpoints that visibly change the layout;
- interactive states: hover, active, expanded, open, slide transitions.

Prefer:

- computed styles for the final visible result;
- reusable design tokens;
- original asset URLs from network/DOM;
- section-level measurements.

Avoid blindly copying:

- tracking scripts;
- analytics;
- builder-specific wrapper div soup;
- plugin-generated ids/classes unless they are needed for behavior;
- giant inline style blobs when 3-5 reusable classes/tokens express the same thing.

## 4. Rebuild cleanly

Reimplement the block in the target stack with cleaner structure than the source.

Rules:

- preserve visual hierarchy and spacing;
- preserve CTA order and reading flow;
- preserve images, embeds, and meaningful interactions;
- simplify DOM depth whenever possible;
- keep components reusable across similar pages.

Recovery rules:

- fix one complained-about block at a time;
- prefer local block fixes over page-wide scaling or compensating layout hacks;
- do not announce the block as done until you rerun the comparison at the complained-about width;
- if the user says nothing changed, re-check the served build, cache/versioning, and actual DOM state before another CSS edit.

Do not "transfer from dev mode" by dumping copied production HTML into the new codebase and only renaming a few classes. That imports legacy debt instead of transferring the design.

## 5. Verification standard

Minimum verification before calling the block transferred:

- save lightweight evidence from inspection and comparison: at least one desktop capture and one mobile capture, or equivalent per-block notes/screenshots;
- compare the result side-by-side with the live source on desktop;
- compare at least one mobile width;
- verify headings, text order, CTA labels, and assets;
- verify that any meaningful gallery, slider, accordion, or menu still behaves plausibly;
- verify that clickable-looking controls either work or are intentionally decorative in both behavior and affordance.

Recommended working widths:

- `390`
- `768`
- `1024`
- `1440`

If the source visibly changes outside these widths, test the real breakpoints you observe.

If you cannot leave this minimum evidence trail, do not claim `clean-transfer`; use `needs-polish` or `blocked`, depending on what is missing.

## 6. Honest status language

Use these labels honestly:

- `clean-transfer` when the rebuilt block/page is faithful and production-usable;
- `close-match` when visual fidelity is strong but there are still spacing or behavior differences;
- `needs-polish` when the structure is there but details remain;
- `changed-source` when the live site drifted while you were transferring it;
- `blocked` when critical assets, behavior, or tooling are unavailable.

Do not say `pixel-perfect` from dev mode alone unless you actually did the stricter proof work.

## Special cases

### WordPress / Elementor / builder pages

Treat the live page as a visual reference, not as a DOM template.

Usually safe to extract:

- block order;
- text;
- assets;
- visible spacing;
- card/grid patterns;
- button styles.

Usually not worth preserving:

- nested builder wrappers;
- plugin-specific utility classes;
- auto-generated ids;
- excess spacer elements.

### Legacy static / old CMS pages

Expect:

- table-like layout habits;
- hard-coded widths;
- inline styles;
- outdated image dimensions;
- duplicate pages with near-identical content.

Transfer the design language, not the legacy implementation baggage.

### Runtime-heavy pages

If you discover canvas, complex sliders, heavy animation, or runtime-only UI state, stop pretending dev-mode copy is enough. Escalate to:

- stricter manual behavior capture, or
- `h2d-pixel-perfect-transfer` if proof-grade reconstruction is required.

## Reference

Read `references/dev-mode-transfer-checklist.md` when you need:

- the route decision matrix;
- a capture checklist from dev mode;
- stack-specific warnings;
- the final handoff checklist.
