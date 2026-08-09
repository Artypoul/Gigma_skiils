#!/usr/bin/env python3
"""Regenerate H2D reports and bind them to the current candidate and immutable contract."""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
from urllib.parse import urlparse
from datetime import datetime, timezone
from pathlib import Path

from evidence_integrity import EvidenceError, matrix_keys, resolve_inside, sha256_bytes, sha256_file, verify_contract


SCRIPT = Path(__file__).resolve()
SPECIALIST_SCRIPTS = {
    "visual": "compare_frozen_visual.js",
    "geometry": "validate_active_viewport.js",
    "typography": "font_manifest.js",
    "behavior": "behavior_compare_traces.py",
    "liveness": "liveness_compare_traces.py",
}


def bounded_cwd(root: Path, value: str | None) -> Path:
    candidate = (root / (value or ".")).resolve()
    candidate.relative_to(root.resolve())
    if not candidate.is_dir():
        raise EvidenceError(f"command cwd is missing: {candidate}")
    return candidate


def run_checked(command: list[str], cwd: Path, env: dict[str, str]) -> None:
    if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
        raise EvidenceError("contract command must be a non-empty string array")
    subprocess.run(command, cwd=cwd, env=env, check=True)


def fetch_bounded(url: str, timeout_seconds: float, process: subprocess.Popen[str] | None = None) -> bytes:
    deadline = time.monotonic() + timeout_seconds
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise EvidenceError(f"candidate server exited before owning the configured origin (exit={process.returncode})")
        try:
            with urllib.request.urlopen(url, timeout=min(2.0, timeout_seconds)) as response:
                if 200 <= response.status < 400:
                    return response.read(16 * 1024 * 1024)
        except Exception as error:  # bounded polling with retained root symptom
            last_error = error
        time.sleep(0.25)
    raise EvidenceError(f"candidate health check failed for {url}: {last_error}")


def require_unoccupied_origin(url: str) -> None:
    parsed = urlparse(url)
    port = parsed.port or 80
    try:
        with socket.create_connection((parsed.hostname or "", port), timeout=0.35):
            raise EvidenceError(f"candidate origin is already occupied before start: {parsed.hostname}:{port}")
    except EvidenceError:
        raise
    except OSError:
        return


def quarantine_previous_reports(output: Path, expected_reports: list[str]) -> None:
    reports_root = (output / "reports").resolve()
    reports_root.mkdir(parents=True, exist_ok=True)
    backup_root = reports_root / ".previous-current" / str(time.time_ns())
    values = list(expected_reports) + ["reports/current_evidence.json", "reports/validation_run.json"]
    for value in values:
        path = (output / value).resolve()
        try:
            relative = path.relative_to(reports_root)
        except ValueError as exc:
            raise EvidenceError(f"expected report must stay under reports/: {value}") from exc
        if path.is_file():
            target = backup_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            path.replace(target)


def extract_matrix_keys(report: object, allowed_verdicts: set[str]) -> list[str]:
    if not isinstance(report, dict):
        return []
    found: set[str] = set()
    for field in ("matrix_results", "rows", "viewports", "results", "entries"):
        values = report.get(field)
        if not isinstance(values, list):
            continue
        for item in values:
            verdict = item.get("result", item.get("verdict")) if isinstance(item, dict) else None
            if isinstance(item, dict) and isinstance(item.get("matrix_key"), str) and verdict in allowed_verdicts:
                found.add(item["matrix_key"])
    return sorted(found)


def matrix_role_paths(classification: dict) -> dict[str, tuple[str, set[str]]]:
    role_paths = {
        "visual": ("reports/diff_summary.json", {"pass"}),
        "geometry": ("reports/node_validation.json", {"pass"}),
        "typography": ("reports/font_manifest.json", {"pass", "font-exact", "font-substituted"}),
    }
    if classification.get("behavior_required"):
        role_paths["behavior"] = ("reports/behavior_validation.json", {"pass"})
    if classification.get("liveness_required"):
        role_paths["liveness"] = ("reports/liveness_validation.json", {"pass"})
    return role_paths


