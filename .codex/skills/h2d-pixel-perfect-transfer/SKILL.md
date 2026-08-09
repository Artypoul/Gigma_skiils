---
name: h2d-pixel-perfect-transfer
description: "Transfer pages or components from .h2d snapshots into Tailwind HTML/React with hard validation gates for source intake, typography, geometry, asset paint, provenance, live comparison, behavior replay, and liveness/WebGL motion. Use when the user asks for H2D transfer, html.to.design reconstruction, pixel-perfect frontend recreation, a full-page transfer from a .h2d donor, or a live clone that must prove runtime fidelity instead of shipping a static screenshot."
---

# H2D Pixel-Perfect Transfer

Use this skill for `.h2d` to code work where "looks close enough" is not acceptable.

Resolve bundled paths relative to this `SKILL.md`.

If the user says the result is wrong, not from the source, not pixel-perfect, or nothing changed, stop the previous fix path, rebuild the active scope row, and only then continue implementation.

## Agent Stance

Act like a proof-driven transfer agent.

- trust gates over intuition;
- trust current source artifacts over your memory of the last pass;
- transfer the donor's **system** (fonts, containers, spacing chain), never fit individual pixels;
- repair the failing scope, not the whole page;
- after a complaint, assume the previous "ready" claim is invalid until proven again.

## Recovery Protocol

After complaint-driven feedback:

1. stop the previous repair path;
2. rebuild `scope | source artifact | judged viewport | failing gate | next proof`;
3. restate which gate or viewport actually failed;
4. repair only that scope;
5. rerun the failing gate and the final runner before claiming recovery.

## Non-Negotiable Gates

1. Start with source intake and H2D decode before writing final HTML.
2. Transfer order is fixed: **typography → containers → blocks**. No block markup before the font gate (see Design System First).
3. Do not call the work `ready`, `done`, `completed`, or `pixel-perfect` until:
   - `reports/font_manifest.json.result` is `font-exact` or `font-substituted`
   - `reports/node_validation.json.result == "pass"` (rects **and** text styles)
   - `reports/asset_paint_validation.json.result == "pass"`
   - `reports/asset_provenance.json.result == "pass"`
   - `reports/diff_summary.json.result == "pass"`, or `changed-source` explicitly accepted by the owner (see Drifted Donor)
   - `reports/behavior_validation.json.result == "pass"` for interactive scope
   - `reports/liveness_validation.json.result == "pass"` for dynamic or WebGL/canvas scope
   - `reports/validation_run.json.result == "pass"`
4. Run the final gate after the last HTML/CSS/assets/behavior/runtime change:

```bash
python scripts/run_all_gates.py --output h2d-transfer-output --behavior-required auto --liveness-required auto
```

5. A static screenshot clone is a failure when the original has interaction, animation, canvas, WebGL, video, or scroll-linked motion unless the user explicitly accepts a documented static fallback.

Read `h2d-transfer-mandatory-invocation.md` from the plugin `reference/` folder, or from `.codex/reference/` after mirror sync, when you need the exact hard-gate wording.

## Design System First

The two expensive failure modes are building geometry on the wrong font and fitting boxes with compensations. Both are forbidden by order of work:

1. **Fonts before anything.** From the decode, read `platformFont.postScriptName` on text runs and `styles.fontFamily/fontSize/fontWeight/lineHeight/letterSpacing` on elements. Establish: families and weights in use, whether the donor font covers the candidate's script (e.g. Cyrillic), what fallback the donor itself uses, and licensing (do not package proprietary font files without permission — record evidence in `licensing_notes`). Wire the real webfonts or the documented fallback into the candidate **first**, then write `reports/font_manifest.json` from measured computed styles, not by hand. `font-exact` = same family and weights render; `font-substituted` = documented fallback (e.g. missing script coverage) accepted by the owner.
2. **Containers before blocks.** Extract the per-viewport chain `viewport → page container → section container → content` (widths, gutters, paddings) from the decode and implement it as shared tokens/classes. Block-level rects must inherit from this chain, not carry their own copies of it.
3. Only then transfer blocks/sections.

## No Compensation Rule

Geometry must emerge from the same structural mechanism the donor uses (padding/margin/flex/grid/gap chain). It is a gate failure, not a technique, to force a rect match with:

