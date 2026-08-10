#!/usr/bin/env python3
"""Preflight check for the H2D transfer skill runtime.

Node packages resolve from the working directory, and an installed skill
directory carries no `node_modules`. So the probes must run where the driver
actually lives — the candidate project:

  python <skill>/scripts/preflight_env.py --candidate-root .

Without `--candidate-root` the probes run inside the skill, which is only
correct when the skill checkout itself has the dependencies installed.
"""
from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        executable = shutil.which(cmd[0]) or cmd[0]
        completed = subprocess.run(
            [executable, *cmd[1:]],
            cwd=cwd,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError as exc:
        return False, str(exc)
    except subprocess.CalledProcessError as exc:
        output = (exc.stdout or "") + ("\n" if exc.stdout and exc.stderr else "") + (exc.stderr or "")
        return False, output.strip() or str(exc)
    output = (completed.stdout or "") + ("\n" if completed.stdout and completed.stderr else "") + (completed.stderr or "")
    return True, output.strip()


def check_import(module_name: str, install_name: str) -> tuple[bool, str]:
    try:
        importlib.import_module(module_name)
        return True, f"{install_name} available"
    except Exception as exc:  # pragma: no cover - message is the point
        return False, f"{install_name} missing: {exc}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--candidate-root",
        type=Path,
        default=None,
        help="Project the gates will measure; Node probes run here because that is where node_modules lives.",
    )
    args = ap.parse_args()
    probe_root = (args.candidate_root or ROOT).resolve()
    if not probe_root.is_dir():
        raise SystemExit(f"--candidate-root is not a directory: {probe_root}")

    checks: list[dict[str, str]] = []

    for module_name, install_name in (("PIL", "Pillow"), ("jsonschema", "jsonschema")):
        ok, message = check_import(module_name, install_name)
        checks.append(
            {
                "name": f"python:{install_name}",
                "result": "pass" if ok else "fail",
                "message": message,
            }
        )

    for cmd, label in ((["node", "--version"], "node"), (["npm", "--version"], "npm"), (["npx", "--version"], "npx")):
        ok, message = run(cmd, probe_root)
        checks.append(
            {
                "name": label,
                "result": "pass" if ok else "fail",
                "message": message,
            }
        )

    # Either driver is fine: the gates run through scripts/browser.js, which
    # falls back to playwright-core plus an installed Chrome/Edge.
    driver_probe = (
        "const names=['playwright','playwright-core'];"
        "const found=names.filter(n=>{try{require.resolve(n);return true}catch{return false}});"
        "if(!found.length){console.error('neither playwright nor playwright-core resolves');process.exit(1)}"
        "console.log(found.join(', '));"
    )
    ok, message = run(["node", "-e", driver_probe], probe_root)
    checks.append({"name": "node-package:playwright", "result": "pass" if ok else "fail", "message": message})

    # Probe pngjs exactly as asset_paint_audit.js loads it: through the shared
    # requireDep helper, so a passing probe cannot mean a failing gate.
    browser_js = str(ROOT / "scripts" / "browser.js").replace(chr(92), "/")
    pngjs_probe = (
        f"const {{ requireDep }} = require({browser_js!r});"
        "requireDep('pngjs');console.log('pngjs resolvable');"
    )
    ok, message = run(["node", "-e", pngjs_probe], probe_root)
    checks.append({"name": "node-package:pngjs", "result": "pass" if ok else "fail", "message": message})

    launch_script = (
        f"const {{ launchChromium }} = require({str(ROOT / 'scripts' / 'browser.js').replace(chr(92), '/')!r});"
        "(async()=>{const browser=await launchChromium();"
        "await browser.close(); console.log('chromium launch ok');})()"
        ".catch(err=>{console.error(err && err.message ? err.message : String(err)); process.exit(1);});"
    )
    ok, message = run(["node", "-e", launch_script], probe_root)
    checks.append(
        {
            "name": "playwright:chromium-launch",
            "result": "pass" if ok else "fail",
            "message": message,
        }
    )

    failed = [check for check in checks if check["result"] != "pass"]
    result = {
        "result": "pass" if not failed else "fail",
        "skill_root": str(ROOT),
        "probe_root": str(probe_root),
        "checks": checks,
        # Node dependencies belong to the project being measured, so the fixes
        # are run there — not inside the installed skill.
        "next_steps": [] if not failed else [
            f'python -m pip install -r "{ROOT / "requirements.txt"}"',
            f"cd {probe_root} && npm install",
            f"cd {probe_root} && npx playwright install chromium",
            f"python {ROOT / 'scripts' / 'preflight_env.py'} --candidate-root {probe_root}",
        ],
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