def command_invokes_script(commands: list[list[str]], script: Path, cwd: Path) -> bool:
    target = script.resolve()
    for command in commands:
        if not isinstance(command, list) or not command:
            continue
        positional = next((value for value in command[1:] if isinstance(value, str) and value and not value.startswith("-")), command[0])
        candidate = Path(positional)
        if not candidate.is_absolute():
            candidate = cwd / candidate
        try:
            if candidate.resolve() == target:
                return True
        except OSError:
            continue
    return False


def require_specialist_command_suffix(commands: list[list[str]], roles: set[str], cwd: Path) -> None:
    scripts = {role: (SCRIPT.parent / SPECIALIST_SCRIPTS[role]).resolve() for role in roles}
    recognized = []
    for index, command in enumerate(commands):
        matches = [role for role, script in scripts.items() if command_invokes_script([command], script, cwd)]
        if len(matches) > 1:
            raise EvidenceError("one command cannot attest multiple specialist gates")
        if matches:
            recognized.append((index, matches[0]))
    if len(recognized) != len(roles) or {role for _, role in recognized} != roles:
        raise EvidenceError("current commands are missing a bundled specialist invocation")
    first = min(index for index, _ in recognized)
    if any(not any(index == current for current, _ in recognized) for index in range(first, len(commands))):
        raise EvidenceError("bundled specialist invocations must be the final command suffix")


def verify_matrix_artifacts(output: Path, coverage: dict, classification: dict, expected_matrix: list[str], commands: list[list[str]] | None = None, candidate_root: Path | None = None, require_specialist: bool = True) -> None:
    role_paths = matrix_role_paths(classification)
    rows = coverage.get("artifacts")
    if not isinstance(rows, list):
        raise EvidenceError("matrix coverage must cite the individual gate artifacts")
    if require_specialist:
        if not commands or candidate_root is None:
            raise EvidenceError("matrix artifacts require bundled specialist commands")
        require_specialist_command_suffix(commands, set(role_paths), candidate_root)
    by_role = {row.get("role"): row for row in rows if isinstance(row, dict) and isinstance(row.get("role"), str)}
    if set(by_role) != set(role_paths):
        raise EvidenceError(f"matrix coverage artifact roles differ: expected {sorted(role_paths)}, got {sorted(by_role)}")
    for role, (relative, allowed_verdicts) in role_paths.items():
        row = by_role[role]
        if row.get("path") != relative or sorted(row.get("matrix_completed") or []) != expected_matrix:
            raise EvidenceError(f"matrix coverage for {role} is missing or incomplete")
        path = (output / relative).resolve()
        path.relative_to(output)
        if not path.is_file() or row.get("sha256") != sha256_file(path):
            raise EvidenceError(f"matrix coverage for {role} is not bound to the current artifact")
        report = json.loads(path.read_text(encoding="utf-8"))
        specialist = SCRIPT.parent / SPECIALIST_SCRIPTS[role]
        if require_specialist and (report.get("generator_sha256") != sha256_file(specialist) or not command_invokes_script(commands, specialist, candidate_root)):
            raise EvidenceError(f"{relative} was not generated by a bundled specialist invocation")
        artifact_keys = extract_matrix_keys(report, allowed_verdicts)
        if artifact_keys != expected_matrix:
            raise EvidenceError(f"{relative} does not contain the complete matrix")


def build_matrix_coverage(output: Path, classification: dict, expected_matrix: list[str], commands: list[list[str]], candidate_root: Path, require_specialist: bool = True) -> dict:
    artifacts = []
    for role, (relative, _) in matrix_role_paths(classification).items():
        path = (output / relative).resolve(); path.relative_to(output)
        if not path.is_file():
            raise EvidenceError(f"specialist gate did not generate {relative}")
        artifacts.append({"role": role, "path": relative, "sha256": sha256_file(path), "matrix_completed": expected_matrix})
    coverage = {"result": "pass", "matrix_completed": expected_matrix, "artifacts": artifacts, "generator_sha256": sha256_file(SCRIPT)}
    verify_matrix_artifacts(output, coverage, classification, expected_matrix, commands, candidate_root, require_specialist)
    return coverage


