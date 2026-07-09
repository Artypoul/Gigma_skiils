---
name: h2d-pixel-perfect-transfer
description: "Transfer pages or components from .h2d snapshots into Tailwind HTML/React with hard validation gates for source intake, geometry, asset paint, live comparison, behavior replay, and liveness/WebGL motion. Use when the user asks for H2D transfer, html.to.design reconstruction, pixel-perfect frontend recreation, or a live clone that must prove runtime fidelity instead of shipping a static screenshot."
---

# H2D Pixel-Perfect Transfer

Use this skill for `.h2d` to code work where "looks close enough" is not acceptable.

Resolve bundled paths relative to this `SKILL.md`.

If the user says the result is wrong, not from the source, not pixel-perfect, or nothing changed, stop the previous fix path, rebuild the active scope row, and only then continue implementation.

## Agent Stance

Act like a proof-driven transfer agent.

- trust gates over intuition;
- trust current source artifacts over your memory of the last pass;
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
2. Do not call the work `ready`, `done`, `completed`, or `pixel-perfect` until:
   - `reports/node_validation.json.result == "pass"`
   - `reports/asset_paint_validation.json.result == "pass"`
   - `reports/diff_summary.json.result == "pass"`
   - `reports/behavior_validation.json.result == "pass"` for interactive scope
   - `reports/liveness_validation.json.result == "pass"` for dynamic or WebGL/canvas scope
   - `reports/validation_run.json.result == "pass"`
3. Run the final gate after the last HTML/CSS/assets/behavior/runtime change:

```bash
python scripts/run_all_gates.py --output h2d-transfer-output --behavior-required auto --liveness-required auto
```

4. If live original is unavailable or changed, return an honest non-final status such as `changed-source`, `needs-fix`, `manual-review`, or `blocked`.
5. A static screenshot clone is a failure when the original has interaction, animation, canvas, WebGL, video, or scroll-linked motion unless the user explicitly accepts a documented static fallback.

Read `h2d-transfer-mandatory-invocation.md` from the plugin `reference/` folder, or from `.codex/reference/` after mirror sync, when you need the exact hard-gate wording.

## Scope Lock Before Repair

Before the first implementation pass, and again after a complaint, lock the active scope:

- exact snapshot/source artifact;
- exact viewport branch under judgment;
- exact block/component scope;
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

2. Build viewport-scoped rect targets before final layout validation:

```bash
python scripts/extract_rect_targets.py \
  --tree-index h2d-transfer-output/source/h2d_tree_index.json \
  --scope hero \
  --root-map '{"390":"0.0.0.2.0","768":"0.0.0.2.0"}' \
  --out h2d-transfer-output/reports/rect_targets.json
```

3. Implement the candidate under `dist/<scope>.html` or the equivalent React/Tailwind component output.
4. Validate geometry on the active viewport branch only:

```bash
node scripts/validate_active_viewport.js \
  --html h2d-transfer-output/dist/hero.html \
  --rect-targets h2d-transfer-output/reports/rect_targets.json \
  --viewports 390,768,1024,1440,1536,1920 \
  --out h2d-transfer-output/reports/node_validation.json
```

5. Validate asset paint proof:

```bash
node scripts/asset_paint_audit.js \
  --html h2d-transfer-output/dist/hero.html \
  --asset-map h2d-transfer-output/reports/asset_map.json \
  --out-dir h2d-transfer-output
```

6. Capture live comparison and produce a real `pass` or `fail` verdict:

```bash
node scripts/capture_visual_diff.js \
  --original https://original.example \
  --candidate h2d-transfer-output/dist/hero.html \
  --viewports 390,768,1024,1440,1536,1920 \
  --out-dir h2d-transfer-output
```

7. If the scope is interactive, run the behavior pipeline.
8. If the original has runtime surfaces, run the liveness/WebGL pipeline.
9. Run the final runner and only then report final readiness.

If live diff fails and investigation shows the production site drifted away from the H2D snapshot, keep the evidence but report `changed-source` or `manual-review` honestly instead of calling the transfer ready.

After a complaint-driven fix, rerun the failing proof gate and the final runner. Do not say `fixed` from visual intuition alone.

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
- `changed-source` when live original diverged from the H2D snapshot.
- `manual-review` when evidence is incomplete or ambiguous.
- `blocked` when a required live input or runtime dependency is unavailable.

Do not collapse those states into a fake `pass`.
