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
from evidence_integrity import candidate_closure, sha256_file, verify_current_evidence  # noqa: E402
from run_all_gates import add_font_approval_check  # noqa: E402


class CurrentRunnerTests(unittest.TestCase):
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
            bundle = {"schema_version":"2.0","result":"pass","coverage_complete":True,"source_sha256":source_sha,"donor_identity":"sha256:donor","matrix_keys":["390x844@headless"],"visual":{"donor_identity":"sha256:donor"},"dynamic":{"donor_identity":None},"classification":{"behavior_required":False,"liveness_required":False,"coverage_complete":True},"artifacts":[{"path":"reference.png","sha256":sha256_file(reference / "reference.png")} ]}
            bundle_path = reference / "reference_bundle.json"; bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            helper = contract_dir / "generate_reports.py"
            helper.write_text(textwrap.dedent(f"""
                import json, os, shutil
                from pathlib import Path
                output=Path(os.environ['H2D_OUTPUT']); reports=output/'reports'; source_out=output/'source'; reports.mkdir(parents=True,exist_ok=True); source_out.mkdir(parents=True,exist_ok=True)
                templates=Path({str(SKILL / 'templates')!r}); fresh=output/'contract'/'fresh_decode'/'source'
                for src,dst in [('input.h2d','input.original'),('input.h2d','input.h2d'),('h2d_decoded.json','h2d_decoded.json'),('h2d_tree_index.json','h2d_tree_index.json')]: shutil.copyfile(fresh/src,source_out/dst)
                (source_out/'input.sha256').write_text('0'*64,encoding='utf-8')
                mapping={{'source_intake':'source_intake','source_manifest':'source_manifest','h2d_unpack_report':'h2d_unpack_report','raw_asset_inventory':'raw_asset_inventory','decode_candidates':'decode_candidates','schema_discovery':'schema_discovery','font_manifest':'font_manifest','rect_targets':'rect_targets','asset_map':'asset_map','asset_bitmap_audit':'asset_bitmap_audit','asset_visibility_chain':'asset_visibility_chain','broken_asset_requests':'broken_asset_requests','asset_paint_validation':'asset_paint_validation','asset_provenance':'asset_provenance','node_validation':'node_validation','diff_summary':'diff_summary','behavior_validation':'behavior_validation_static','liveness_validation':'liveness_validation_static','output_manifest':'output_manifest'}}
                for dst,src in mapping.items(): shutil.copyfile(templates/f'{{src}}_template.json',reports/f'{{dst}}.json')
                keys=json.loads(os.environ['H2D_MATRIX_KEYS']); (reports/'matrix_coverage.json').write_text(json.dumps({{'result':'pass','matrix_completed':keys}}),encoding='utf-8'); (reports/'review.md').write_text('Synthetic current runner proof',encoding='utf-8')
            """), encoding="utf-8")
            names = ["source_intake","source_manifest","h2d_unpack_report","raw_asset_inventory","decode_candidates","schema_discovery","font_manifest","rect_targets","asset_map","asset_bitmap_audit","asset_visibility_chain","broken_asset_requests","asset_paint_validation","asset_provenance","node_validation","diff_summary","behavior_validation","liveness_validation","output_manifest","matrix_coverage"]
            closure = candidate_closure(candidate, ["index.html"], output)
            contract = {"schema_version":"2.0","workspace_root":str(root),"source":{"path":"fresh_decode/source/input.h2d","sha256":source_sha},"decoder":{"path":"builtin:scripts/h2d_unpack_source.py","sha256":sha256_file(SKILL/'scripts'/'h2d_unpack_source.py')},"decoded_artifacts":[{"path":"fresh_decode/source/h2d_decoded.json","sha256":sha256_file(source/'h2d_decoded.json')},{"path":"fresh_decode/source/h2d_tree_index.json","sha256":sha256_file(source/'h2d_tree_index.json')}],"responsive_matrix":[{"width":390,"height":844,"kind":"decoded"}],"browser_profiles":[{"id":"headless","headless":True,"device_scale_factor":1,"is_mobile":False,"has_touch":False,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}],"candidate":{"mode":"entry","project_root":"candidate","include":["index.html"],"closure_sha256":closure['digest']},"classification":bundle['classification'],"reference_bundle":{"path":"reference/reference_bundle.json","sha256":sha256_file(bundle_path)},"sidecars":[{"role":"report-generator","path":"generate_reports.py","sha256":sha256_file(helper)}],"approvals":[],"current_commands":[[sys.executable,str(helper)]],"expected_reports":[f"reports/{name}.json" for name in names]}
            contract_path = contract_dir / "transfer_contract.json"; contract_path.write_text(json.dumps(contract), encoding="utf-8")
            completed = subprocess.run([sys.executable, str(SKILL / "scripts" / "run_current_gates.py"), "--contract", str(contract_path), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
            self.assertEqual(json.loads((reports / "validation_run.json").read_text(encoding="utf-8"))["result"], "pass")
            verify_current_evidence(reports / "current_evidence.json")
            (candidate / "index.html").write_text("mutated", encoding="utf-8")
            direct = subprocess.run([sys.executable, str(SKILL / "scripts" / "run_all_gates.py"), "--output", str(output)], capture_output=True, text=True)
            self.assertEqual(direct.returncode, 2)
            stale = json.loads((reports / "validation_run.json").read_text(encoding="utf-8"))
            self.assertTrue(any(row["name"] == "current_evidence.json" and row["result"] == "fail" for row in stale["checks"]))


if __name__ == "__main__":
    unittest.main()