- spacer elements or reserved `min-height` blocks standing in for absent content;
- fractional nudges: `scale(1.00…)`, sub-pixel `translate`, per-viewport magic offsets;
- `letter-spacing`/`font-size` fitting to make a different font hit the donor's box;
- copy edits made to fit a box (see Content Divergence Protocol).

If a rect only matches *with* a compensation, the structural cause is still wrong — find it. Before the final runner, self-check the candidate diff for compensation patterns (fractional transforms, large fixed `min-height`, unexplained magic numbers); every hit must be either removed or justified in `review.md`.

## Content Divergence Protocol

The donor gives geometry, typography and composition. The candidate keeps **its own meaning**: brand, language, copy, links, titles/meta/aria texts.

When the real copy does not fit the donor geometry (longer language, different brand length):

1. **Stop before implementing.** Do not silently shorten, rewrite or delete the candidate's copy, and do not delete content blocks (leads, CTAs) merely because the donor lacks them.
2. Present the owner 2–3 concrete options: shorten the copy / relax the affected geometry locally / adjust type size for that block.
3. Record the owner's decision in `accepted_deviations` (asset_map or review.md) **before** building the block.

An interactive-looking control that does nothing (e.g. a decorative play button) is a divergence too: either implement the behavior, or record it as an accepted deviation.

## Full-Page Transfer Conveyor

For a whole-page transfer, do not treat the page as one scope:

1. After unpack, enumerate the top-level sections of the donor per viewport from `h2d_tree_index.json` and write the section list into `review.md` as the scope table.
2. Transfer in order: design system (fonts, tokens, containers) → header → sections top-down.
3. Each section gets its own scope row and passes rect + text-style + asset gates for its subtree before the next section starts.
4. `node_validation`, `diff_summary`, behavior and liveness run over the full page after the last section.
5. No section disappears silently: every donor section is either transferred or listed as an owner-approved exclusion.

## Reports Are Generated, Not Written

Every `reports/*.json` must be produced by a bundled script (or a command recorded in `review.md`). Hand-writing or hand-editing a report so a schema or gate passes is itself a failed gate — regenerate the report instead. When a pipeline genuinely cannot run (e.g. the `.h2d` only stores a closed menu state), record the honest `static-scope`/`not-tested` status through the script's own flags and name the limitation in `review.md` — never fabricate a `pass`.

## Scope Lock Before Repair

Before the first implementation pass, and again after a complaint, lock the active scope:

- exact snapshot/source artifact;
- exact viewport branch under judgment;
- exact block/component scope;
- page state of the judged frame (scroll position, opened/closed overlays) — `.h2d` frames may be captured mid-scroll; never mix two states in one comparison;
- whether behavior, liveness, or both are in scope;
- what counts as an allowed deviation, if any.

Keep a tiny working row:

```text
scope | source artifact | judged viewport | failing gate | next proof
```

Do not respond to one failing viewport by globally scaling or shifting unrelated scopes. Repair the active scope and rerun the gates that prove that repair.

## Environment Preflight

Run the bundled preflight before the first real transfer on a new machine or fresh workspace:

```bash
python scripts/preflight_env.py
```

If preflight fails, fix the environment before claiming any gate result:

```bash
python -m pip install -r requirements.txt
npm install
npx playwright install chromium
python scripts/preflight_env.py
```

The preflight checks Python packages, Node packages, and whether Playwright can actually launch Chromium.

Read `h2d-transfer-bootstrap.md` from the plugin `reference/` folder, or from `.codex/reference/` after mirror sync, when the agent is on a new machine or the environment is not trusted yet.

## Quick Workflow

0. Run environment preflight on a new machine or after dependency changes.
1. Intake and unpack the source:

```bash
python scripts/h2d_unpack_source.py input.h2d --out h2d-transfer-output --extract-assets
```

Required source artifacts:

- `reports/source_intake.json`
- `reports/decode_candidates.json`
- `reports/h2d_unpack_report.json`
- `source/h2d_decoded.json`
- `source/h2d_tree_index.json`

2. Design system first: fonts and containers (see Design System First), then `reports/font_manifest.json` from measured styles.
3. Build viewport-scoped rect targets before final layout validation (the tree index rows carry `text_style` where the donor exposes it — targets inherit it):

