#!/usr/bin/env python3
"""Compare semantic, intent, accessibility and visual post-state behavior evidence."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from image_diff_metrics import compare as compare_images


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def normalized_intents(row: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = []
    for item in row.get("intents") or []:
        destination = item.get("destination") or {}
        normalized.append({
            "kind": item.get("kind"), "method": item.get("method"), "target": item.get("target"),
            "download": item.get("download"), "destination_sha256": destination.get("canonical_url_sha256"),
        })
    return normalized


def normalized_outcomes(row: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    requests = [{"method": item.get("method"), "url_sha256": item.get("canonical_url_sha256"), "action": item.get("action")} for item in row.get("blocked_requests") or []]
    transports = [{"kind": item.get("kind"), "url": item.get("url")} for item in row.get("blocked_transports") or []]
    return {"requests": requests, "transports": transports}


def semantic_checks(expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, str]:
    fields = ["exists", "aria_expanded", "aria_checked", "value", "controlled_visible", "body_overflow", "accessibility_sha256"]
    checks: dict[str, str] = {}
    for phase in ("before", "after"):
        for field in fields:
            expected_value = (expected.get(phase) or {}).get(field)
            actual_value = (actual.get(phase) or {}).get(field)
            if expected_value is None and actual_value is None:
                continue
            checks[f"{phase}_{field}"] = "pass" if expected_value == actual_value else "fail"
    return checks


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--max-state-pixel-mismatch-ratio", type=float, default=0.005)
    args = parser.parse_args()
    original = {row.get("interaction_id"): row for row in read_jsonl(args.original)}
    candidate = {row.get("interaction_id"): row for row in read_jsonl(args.candidate)}
    comparisons = []
    issues = []
    for interaction_id, expected in original.items():
        actual = candidate.get(interaction_id)
        if expected.get("errors") or expected.get("runtime_errors"):
            issues.append({"type": "invalid-reference-trace", "interaction_id": interaction_id, "severity": "fail"})
            continue
        if not actual:
            issues.append({"type": "missing-candidate-state", "interaction_id": interaction_id, "severity": "fail"})
            continue
        checks: dict[str, Any] = semantic_checks(expected, actual)
        checks["intent"] = "pass" if normalized_intents(expected) == normalized_intents(actual) else "fail"
        checks["blocked_outcomes"] = "pass" if normalized_outcomes(expected) == normalized_outcomes(actual) else "fail"
        if actual.get("errors"):
            checks["candidate_action_errors"] = "fail"
        if actual.get("runtime_errors"):
            checks["candidate_runtime_errors"] = "fail"
        original_shot = (args.original_root / str(expected.get("screenshot", ""))).resolve()
        candidate_shot = (args.candidate_root / str(actual.get("screenshot", ""))).resolve()
        try:
            metrics = compare_images(original_shot, candidate_shot)
            checks["state_pixels"] = "pass" if metrics["pixel_mismatch_ratio"] <= args.max_state_pixel_mismatch_ratio else "fail"
            checks["state_pixel_mismatch_ratio"] = metrics["pixel_mismatch_ratio"]
        except Exception as error:
            checks["state_pixels"] = "fail"
            checks["state_pixel_error"] = str(error)[:300]
        failed = any(value == "fail" for value in checks.values())
        if failed:
            issues.append({"type": "behavior-state-mismatch", "interaction_id": interaction_id, "severity": "fail", "checks": checks})
        comparisons.append({"interaction_id": interaction_id, "matrix_key": expected.get("matrix_key"), "result": "fail" if failed else "pass", "checks": checks})
    for interaction_id in sorted(set(candidate) - set(original)):
        issues.append({"type": "extra-candidate-state", "interaction_id": interaction_id, "severity": "fail"})
    result = "fail" if issues else "pass"
    matrix_keys = sorted({row.get("matrix_key") for row in comparisons if row.get("matrix_key")})
    matrix_results = [{"matrix_key": key, "result": "pass" if all(row["result"] == "pass" for row in comparisons if row.get("matrix_key") == key) else "fail"} for key in matrix_keys]
    report = {"result": result, "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), "behavior_required": True, "matrix_results": matrix_results, "comparisons": comparisons, "accepted_deviations": [], "issues": issues, "safe_boundaries": []}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"behavior={result} comparisons={len(comparisons)} issues={len(issues)} out={args.out}")
    return 0 if result == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
