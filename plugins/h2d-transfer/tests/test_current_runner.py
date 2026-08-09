from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "h2d-pixel-perfect-transfer"
sys.path.insert(0, str(SKILL / "scripts"))
from evidence_integrity import EvidenceError, candidate_closure, canonical_json_sha256, command_executable_records, sha256_file, verify_current_evidence  # noqa: E402
from run_all_gates import add_font_approval_check, check_output  # noqa: E402
from run_current_gates import verify_matrix_artifacts, verify_output_source  # noqa: E402


class CurrentRunnerTests(unittest.TestCase):
    def test_required_dynamic_inventories_reject_partial_or_manual_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            reports = output / "reports"
            reports.mkdir()
            behavior_files = [
                "behavior_inventory", "interaction_matrix", "event_listener_inventory",
                "behavior_state_targets", "behavior_implementation_map",
            ]
            for name in behavior_files:
                data = json.loads((SKILL / "templates" / f"{name}_template.json").read_text(encoding="utf-8"))
                data["result"] = "partial"
                (reports / f"{name}.json").write_text(json.dumps(data), encoding="utf-8")
            liveness = json.loads((SKILL / "templates" / "liveness_inventory_template.json").read_text(encoding="utf-8"))
            liveness["result"] = "partial"
            (reports / "liveness_inventory.json").write_text(json.dumps(liveness), encoding="utf-8")
            webgl = json.loads((SKILL / "templates" / "webgl_capture_report_template.json").read_text(encoding="utf-8"))
            webgl["result"] = "manual-review"
            (reports / "webgl_capture_report.json").write_text(json.dumps(webgl), encoding="utf-8")
            result = check_output(output, "true", "true")
            checks = {row["name"]: row["result"] for row in result["checks"]}
            for name in behavior_files + ["liveness_inventory", "webgl_capture_report"]:
                self.assertEqual(checks[f"{name}.json"], "fail")

    def test_output_source_must_match_contract_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)
            contract_dir = output / "contract"
            fresh = contract_dir / "fresh_decode" / "source"
            source = output / "source"
            fresh.mkdir(parents=True)
            source.mkdir()
            values = {"input.h2d": b"donor", "h2d_decoded.json": b"{}", "h2d_tree_index.json": b"[]"}
            for name, value in values.items():
                (fresh / name).write_bytes(value)
            source_sha = sha256_file(fresh / "input.h2d")
            for name in ("input.original", "input.h2d"):
                (source / name).write_bytes(values["input.h2d"])
            for name in ("h2d_decoded.json", "h2d_tree_index.json"):
                (source / name).write_bytes(values[name])
            (source / "input.sha256").write_text(f"{source_sha}  input.original\n", encoding="utf-8")
            contract = {
                "source": {"path": "fresh_decode/source/input.h2d", "sha256": source_sha},
                "decoded_artifacts": [
                    {"path": f"fresh_decode/source/{name}", "sha256": sha256_file(fresh / name)}
                    for name in ("h2d_decoded.json", "h2d_tree_index.json")
                ],
            }
            artifacts = verify_output_source(output, contract_dir / "transfer_contract.json", contract)
            self.assertEqual(len(artifacts), 5)
            (source / "h2d_decoded.json").write_text('{"stale":true}', encoding="utf-8")
            with self.assertRaisesRegex(EvidenceError, "differs from the contract"):
                verify_output_source(output, contract_dir / "transfer_contract.json", contract)

    def test_self_reported_matrix_list_without_gate_artifacts_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(EvidenceError, "individual gate artifacts"):
                verify_matrix_artifacts(Path(temp), {"result": "pass", "matrix_completed": ["390x844@headless"]}, {}, ["390x844@headless"])

    def test_matrix_artifact_does_not_count_not_tested_as_coverage(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp); reports = output / "reports"; reports.mkdir()
            matrix_key = "390x844@headless"; artifacts = []
            for role, name, result in (("visual","diff_summary.json","not-tested"),("geometry","node_validation.json","pass"),("typography","font_manifest.json","font-exact")):
                path = reports / name
                path.write_text(json.dumps({"result":"pass","matrix_results":[{"matrix_key":matrix_key,"result":result}]}), encoding="utf-8")
                artifacts.append({"role":role,"path":f"reports/{name}","sha256":sha256_file(path),"matrix_completed":[matrix_key]})
            with self.assertRaisesRegex(EvidenceError, "does not contain the complete matrix"):
                verify_matrix_artifacts(output, {"artifacts":artifacts}, {}, [matrix_key])

    def test_webgl_inventory_rejects_not_present_capture(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp); reports = output / "reports"; reports.mkdir()
            inventory = json.loads((SKILL / "templates" / "liveness_inventory_template.json").read_text(encoding="utf-8"))
            inventory["result"] = "pass"; inventory["coverage_complete"] = True
            (reports / "liveness_inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
            capture = json.loads((SKILL / "templates" / "webgl_capture_report_template.json").read_text(encoding="utf-8"))
            capture["result"] = "not-present"
            (reports / "webgl_capture_report.json").write_text(json.dumps(capture), encoding="utf-8")
            result = check_output(output, "false", "true")
            consistency = next(row for row in result["checks"] if row["name"] == "webgl_inventory_consistency")
            self.assertEqual(consistency["result"], "fail")

    def test_font_substitution_requires_verified_contract_scope(self) -> None:
        checks: list[dict[str, str]] = []
        add_font_approval_check(checks, {"result": "font-substituted"}, {"contract": {"approvals": []}})
        self.assertEqual(checks[-1]["result"], "fail")
        checks.clear()
        verified = {"contract": {"approvals": [{"approved": True, "scope": ["font.substitutions"]}]}}
        add_font_approval_check(checks, {"result": "font-substituted"}, verified)
        self.assertEqual(checks[-1]["result"], "pass")

    def test_static_current_runner_rebuilds_and_passes_final_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "output"; contract_dir = output / "contract"; reports = output / "reports"; candidate = root / "candidate"
            candidate.mkdir(parents=True); (candidate / "index.html").write_text("<h1>Meaning stays here</h1>", encoding="utf-8")
            source = contract_dir / "fresh_decode" / "source"; source.mkdir(parents=True)
            for name, content in {"input.h2d":"{}", "h2d_decoded.json":"{}", "h2d_tree_index.json":"[]"}.items(): (source / name).write_text(content, encoding="utf-8")
            reference = contract_dir / "reference"; reference.mkdir(parents=True); (reference / "reference.png").write_bytes(b"pinned")
            source_sha = sha256_file(source / "input.h2d")
            donor_closure = [{"path":"donor.html","sha256":"0"*64,"size":0}]; donor_identity = f"sha256:{canonical_json_sha256(donor_closure)}"
            classification = {"result":"pass","generator_sha256":sha256_file(SKILL/'scripts'/'classify_reference.js'),"behavior_required":False,"liveness_required":False,"coverage_complete":True,"source_sha256":source_sha,"donor_identity":donor_identity,"donor_closure":donor_closure,"matrix_keys":["390x844@headless"],"breakpoints":[]}
            bundle = {"schema_version":"2.0","result":"pass","coverage_complete":True,"source_sha256":source_sha,"donor_identity":donor_identity,"donor_closure":donor_closure,"environment_by_profile":{"headless":"0"*64},"matrix_keys":["390x844@headless"],"visual":{"donor_identity":donor_identity},"dynamic":{"donor_identity":None},"classification":classification,"artifacts":[{"path":"reference.png","sha256":sha256_file(reference / "reference.png")} ]}
            bundle_path = reference / "reference_bundle.json"; bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            helper = contract_dir / "generate_reports.py"
            helper.write_text(textwrap.dedent(f"""
                import hashlib, json, os, shutil
                from pathlib import Path
                output=Path(os.environ['H2D_OUTPUT']); reports=output/'reports'; source_out=output/'source'; reports.mkdir(parents=True,exist_ok=True); source_out.mkdir(parents=True,exist_ok=True)
                templates=Path({str(SKILL / 'templates')!r}); fresh=output/'contract'/'fresh_decode'/'source'
                for src,dst in [('input.h2d','input.original'),('input.h2d','input.h2d'),('h2d_decoded.json','h2d_decoded.json'),('h2d_tree_index.json','h2d_tree_index.json')]: shutil.copyfile(fresh/src,source_out/dst)
                source_sha=hashlib.sha256((source_out/'input.original').read_bytes()).hexdigest(); (source_out/'input.sha256').write_text(f'{{source_sha}}  input.original\\n',encoding='utf-8')
                mapping={{'source_intake':'source_intake','source_manifest':'source_manifest','h2d_unpack_report':'h2d_unpack_report','raw_asset_inventory':'raw_asset_inventory','decode_candidates':'decode_candidates','schema_discovery':'schema_discovery','font_manifest':'font_manifest','rect_targets':'rect_targets','asset_map':'asset_map','asset_bitmap_audit':'asset_bitmap_audit','asset_visibility_chain':'asset_visibility_chain','broken_asset_requests':'broken_asset_requests','asset_paint_validation':'asset_paint_validation','asset_provenance':'asset_provenance','node_validation':'node_validation','diff_summary':'diff_summary','behavior_validation':'behavior_validation_static','liveness_validation':'liveness_validation_static','output_manifest':'output_manifest'}}
                for dst,src in mapping.items(): shutil.copyfile(templates/f'{{src}}_template.json',reports/f'{{dst}}.json')
                keys=json.loads(os.environ['H2D_MATRIX_KEYS'])
                roles={{'visual':'diff_summary.json','geometry':'node_validation.json','typography':'font_manifest.json'}}
                artifacts=[]
                for role,name in roles.items():
                    path=reports/name; data=json.loads(path.read_text(encoding='utf-8')); data['matrix_results']=[{{'matrix_key':key,'result':'pass'}} for key in keys]; path.write_text(json.dumps(data),encoding='utf-8')
                    artifacts.append({{'role':role,'path':f'reports/{{name}}','sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'matrix_completed':keys}})
                (reports/'matrix_coverage.json').write_text(json.dumps({{'result':'pass','matrix_completed':keys,'artifacts':artifacts}}),encoding='utf-8'); (reports/'review.md').write_text('Synthetic current runner proof',encoding='utf-8')
            """), encoding="utf-8")
            names = ["source_intake","source_manifest","h2d_unpack_report","raw_asset_inventory","decode_candidates","schema_discovery","font_manifest","rect_targets","asset_map","asset_bitmap_audit","asset_visibility_chain","broken_asset_requests","asset_paint_validation","asset_provenance","node_validation","diff_summary","behavior_validation","liveness_validation","output_manifest","matrix_coverage"]
            closure = candidate_closure(candidate, ["index.html"], output)
            current_commands = [[sys.executable, str(helper)]]
            contract = {"schema_version":"2.0","workspace_root":str(root),"source":{"path":"fresh_decode/source/input.h2d","sha256":source_sha},"decoder":{"path":"builtin:scripts/h2d_unpack_source.py","sha256":sha256_file(SKILL/'scripts'/'h2d_unpack_source.py')},"decoded_artifacts":[{"path":"fresh_decode/source/h2d_decoded.json","sha256":sha256_file(source/'h2d_decoded.json')},{"path":"fresh_decode/source/h2d_tree_index.json","sha256":sha256_file(source/'h2d_tree_index.json')}],"responsive_matrix":[{"width":390,"height":844,"kind":"decoded"}],"browser_profiles":[{"id":"headless","headless":True,"device_scale_factor":1,"is_mobile":False,"has_touch":False,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}],"candidate":{"mode":"entry","project_root":"candidate","include":["index.html"],"closure_sha256":closure['digest']},"classification":bundle['classification'],"breakpoint_source":{"kind":"generated-reference-classification","donor_identity":donor_identity,"breakpoints":[]},"reference_bundle":{"path":"reference/reference_bundle.json","sha256":sha256_file(bundle_path)},"sidecars":[{"role":"report-generator","path":"generate_reports.py","sha256":sha256_file(helper)}],"approvals":[],"current_commands":current_commands,"command_executables":command_executable_records(current_commands,candidate),"expected_reports":[f"reports/{name}.json" for name in names] + ["reports/review.md"]}
            contract_path = contract_dir / "transfer_contract.json"; contract_path.write_text(json.dumps(contract), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(SKILL / "scripts" / "run_current_gates.py"), "--contract", str(contract_path), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(json.loads((reports / "validation_run.json").read_text(encoding="utf-8"))["result"], "pass")
            verify_current_evidence(reports / "current_evidence.json")
            stale_only = reports / "stale_only.json"
            stale_only.write_text(json.dumps({"result": "pass"}), encoding="utf-8")
            contract["expected_reports"].append("reports/stale_only.json")
            contract_path.write_text(json.dumps(contract), encoding="utf-8")
            missing_regeneration = subprocess.run([sys.executable, str(SKILL / "scripts" / "run_current_gates.py"), "--contract", str(contract_path), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(missing_regeneration.returncode, 2)
            self.assertIn("expected current report is missing", missing_regeneration.stderr)
            self.assertFalse(stale_only.exists())
            (candidate / "index.html").write_text("mutated", encoding="utf-8")
            direct = subprocess.run([sys.executable, str(SKILL / "scripts" / "run_all_gates.py"), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(direct.returncode, 2)
            stale = json.loads((reports / "validation_run.json").read_text(encoding="utf-8"))
            self.assertTrue(any(row["name"] == "current_evidence.json" and row["result"] == "fail" for row in stale["checks"]))


if __name__ == "__main__":
    unittest.main()