```bash
python scripts/extract_rect_targets.py \
  --tree-index h2d-transfer-output/source/h2d_tree_index.json \
  --scope hero \
  --root-map '{"390":"0.0.0.2.0","768":"0.0.0.2.0"}' \
  --out h2d-transfer-output/reports/rect_targets.json
```

4. Implement the candidate: `dist/<scope>.html`, an equivalent React/Tailwind component, or **integration mode** — the live project page itself.
5. Validate geometry and text styles on the active viewport branch only. The candidate is either a file or a URL; when the project's markup cannot carry `data-h2d-path` markers, pass a selector map instead:

```bash
node scripts/validate_active_viewport.js \
  --html h2d-transfer-output/dist/hero.html \
  --rect-targets h2d-transfer-output/reports/rect_targets.json \
  --viewports 390,768,1024,1440,1536,1920 \
  --out h2d-transfer-output/reports/node_validation.json
# integration mode:
#   --html http://127.0.0.1:5005/ --selector-map h2d-transfer-output/reports/selector_map.json
# selector map format: {"<data_h2d_path>": "<css selector>"} or {"<viewport>": {"<path>": "<selector>"}}
```

6. Validate asset paint proof:

```bash
node scripts/asset_paint_audit.js \
  --html h2d-transfer-output/dist/hero.html \
  --asset-map h2d-transfer-output/reports/asset_map.json \
  --out-dir h2d-transfer-output
```

7. Record asset provenance. Every asset is matched to the donor inventory by content hash; donor-derived material needs a declared brand status, and third-party brand content or anything over 1 MB needs an owner decision before `pass`:

```bash
python scripts/asset_provenance.py \
  --assets public/hero-orb-1440.png public/hero-showreel.mp4 \
  --raw-asset-inventory h2d-transfer-output/reports/raw_asset_inventory.json \
  --decisions h2d-transfer-output/reports/asset_decisions.json \
  --out h2d-transfer-output/reports/asset_provenance.json
```

An `unknown` origin means the shipped bytes are in neither the donor inventory nor the decisions file — find out what that file really is instead of declaring it by hand. Canvas/WebGL frames re-captured in a later unpack will not hash-match an earlier extraction: capture them once and reuse that file.
8. Capture live comparison and produce a real `pass` or `fail` verdict:

```bash
node scripts/capture_visual_diff.js \
  --original https://original.example \
  --candidate h2d-transfer-output/dist/hero.html \
  --viewports 390,768,1024,1440,1536,1920 \
  --out-dir h2d-transfer-output
```

Дополнительные флаги сравнения:

- `--height-map '{"390":2400,"1440":1800}'` — высота вьюпорта для конкретной ширины, когда рендер зависит от высоты. Разрешённая высота и её источник пишутся в каждую строку отчёта (`viewport_height`, `height_source`), сама карта — в `environment.heightMap`.
- `--hide-original-selector '<css>'` — скрыть элемент только на оригинале перед съёмкой (например, фиксированный оверлей, которого нет в кандидате). Это **изменение эталона**: отчёт помечается `original_normalized`, вердикт вьюпорта становится `pass-with-normalization`, общий `result` понижается до `manual-review`, а в `issues` добавляется требование подтвердить, что скрытый элемент — согласованное отклонение. Строгий гейт `run_all_gates.py` требует `result == "pass"`, поэтому такой прогон не закрывает обязательную живую сверку автоматически.

9. If the scope is interactive, run the behavior pipeline.
10. If the original has runtime surfaces, run the liveness/WebGL pipeline.
11. Run the final runner and only then report final readiness.

After a complaint-driven fix, rerun the failing proof gate and the final runner. Do not say `fixed` from visual intuition alone.

## Drifted Donor

The `.h2d` snapshot is the reference. The live original only corroborates it.

If the live diff fails and investigation proves the production site drifted away from the snapshot (donor redesigned, content rotated):

1. keep the diff evidence and mark `diff_summary.result = "changed-source"`;
2. tell the owner what drifted and ask whether the snapshot stays the reference;
3. only after the owner confirms, rerun the final runner with the acknowledgment flag:

```bash
python scripts/run_all_gates.py --output h2d-transfer-output --accept-changed-source ...
```

Readiness then rests on the node/text-style, asset, provenance, behavior and liveness gates. Without the owner's confirmation the state stays `changed-source` — do not self-accept the drift, and never call a drifted comparison `pass`.

