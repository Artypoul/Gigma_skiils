---
name: h2d-pixel-perfect-transfer
description: "Transfer pages or components from .h2d snapshots into clean frontend code with a source-derived design system, complete layout/container chain, reusable components, and hard validation gates for typography, responsive geometry, tokens, assets, provenance, live comparison, behavior, and liveness/WebGL motion. Use for H2D or html.to.design reconstruction, pixel-perfect frontend recreation, full-page transfer, or any clone that must prove structural and runtime fidelity instead of fitting a screenshot."
---

# H2D Pixel-Perfect Transfer

Use this skill for `.h2d` to code work where "looks close enough" is not acceptable.

Resolve bundled paths relative to this `SKILL.md`.

Read `../../reference/layout-container-contract.md` before implementation. Its complete ancestor chain, design-system inventory, responsive ownership map, independent-reference and no-compensation rules are mandatory for every scope.

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
2. Transfer order is fixed: **typography → design-system inventory → complete container chain → reusable components → blocks**. No production block layout before the source-derived maps exist (see Design System First).
3. Do not call the work `ready`, `done`, `completed`, or `pixel-perfect` until:
   - `reports/font_manifest.json.result` is `font-exact` or `font-substituted`
   - `reports/design_system.json.result == "pass"`, `reports/component_reuse.json.result` is `pass` or `no-repeated-patterns`, and `reports/token_reuse.json.result` is `pass` or `no-donor-palette`
   - `reports/node_validation.json.result == "pass"` (rects **and** text styles)
   - `reports/asset_paint_validation.json.result == "pass"`
   - `reports/asset_provenance.json.result == "pass"`
   - `reports/diff_summary.json.result == "pass"`, or `changed-source` explicitly accepted by the owner (see Drifted Donor)
   - `reports/behavior_validation.json.result == "pass"` for interactive scope
   - `reports/liveness_validation.json.result == "pass"` for dynamic or WebGL/canvas scope
   - `reports/current_evidence.json.result == "pass"` and its matrix equals every contract viewport/profile pair
   - `reports/validation_run.json.result == "pass"`
4. Run the final gate after the last HTML/CSS/assets/behavior/runtime change:

```bash
python scripts/run_current_gates.py \
  --contract h2d-transfer-output/contract/transfer_contract.json \
  --output h2d-transfer-output
```

`run_all_gates.py --output ...` is no longer a regeneration path. It verifies mandatory current-evidence provenance and therefore fails on an old/manual report set or after any included candidate file changes. `--check-package` remains its package self-check mode.

5. A static screenshot clone is a failure when the original has interaction, animation, canvas, WebGL, video, or scroll-linked motion unless the user explicitly accepts a documented static fallback.

Read `h2d-transfer-mandatory-invocation.md` from the bundled `reference/` folder (`../../reference/` relative to this SKILL.md), when you need the exact hard-gate wording.

## Immutable Current-Evidence Contract

Before implementation, freeze the runnable donor and finalize one contract. Do not type viewport lists from the filename or memory.

