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
4. Implement candidate HTML/React
5. `node scripts/validate_active_viewport.js ...`
6. `node scripts/asset_paint_audit.js ...`
7. `node scripts/capture_visual_diff.js ...`
8. behavior pipeline when interactive
9. liveness pipeline when dynamic
10. `python scripts/run_all_gates.py --output h2d-transfer-output --behavior-required auto --liveness-required auto`

## 6. Honest failure modes

If bootstrap fails:

- report `blocked` for missing runtime dependencies;
- do not claim any gate result;
- do not say `ready`, `done`, or `pixel-perfect`.
