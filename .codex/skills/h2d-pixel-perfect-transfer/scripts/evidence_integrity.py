#!/usr/bin/env python3
"""Integrity primitives for immutable H2D transfer contracts and current evidence."""
from __future__ import annotations

import hashlib
import base64
import ipaddress
import json
import os
import shutil
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse


HEX64 = set("0123456789abcdef")
IGNORED_CACHE_PARTS = {".git", "node_modules", ".svelte-kit", ".next", "dist", "build", "__pycache__"}


class EvidenceError(ValueError):
    """A fail-closed evidence or provenance violation."""


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(data: Any) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def canonical_json_sha256(data: Any) -> str:
    return sha256_bytes(canonical_json(data))


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(ch in HEX64 for ch in value.lower())


def require_sha256(value: Any, label: str) -> str:
    if not is_sha256(value):
        raise EvidenceError(f"{label} must be a lowercase 64-character SHA-256 digest")
    return str(value).lower()


def require_local_candidate_urls(health_url: Any, identity_url: Any) -> None:
    parsed = []
    for label, value in (("health_url", health_url), ("build_identity_url", identity_url)):
        if not isinstance(value, str) or not value:
            raise EvidenceError(f"candidate.lifecycle.{label} is required")
        current = urlparse(value)
        if current.scheme != "http" or not current.hostname:
            raise EvidenceError(f"candidate.lifecycle.{label} must be a local http URL")
        try:
            port = current.port or 80
        except ValueError as exc:
            raise EvidenceError(f"candidate.lifecycle.{label} has an invalid port") from exc
        if current.hostname == "localhost":
            is_loopback = True
        else:
            try:
                is_loopback = ipaddress.ip_address(current.hostname).is_loopback
            except ValueError:
                is_loopback = False
        if not is_loopback:
            raise EvidenceError(f"candidate.lifecycle.{label} must use a loopback host")
        parsed.append((current.scheme, current.hostname, port))
    if parsed[0] != parsed[1]:
        raise EvidenceError("candidate lifecycle health and build identity URLs must use the same local origin")


def resolve_command_executable(value: str, cwd: Path | None = None) -> Path:
    candidate = Path(value)
    execution_root = (cwd or Path.cwd()).resolve()
    if candidate.is_absolute():
        resolved = candidate.resolve()
    elif "/" in value or "\\" in value:
        resolved = (execution_root / candidate).resolve()
    else:
        search_entries = []
        for entry in os.get_exec_path():
            current = Path(entry or ".")
            if not current.is_absolute():
                current = execution_root / current
            search_entries.append(str(current.resolve()))
        discovered = shutil.which(value, path=os.pathsep.join(search_entries))
        if not discovered:
            raise EvidenceError(f"pinned command executable cannot be resolved: {value}")
        resolved = Path(discovered).resolve()
    if not resolved.is_file():
        raise EvidenceError(f"pinned command executable is missing: {resolved}")
    return resolved


def command_executable_records(commands: Iterable[list[str]], cwd: Path | None = None) -> list[dict[str, str]]:
    execution_root = (cwd or Path.cwd()).resolve()
    records: dict[tuple[str, str], dict[str, str]] = {}
    for command in commands:
        if not isinstance(command, list) or not command or any(not isinstance(item, str) or not item for item in command):
            raise EvidenceError("all pinned commands must be non-empty string arrays")
        executable = resolve_command_executable(command[0], execution_root)
        record = {"command": command[0], "cwd": str(execution_root), "resolved_path": str(executable), "sha256": sha256_file(executable)}
        key = (command[0], str(execution_root))
        previous = records.get(key)
        if previous and previous != record:
            raise EvidenceError(f"command executable resolved inconsistently: {command[0]}")
        records[key] = record
    return [records[key] for key in sorted(records)]


def command_executable_records_for_specs(command_specs: Iterable[tuple[list[str], Path]]) -> list[dict[str, str]]:
    records: dict[tuple[str, str, str], dict[str, str]] = {}
    for command, cwd in command_specs:
        for record in command_executable_records([command], cwd):
            key = (record["command"], record["cwd"], record["resolved_path"])
            records[key] = record
    return [records[key] for key in sorted(records)]


def resolve_inside(root: Path, value: str | Path, label: str) -> Path:
    root = root.resolve()
    candidate = Path(value)
    if not candidate.is_absolute():
        candidate = root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise EvidenceError(f"{label} escapes root {root}: {candidate}") from exc
    return candidate