1. `freeze_reference_bundle.py` accepts a pinned local runnable donor, hashes the transitive local resource closure, captures every explicit viewport/profile under a deny-by-default network sandbox, and runs the bundled reachable-state classifier. The closure includes resources loaded only after interactions. Visual, classification and dynamic evidence must share that exact donor identity. A live URL is not a frozen reference.
2. Breakpoints come only from the bundled generated classification (CSS/media queries plus runtime `matchMedia`), never from the filename, memory or a handwritten CLI list. Use `derive_reference_matrix.py` for a decoded-width seed matrix, run `freeze_reference_bundle.py --prepare-only`, then derive the final breakpoint/interval matrix from `reference_classification.json` and recapture the final reference. `create_transfer_contract.py` accepts only that pinned matrix/provenance pair. Include `reports/design_system.json`, `reports/component_reuse.json` and `reports/token_reuse.json` in the contract's `expected_reports` and regenerate all three inside `current_commands` — a design-system report left over from an earlier donor must be quarantined and rebuilt like every other current report, not accepted because it still says `pass`. Pin `contract/component_map.json` and `contract/token_map.json` as mandatory hashed sidecars: `create_transfer_contract.py --sidecar component_map=h2d-transfer-output/contract/component_map.json --sidecar token_map=h2d-transfer-output/contract/token_map.json …`. The current runner requires both validators to read those exact files.
3. Every approved deviation/fallback/substitution needs a verified owner-signed or trusted owner-event receipt. A locally authored `approved: true` is invalid.
4. `run_current_gates.py` pins executable binaries and file inputs against the exact cwd used by each current/build/start/teardown command, quarantines earlier reports, runs the commands, binds the final `source/` copies to the immutable `.h2d`/decode artifacts, and derives matrix completion only from per-row passing visual/geometry/typography/behavior/liveness artifacts produced by direct bundled specialist-script invocations. A copied template or wrapper-authored matrix row has no specialist provenance and is non-final. Managed URL mode requires an unused loopback origin, a live child process and JSON build identity bound to the current candidate/source closure. The candidate closure is re-hashed after generation; the evidence directory is the only allowed self-exclusion.
5. Missing behavior/liveness classification, truncated discovery, delegated document/window listeners, unsupported interactive boundaries, reference action/runtime errors, stale artifacts or incomplete matrix are non-pass. Structural ARIA roles alone are not behavior; actionable roles/listeners are. Timers and media playback are liveness. Never infer static scope from a missing report.
6. When behavior or liveness is required, every discovery/inventory/mapping artifact must be a complete `pass`. `partial`, `manual-review`, `not-tested` and `static-scope` do not count as completed required matrix rows. A dynamic bundle is final only when `finalize_dynamic_reference.py` generates a non-empty, complete role×matrix manifest bound to the exact classification; a handwritten/empty manifest is invalid.

The same matrix is mandatory after feedback. A generic Playwright screenshot, one desktop width, one mobile width, or "viewport plus neighbor" is diagnostic only.

The reference preparation sequence is deterministic:

```bash
python scripts/derive_reference_matrix.py --h2d input.h2d --height-map heights.json --out seed-matrix.json
python scripts/freeze_reference_bundle.py --h2d input.h2d --donor donor.html --donor-root donor-root --matrix seed-matrix.json --profiles profiles.json --out h2d-transfer-output/contract/reference --prepare-only
python scripts/derive_reference_matrix.py --h2d input.h2d --height-map heights.json --classification h2d-transfer-output/contract/reference/reference_classification.json --out final-matrix.json
# Recapture/finalize dynamic artifacts against final-matrix.json when classification requires them.
python scripts/finalize_dynamic_reference.py --classification h2d-transfer-output/contract/reference/reference_classification.json --artifact kind@matrix-key=path --out dynamic/dynamic_reference_manifest.json
python scripts/freeze_reference_bundle.py --h2d input.h2d --donor donor.html --donor-root donor-root --matrix final-matrix.json --profiles profiles.json --dynamic-manifest dynamic/dynamic_reference_manifest.json --out h2d-transfer-output/contract/reference
```

For a genuinely static classification, omit the dynamic-finalizer command and the final `--dynamic-manifest` argument. If the final matrix differs from the seed and behavior/liveness is required, run `--prepare-only` once more on the final matrix before capturing/finalizing dynamic artifacts.

## Design System First

The donor was built from a system — a palette, a type scale, a spacing scale, shared containers and repeated components. A transfer that copies boxes one by one produces a page of hand-fitted blocks that measures right and maintains wrong. The order of work is fixed:

