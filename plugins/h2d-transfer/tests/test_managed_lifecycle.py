from __future__ import annotations

import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "h2d-pixel-perfect-transfer"
sys.path.insert(0, str(SKILL / "scripts"))
from evidence_integrity import candidate_closure, canonical_json_sha256, command_executable_records, sha256_file  # noqa: E402


class ManagedLifecycleTests(unittest.TestCase):
    def write_json(self, path: Path, value: object) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_managed_url_proves_served_build_and_rejects_stale_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "output"
            contract_dir = output / "contract"
            candidate = root / "candidate"
            candidate.mkdir(parents=True)
            (candidate / "index.html").write_text("<h1>current candidate source</h1>", encoding="utf-8")

            source = contract_dir / "fresh_decode" / "source"
            source.mkdir(parents=True)
            for name, value in {"input.h2d": "{}", "h2d_decoded.json": "{}", "h2d_tree_index.json": "[]"}.items():
                (source / name).write_text(value, encoding="utf-8")
            source_sha = sha256_file(source / "input.h2d")
            reference = contract_dir / "reference"
            reference.mkdir(parents=True)
            (reference / "reference.png").write_bytes(b"reference")
            donor_closure = [{"path": "donor.html", "sha256": "0" * 64, "size": 0}]
            donor_identity = f"sha256:{canonical_json_sha256(donor_closure)}"
            classification = {"result": "pass", "generator_sha256": sha256_file(SKILL / "scripts" / "classify_reference.js"), "behavior_required": False, "liveness_required": False, "coverage_complete": True, "source_sha256": source_sha, "donor_identity": donor_identity, "matrix_keys": ["390x844@headless"]}
            bundle = {
                "schema_version": "2.0", "result": "pass", "coverage_complete": True,
                "source_sha256": source_sha, "donor_identity": donor_identity, "donor_closure": donor_closure,
                "environment_by_profile": {"headless": "0" * 64},
                "matrix_keys": ["390x844@headless"], "visual": {"donor_identity": donor_identity},
                "dynamic": {"donor_identity": None},
                "classification": classification,
                "artifacts": [{"path": "reference.png", "sha256": sha256_file(reference / "reference.png")}],
            }
            bundle_path = reference / "reference_bundle.json"
            self.write_json(bundle_path, bundle)

            closure = candidate_closure(candidate, ["index.html"], output)
            identity_data = {"schema_version": "2.0", "candidate_closure_sha256": closure["digest"], "source_sha256": source_sha}
            identity = json.dumps(identity_data, separators=(",", ":")).encode("utf-8")
            build = contract_dir / "build.py"
            build.write_text(textwrap.dedent(f"""
                from pathlib import Path
                out = Path('dist'); out.mkdir(exist_ok=True)
                (out / 'index.html').write_text('<h1>served current build</h1>', encoding='utf-8')
                (out / 'build-id.txt').write_bytes({identity!r})
            """), encoding="utf-8")
            reports = contract_dir / "reports.py"
            reports.write_text(textwrap.dedent("""
                import hashlib, json, os, shutil
                from pathlib import Path
                output = Path(os.environ['H2D_OUTPUT']); out = output / 'reports'; out.mkdir(parents=True, exist_ok=True)
                fresh = output / 'contract' / 'fresh_decode' / 'source'; source = output / 'source'; source.mkdir(parents=True, exist_ok=True)
                for src,dst in [('input.h2d','input.original'),('input.h2d','input.h2d'),('h2d_decoded.json','h2d_decoded.json'),('h2d_tree_index.json','h2d_tree_index.json')]: shutil.copyfile(fresh/src, source/dst)
                source_sha = hashlib.sha256((source / 'input.original').read_bytes()).hexdigest(); (source / 'input.sha256').write_text(f'{source_sha}  input.original\\n', encoding='utf-8')
                keys = json.loads(os.environ['H2D_MATRIX_KEYS'])
                artifacts=[]
                for role,name in {'visual':'diff_summary.json','geometry':'node_validation.json','typography':'font_manifest.json'}.items():
                    path=out/name; path.write_text(json.dumps({'result':'pass','matrix_results':[{'matrix_key':key,'result':'pass'} for key in keys]}), encoding='utf-8')
                    artifacts.append({'role':role,'path':f'reports/{name}','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'matrix_completed':keys})
                (out / 'matrix_coverage.json').write_text(json.dumps({'result':'pass','matrix_completed':keys,'artifacts':artifacts}), encoding='utf-8')
                (out / 'review.md').write_text('Managed lifecycle current proof', encoding='utf-8')
            """), encoding="utf-8")
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            node_version = subprocess.run(["node", "--version"], check=True, capture_output=True, text=True).stdout.strip()
            lifecycle = {
                "build": [sys.executable, str(build)],
                "start": [sys.executable, "-m", "http.server", str(port), "--bind", "127.0.0.1", "--directory", "dist"],
                "cwd": ".", "health_url": f"http://127.0.0.1:{port}/index.html",
                "build_identity_url": f"http://127.0.0.1:{port}/build-id.txt",
                "build_identity_sha256": hashlib.sha256(identity).hexdigest(),
                "toolchain": {"node": node_version}, "public_env_sha256": {},
                "health_timeout_seconds": 5,
            }
            current_commands = [[sys.executable, str(reports)]]
            lifecycle_commands = [lifecycle["build"], lifecycle["start"]]
            contract = {
                "schema_version": "2.0", "workspace_root": str(root),
                "source": {"path": "fresh_decode/source/input.h2d", "sha256": source_sha},
                "decoder": {"path": "builtin:scripts/h2d_unpack_source.py", "sha256": sha256_file(SKILL / "scripts" / "h2d_unpack_source.py")},
                "decoded_artifacts": [
                    {"path": "fresh_decode/source/h2d_decoded.json", "sha256": sha256_file(source / "h2d_decoded.json")},
                    {"path": "fresh_decode/source/h2d_tree_index.json", "sha256": sha256_file(source / "h2d_tree_index.json")},
                ],
                "responsive_matrix": [{"width": 390, "height": 844, "kind": "decoded"}],
                "browser_profiles": [{"id": "headless", "headless": True, "device_scale_factor": 1, "is_mobile": False, "has_touch": False, "locale": "en-US", "timezone": "UTC", "reduced_motion": "reduce"}],
                "candidate": {"mode": "managed-url", "project_root": "candidate", "include": ["index.html"], "closure_sha256": closure["digest"], "lifecycle": lifecycle},
                "classification": bundle["classification"],
                "reference_bundle": {"path": "reference/reference_bundle.json", "sha256": sha256_file(bundle_path)},
                "sidecars": [
                    {"path": "build.py", "sha256": sha256_file(build)},
                    {"path": "reports.py", "sha256": sha256_file(reports)},
                ],
                "approvals": [], "current_commands": current_commands,
                "command_executables": command_executable_records(current_commands + lifecycle_commands),
                "expected_reports": ["reports/diff_summary.json", "reports/node_validation.json", "reports/font_manifest.json", "reports/matrix_coverage.json", "reports/review.md"],
            }
            contract_path = contract_dir / "transfer_contract.json"
            self.write_json(contract_path, contract)
            command = [sys.executable, str(SKILL / "scripts" / "run_current_gates.py"), "--contract", str(contract_path), "--output", str(output), "--no-final-legacy-gate"]
            current = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(current.returncode, 3, current.stdout + current.stderr)
            self.assertEqual(json.loads((output / "reports" / "current_evidence.json").read_text(encoding="utf-8"))["result"], "pass")

            contract["candidate"]["lifecycle"]["build_identity_sha256"] = "0" * 64
            self.write_json(contract_path, contract)
            (output / "reports" / "current_evidence.json").unlink()
            stale = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(stale.returncode, 2, stale.stdout + stale.stderr)
            self.assertIn("stale or different build identity", stale.stderr)
            self.assertFalse((output / "reports" / "current_evidence.json").exists())

            contract["candidate"]["lifecycle"]["build_identity_sha256"] = hashlib.sha256(identity).hexdigest()
            self.write_json(contract_path, contract)
            with socket.socket() as occupied_origin:
                occupied_origin.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                occupied_origin.bind(("127.0.0.1", port))
                occupied_origin.listen(1)
                occupied = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(occupied.returncode, 2, occupied.stdout + occupied.stderr)
            self.assertIn("origin is already occupied", occupied.stderr)


if __name__ == "__main__":
    unittest.main()
