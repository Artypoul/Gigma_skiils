# H2D transfer bootstrap

Use this checklist on a new machine before the first real `.h2d` transfer.

## 1. Check base tools

You need:

- Python 3.10+ with `python` on `PATH`
- Node.js 20+ with `node`, `npm`, and `npx` on `PATH`

Quick check:

```bash
python --version
node --version
npm --version
npx --version
```

If `npm` or `npx` is missing, reinstall Node.js from the official installer and reopen the terminal.

## 2. Install Python dependencies

Run from the skill folder:

```bash
python -m pip install -r requirements.txt
```

This installs:

- `Pillow` for image diff and bitmap checks
- `jsonschema` for template/report validation

## 3. Install Node dependencies

Run from the skill folder:

```bash
npm install
npx playwright install chromium
```

This installs:

- `playwright`
- `pngjs`
- the Playwright Chromium browser used by the capture and validation scripts

Inside an existing project, `playwright-core` plus an installed Chrome or Edge is enough: the gates launch through `scripts/browser.js`. Point it at a browser with `CHROME_PATH` or `--browser-executable <path>` when it lives in a non-standard location.

## 4. Run preflight

```bash
python scripts/preflight_env.py
```

Expected result:

```json
{ "result": "pass" }
```

Do not start a real transfer until preflight passes.

## 5. First transfer order

After bootstrap passes, use this order:

1. `python scripts/preflight_env.py`
2. `python scripts/h2d_unpack_source.py ...`
3. `python scripts/extract_rect_targets.py ...`
4. Wire fonts and the container chain, then implement the candidate HTML/React
5. `node scripts/font_manifest.js ...` — typography is proved before the blocks
6. `node scripts/validate_active_viewport.js ...`
7. `node scripts/asset_paint_audit.js ...`
8. `python scripts/asset_provenance.py ...`
9. `node scripts/capture_visual_diff.js ...`
10. behavior pipeline when interactive
11. liveness pipeline when dynamic
12. `python scripts/run_all_gates.py --output h2d-transfer-output --behavior-required auto --liveness-required auto`

Steps 5 and 8 are mandatory reports: the final runner requires `font_manifest.json` and `asset_provenance.json`, and every report must come from a script rather than by hand.

## 6. Honest failure modes

If bootstrap fails:

- report `blocked` for missing runtime dependencies;
- do not claim any gate result;
- do not say `ready`, `done`, or `pixel-perfect`.
