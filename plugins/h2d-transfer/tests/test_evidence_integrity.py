from __future__ import annotations

import json
import os
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
    sha256_file,
    verify_approval_records,
    verify_contract,
    verify_current_evidence,
    require_local_candidate_urls,
)


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
        bundle = {
            "schema_version": "2.0", "result": "pass", "coverage_complete": True,
            "source_sha256": source_sha, "donor_identity": "sha256:donor",
            "matrix_keys": ["390x844@mobile"],
            "visual": {"donor_identity": "sha256:donor"},
            "dynamic": {"donor_identity": None},
            "artifacts": [{"path": "reference.png", "sha256": sha256_file(reference_dir / "reference.png")}],
            "classification": {"behavior_required": False, "liveness_required": False, "coverage_complete": True},
        }
        bundle_path = reference_dir / "reference_bundle.json"
        self.write_json(bundle_path, bundle)
        report = reports / "node_validation.json"
        self.write_json(report, {"result": "pass", "matrix_keys": ["390x844@mobile"]})
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
            "reference_bundle": {"path": "reference/reference_bundle.json", "sha256": sha256_file(bundle_path)},
            "sidecars": [], "approvals": [], "current_commands": [["true"]], "expected_reports": ["reports/node_validation.json"],
        }
        contract_path = contract_dir / "transfer_contract.json"
        self.write_json(contract_path, contract)
        evidence = {
            "schema_version": "2.0", "result": "pass",
            "contract_path": "contract/transfer_contract.json", "contract_sha256": sha256_file(contract_path),
            "runner_sha256": sha256_file(SKILL / "scripts" / "run_current_gates.py"), "candidate_digest_before": closure["digest"], "candidate_digest_after": closure["digest"],
            "matrix_completed": ["390x844@mobile"],
            "reports": [{"path": "reports/node_validation.json", "sha256": sha256_file(report)}],
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
            self.write_json(contract_path, contract)
            with self.assertRaisesRegex(EvidenceError, "outside candidate closure/hashed sidecars"):
                verify_contract(contract_path, evidence.parents[1])

    def test_managed_candidate_urls_are_loopback_and_same_origin(self) -> None:
        require_local_candidate_urls("http://127.0.0.1:5005/health", "http://127.0.0.1:5005/build-id")
        with self.assertRaisesRegex(EvidenceError, "loopback host"):
            require_local_candidate_urls("http://example.com/health", "http://example.com/build-id")
        with self.assertRaisesRegex(EvidenceError, "same local origin"):
            require_local_candidate_urls("http://127.0.0.1:5005/health", "http://127.0.0.1:5006/build-id")


if __name__ == "__main__":
    unittest.main()