def _walk_include(root: Path, value: str | Path) -> Iterable[Path]:
    target = resolve_inside(root, value, "candidate include")
    if not target.exists():
        raise EvidenceError(f"candidate include is missing: {target}")
    if target.is_symlink():
        raise EvidenceError(f"candidate include may not be a symlink: {target}")
    if target.is_file():
        yield target
        return
    for path in sorted(target.rglob("*")):
        if any(part in IGNORED_CACHE_PARTS for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise EvidenceError(f"candidate closure may not contain symlinks: {path}")
        if path.is_file():
            yield path


def candidate_closure(root: Path, includes: Iterable[str], evidence_dir: Path | None = None) -> dict[str, Any]:
    root = root.resolve()
    evidence = evidence_dir.resolve() if evidence_dir else None
    files: dict[str, dict[str, Any]] = {}
    for include in includes:
        for path in _walk_include(root, include):
            if evidence:
                try:
                    path.resolve().relative_to(evidence)
                    continue
                except ValueError:
                    pass
            rel = path.resolve().relative_to(root).as_posix()
            files[rel] = {"path": rel, "size": path.stat().st_size, "sha256": sha256_file(path)}
    if not files:
        raise EvidenceError("candidate include closure is empty")
    ordered = [files[key] for key in sorted(files)]
    return {"files": ordered, "digest": canonical_json_sha256(ordered)}


def verify_hashed_files(base: Path, entries: Iterable[dict[str, Any]], label: str) -> list[str]:
    verified: list[str] = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise EvidenceError(f"{label}[{index}] must be an object")
        rel = entry.get("path")
        expected = require_sha256(entry.get("sha256"), f"{label}[{index}].sha256")
        if not isinstance(rel, str) or not rel:
            raise EvidenceError(f"{label}[{index}].path is required")
        path = resolve_inside(base, rel, f"{label}[{index}]")
        if not path.is_file():
            raise EvidenceError(f"{label}[{index}] is missing: {path}")
        actual = sha256_file(path)
        if actual != expected:
            raise EvidenceError(f"{label}[{index}] changed: {rel}; expected {expected}, got {actual}")
        verified.append(rel)
    return verified


def reject_candidate_reference_code_overlap(closure: dict[str, Any], reference: dict[str, Any]) -> None:
    """Reject candidate-derived references without blocking one shared utility/reset."""
    authored = {".html", ".htm", ".css", ".scss", ".less", ".js", ".mjs", ".cjs", ".ts", ".tsx", ".jsx", ".svelte", ".vue"}
    donor_hashes = {
        item.get("sha256")
        for item in (reference.get("donor_closure") or [])
        if isinstance(item, dict) and Path(str(item.get("path", ""))).suffix.lower() in authored
    }
    candidate = [
        item for item in (closure.get("files") or [])
        if isinstance(item, dict) and Path(str(item.get("path", ""))).suffix.lower() in authored
    ]
    total_bytes = sum(int(item.get("size") or 0) for item in candidate)
    overlapping = [item for item in candidate if item.get("sha256") in donor_hashes]
    overlap_bytes = sum(int(item.get("size") or 0) for item in overlapping)
    if candidate and overlapping and (len(overlapping) == len(candidate) or (total_bytes and overlap_bytes / total_bytes >= 0.5)):
        sample = ", ".join(str(item.get("path")) for item in overlapping[:3])
        raise EvidenceError(
            "candidate authored code substantially overlaps the frozen donor; the reference must be independent "
            f"instead of candidate-derived (sample: {sample})"
        )


def required_dynamic_roles(classification: dict[str, Any]) -> set[str]:
    roles: set[str] = set()
    if classification.get("behavior_required"):
        roles |= {
            "behavior-inventory", "interaction-matrix", "event-listener-inventory",
            "behavior-state-targets", "original-behavior-traces", "behavior-state-screenshot",
        }
    if classification.get("liveness_required"):
        roles |= {"liveness-inventory", "original-animation-traces", "liveness-screenshot"}
        has_webgl = any(
            "webgl" in str(surface.get("kind", "")).lower()
            for row in classification.get("rows") or []
            for state in row.get("states") or []
            for surface in state.get("surfaces") or []
            if isinstance(surface, dict)
        )
        if has_webgl:
            roles.add("webgl-capture")
    return roles


DYNAMIC_ROLE_GENERATORS = {
    "behavior-inventory": "behavior_inventory.js",
    "interaction-matrix": "behavior_matrix_generate.js",
    "event-listener-inventory": "behavior_inventory.js",
    "behavior-state-targets": "behavior_build_state_targets.py",
    "original-behavior-traces": "behavior_capture_trace.js",
    "behavior-state-screenshot": "behavior_capture_trace.js",
    "liveness-inventory": "liveness_inventory.js",
    "original-animation-traces": "liveness_capture_trace.js",
    "liveness-screenshot": "liveness_capture_trace.js",
    "webgl-capture": "webgl_capture.js",
}


def validate_dynamic_artifact_source(kind: str, source: Path) -> dict[str, Any]:
    """Parse a role-specific artifact and bind it to the bundled generator."""
    generator_name = DYNAMIC_ROLE_GENERATORS.get(kind)
    if not generator_name:
        raise EvidenceError(f"unsupported dynamic artifact role: {kind}")
    generator = Path(__file__).resolve().parent / generator_name
    expected_generator = sha256_file(generator)
    evidence: dict[str, Any] = {"generator_sha256": expected_generator, "referenced_screenshots": set()}
    if kind in {"behavior-state-screenshot", "liveness-screenshot"}:
        data = source.read_bytes()
        if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR" or int.from_bytes(data[16:20], "big") < 1 or int.from_bytes(data[20:24], "big") < 1:
            raise EvidenceError(f"{kind} must be a non-empty PNG with a valid IHDR: {source}")
        return evidence
    if kind in {"original-behavior-traces", "original-animation-traces"}:
        try:
            rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EvidenceError(f"{kind} must be valid JSONL: {source}") from exc
        if not rows or any(not isinstance(row, dict) or row.get("generator_sha256") != expected_generator or row.get("side") != "original" or row.get("errors") or row.get("runtime_errors") for row in rows):
            raise EvidenceError(f"{kind} must contain generated, error-free original traces")
        if kind == "original-behavior-traces":
            if any(not row.get("interaction_id") or not isinstance(row.get("before"), dict) or not isinstance(row.get("after"), dict) or not is_sha256(row.get("screenshot_sha256")) for row in rows):
                raise EvidenceError("original behavior traces are incomplete")
            evidence["referenced_screenshots"] = {row["screenshot_sha256"] for row in rows}
        else:
            samples = [sample for row in rows for sample in (row.get("samples") or [])]
            if any(not row.get("trace_id") or len(row.get("samples") or []) < 3 for row in rows) or any(not is_sha256(sample.get("frame_hash")) for sample in samples):
                raise EvidenceError("original animation traces are incomplete")
            evidence["referenced_screenshots"] = {sample["frame_hash"] for sample in samples}
        return evidence
    try:
        report = json.loads(source.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise EvidenceError(f"{kind} must be valid JSON: {source}") from exc
    if not isinstance(report, dict) or report.get("generator_sha256") != expected_generator:
        raise EvidenceError(f"{kind} is missing trusted bundled-generator provenance")
    if kind == "behavior-inventory" and not (report.get("result") == "pass" and report.get("coverage_complete") is True and isinstance(report.get("components"), list) and report["components"]):
        raise EvidenceError("behavior inventory is incomplete")
    if kind == "interaction-matrix" and not (report.get("result") == "pass" and report.get("coverage_complete") is True and isinstance(report.get("interactions"), list) and report["interactions"]):
        raise EvidenceError("interaction matrix is incomplete")
    if kind == "event-listener-inventory" and not (report.get("result") == "pass" and report.get("coverage_complete") is True and isinstance(report.get("listeners"), list)):
        raise EvidenceError("event listener inventory is incomplete")
    if kind == "behavior-state-targets" and not (report.get("result") == "pass" and isinstance(report.get("targets"), list) and report["targets"]):
        raise EvidenceError("behavior state targets are incomplete")
    if kind == "liveness-inventory" and not (report.get("result") == "pass" and report.get("coverage_complete") is True and isinstance(report.get("surfaces"), list) and report["surfaces"]):
        raise EvidenceError("liveness inventory is incomplete")
    if kind == "webgl-capture":
        contexts = report.get("contexts") or []
        if (
            report.get("result") != "pass"
            or report.get("coverage_complete") is not True
            or not isinstance(contexts, list)
            or not contexts
            or report.get("issues") != []
            or any(
                not isinstance(row, dict)
                or not isinstance(row.get("canvas_selector"), str)
                or row.get("context_type") not in {"webgl", "webgl2"}
                or not isinstance(row.get("rect"), dict)
                or not isinstance(row.get("context_attributes"), dict)
                or not isinstance(row.get("vendor"), str)
                or not isinstance(row.get("renderer"), str)
                or not isinstance(row.get("frame_hashes"), list)
                or len(row.get("frame_hashes") or []) < 3
                or any(not is_sha256(value) for value in (row.get("frame_hashes") or []))
                or type(row.get("non_blank_samples")) is not int
                or row["non_blank_samples"] < 1
                for row in contexts
            )
        ):
            raise EvidenceError("WebGL capture is incomplete")
    return evidence


def validate_dynamic_artifact_links(validated: list[tuple[str, Path, dict[str, Any]]]) -> None:
    for trace_kind, screenshot_kind in (("original-behavior-traces", "behavior-state-screenshot"), ("original-animation-traces", "liveness-screenshot")):
        referenced = {value for kind, _, evidence in validated if kind == trace_kind for value in evidence.get("referenced_screenshots") or set()}
        screenshots = {sha256_file(path) for kind, path, _ in validated if kind == screenshot_kind}
        if referenced != screenshots:
            raise EvidenceError(f"{screenshot_kind} files must exactly match screenshots referenced by {trace_kind}")


def validate_dynamic_manifest(
    dynamic: dict[str, Any],
    classification: dict[str, Any],
    expected_matrix: list[str],
    artifact_base: Path | None = None,
) -> None:
    generator = Path(__file__).resolve().parent / "finalize_dynamic_reference.py"
    if dynamic.get("result") != "pass" or dynamic.get("coverage_complete") is not True:
        raise EvidenceError("dynamic reference manifest is incomplete or non-pass")
    if dynamic.get("generator_sha256") != sha256_file(generator):
        raise EvidenceError("dynamic reference manifest was not produced by the bundled finalizer")
    if dynamic.get("classification_sha256") != canonical_json_sha256(classification):
        raise EvidenceError("dynamic reference manifest is bound to a different generated classification")
    if dynamic.get("donor_identity") != classification.get("donor_identity"):
        raise EvidenceError("visual/classification/dynamic phases used different donor identities")
    if sorted(dynamic.get("matrix_keys") or []) != sorted(expected_matrix):
        raise EvidenceError("dynamic reference matrix differs from visual matrix")
    artifacts = dynamic.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        raise EvidenceError("dynamic reference manifest has no artifacts")
    required = required_dynamic_roles(classification)
    if sorted(dynamic.get("required_roles") or []) != sorted(required):
        raise EvidenceError("dynamic reference required roles differ from generated classification")
    seen: set[tuple[str, str]] = set()
    validated: list[tuple[str, Path, dict[str, Any]]] = []
    for index, item in enumerate(artifacts):
        if not isinstance(item, dict):
            raise EvidenceError(f"dynamic artifact[{index}] must be an object")
        kind = item.get("kind")
        path = item.get("path")
        keys = item.get("matrix_keys")
        if not isinstance(kind, str) or not kind or not isinstance(path, str) or not path:
            raise EvidenceError(f"dynamic artifact[{index}] kind/path is missing")
        if Path(path).is_absolute() or ".." in Path(path).parts:
            raise EvidenceError(f"dynamic artifact[{index}] path is unsafe")
        if not isinstance(keys, list) or not keys or any(key not in expected_matrix for key in keys):
            raise EvidenceError(f"dynamic artifact[{index}] matrix coverage is invalid")
        identity = (kind, path)
        if identity in seen:
            raise EvidenceError(f"dynamic artifact[{index}] duplicates {kind}@{path}")
        seen.add(identity)
        require_sha256(item.get("sha256"), f"dynamic artifact[{index}].sha256")
        if artifact_base is not None:
            target = resolve_inside(artifact_base, path, f"dynamic artifact[{index}]")
            if not target.is_file() or target.stat().st_size == 0 or sha256_file(target) != item["sha256"]:
                raise EvidenceError(f"dynamic artifact is missing, empty, or changed: {path}")
            evidence = validate_dynamic_artifact_source(kind, target)
            if item.get("generator_sha256") != evidence["generator_sha256"]:
                raise EvidenceError(f"dynamic artifact[{index}] generator provenance differs")
            validated.append((kind, target, evidence))
    for role in required:
        covered = {
            key
            for item in artifacts
            if item.get("kind") == role
            for key in item.get("matrix_keys") or []
        }
        if covered != set(expected_matrix):
            raise EvidenceError(f"dynamic reference role {role} does not cover the complete matrix")
    if artifact_base is not None:
        validate_dynamic_artifact_links(validated)


def matrix_keys(contract: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    profiles = contract.get("browser_profiles") or []
    widths = contract.get("responsive_matrix") or []
    for viewport in widths:
        width = viewport.get("width") if isinstance(viewport, dict) else None
        height = viewport.get("height") if isinstance(viewport, dict) else None
        if not isinstance(width, int) or width <= 0 or not isinstance(height, int) or height <= 0:
            raise EvidenceError("every responsive_matrix row needs positive integer width and height")
        for profile in profiles:
            profile_id = profile.get("id") if isinstance(profile, dict) else None
            if not isinstance(profile_id, str) or not profile_id:
                raise EvidenceError("every browser profile needs a stable id")
            keys.append(f"{width}x{height}@{profile_id}")
    if not keys:
        raise EvidenceError("responsive_matrix × browser_profiles is empty")
    if len(keys) != len(set(keys)):
        raise EvidenceError("responsive_matrix × browser_profiles contains duplicate keys")
    return sorted(keys)


def verify_approval_records(records: Iterable[dict[str, Any]]) -> None:
    for index, record in enumerate(records):
        if not record.get("approved"):
            continue
        scope = record.get("scope")
        if not isinstance(scope, list) or not scope or any(not isinstance(item, str) or not item for item in scope):
            raise EvidenceError(f"approval[{index}] must list exact approved fields/scope")
        proof = record.get("verification")
        if not isinstance(proof, dict):
            raise EvidenceError(f"approval[{index}] has no trusted verification")
        kind = proof.get("kind")
        if kind not in {"owner-signature", "trusted-owner-event"}:
            raise EvidenceError(f"approval[{index}] uses untrusted verification kind {kind!r}")
        if proof.get("verified") is not True:
            raise EvidenceError(f"approval[{index}] is not verified")
        payload = {key: value for key, value in record.items() if key != "verification"}
        payload_bytes = canonical_json(payload)
        payload_sha256 = require_sha256(proof.get("payload_sha256"), f"approval[{index}].verification.payload_sha256")
        if sha256_bytes(payload_bytes) != payload_sha256:
            raise EvidenceError(f"approval[{index}] verification is bound to different approval content")
        if kind == "owner-signature":
            if proof.get("algorithm") != "ed25519" or not all(isinstance(proof.get(key), str) and proof.get(key) for key in ("key_id", "signature", "verified_by")):
                raise EvidenceError(f"approval[{index}] owner signature receipt is incomplete")
            try:
                trusted_keys = json.loads(os.environ.get("H2D_OWNER_PUBLIC_KEYS_JSON", "{}"))
            except json.JSONDecodeError as exc:
                raise EvidenceError("H2D_OWNER_PUBLIC_KEYS_JSON is invalid JSON") from exc
            encoded_key = trusted_keys.get(proof["key_id"]) if isinstance(trusted_keys, dict) else None
            if not isinstance(encoded_key, str) or not encoded_key:
                raise EvidenceError(f"approval[{index}] key_id is not present in the external owner trust store")
            try:
                from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
                public_key = Ed25519PublicKey.from_public_bytes(base64.b64decode(encoded_key, validate=True))
                public_key.verify(base64.b64decode(proof["signature"], validate=True), payload_bytes)
            except ImportError as exc:
                raise EvidenceError("cryptography is required to verify owner approvals") from exc
            except Exception as exc:
                raise EvidenceError(f"approval[{index}] owner signature is invalid") from exc
        else:
            if not all(isinstance(proof.get(key), str) and proof.get(key) for key in ("provider", "event_id", "actor_id", "verified_by")):
                raise EvidenceError(f"approval[{index}] trusted event receipt is incomplete")
            try:
                trusted_events = json.loads(os.environ.get("H2D_TRUSTED_OWNER_EVENTS_JSON", "{}"))
            except json.JSONDecodeError as exc:
                raise EvidenceError("H2D_TRUSTED_OWNER_EVENTS_JSON is invalid JSON") from exc
            receipt_key = f'{proof["provider"]}:{proof["event_id"]}:{proof["actor_id"]}'
            if not isinstance(trusted_events, dict) or trusted_events.get(receipt_key) != payload_sha256:
                raise EvidenceError(f"approval[{index}] event is absent from the external trusted-event receipt store")


def verify_reference_bundle(contract: dict[str, Any], contract_dir: Path) -> dict[str, Any]:
    reference = contract.get("reference_bundle")
    if not isinstance(reference, dict):
        raise EvidenceError("contract.reference_bundle is required")
    bundle_path = resolve_inside(contract_dir, reference.get("path", ""), "reference bundle")
    expected = require_sha256(reference.get("sha256"), "reference_bundle.sha256")
    if not bundle_path.is_file() or sha256_file(bundle_path) != expected:
        raise EvidenceError("reference bundle is missing or changed")
    bundle = load_json(bundle_path)
    source_sha = require_sha256(contract.get("source", {}).get("sha256"), "source.sha256")
    if bundle.get("source_sha256") != source_sha:
        raise EvidenceError("reference bundle is bound to a different H2D source")
    donor_id = bundle.get("donor_identity")
    if not isinstance(donor_id, str) or not donor_id:
        raise EvidenceError("reference bundle donor_identity is missing")
    donor_closure = bundle.get("donor_closure")
    if not isinstance(donor_closure, list) or not donor_closure:
        raise EvidenceError("reference bundle donor_closure is missing")
    for index, item in enumerate(donor_closure):
        if not isinstance(item, dict) or not isinstance(item.get("path"), str) or not is_sha256(item.get("sha256")) or not isinstance(item.get("size"), int):
            raise EvidenceError(f"reference donor_closure[{index}] is invalid")
        if Path(item["path"]).is_absolute() or ".." in Path(item["path"]).parts:
            raise EvidenceError(f"reference donor_closure[{index}] path is unsafe")
    if donor_id != f"sha256:{canonical_json_sha256(donor_closure)}":
        raise EvidenceError("reference donor_identity does not hash the transitive donor closure")
    expected_keys = matrix_keys(contract)
    if sorted(bundle.get("matrix_keys") or []) != expected_keys:
        raise EvidenceError("reference bundle does not cover the complete contract matrix")
    if bundle.get("result") != "pass" or bundle.get("coverage_complete") is not True:
        raise EvidenceError("reference bundle is not final: incomplete or non-pass coverage")
    if bundle.get("visual", {}).get("donor_identity") != donor_id:
        raise EvidenceError("visual reference came from a different donor identity")
    profile_ids = {profile["id"] for profile in contract.get("browser_profiles") or []}
    environment_by_profile = bundle.get("environment_by_profile")
    if not isinstance(environment_by_profile, dict) or set(environment_by_profile) != profile_ids or any(not is_sha256(value) for value in environment_by_profile.values()):
        raise EvidenceError("reference rendering environment is not pinned separately for every profile")
    classification = bundle.get("classification")
    if not isinstance(classification, dict) or classification.get("result") != "pass" or classification.get("coverage_complete") is not True:
        raise EvidenceError("reference donor classification is missing or incomplete")
    classifier = Path(__file__).resolve().parent / "classify_reference.js"
    if classification.get("generator_sha256") != sha256_file(classifier):
        raise EvidenceError("reference donor classification was not generated by the bundled classifier")
    if classification.get("source_sha256") != source_sha or classification.get("donor_identity") != donor_id or sorted(classification.get("matrix_keys") or []) != expected_keys:
        raise EvidenceError("reference donor classification is bound to different source, donor, or matrix")
    if classification.get("donor_closure") != donor_closure:
        raise EvidenceError("reference donor classification closure differs from the bundle closure")
    breakpoints = classification.get("breakpoints")
    if not isinstance(breakpoints, list) or any(not isinstance(value, int) or isinstance(value, bool) or value < 1 for value in breakpoints) or breakpoints != sorted(set(breakpoints)):
        raise EvidenceError("reference donor classification breakpoints are invalid")
    dynamic_required = bool(classification.get("behavior_required") or classification.get("liveness_required"))
    if dynamic_required:
        if bundle.get("dynamic", {}).get("donor_identity") != donor_id:
            raise EvidenceError("dynamic reference came from a different donor identity")
    artifact_entries = bundle.get("artifacts") or []
    verify_hashed_files(bundle_path.parent, artifact_entries, "reference artifacts")
    dynamic_manifests = [item for item in artifact_entries if isinstance(item, dict) and item.get("kind") == "dynamic-manifest"]
    if dynamic_required:
        if len(dynamic_manifests) != 1:
            raise EvidenceError("dynamic reference requires exactly one hashed dynamic manifest")
        manifest_path = resolve_inside(bundle_path.parent, dynamic_manifests[0].get("path", ""), "dynamic manifest")
        validate_dynamic_manifest(load_json(manifest_path), classification, expected_keys, manifest_path.parent)
    elif dynamic_manifests:
        raise EvidenceError("static reference bundle may not contain a dynamic manifest")
    return bundle


def verify_contract(contract_path: Path, evidence_dir: Path | None = None) -> dict[str, Any]:
    contract_path = contract_path.resolve()
    contract = load_json(contract_path)
    if contract.get("schema_version") != "2.0":
        raise EvidenceError("transfer contract schema_version must be 2.0")
    source = contract.get("source") or {}
    source_path = resolve_inside(contract_path.parent, source.get("path", ""), "H2D source")
    if not source_path.is_file() or sha256_file(source_path) != require_sha256(source.get("sha256"), "source.sha256"):
        raise EvidenceError("pinned H2D source is missing or changed")
    decoder = contract.get("decoder") or {}
    decoder_value = decoder.get("path", "")
    if isinstance(decoder_value, str) and decoder_value.startswith("builtin:"):
        decoder_path = Path(__file__).resolve().parent / Path(decoder_value.removeprefix("builtin:")).name
    else:
        decoder_path = resolve_inside(contract_path.parent, decoder_value, "decoder")
    if not decoder_path.is_file() or sha256_file(decoder_path) != require_sha256(decoder.get("sha256"), "decoder.sha256"):
        raise EvidenceError("decoder identity changed")
    verified_decoded = verify_hashed_files(contract_path.parent, contract.get("decoded_artifacts") or [], "decoded artifacts")
    sidecar_entries = contract.get("sidecars") or []
    verified_sidecars = verify_hashed_files(contract_path.parent, sidecar_entries, "sidecars")
    sidecar_by_role: dict[str, Path] = {}
    for index, entry in enumerate(sidecar_entries):
        role = entry.get("role") if isinstance(entry, dict) else None
        if not isinstance(role, str) or not role or role in sidecar_by_role:
            raise EvidenceError(f"sidecars[{index}].role must be a unique non-empty string")
        sidecar_by_role[role] = resolve_inside(contract_path.parent, entry["path"], f"sidecar role {role}")
    missing_system_sidecars = {"component_map", "token_map"} - set(sidecar_by_role)
    if missing_system_sidecars:
        raise EvidenceError(f"system-transfer sidecars are missing: {sorted(missing_system_sidecars)}")
    verify_approval_records(contract.get("approvals") or [])
    matrix_keys(contract)
    expected_reports = contract.get("expected_reports")
    if not isinstance(expected_reports, list) or not expected_reports or len(expected_reports) != len(set(expected_reports)):
        raise EvidenceError("expected_reports must be a non-empty unique list")
    required_matrix_reports = {
        "reports/matrix_coverage.json",
        "reports/diff_summary.json",
        "reports/node_validation.json",
        "reports/font_manifest.json",
        "reports/review.md",
        "reports/design_system.json",
        "reports/component_reuse.json",
        "reports/token_reuse.json",
    }
    classification = contract.get("classification") or {}
    if classification.get("behavior_required"):
        required_matrix_reports.add("reports/behavior_validation.json")
    if classification.get("liveness_required"):
        required_matrix_reports.add("reports/liveness_validation.json")
    if not required_matrix_reports.issubset(set(expected_reports)):
        raise EvidenceError(f"expected_reports misses matrix-bearing gates: {sorted(required_matrix_reports - set(expected_reports))}")
    reports_root = contract_path.parents[1] / "reports"
    for value in expected_reports:
        if not isinstance(value, str) or not value.startswith("reports/") or value in {"reports/current_evidence.json", "reports/validation_run.json"}:
            raise EvidenceError(f"unsafe or reserved expected report path: {value!r}")
        resolve_inside(reports_root, Path(value).relative_to("reports"), "expected report")
    reference = verify_reference_bundle(contract, contract_path.parent)
    if contract.get("classification") != reference.get("classification"):
        raise EvidenceError("contract classification differs from the generated reference classification")
    breakpoint_source = contract.get("breakpoint_source")
    expected_breakpoints = sorted(reference.get("classification", {}).get("breakpoints") or [])
    if not isinstance(breakpoint_source, dict) or breakpoint_source.get("kind") != "generated-reference-classification":
        raise EvidenceError("contract breakpoint_source must come from the generated reference classification")
    if breakpoint_source.get("donor_identity") != reference.get("donor_identity") or sorted(breakpoint_source.get("breakpoints") or []) != expected_breakpoints:
        raise EvidenceError("contract breakpoint source differs from the pinned donor classification")
    workspace_value = contract.get("workspace_root")
    workspace = Path(workspace_value) if isinstance(workspace_value, str) and workspace_value else contract_path.parent
    if not workspace.is_absolute():
        workspace = (contract_path.parent / workspace).resolve()
    if not workspace.is_dir():
        raise EvidenceError(f"contract workspace_root is missing: {workspace}")
    candidate = contract.get("candidate") or {}
    root = resolve_inside(workspace, candidate.get("project_root", ""), "candidate project root")
    includes = candidate.get("include") or []
    if not isinstance(includes, list) or any(not isinstance(item, str) for item in includes):
        raise EvidenceError("candidate.include must be an explicit list of files/directories")
    closure = candidate_closure(root, includes, evidence_dir)
    if closure["digest"] != candidate.get("closure_sha256"):
        raise EvidenceError("candidate file closure is stale")
    reject_candidate_reference_code_overlap(closure, reference)
    if candidate.get("mode") == "managed-url":
        lifecycle = candidate.get("lifecycle")
        required_lifecycle = {"build", "start", "cwd", "health_url", "build_identity_url", "build_identity_sha256", "toolchain", "public_env_sha256"}
        if not isinstance(lifecycle, dict) or required_lifecycle - set(lifecycle):
            raise EvidenceError(f"managed-url lifecycle misses {sorted(required_lifecycle - set(lifecycle or {}))}")
        require_local_candidate_urls(lifecycle.get("health_url"), lifecycle.get("build_identity_url"))
        require_sha256(lifecycle.get("build_identity_sha256"), "candidate.lifecycle.build_identity_sha256")
        if not isinstance(lifecycle.get("toolchain"), dict) or not lifecycle["toolchain"]:
            raise EvidenceError("managed-url lifecycle.toolchain must pin runtime versions")
        if not isinstance(lifecycle.get("public_env_sha256"), dict):
            raise EvidenceError("managed-url lifecycle.public_env_sha256 must be an object")
        for key, digest in lifecycle["public_env_sha256"].items():
            if not isinstance(key, str) or not key or any(token in key.upper() for token in ("SECRET", "TOKEN", "PASSWORD", "PRIVATE", "CREDENTIAL")):
                raise EvidenceError("only non-secret public build environment names may be pinned")
            require_sha256(digest, f"candidate.lifecycle.public_env_sha256.{key}")
    candidate_files = {(root / entry["path"]).resolve() for entry in closure["files"]}
    sidecar_files = {(contract_path.parent / rel).resolve() for rel in verified_sidecars}
    decoded_files = {(contract_path.parent / rel).resolve() for rel in verified_decoded}
    bundled_system_generators = {
        (Path(__file__).resolve().parent / name).resolve()
        for name in ("extract_design_system.py", "validate_component_reuse.js", "validate_token_reuse.py")
    }
    expected_report_files = {
        (contract_path.parents[1] / value).resolve()
        for value in expected_reports
        if isinstance(value, str) and value.startswith("reports/")
    }
    command_specs: list[tuple[list[str], Path]] = [(command, root) for command in (contract.get("current_commands") or [])]
    lifecycle = candidate.get("lifecycle") or {}
    lifecycle_cwd = resolve_inside(root, lifecycle.get("cwd") or ".", "candidate lifecycle cwd")
    for key in ("build", "start", "teardown"):
        if lifecycle.get(key):
            command_specs.append((lifecycle[key], lifecycle_cwd))

    actual_executables = command_executable_records_for_specs(command_specs)
    pinned_executables = contract.get("command_executables")
    if not isinstance(pinned_executables, list) or pinned_executables != actual_executables:
        raise EvidenceError("command executable identities are missing, stale, or incomplete")
    known_input_suffixes = {".py", ".js", ".mjs", ".cjs", ".sh", ".ps1", ".cmd", ".bat", ".json", ".yaml", ".yml", ".toml", ".html", ".css", ".svg", ".txt"}
    for command, execution_cwd in command_specs:
        for index, value in enumerate(command[1:], start=1):
            if not isinstance(value, str):
                continue
            if (index > 0 and command[index - 1] == "--out") or value.startswith("--out="):
                continue
            raw_value = value.split("=", 1)[1] if value.startswith("--") and "=" in value else value
            if raw_value.startswith(("http://", "https://")):
                continue
            path = Path(raw_value)
            path = path.resolve() if path.is_absolute() else (execution_cwd / path).resolve()
            if not path.exists() and path not in expected_report_files and Path(raw_value).suffix.lower() in known_input_suffixes:
                raise EvidenceError(f"pinned command input is missing: {path}")
            if path.is_file() and path not in candidate_files and path not in sidecar_files and path not in decoded_files and path not in bundled_system_generators and path not in expected_report_files:
                raise EvidenceError(f"command input is outside candidate closure/hashed sidecars: {path}")
    return {"contract": contract, "contract_path": contract_path, "candidate_root": root, "closure": closure, "reference": reference}


def verify_current_evidence(evidence_path: Path) -> dict[str, Any]:
    evidence_path = evidence_path.resolve()
    evidence = load_json(evidence_path)
    if evidence.get("schema_version") != "2.0" or evidence.get("result") != "pass":
        raise EvidenceError("current evidence is missing a schema 2.0 pass verdict")
    runner_path = Path(__file__).resolve().parent / "run_current_gates.py"
    if evidence.get("runner_sha256") != sha256_file(runner_path):
        raise EvidenceError("current evidence was not produced by this runner version")
    output_root = evidence_path.parents[1]
    contract_path = resolve_inside(output_root, evidence.get("contract_path", ""), "current contract")
    if sha256_file(contract_path) != require_sha256(evidence.get("contract_sha256"), "current contract_sha256"):
        raise EvidenceError("current evidence contract changed")
    verified = verify_contract(contract_path, output_root)
    if evidence.get("candidate_digest_before") != verified["closure"]["digest"]:
        raise EvidenceError("current evidence was generated for a different candidate")
    if evidence.get("candidate_digest_after") != verified["closure"]["digest"]:
        raise EvidenceError("candidate changed while evidence was generated")
    expected = matrix_keys(verified["contract"])
    if sorted(evidence.get("matrix_completed") or []) != expected:
        raise EvidenceError("current evidence matrix is incomplete")
    contract = verified["contract"]
    source_sha = contract["source"]["sha256"]
    expected_sources = {
        "source/input.original": source_sha,
        "source/input.h2d": source_sha,
    }
    for entry in contract.get("decoded_artifacts") or []:
        path = f"source/{Path(entry['path']).name}"
        if path in expected_sources:
            raise EvidenceError(f"current source artifact name is ambiguous: {path}")
        expected_sources[path] = entry["sha256"]
    checksum_path = resolve_inside(output_root, "source/input.sha256", "current source checksum")
    if not checksum_path.is_file() or checksum_path.read_text(encoding="utf-8") != f"{source_sha}  input.original\n":
        raise EvidenceError("current evidence source checksum is missing or not bound to the contract")
    expected_sources["source/input.sha256"] = sha256_file(checksum_path)
    source_entries = evidence.get("source_artifacts") or []
    actual_sources = {
        entry.get("path"): entry.get("sha256")
        for entry in source_entries
        if isinstance(entry, dict) and isinstance(entry.get("path"), str)
    }
    if actual_sources != expected_sources or len(source_entries) != len(expected_sources):
        raise EvidenceError("current evidence source artifacts are missing, stale, or incomplete")
    verify_hashed_files(output_root, source_entries, "current source artifacts")
    report_entries = evidence.get("reports") or []
    actual_report_paths = [entry.get("path") for entry in report_entries if isinstance(entry, dict)]
    expected_report_paths = sorted(contract.get("expected_reports") or [])
    if sorted(actual_report_paths) != expected_report_paths or len(actual_report_paths) != len(expected_report_paths):
        raise EvidenceError("current evidence reports are missing, stale, or incomplete")
    verify_hashed_files(output_root, report_entries, "current reports")
    return {**verified, "evidence": evidence}