1. **Fonts before anything.** From the decode, read `platformFont.postScriptName` on text runs and `styles.fontFamily/fontSize/fontWeight/lineHeight/letterSpacing` on elements. Establish: families and weights in use, whether the donor font covers the candidate's script (e.g. Cyrillic), what fallback the donor itself uses, and licensing (do not package proprietary font files without permission — record evidence in `licensing_notes`). Wire the real webfonts or the documented fallback into the candidate **first**, then write `reports/font_manifest.json` from measured computed styles, not by hand. `font-exact` = same family and weights render; `font-substituted` = documented fallback (e.g. missing script coverage) accepted by the owner.
2. **Extract the system, not just values.** Run the extractor and read its report before writing any candidate CSS:

```bash
python scripts/extract_design_system.py \
  --decoded h2d-transfer-output/source/h2d_decoded.json \
  --out h2d-transfer-output/reports/design_system.json
```

   It returns the donor's recurring colors, type scale, spacing scale, radii and shadows (`tokens`), the shared per-viewport container widths (`containers`), the recurring flex/grid mechanisms (`layouts`) and the repeated subtrees (`components`). Implement the tokens as **one shared layer** — CSS custom properties, a Tailwind theme, or the project's token file — and take block values from that layer. Scattering the same literal per block is the token-level equivalent of a compensation, and it is gated on the candidate's sources:

```bash
python scripts/validate_token_reuse.py \
  --design-system h2d-transfer-output/reports/design_system.json \
  --candidate-root . \
  --token-map h2d-transfer-output/contract/token_map.json \
  --out h2d-transfer-output/reports/token_reuse.json
```

   Before freezing the contract, map every significant donor color in `contract/token_map.json` to one candidate `definition`, token name, and usage spelling (for example `--color-ink` plus `var(--color-ink)`), then pin that file with `--sidecar token_map=…`. The gate proves that the definition contains the donor literal and token, the usage occurs outside the definition, and repeated raw literals do not. The repeat floor and scatter allowance are bundled invariants, not adjustable CLI flags. `token_reuse.json` is required; `no-donor-palette` is honest only when the donor has no repeated colors. A snapshot can carry capture artifacts (translation spans like `ya-tr-span`, `YS Text` overlays, builder debris) — exclude them from the token and component maps instead of transferring them; only known injector tags (Yandex/Google translate, Grammarly, DeepL) are self-serve exclusions, a donor-authored pattern needs an owner approval.
3. **Containers and layout mechanisms before blocks.** Implement the container chain `viewport → page container → section container → content` from `design_system.json` as shared classes/tokens; block-level rects must inherit from this chain, not carry their own copies of it. Reproduce each block's layout with the donor's mechanism — the same `display`, flex direction/alignment, grid track count — because these fields are gated: identical rects laid out by absolute offsets instead of the donor's flex/grid chain fail `node_validation`.
4. **Components, not copies.** Every entry in `design_system.json.components` (a card, a menu item, a tag, a gallery cell repeated N times) becomes **one** component in the candidate — a Svelte/React component, a template partial, or a single class — instantiated N times with different content. Write the pattern → selector mapping into `contract/component_map.json` (capture artifacts go under `excluded` with a reason) and prove reuse on the rendered candidate:

```bash
node scripts/validate_component_reuse.js \
  --candidate http://127.0.0.1:5005/ \
  --candidate-root . \
  --design-system h2d-transfer-output/reports/design_system.json \
  --component-map h2d-transfer-output/contract/component_map.json \
  --out h2d-transfer-output/reports/component_reuse.json
```

The gate looks at the candidate, not the donor, and proves reuse on three layers: **source** — each mapped entry names its single `definition` file (the component/partial/class that defines the pattern; N pasted copies have none to name); **count** — the expected instance count comes from the donor's design-system report, and a different count is legitimate only as a recorded owner decision (`instances_expected` + `instances_reason`); **render** — at the component's own donor viewport, every instance the selector finds must share one subtree shape and one set of computed tokens, so an edited pasted copy fails the moment it drifts. `component_reuse.json` is a required report (`no-repeated-patterns` is the honest value for a scope with nothing repeated).

