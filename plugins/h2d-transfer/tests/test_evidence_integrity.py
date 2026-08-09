from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SKILL = Path(__file__).resolve().parents[1] / "skills" / "h2d-pixel-perfect-transfer"
sys.path.insert(0, str(SKILL / "scripts"))

from evidence_integrity import (  # noqa: E402
    EvidenceError,
    candidate_closure,
    canonical_json_sha256,
    command_executable_records,
    sha256_file,
    verify_approval_records,
    verify_contract,
    verify_current_evidence,
    require_local_candidate_urls,
    validate_dynamic_manifest,
)
from create_transfer_contract import responsive_matrix  # noqa: E402
from freeze_reference_bundle import resolve_artifact_path  # noqa: E402


class EvidenceIntegrityTests(unittest.TestCase):
    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, indent=2), encoding="utf-8")

    def fixture(self, root: Path) -> tuple[Path, Path]:
        output = root / "transfer-output"
        contract_dir = output / "contract"
        reports = output / "reports"
        candidate = root / "candidate"
        candidate.mkdir(parents=True)
        (candidate / "index.html").write_text("<h1>Candidate meaning</h1>", encoding="utf-8")
        source_dir = contract_dir / "fresh_decode" / "source"
        source_dir.mkdir(parents=True)
        (source_dir / "input.h2d").write_text('{"width":390,"frame":{"type":"div","children":[]}}', encoding="utf-8")
        (source_dir / "h2d_decoded.json").write_text('{"width":390,"frame":{"type":"div","children":[]}}', encoding="utf-8")
        (source_dir / "h2d_tree_index.json").write_text("[]", encoding="utf-8")
        reference_dir = contract_dir / "reference"
        reference_dir.mkdir(parents=True)
        (reference_dir / "reference.png").write_bytes(b"png-evidence")
        source_sha = sha256_file(source_dir / "input.h2d")
        donor_closure = [{"path": "donor.html", "sha256": "0" * 64, "size": 0}]
        donor_identity = f"sha256:{canonical_json_sha256(donor_closure)}"
        classification = {"result": "pass", "generator_sha256": sha256_file(SKILL / "scripts" / "classify_reference.js"), "behavior_required": False, "liveness_required": False, "coverage_complete": True, "source_sha256": source_sha, "donor_identity": donor_identity, "donor_closure": donor_closure, "matrix_keys": ["390x844@mobile"], "breakpoints": []}
        bundle = {
            "schema_version": "2.0", "result": "pass", "coverage_complete": True,
            "source_sha256": source_sha, "donor_identity": donor_identity, "donor_closure": donor_closure,
            "environment_by_profile": {"mobile": "0" * 64},
            "matrix_keys": ["390x844@mobile"],
            "visual": {"donor_identity": donor_identity},
            "dynamic": {"donor_identity": None},
            "artifacts": [{"path": "reference.png", "sha256": sha256_file(reference_dir / "reference.png")}],
            "classification": classification,
        }
        bundle_path = reference_dir / "reference_bundle.json"
        self.write_json(bundle_path, bundle)
        report_names = ["diff_summary.json", "node_validation.json", "font_manifest.json", "matrix_coverage.json"]
        for name in report_names:
            self.write_json(reports / name, {"result": "pass", "matrix_keys": ["390x844@mobile"]})
        (reports / "review.md").write_text("Current fixture review", encoding="utf-8")
        output_source = output / "source"
        output_source.mkdir(parents=True)
        (output_source / "input.original").write_bytes((source_dir / "input.h2d").read_bytes())
        (output_source / "input.h2d").write_bytes((source_dir / "input.h2d").read_bytes())
        for name in ("h2d_decoded.json", "h2d_tree_index.json"):
            (output_source / name).write_bytes((source_dir / name).read_bytes())
        (output_source / "input.sha256").write_text(f"{source_sha}  input.original\n", encoding="utf-8")
        closure = candidate_closure(candidate, ["index.html"], output)
        decoder = SKILL / "scripts" / "h2d_unpack_source.py"
        contract = {
            "schema_version": "2.0", "workspace_root": str(root),
            "source": {"path": "fresh_decode/source/input.h2d", "sha256": source_sha},
            "decoder": {"path": "builtin:scripts/h2d_unpack_source.py", "sha256": sha256_file(decoder)},
            "decoded_artifacts": [
                {"path": "fresh_decode/source/h2d_decoded.json", "sha256": sha256_file(source_dir / "h2d_decoded.json")},
                {"path": "fresh_decode/source/h2d_tree_index.json", "sha256": sha256_file(source_dir / "h2d_tree_index.json")},
            ],
            "responsive_matrix": [{"width": 390, "height": 844, "kind": "decoded"}],
            "browser_profiles": [{"id": "mobile", "headless": True, "device_scale_factor": 1, "is_mobile": True, "has_touch": True, "locale": "en-US", "timezone": "UTC", "reduced_motion": "reduce"}],
            "candidate": {"mode": "entry", "project_root": "candidate", "include": ["index.html"], "closure_sha256": closure["digest"]},
            "classification": bundle["classification"],
            "breakpoint_source": {"kind": "generated-reference-classification", "donor_identity": donor_identity, "breakpoints": []},
            "reference_bundle": {"path": "reference/reference_bundle.json", "sha256": sha256_file(bundle_path)},
            "sidecars": [], "approvals": [], "current_commands": [[sys.executable, "-c", "pass"]],
            "command_executables": command_executable_records([[sys.executable, "-c", "pass"]], candidate),
            "expected_reports": ["reports/diff_summary.json", "reports/node_validation.json", "reports/font_manifest.json", "reports/matrix_coverage.json", "reports/review.md"],
        }
        contract_path = contract_dir / "transfer_contract.json"
        self.write_json(contract_path, contract)
        evidence = {
            "schema_version": "2.0", "result": "pass",
            "contract_path": "contract/transfer_contract.json", "contract_sha256": sha256_file(contract_path),
            "runner_sha256": sha256_file(SKILL / "scripts" / "run_current_gates.py"), "candidate_digest_before": closure["digest"], "candidate_digest_after": closure["digest"],
            "matrix_completed": ["390x844@mobile"],
            "source_artifacts": [
                {"path": f"source/{name}", "sha256": sha256_file(output_source / name)}
                for name in ("input.original", "input.h2d", "input.sha256", "h2d_decoded.json", "h2d_tree_index.json")
            ],
            "reports": [
                {"path": f"reports/{name}", "sha256": sha256_file(reports / name)}
                for name in report_names + ["review.md"]
            ],
        }
        evidence_path = reports / "current_evidence.json"
        self.write_json(evidence_path, evidence)
        return evidence_path, candidate / "index.html"

    def test_current_evidence_rejects_candidate_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, candidate = self.fixture(Path(temp))
            verify_current_evidence(evidence)
            candidate.write_text("<h1>Changed after evidence</h1>", encoding="utf-8")
            with self.assertRaisesRegex(EvidenceError, "closure is stale"):
                verify_current_evidence(evidence)

    def test_current_evidence_rejects_missing_matrix_pair(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, _ = self.fixture(Path(temp))
            data = json.loads(evidence.read_text(encoding="utf-8"))
            data["matrix_completed"] = []
            self.write_json(evidence, data)
            with self.assertRaisesRegex(EvidenceError, "matrix is incomplete"):
                verify_current_evidence(evidence)

    def test_current_evidence_rejects_reference_artifact_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, _ = self.fixture(Path(temp))
            artifact = evidence.parents[1] / "contract" / "reference" / "reference.png"
            artifact.write_bytes(b"mutated")
            with self.assertRaisesRegex(EvidenceError, "reference artifacts.*changed"):
                verify_current_evidence(evidence)

    def test_current_evidence_rejects_output_source_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, _ = self.fixture(Path(temp))
            source = evidence.parents[1] / "source" / "h2d_tree_index.json"
            source.write_text('[{"stale":true}]', encoding="utf-8")
            with self.assertRaisesRegex(EvidenceError, "current source artifacts.*changed"):
                verify_current_evidence(evidence)

    def test_current_evidence_rejects_omitted_expected_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, _ = self.fixture(Path(temp))
            data = json.loads(evidence.read_text(encoding="utf-8"))
            data["reports"] = [row for row in data["reports"] if row["path"] != "reports/review.md"]
            self.write_json(evidence, data)
            with self.assertRaisesRegex(EvidenceError, "reports are missing"):
                verify_current_evidence(evidence)

    def test_contract_rejects_expected_report_escape(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, _ = self.fixture(Path(temp))
            contract_path = evidence.parents[1] / "contract" / "transfer_contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["expected_reports"].append("reports/../source/input.h2d")
            self.write_json(contract_path, contract)
            with self.assertRaisesRegex(EvidenceError, "expected report escapes"):
                verify_contract(contract_path, evidence.parents[1])

    def test_contract_classification_must_match_generated_bundle_exactly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, _ = self.fixture(Path(temp))
            contract_path = evidence.parents[1] / "contract" / "transfer_contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["classification"]["behavior_required"] = True
            contract["expected_reports"].append("reports/behavior_validation.json")
            self.write_json(contract_path, contract)
            with self.assertRaisesRegex(EvidenceError, "classification differs"):
                verify_contract(contract_path, evidence.parents[1])

    def test_dynamic_manifest_rejects_empty_required_artifacts(self) -> None:
        classification = {"donor_identity":"sha256:" + "0" * 64,"behavior_required":True,"liveness_required":False}
        dynamic = {
            "result":"pass", "coverage_complete":True,
            "generator_sha256":sha256_file(SKILL / "scripts" / "finalize_dynamic_reference.py"),
            "classification_sha256":canonical_json_sha256(classification),
            "donor_identity":classification["donor_identity"], "matrix_keys":["390x844@mobile"],
            "required_roles":["behavior-inventory","behavior-state-screenshot","behavior-state-targets","event-listener-inventory","interaction-matrix","original-behavior-traces"],
            "artifacts":[],
        }
        with self.assertRaisesRegex(EvidenceError, "has no artifacts"):
            validate_dynamic_manifest(dynamic, classification, ["390x844@mobile"])

    def test_command_executable_resolution_is_bound_to_lifecycle_cwd(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            lifecycle_cwd = Path(temp) / "candidate" / "app"
            lifecycle_cwd.mkdir(parents=True)
            executable = lifecycle_cwd / "local-runner"
            executable.write_text("runner", encoding="utf-8")
            records = command_executable_records([["./local-runner"]], lifecycle_cwd)
            self.assertEqual(records[0]["cwd"], str(lifecycle_cwd.resolve()))
            self.assertEqual(records[0]["resolved_path"], str(executable.resolve()))

    def test_self_authored_approval_is_rejected(self) -> None:
        with self.assertRaisesRegex(EvidenceError, "trusted verification"):
            verify_approval_records([{"approved": True, "scope": ["hero.copy"]}])
        with self.assertRaisesRegex(EvidenceError, "untrusted verification"):
            verify_approval_records([{"approved": True, "scope": ["hero.copy"], "verification": {"kind": "local-hash", "verified": True, "payload_sha256": "0" * 64}}])

    def test_trusted_owner_event_requires_exact_scope(self) -> None:
        record = {"approved": True, "scope": ["hero.copy"]}
        from evidence_integrity import canonical_json_sha256
        payload_sha256 = canonical_json_sha256(record)
        record["verification"] = {"kind": "trusted-owner-event", "verified": True, "payload_sha256": payload_sha256, "provider": "owner-controlled", "event_id": "evt-1", "actor_id": "owner-1", "verified_by": "read-only-connector"}
        receipt = {"owner-controlled:evt-1:owner-1": payload_sha256}
        with patch.dict(os.environ, {"H2D_TRUSTED_OWNER_EVENTS_JSON": json.dumps(receipt)}, clear=False):
            verify_approval_records([record])
        record["scope"] = []
        with self.assertRaisesRegex(EvidenceError, "exact approved fields"):
            verify_approval_records([record])

    def test_owner_signature_uses_external_trust_store(self) -> None:
        import base64
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
        from evidence_integrity import canonical_json, canonical_json_sha256

        record = {"approved": True, "scope": ["hero.copy"], "reason": "Owner keeps product meaning"}
        private_key = Ed25519PrivateKey.generate()
        public_key = private_key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        signature = private_key.sign(canonical_json(record))
        record["verification"] = {
            "kind": "owner-signature", "verified": True, "algorithm": "ed25519", "key_id": "art-owner-1",
            "payload_sha256": canonical_json_sha256(record), "signature": base64.b64encode(signature).decode("ascii"),
            "verified_by": "evidence_integrity.py",
        }
        with self.assertRaisesRegex(EvidenceError, "external owner trust store"):
            verify_approval_records([record])
        trust = {"art-owner-1": base64.b64encode(public_key).decode("ascii")}
        with patch.dict(os.environ, {"H2D_OWNER_PUBLIC_KEYS_JSON": json.dumps(trust)}, clear=False):
            verify_approval_records([record])

    def test_contract_rejects_unhashed_command_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            evidence, candidate = self.fixture(Path(temp))
            contract_path = evidence.parents[1] / "contract" / "transfer_contract.json"
            rogue = candidate.parent / "rogue.py"
            rogue.write_text("print('not covered')\n", encoding="utf-8")
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            contract["current_commands"] = [[sys.executable, str(rogue)]]
            contract["command_executables"] = command_executable_records(contract["current_commands"], candidate.parent)
            self.write_json(contract_path, contract)
            with self.assertRaisesRegex(EvidenceError, "outside candidate closure/hashed sidecars"):
                verify_contract(contract_path, evidence.parents[1])

    def test_contract_pins_direct_executable_and_all_existing_data_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            evidence, candidate = self.fixture(root)
            contract_path = evidence.parents[1] / "contract" / "transfer_contract.json"
            contract = json.loads(contract_path.read_text(encoding="utf-8"))
            wrapper = root / "external-gate-wrapper"
            wrapper.write_text("version one\n", encoding="utf-8")
            contract["current_commands"] = [[str(wrapper)]]
            contract["command_executables"] = command_executable_records(contract["current_commands"], candidate.parent)
            self.write_json(contract_path, contract)
            verify_contract(contract_path, evidence.parents[1])
            wrapper.write_text("version two\n", encoding="utf-8")
            with self.assertRaisesRegex(EvidenceError, "executable identities"):
                verify_contract(contract_path, evidence.parents[1])

            selector_map = candidate.parent / "external-selectors.json"
            selector_map.write_text("{}", encoding="utf-8")
            contract["current_commands"] = [[sys.executable, "-c", "pass", str(selector_map)]]
            contract["command_executables"] = command_executable_records(contract["current_commands"], candidate.parent)
            self.write_json(contract_path, contract)
            with self.assertRaisesRegex(EvidenceError, "outside candidate closure/hashed sidecars"):
                verify_contract(contract_path, evidence.parents[1])

    def test_managed_candidate_urls_are_loopback_and_same_origin(self) -> None:
        require_local_candidate_urls("http://127.0.0.1:5005/health", "http://127.0.0.1:5005/build-id")
        with self.assertRaisesRegex(EvidenceError, "loopback host"):
            require_local_candidate_urls("http://example.com/health", "http://example.com/build-id")
        with self.assertRaisesRegex(EvidenceError, "same local origin"):
            require_local_candidate_urls("http://127.0.0.1:5005/health", "http://127.0.0.1:5006/build-id")

    def test_sparse_responsive_contract_requires_interval_breakpoints(self) -> None:
        with self.assertRaisesRegex(EvidenceError, "complete generated donor breakpoints"):
            responsive_matrix([390, 1440], {"390": 844, "1440": 900}, [])
        rows = responsive_matrix([390, 1440], {"390": 844, "1440": 900}, [768])
        self.assertTrue({767, 768, 769, 915}.issubset({row["width"] for row in rows}))

    def test_reference_matrix_is_derived_from_generated_breakpoints(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); h2d = root / "source.h2d"; heights = root / "heights.json"; classification = root / "classification.json"; out = root / "matrix.json"
            nodes = [{"type":"TEXT","tag":"span","x":10,"y":20 + index * 30,"width":200,"height":24,"text":f"Text {index}","children":[]} for index in range(12)]
            h2d.write_text(json.dumps({"width":390,"height":844,"frame":{"type":"FRAME","tag":"div","x":0,"y":0,"width":390,"height":844,"children":nodes}}), encoding="utf-8")
            heights.write_text('{"390":844}', encoding="utf-8")
            self.write_json(classification, {
                "result":"pass", "coverage_complete":True,
                "generator_sha256":sha256_file(SKILL / "scripts" / "classify_reference.js"),
                "source_sha256":sha256_file(h2d), "breakpoints":[768],
            })
            completed = subprocess.run([sys.executable, str(SKILL / "scripts" / "derive_reference_matrix.py"), "--h2d", str(h2d), "--height-map", str(heights), "--classification", str(classification), "--out", str(out)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual({row["width"] for row in json.loads(out.read_text(encoding="utf-8"))}, {390, 767, 768, 769})

    def test_dynamic_artifact_destination_cannot_escape_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(EvidenceError, "escapes"):
                resolve_artifact_path(root / "dynamic", "../../victim.txt", "dynamic destination artifact")


if __name__ == "__main__":
    unittest.main()