## Pick The Right Reference

- Read `h2d-transfer-contracts.md` from the plugin `reference/` folder, or from `.codex/reference/` after mirror sync, for the canonical output contract and final verdict rules.
- Read `h2d-transfer-bootstrap.md` when setting up a new machine or recovering from missing runtime dependencies.
- Read `h2d-transfer-agent-classes.md` when mapping work to discovery, validation, and output roles.
- Read `h2d-transfer-asset-paint.md` when a canvas, image, fallback asset, or visibility chain looks suspicious.
- Read `h2d-transfer-behavior-pipeline.md` when the scope includes menus, modals, tabs, sliders, forms, or keyboard states.
- Read `h2d-transfer-liveness-motion-webgl.md` when the original contains animation, canvas, WebGL, video, counters, parallax, or runtime libraries such as Three.js, GSAP, Lottie, Rive, Pixi, or Swiper.

## Behavior Pipeline

Run this when the user asks for working behavior or when the original contains meaningful interaction:

```bash
node scripts/behavior_inventory.js --url https://original.example --out h2d-transfer-output/reports/behavior_inventory.json
node scripts/behavior_matrix_generate.js --inventory h2d-transfer-output/reports/behavior_inventory.json --out h2d-transfer-output/reports/interaction_matrix.json
node scripts/behavior_capture_trace.js --url https://original.example --matrix h2d-transfer-output/reports/interaction_matrix.json --side original --out h2d-transfer-output/reports/original_behavior_traces.jsonl
python scripts/behavior_build_state_targets.py --traces h2d-transfer-output/reports/original_behavior_traces.jsonl --out h2d-transfer-output/reports/behavior_state_targets.json
node scripts/behavior_capture_trace.js --url h2d-transfer-output/dist/hero.html --matrix h2d-transfer-output/reports/interaction_matrix.json --side candidate --out h2d-transfer-output/reports/candidate_behavior_traces.jsonl
python scripts/behavior_compare_traces.py --original h2d-transfer-output/reports/original_behavior_traces.jsonl --candidate h2d-transfer-output/reports/candidate_behavior_traces.jsonl --targets h2d-transfer-output/reports/behavior_state_targets.json --out h2d-transfer-output/reports/behavior_validation.json
```

Use `static-scope` only when the scope is genuinely non-interactive and that fact is documented in the output review.

## Liveness And WebGL Pipeline

Run this when the original contains animation, canvas, WebGL, video, parallax, timers, runtime libraries, or any moving surface:

```bash
node scripts/liveness_inventory.js --url https://original.example --out h2d-transfer-output/reports/liveness_inventory.json
node scripts/liveness_capture_trace.js --url https://original.example --inventory h2d-transfer-output/reports/liveness_inventory.json --side original --out h2d-transfer-output/reports/original_animation_trace.jsonl
node scripts/liveness_capture_trace.js --url h2d-transfer-output/dist/hero.html --inventory h2d-transfer-output/reports/liveness_inventory.json --side candidate --out h2d-transfer-output/reports/candidate_animation_trace.jsonl
python scripts/liveness_compare_traces.py --original h2d-transfer-output/reports/original_animation_trace.jsonl --candidate h2d-transfer-output/reports/candidate_animation_trace.jsonl --inventory h2d-transfer-output/reports/liveness_inventory.json --out h2d-transfer-output/reports/liveness_validation.json
```

Treat WebGL or canvas as a runtime surface, not as a decorative static asset.

## Bundled Resources

- `scripts/` contains the runnable validators and capture helpers.
- `schemas/` contains the report schemas used by `scripts/run_all_gates.py`.
- `templates/` contains valid JSON examples for expected artifacts.
- `package.json` documents the Node dependencies for the JS pipeline.
- `requirements.txt` documents the Python dependencies for schema and image checks.
- `scripts/preflight_env.py` checks whether the local machine can actually run the bundled gates before transfer work begins.

## Honest Final States

Use these rules in the final answer:

- `pass` only when the runner passes.
- `needs-fix` when one or more proof gates failed and you know what to repair.
- `changed-source` when live original diverged from the H2D snapshot and the owner has not yet accepted the snapshot as the reference.
- `manual-review` when evidence is incomplete or ambiguous.
- `blocked` when a required live input or runtime dependency is unavailable.

Do not collapse those states into a fake `pass`.