Only then transfer blocks/sections.

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
2. Build the component map before any section: match `design_system.json.components` against the section list, name each component (`work-tag`, `gallery-cell`, `nav-link`), and record which sections instantiate it. Components shared by several sections are built once, before the first section that uses them.
3. Transfer in order: design system (fonts, tokens, containers, shared components) → header → sections top-down.
4. Each section gets its own scope row and passes rect + text-style + asset gates for its subtree before the next section starts. A section that re-implements an already-built component instead of instantiating it is a defect, not a style choice.
5. `node_validation`, `diff_summary`, behavior and liveness run over the full page after the last section.
6. No section disappears silently: every donor section is either transferred or listed as an owner-approved exclusion.

## Reports Are Generated, Not Written

Every `reports/*.json` must be produced by a bundled script (or a command recorded in `review.md`). Hand-writing or hand-editing a report so a schema or gate passes is itself a failed gate — regenerate the report instead; `design_system.json`, `component_reuse.json` and `token_reuse.json` additionally carry a `generator_sha256` that the final runner verifies against the bundled script. When a pipeline genuinely cannot run (e.g. the `.h2d` only stores a closed menu state), record the honest `static-scope`/`not-tested` status through the script's own flags and name the limitation in `review.md` — never fabricate a `pass`.

Declarative **inputs** are a different thing from reports and live under `contract/`, not `reports/`: `contract/component_map.json` (pattern → selector/definition), `contract/token_map.json` (donor token → candidate definition/usage), `contract/selector_map.json` (donor path → project selector), `contract/asset_decisions.json` (owner decisions on assets). The agent writes these by hand — they are declarations to be verified, must be pinned as hashed sidecars before the contract is finalized, and the gates judge the candidate against them.

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

**Run every browser gate from the candidate project root, not from the skill folder.** The bundled JS gates resolve their driver from the working directory: `playwright`, else `playwright-core` plus an installed Chrome/Edge (override with `--browser-executable` or `CHROME_PATH`). A skill folder installed on its own — a personal `skills/` directory, a plugin cache — carries no `node_modules`, so preflight and every browser gate fail there while the same commands pass from a project that has the driver. That is the intended shape: the gates measure a candidate, and the candidate is where its dependencies live. If the project has neither package, install one there before claiming any gate result.

Read `h2d-transfer-bootstrap.md` from the bundled `reference/` folder (`../../reference/` relative to this SKILL.md), when the agent is on a new machine or the environment is not trusted yet.

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

2. Build viewport-scoped rect targets — every later gate reads them, so they come first (the tree index rows carry `text_style`, `rendered_font` and `box_style` where the donor exposes them; targets inherit all three):

```bash
python scripts/extract_rect_targets.py \
  --tree-index h2d-transfer-output/source/h2d_tree_index.json \
  --scope hero \
  --root-map '{"390":"0.0.0.2.0","768":"0.0.0.2.0"}' \
  --out h2d-transfer-output/reports/rect_targets.json
```

The extractor includes the complete ancestor chain by default and binds the report to the current tree and bundled generator hashes. `--without-ancestors` is diagnostic only and the final runner rejects it.

3. Design system first: extract the donor's system (`extract_design_system.py` → required report `reports/design_system.json`), wire the fonts, the token layer, the container chain and the shared components into the candidate (see Design System First), then prove the typography on the rendered page **before** building blocks:

```bash
node scripts/font_manifest.js \
  --candidate h2d-transfer-output/dist/hero.html \
  --rect-targets h2d-transfer-output/reports/rect_targets.json \
  --out h2d-transfer-output/reports/font_manifest.json
```

Every recorded viewport is measured by default, because typography is responsive; narrow the run only with `--allow-partial-viewports`. `font-exact` requires both that the primary families match the donor's and that each one can actually paint its text — a declared brand face the browser silently replaces reports `font-mismatch-risk`. A deliberate replacement needs both a recorded `--substitutions` entry and an externally verified transfer-contract approval scoped to `font.substitutions`; without both, final validation fails, so an agent-authored fallback can never pass as the owner's decision.

