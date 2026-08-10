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
            donor.write_text("""<!doctype html><style>#modal{display:none}.spin{animation:pulse 1s infinite}@keyframes pulse{50%{transform:scale(1.1)}}</style><button id='open'>Open</button><div id='modal'><div class='spin'>Animated modal</div><button id='hidden-action'>Hidden action</button></div><script>document.getElementById('open').onclick=()=>document.getElementById('modal').style.display='block';document.getElementById('hidden-action').onclick=event=>event.currentTarget.dataset.used='1'</script>""", encoding="utf-8")
            h2d.write_text("{}", encoding="utf-8")
            matrix = root / "matrix.json"; profiles = root / "profiles.json"; visual_out = root / "visual"; classification = root / "classification.json"
            matrix.write_text(json.dumps([{"width":390,"height":844,"kind":"decoded"}]), encoding="utf-8")
            profile_data = {"id":"mobile","headless":True,"device_scale_factor":1,"is_mobile":True,"has_touch":True,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}
            profiles.write_text(json.dumps([profile_data]), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "freeze_visual_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out-dir", str(visual_out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            subprocess.run(["node", str(SKILL / "scripts" / "classify_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--h2d", str(h2d), "--matrix", str(matrix), "--profiles", str(profiles), "--visual-manifest", str(visual_out / "visual_reference_manifest.json"), "--out", str(classification), "--project-root", str(SKILL), "--max-states", "12"], cwd=SKILL, check=True)
            report = json.loads(classification.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "pass")
            self.assertTrue(report["behavior_required"])
            self.assertTrue(report["liveness_required"])
            self.assertGreaterEqual(len(report["rows"][0]["states"]), 2)
            inventory = root / "behavior-inventory.json"
            profile = root / "profile.json"; profile.write_text(json.dumps(profile_data), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "behavior_inventory.js"), "--url", str(donor), "--classification", str(classification), "--profile", str(profile), "--viewport", "390", "--height", "844", "--out", str(inventory), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            behavior = json.loads(inventory.read_text(encoding="utf-8"))
            hidden = next(row for row in behavior["components"] if row["selector"] == "#hidden-action")
            self.assertEqual(behavior["result"], "pass")
            self.assertEqual(hidden["prerequisite_sequence"], [{"action": "click", "selector": "#open"}])
            self.assertIn("click", hidden["listeners"])

    def test_behavior_inventory_keeps_same_selector_in_each_reachable_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; h2d = root / "source.h2d"
            donor.write_text("<!doctype html><button id='next'>Next</button><output id='step'>0</output><script>next.onclick=()=>{const value=Number(step.textContent)+1;step.textContent=String(value);if(value===2)next.remove()}</script>", encoding="utf-8")
            h2d.write_text("{}", encoding="utf-8")
            matrix = root / "matrix.json"; profiles = root / "profiles.json"; profile = root / "profile.json"; visual = root / "visual"; classification = root / "classification.json"; inventory = root / "inventory.json"
            matrix.write_text(json.dumps([{"width":390,"height":844,"kind":"decoded"}]), encoding="utf-8")
            profile_data = {"id":"desktop","headless":True,"device_scale_factor":1,"is_mobile":False,"has_touch":False,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}
            profiles.write_text(json.dumps([profile_data]), encoding="utf-8"); profile.write_text(json.dumps(profile_data), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "freeze_visual_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out-dir", str(visual), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            subprocess.run(["node", str(SKILL / "scripts" / "classify_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--h2d", str(h2d), "--matrix", str(matrix), "--profiles", str(profiles), "--visual-manifest", str(visual / "visual_reference_manifest.json"), "--out", str(classification), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            subprocess.run(["node", str(SKILL / "scripts" / "behavior_inventory.js"), "--url", str(donor), "--viewport", "390", "--height", "844", "--profile", str(profile), "--classification", str(classification), "--out", str(inventory), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            report = json.loads(inventory.read_text(encoding="utf-8"))
            occurrences = [row for row in report["components"] if row["selector"] == "#next"]
            self.assertEqual(len(occurrences), 2)
            self.assertEqual(sorted(len(row["prerequisite_sequence"]) for row in occurrences), [0, 1])
            self.assertEqual(len({row["state_sha256"] for row in occurrences}), 2)

    def test_classification_discovers_breakpoints_timers_and_interaction_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; h2d = root / "source.h2d"
            (root / "lazy.svg").write_text("<svg xmlns='http://www.w3.org/2000/svg' width='20' height='20'><rect width='20' height='20'/></svg>", encoding="utf-8")
            donor.write_text("""<!doctype html><style>@supports (width: 1dvw){body{border:0}}@supports (container-type: inline-size){main{container-type:inline-size}}@media (min-width: 48em){body{padding:1px}}@media (max-width: 1024px){body{margin:0}}</style><main><div role='navigation'>Structural navigation</div><button id='load'>Load</button><img id='lazy' alt=''></main><script>setTimeout(()=>document.body.dataset.ready='1',10);document.getElementById('load').onclick=()=>document.getElementById('lazy').src='lazy.svg'</script>""", encoding="utf-8")
            h2d.write_text("{}", encoding="utf-8")
            matrix = root / "matrix.json"; profiles = root / "profiles.json"; visual = root / "visual"; classification = root / "classification.json"
            matrix.write_text(json.dumps([{"width":390,"height":844,"kind":"decoded"}]), encoding="utf-8")
            profiles.write_text(json.dumps([{"id":"desktop","headless":True,"device_scale_factor":1,"is_mobile":False,"has_touch":False,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}]), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "freeze_visual_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out-dir", str(visual), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            subprocess.run(["node", str(SKILL / "scripts" / "classify_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--h2d", str(h2d), "--matrix", str(matrix), "--profiles", str(profiles), "--visual-manifest", str(visual / "visual_reference_manifest.json"), "--out", str(classification), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            report = json.loads(classification.read_text(encoding="utf-8"))
            self.assertEqual(report["breakpoints"], [768, 1024])
            self.assertTrue(report["liveness_required"])
            self.assertIn("lazy.svg", {row["path"] for row in report["donor_closure"]})
            controls = report["rows"][0]["states"][0]["controls"]
            self.assertFalse(any(row.get("role") == "navigation" for row in controls))
            liveness = root / "liveness.json"
            subprocess.run(["node", str(SKILL / "scripts" / "liveness_inventory.js"), "--url", str(donor), "--viewport", "390", "--height", "844", "--out", str(liveness), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            inventory = json.loads(liveness.read_text(encoding="utf-8"))
            self.assertEqual(inventory["result"], "pass")
            self.assertTrue(any(row["kind"] == "unknown-runtime" for row in inventory["surfaces"]))

    def test_classification_fails_closed_on_delegated_global_listener(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; h2d = root / "source.h2d"
            donor.write_text("<!doctype html><style>@media(min-width:50vw){body{margin:0}}</style><button id='child'>Child</button><script>document.addEventListener('click',event=>event.target.dataset.clicked='1');window.onkeydown=()=>{}</script>", encoding="utf-8")
            h2d.write_text("{}", encoding="utf-8")
            matrix = root / "matrix.json"; profiles = root / "profiles.json"; visual = root / "visual"; classification = root / "classification.json"
            matrix.write_text(json.dumps([{"width":390,"height":844,"kind":"decoded"}]), encoding="utf-8")
            profiles.write_text(json.dumps([{"id":"desktop","headless":True,"device_scale_factor":1,"is_mobile":False,"has_touch":False,"locale":"en-US","timezone":"UTC","reduced_motion":"reduce"}]), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "freeze_visual_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--matrix", str(matrix), "--profiles", str(profiles), "--out-dir", str(visual), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            completed = subprocess.run(["node", str(SKILL / "scripts" / "classify_reference.js"), "--donor", str(donor), "--donor-root", str(root), "--h2d", str(h2d), "--matrix", str(matrix), "--profiles", str(profiles), "--visual-manifest", str(visual / "visual_reference_manifest.json"), "--out", str(classification), "--project-root", str(SKILL)], cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            report = json.loads(classification.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "fail")
            self.assertTrue(any("unresolved delegated listener" in issue.get("message", "") for issue in report["issues"]))
            self.assertTrue(any("window:keydown" in issue.get("message", "") for issue in report["issues"]))
            self.assertTrue(any("unsupported responsive breakpoint query" in issue.get("message", "") for issue in report["issues"]))

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
            # The system-transfer gates are mandatory expected reports: a
            # contract without them is rejected before anything is pinned.
            base_contract_args = [sys.executable, str(SKILL / "scripts" / "create_transfer_contract.py"), "--h2d", str(h2d), "--workspace-root", str(root), "--candidate-root", str(candidate), "--candidate-include", "index.html", "--candidate-include", "generate.py", "--profiles", str(profiles), "--height-map", str(heights), "--reference-bundle", str(reference / "reference_bundle.json"), "--current-command", json.dumps([sys.executable, "generate.py"]), "--expected-report", "reports/diff_summary.json", "--expected-report", "reports/node_validation.json", "--expected-report", "reports/font_manifest.json", "--expected-report", "reports/matrix_coverage.json", "--expected-report", "reports/review.md"]
            rejected = subprocess.run(base_contract_args + ["--out", str(contract)], cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(rejected.returncode, 2)
            self.assertIn("design_system.json", rejected.stderr + rejected.stdout)
            subprocess.run(base_contract_args + ["--expected-report", "reports/design_system.json", "--expected-report", "reports/component_reuse.json", "--expected-report", "reports/token_reuse.json", "--out", str(contract)], cwd=SKILL, check=True)
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
            self.assertTrue(all("fonts" not in row["environment"] for row in manifest["rows"]))
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
            self.assertEqual(report["result"], "partial")
            self.assertFalse(report["coverage_complete"])
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

    def test_candidate_behavior_replay_uses_implementation_map(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); candidate = root / "candidate.html"; matrix = root / "matrix.json"; mapping = root / "map.json"; out = root / "reports" / "candidate.jsonl"
            candidate.write_text("<!doctype html><button id='candidate' aria-expanded='false'>Toggle</button><script>document.getElementById('candidate').onclick=event=>event.currentTarget.setAttribute('aria-expanded','true')</script>", encoding="utf-8")
            matrix.write_text(json.dumps({"interactions":[{"interaction_id":"toggle:click","component_id":"toggle","selector":"#original","frame_path":"main","action":"click","expected_transition":True,"sequence":[{"action":"click","selector":"#original"}]}]}), encoding="utf-8")
            mapping.write_text(json.dumps({"result":"pass","mappings":[{"component_id":"toggle","original_selector":"#original","candidate_selector":"#candidate"}]}), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "behavior_capture_trace.js"), "--url", str(candidate), "--matrix", str(matrix), "--implementation-map", str(mapping), "--side", "candidate", "--out", str(out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            trace = json.loads(out.read_text(encoding="utf-8").strip())
            self.assertEqual(trace["resolved_selector"], "#candidate")
            self.assertEqual(trace["after"]["aria_expanded"], "true")
            self.assertEqual(trace["errors"], [])

    def test_behavior_pre_state_is_captured_after_prerequisites(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; matrix = root / "matrix.json"; out = root / "reports" / "original.jsonl"
            donor.write_text("<!doctype html><button id='open'>Open</button><button id='target' hidden aria-checked='false'>Target</button><script>const opener=document.getElementById('open');const target=document.getElementById('target');opener.onclick=()=>{target.hidden=false;target.setAttribute('aria-checked','mixed')};target.onclick=()=>target.setAttribute('aria-checked','true')</script>", encoding="utf-8")
            matrix.write_text(json.dumps({"interactions":[{"interaction_id":"target:click","component_id":"target","selector":"#target","frame_path":"main","prerequisite_count":1,"sequence":[{"action":"click","selector":"#open"},{"action":"click","selector":"#target"}],"expected_transition":True}]}), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "behavior_capture_trace.js"), "--url", str(donor), "--matrix", str(matrix), "--side", "original", "--out", str(out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            trace = json.loads(out.read_text(encoding="utf-8").strip())
            self.assertTrue(trace["before"]["exists"])
            self.assertEqual(trace["before"]["aria_checked"], "mixed")
            self.assertEqual(trace["after"]["aria_checked"], "true")

    def test_preexisting_blocked_transport_does_not_fake_action_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; matrix = root / "matrix.json"; out = root / "reports" / "original.jsonl"
            donor.write_text("<!doctype html><div id='noop' style='width:40px;height:40px'>No-op</div><script>navigator.sendBeacon('https://example.com/boot','x')</script>", encoding="utf-8")
            matrix.write_text(json.dumps({"interactions":[{"interaction_id":"noop:click","component_id":"noop","selector":"#noop","frame_path":"main","action":"click","expected_transition":True,"sequence":[{"action":"click","selector":"#noop"}]}]}), encoding="utf-8")
            completed = subprocess.run(["node", str(SKILL / "scripts" / "behavior_capture_trace.js"), "--url", str(donor), "--matrix", str(matrix), "--side", "original", "--out", str(out), "--project-root", str(SKILL)], cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
            trace = json.loads(out.read_text(encoding="utf-8").strip())
            self.assertTrue(any(row["action"] == "expected-transition" for row in trace["errors"]))
            self.assertEqual(trace["blocked_transports"], [])

    def test_required_video_playback_failure_is_not_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; inventory = root / "inventory.json"; out = root / "reports" / "original.jsonl"
            donor.write_text("<!doctype html><video id='video'></video>", encoding="utf-8")
            inventory.write_text(json.dumps({"result":"pass","coverage_complete":True,"surfaces":[{"surface_id":"video","selector":"#video","kind":"video","triggers":["playback"]}]}), encoding="utf-8")
            completed = subprocess.run(["node", str(SKILL / "scripts" / "liveness_capture_trace.js"), "--url", str(donor), "--inventory", str(inventory), "--out", str(out), "--project-root", str(SKILL)], cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2, completed.stdout + completed.stderr)
            trace = json.loads(out.read_text(encoding="utf-8").strip())
            self.assertTrue(any(row["type"] in {"trigger-error", "playback-not-advancing"} for row in trace["errors"]))

    def test_generated_webgl_capture_contains_real_nonblank_frames(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); donor = root / "donor.html"; inventory = root / "inventory.json"; out = root / "webgl.json"
            donor.write_text("<!doctype html><canvas id='gl' width='16' height='16'></canvas><script>const context=gl.getContext('webgl',{preserveDrawingBuffer:true});context.clearColor(1,0,0,1);context.clear(context.COLOR_BUFFER_BIT)</script>", encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "liveness_inventory.js"), "--url", str(donor), "--out", str(inventory), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            subprocess.run(["node", str(SKILL / "scripts" / "webgl_capture.js"), "--url", str(donor), "--inventory", str(inventory), "--out", str(out), "--project-root", str(SKILL)], cwd=SKILL, check=True)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["result"], "pass")
            self.assertEqual(len(report["contexts"]), 1)
            self.assertEqual(len(report["contexts"][0]["frame_hashes"]), 3)
            self.assertGreaterEqual(report["contexts"][0]["non_blank_samples"], 1)


if __name__ == "__main__":
    unittest.main()
