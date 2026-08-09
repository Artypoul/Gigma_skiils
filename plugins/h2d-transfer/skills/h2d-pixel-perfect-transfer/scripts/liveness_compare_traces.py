#!/usr/bin/env python3
"""Compare pinned motion timing, transforms, scoped frames and canvas bytes."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from image_diff_metrics import compare as compare_images


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.exists() else []


def rect_differences(expected: dict, actual: dict, tolerance: float) -> dict:
    return {field: [expected.get(field), actual.get(field)] for field in ("x", "y", "width", "height") if not isinstance(expected.get(field), (int, float)) or not isinstance(actual.get(field), (int, float)) or abs(float(expected[field]) - float(actual[field])) > tolerance}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--original", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--original-root", type=Path, required=True)
    parser.add_argument("--candidate-root", type=Path, required=True)
    parser.add_argument("--max-frame-mismatch-ratio", type=float, default=0.005)
    parser.add_argument("--max-rect-delta-px", type=float, default=1.0)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    original = {row.get("trace_id"): row for row in read_jsonl(args.original)}
    candidate = {row.get("trace_id"): row for row in read_jsonl(args.candidate)}
    checks = []
    issues = []
    expected_ids = {f"{surface['surface_id']}@{trigger}" for surface in inventory.get("surfaces", []) for trigger in surface.get("triggers", ["load"])}
    for trace_id in sorted(expected_ids):
        expected = original.get(trace_id); actual = candidate.get(trace_id); detail: dict = {}
        if not expected or not actual:
            detail = {"missing": "original" if not expected else "candidate"}
        elif expected.get("errors"):
            detail = {"invalid_reference_errors": expected.get("errors")}
        elif actual.get("errors"):
            detail = {"candidate_errors": actual.get("errors")}
        else:
            expected_samples = expected.get("samples") or []; actual_samples = actual.get("samples") or []
            if len(expected_samples) < 3 or len(actual_samples) < 3:
                detail["sampling"] = "required motion trace has fewer than three samples"
            if [row.get("t_ms") for row in expected_samples] != [row.get("t_ms") for row in actual_samples]:
                detail["timing"] = "sample timeline differs"
            frame_results = []
            for index, expected_sample in enumerate(expected_samples):
                if index >= len(actual_samples):
                    frame_results.append({"index": index, "result": "fail", "reason": "missing sample"}); continue
                actual_sample = actual_samples[index]
                expected_computed = expected_sample.get("computed") or {}; actual_computed = actual_sample.get("computed") or {}
                style_fields = ["opacity", "transform", "filter", "clipPath", "animationDuration", "animationDelay", "transitionDuration", "transitionDelay"]
                style_diff = {field: [expected_computed.get(field), actual_computed.get(field)] for field in style_fields if expected_computed.get(field) != actual_computed.get(field)}
                try:
                    metrics = compare_images(args.original_root / expected_sample["screenshot"], args.candidate_root / actual_sample["screenshot"])
                    ratio = metrics["pixel_mismatch_ratio"]
                except Exception as error:
                    ratio = 1.0; style_diff["image_error"] = str(error)[:200]
                expected_canvas = (expected_sample.get("canvas") or {}).get("frame_sha256")
                actual_canvas = (actual_sample.get("canvas") or {}).get("frame_sha256")
                canvas_ok = expected_canvas == actual_canvas
                rect_diff = rect_differences(expected_sample.get("rect") or {}, actual_sample.get("rect") or {}, args.max_rect_delta_px)
                expected_media = expected_sample.get("media"); actual_media = actual_sample.get("media")
                media_ok = (expected_media is None and actual_media is None) or (isinstance(expected_media, dict) and isinstance(actual_media, dict) and expected_media.get("paused") == actual_media.get("paused") and abs(float(expected_media.get("current_time", 0)) - float(actual_media.get("current_time", 0))) <= 0.15)
                passed = not style_diff and not rect_diff and ratio <= args.max_frame_mismatch_ratio and canvas_ok and media_ok
                frame_results.append({"index": index, "t_ms": expected_sample.get("t_ms"), "result": "pass" if passed else "fail", "pixel_mismatch_ratio": ratio, "style_diff": style_diff, "rect_diff": rect_diff, "canvas_match": canvas_ok, "media_match": media_ok})
            if any(row["result"] == "fail" for row in frame_results): detail["frames"] = frame_results
        result = "fail" if detail else "pass"
        checks.append({"surface_id": trace_id.split("@")[0], "trace_id": trace_id, "kind": (expected or actual or {}).get("kind"), "result": result, "message": "pinned runtime states match" if not detail else "runtime fidelity mismatch", "details": detail, "evidence": ["original_animation_trace.jsonl", "candidate_animation_trace.jsonl"]})
        if detail: issues.append({"trace_id": trace_id, "result": "fail", "details": detail})
    for trace_id in sorted((set(original) | set(candidate)) - expected_ids):
        issues.append({"trace_id": trace_id, "result": "fail", "details": {"unexpected_trace": True}})
    result = "fail" if issues else ("pass" if expected_ids else "static-scope")
    report = {"result": result, "liveness_required": bool(expected_ids), "checked_at": datetime.now(timezone.utc).isoformat(), "webgl_runtime_verdict": "fail" if issues and any("webgl" in str(item).lower() for item in issues) else ("pass" if any("webgl" in str(item).lower() for item in checks) else "not-present"), "checks": checks, "accepted_deviations": [], "issues": issues}
    args.out.parent.mkdir(parents=True, exist_ok=True); args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"result={result} checks={len(checks)} out={args.out}")
    return 0 if result in {"pass", "static-scope"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