4. Implement the candidate blocks: `dist/<scope>.html`, an equivalent React/Tailwind component, or **integration mode** — the live project page itself.
5. Validate geometry and text styles on the active viewport branch only. The candidate is either a file or a URL; when the project's markup cannot carry `data-h2d-path` markers, pass a selector map instead:

```bash
node scripts/validate_active_viewport.js \
  --html h2d-transfer-output/dist/hero.html \
  --rect-targets h2d-transfer-output/reports/rect_targets.json \
  --viewports 390,768,1024,1440,1536,1920 \
  --out h2d-transfer-output/reports/node_validation.json
# integration mode (a live project page):
#   --candidate http://127.0.0.1:5005/ --selector-map h2d-transfer-output/contract/selector_map.json
#   optional readiness: --ready-selector '.hero__media' --ready-timeout-ms 10000 --wait-ms 300
# selector map format: {"<data_h2d_path>": "<css selector>"} or {"<viewport>": {"<path>": "<selector>"}}
```

In integration mode the validator waits for every mapped selector and for the layout to stop changing before measuring, so a hydrating page is not judged mid-flight. Add `--ready-selector` when the meaningful content arrives after an initial request. The selector map must be injective for source layout nodes: one candidate element cannot stand in for several containers.

Container mismatches (`maxWidth`, `padding`, `gap`, `margin`, flex/grid mechanism) **fail** — that is what gives the no-compensation rule teeth, since a constraint replaced by a parent offset reaches the same rect. Resolve them structurally, or record an owner-approved deviation; `--lenient-box-style` downgrades them to warnings for diagnosis, but the final runner rejects lenient evidence, a non-injective map, stale targets, missing ancestors and incomplete target counts.

`--accepted-deviations` entries must each name the exact node, viewport, field list and a real reason — a blanket approval is rejected, because an approval that covers everything records nothing.

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
  --assets public \
  --scan-root public \
  --raw-asset-inventory h2d-transfer-output/reports/raw_asset_inventory.json \
  --decisions h2d-transfer-output/contract/asset_decisions.json \
  --out h2d-transfer-output/reports/asset_provenance.json
```

Pass `--scan-root` with the directory the candidate actually ships: anything found under it that is missing from the report is an issue, so a partial `--assets` list cannot quietly leave a donor logo or a heavy video unreviewed.

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

1. re-capture with the drift reason so the verdict carries its evidence — the report is still generated, never hand-edited:

```bash
node scripts/capture_visual_diff.js --original https://original.example --candidate ... \
  --changed-source 'donor redesigned the hero after the snapshot: new headline and no orb'