def verify_output_source(output: Path, contract_path: Path, contract: dict) -> list[dict[str, str]]:
    """Bind the legacy final gate's source directory to this exact immutable contract."""
    contract_root = contract_path.parent.resolve()
    source_root = (output / "source").resolve()
    expected_source_sha = contract["source"]["sha256"]
    required = {
        "input.original": expected_source_sha,
        "input.h2d": expected_source_sha,
    }
    decoded_names: set[str] = set()
    for index, entry in enumerate(contract.get("decoded_artifacts") or []):
        source_path = resolve_inside(contract_root, entry["path"], f"decoded_artifacts[{index}]")
        name = source_path.name
        if name in decoded_names or name in required:
            raise EvidenceError(f"decoded artifact output name is ambiguous: {name}")
        decoded_names.add(name)
        required[name] = entry["sha256"]
    artifacts: list[dict[str, str]] = []
    for name, expected in sorted(required.items()):
        path = resolve_inside(source_root, name, f"current source artifact {name}")
        if not path.is_file() or sha256_file(path) != expected:
            raise EvidenceError(f"current source artifact is missing or differs from the contract: source/{name}")
        artifacts.append({"path": f"source/{name}", "sha256": expected})
    checksum = resolve_inside(source_root, "input.sha256", "current source checksum")
    expected_checksum = f"{expected_source_sha}  input.original\n"
    if not checksum.is_file() or checksum.read_text(encoding="utf-8") != expected_checksum:
        raise EvidenceError("source/input.sha256 is missing or not bound to the contract source")
    artifacts.append({"path": "source/input.sha256", "sha256": sha256_file(checksum)})
    return artifacts


