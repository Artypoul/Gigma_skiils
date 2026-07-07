#!/usr/bin/env python3
"""Preflight check for the H2D transfer skill runtime."""
from __future__ import annotations

import importlib
import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(cmd: list[str]) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            cmd,
            cwd=ROOT,
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
        ok, message = run(cmd)
        checks.append(
            {
                "name": label,
                "result": "pass" if ok else "fail",
                "message": message,
            }
        )

    for package_name in ("playwright", "pngjs"):
        ok, message = run(["node", "-e", f"console.log(require.resolve('{package_name}'))"])
        checks.append(
            {
                "name": f"node-package:{package_name}",
                "result": "pass" if ok else "fail",
                "message": message,
            }
        )

    launch_script = (
        "const { chromium } = require('playwright');"
        "(async()=>{const browser=await chromium.launch({headless:true});"
        "await browser.close(); console.log('playwright chromium launch ok');})()"
        ".catch(err=>{console.error(err && err.message ? err.message : String(err)); process.exit(1);});"
    )
    ok, message = run(["node", "-e", launch_script])
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
        "checks": checks,
        "next_steps": [] if not failed else [
            "python -m pip install -r requirements.txt",
            "npm install",
            "npx playwright install chromium",
            "python scripts/preflight_env.py",
        ],
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failed else 2


if __name__ == "__main__":
    raise SystemExit(main())