```

2. tell the owner what drifted and ask whether the snapshot stays the reference;
3. only after the owner confirms, rerun the final runner with the acknowledgment flag:

```bash
python scripts/run_all_gates.py --output h2d-transfer-output --accept-changed-source ...
```

Readiness then rests on the node/text-style, asset, provenance, behavior and liveness gates. Without the owner's confirmation the state stays `changed-source` — do not self-accept the drift, and never call a drifted comparison `pass`.

## Pick The Right Reference

- Read `h2d-transfer-contracts.md` from the bundled `reference/` folder (`../../reference/` relative to this SKILL.md), for the canonical output contract and final verdict rules.
- Read `h2d-transfer-bootstrap.md` when setting up a new machine or recovering from missing runtime dependencies.
- Read `h2d-transfer-agent-classes.md` when mapping work to discovery, validation, and output roles.
- Read `h2d-transfer-asset-paint.md` when a canvas, image, fallback asset, or visibility chain looks suspicious.
- Read `h2d-transfer-behavior-pipeline.md` when the scope includes menus, modals, tabs, sliders, forms, or keyboard states.
- Read `h2d-transfer-liveness-motion-webgl.md` when the original contains animation, canvas, WebGL, video, counters, parallax, or runtime libraries such as Three.js, GSAP, Lottie, Rive, Pixi, or Swiper.

## Behavior Pipeline

Run this when the user asks for working behavior or when classification finds semantic, listener-backed, form, keyboard, pointer, shadow/frame, or navigation/download behavior. Use the pinned offline runnable donor; the sandbox applies to offline files too. Live traversal needs exact request/action allowlists and is not the default.

```bash
node scripts/behavior_inventory.js --url h2d-transfer-output/reference/donor.html --classification h2d-transfer-output/contract/reference/reference_classification.json --profile h2d-transfer-output/contract/profile.json --out h2d-transfer-output/reports/behavior_inventory.json
node scripts/behavior_matrix_generate.js --inventory h2d-transfer-output/reports/behavior_inventory.json --out h2d-transfer-output/reports/interaction_matrix.json
node scripts/behavior_capture_trace.js --url h2d-transfer-output/reference/donor.html --matrix h2d-transfer-output/reports/interaction_matrix.json --profile h2d-transfer-output/contract/profile.json --side original --out h2d-transfer-output/reference/reports/original_behavior_traces.jsonl
python scripts/behavior_build_state_targets.py --traces h2d-transfer-output/reference/reports/original_behavior_traces.jsonl --out h2d-transfer-output/reports/behavior_state_targets.json
node scripts/behavior_capture_trace.js --url h2d-transfer-output/dist/hero.html --matrix h2d-transfer-output/reports/interaction_matrix.json --implementation-map h2d-transfer-output/reports/behavior_implementation_map.json --side candidate --out h2d-transfer-output/reports/candidate_behavior_traces.jsonl
python scripts/behavior_compare_traces.py --original h2d-transfer-output/reference/reports/original_behavior_traces.jsonl --candidate h2d-transfer-output/reports/candidate_behavior_traces.jsonl --original-root h2d-transfer-output/reference --candidate-root h2d-transfer-output --out h2d-transfer-output/reports/behavior_validation.json
```

Use `static-scope` only when the scope is genuinely non-interactive and that fact is documented in the output review.

## Liveness And WebGL Pipeline

Run this when the original contains animation, canvas, WebGL, video, parallax, timers, runtime libraries, or any moving surface:

```bash
node scripts/liveness_inventory.js --url h2d-transfer-output/reference/donor.html --out h2d-transfer-output/reports/liveness_inventory.json
node scripts/webgl_capture.js --url h2d-transfer-output/dist/hero.html --inventory h2d-transfer-output/reports/liveness_inventory.json --out h2d-transfer-output/reports/webgl_capture_report.json
node scripts/liveness_capture_trace.js --url h2d-transfer-output/reference/donor.html --inventory h2d-transfer-output/reports/liveness_inventory.json --side original --out h2d-transfer-output/reference/reports/original_animation_trace.jsonl
node scripts/liveness_capture_trace.js --url h2d-transfer-output/dist/hero.html --inventory h2d-transfer-output/reports/liveness_inventory.json --side candidate --out h2d-transfer-output/reports/candidate_animation_trace.jsonl
python scripts/liveness_compare_traces.py --original h2d-transfer-output/reference/reports/original_animation_trace.jsonl --candidate h2d-transfer-output/reports/candidate_animation_trace.jsonl --inventory h2d-transfer-output/reports/liveness_inventory.json --original-root h2d-transfer-output/reference --candidate-root h2d-transfer-output --out h2d-transfer-output/reports/liveness_validation.json
```

Every trace needs at least three strictly increasing samples starting at 0; comparison includes per-sample position/size, styles, pixels, canvas and media time. Required playback that cannot start/advance is non-pass. Treat WebGL or canvas as a runtime surface, not as a decorative static asset: `not-present` or a nominal `pass` without three hashed frames and non-blank samples for every inventoried WebGL canvas fails.

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

In the user-facing final response, map a complete artifact `pass` to project status `ready`; map `needs-fix`/`manual-review` to `partial`, and keep `blocked` or `unknown` exact.