def verify_lifecycle_environment(lifecycle: dict, env: dict[str, str]) -> None:
    probes = {"node": ["node", "--version"], "npm": ["npm", "--version"]}
    for name, expected in (lifecycle.get("toolchain") or {}).items():
        if name not in probes:
            raise EvidenceError(f"unsupported toolchain probe {name!r}; supported: {sorted(probes)}")
        actual = subprocess.run(probes[name], check=True, capture_output=True, text=True).stdout.strip()
        if actual != expected:
            raise EvidenceError(f"toolchain {name} changed: expected {expected!r}, got {actual!r}")
    for name, expected in (lifecycle.get("public_env_sha256") or {}).items():
        if name not in env:
            raise EvidenceError(f"pinned public build environment variable is missing: {name}")
        actual = sha256_bytes(env[name].encode("utf-8"))
        if actual != expected:
            raise EvidenceError(f"public build environment variable changed: {name}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--no-final-legacy-gate", action="store_true", help="Diagnostic only: generate current evidence but do not claim final pass")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    contract_path = args.contract.resolve()
    contract_path.relative_to(output)
    verified = verify_contract(contract_path, output)
    contract = verified["contract"]
    before = verified["closure"]["digest"]
    expected_matrix = matrix_keys(contract)
    commands = contract.get("current_commands") or []
    expected_reports = contract.get("expected_reports") or []
    if not commands or not expected_reports:
        raise EvidenceError("contract must pin non-empty current_commands and expected_reports")
    env = os.environ.copy()
    env.update({
        "H2D_OUTPUT": str(output), "H2D_CONTRACT": str(contract_path),
        "H2D_MATRIX_KEYS": json.dumps(expected_matrix),
    })
    candidate_root = verified["candidate_root"]
    lifecycle = (contract.get("candidate") or {}).get("lifecycle") or {}
    server: subprocess.Popen[str] | None = None
    quarantine_previous_reports(output, expected_reports)
    try:
        if lifecycle:
            verify_lifecycle_environment(lifecycle, env)
        build = lifecycle.get("build")
        if build:
            run_checked(build, bounded_cwd(candidate_root, lifecycle.get("cwd")), env)
        start = lifecycle.get("start")
        if start:
            if not isinstance(start, list) or not start:
                raise EvidenceError("candidate lifecycle start must be a non-empty array")
            health = lifecycle.get("health_url")
            if not isinstance(health, str) or not health:
                raise EvidenceError("managed candidate lifecycle needs health_url")
            require_unoccupied_origin(health)
            server = subprocess.Popen(start, cwd=bounded_cwd(candidate_root, lifecycle.get("cwd")), env=env, text=True)
            fetch_bounded(health, float(lifecycle.get("health_timeout_seconds", 30)), server)
            identity = fetch_bounded(lifecycle["build_identity_url"], float(lifecycle.get("health_timeout_seconds", 30)), server)
            if sha256_bytes(identity) != lifecycle["build_identity_sha256"]:
                raise EvidenceError("managed candidate served a stale or different build identity")
            try:
                identity_data = json.loads(identity.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise EvidenceError("managed candidate build identity must be canonical JSON") from exc
            required_identity = {"schema_version": "2.0", "candidate_closure_sha256": before, "source_sha256": contract["source"]["sha256"]}
            if identity_data != required_identity:
                raise EvidenceError("managed candidate build identity is not bound to the current candidate/source closure")
        for command in commands:
            run_checked(command, candidate_root, env)
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=float(lifecycle.get("teardown_timeout_seconds", 10)))
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
        teardown = lifecycle.get("teardown") if lifecycle else None
        if teardown:
            run_checked(teardown, bounded_cwd(candidate_root, lifecycle.get("cwd")), env)
    after_verified = verify_contract(contract_path, output)
    after = after_verified["closure"]["digest"]
    if before != after:
        raise EvidenceError("candidate changed while current gates were running")
    source_artifacts = verify_output_source(output, contract_path, contract)
    coverage_path = output / "reports" / "matrix_coverage.json"
    coverage = build_matrix_coverage(output, contract.get("classification") or {}, expected_matrix, commands, candidate_root, not args.no_final_legacy_gate)
    coverage_path.write_text(json.dumps(coverage, indent=2, ensure_ascii=False), encoding="utf-8")
    completed = sorted(coverage.get("matrix_completed") or [])
    if coverage.get("result") != "pass" or completed != expected_matrix:
        raise EvidenceError("matrix coverage report is non-pass or incomplete")
    report_entries = []
    for value in expected_reports:
        report = (output / value).resolve()
        report.relative_to(output)
        if not report.is_file() or report.stat().st_size == 0:
            raise EvidenceError(f"expected current report is missing: {value}")
        report_entries.append({"path": report.relative_to(output).as_posix(), "sha256": sha256_file(report)})
    if "reports/matrix_coverage.json" not in {item["path"] for item in report_entries}:
        report_entries.append({"path": "reports/matrix_coverage.json", "sha256": sha256_file(coverage_path)})
    evidence = {
        "schema_version": "2.0", "result": "pass", "generated_at": datetime.now(timezone.utc).isoformat(),
        "contract_path": contract_path.relative_to(output).as_posix(),
        "contract_sha256": sha256_file(contract_path), "runner_sha256": sha256_file(SCRIPT),
        "candidate_digest_before": before, "candidate_digest_after": after,
        "matrix_completed": completed, "source_artifacts": source_artifacts,
        "reports": sorted(report_entries, key=lambda item: item["path"]),
    }
    evidence_path = output / "reports" / "current_evidence.json"
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(json.dumps(evidence, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.no_final_legacy_gate:
        print(f"result=diagnostic-current evidence={evidence_path}")
        return 3
    from run_all_gates import check_output
    classification = contract.get("classification") or {}
    result = check_output(
        output,
        "true" if classification.get("behavior_required") else "false",
        "true" if classification.get("liveness_required") else "false",
        False,
    )
    final_path = output / "reports" / "validation_run.json"
    final_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"result={result['result']} matrix={len(completed)} evidence={evidence_path}")
    return 0 if result["result"] == "pass" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (EvidenceError, subprocess.CalledProcessError, ValueError) as error:
        print(f"current gates blocked: {error}", file=sys.stderr)
        raise SystemExit(2)
