from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "h2d-pixel-perfect-transfer"


class BehaviorAndLivenessTests(unittest.TestCase):
    def test_matrix_close_actions_have_open_prerequisite(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            inventory = root / "inventory.json"
            out = root / "matrix.json"
            inventory.write_text(json.dumps({"result": "pass", "coverage_complete": True, "components": [{"component_id": "menu", "selector": "#menu", "kind": "disclosure", "criticality": "critical", "listeners": ["click"]}]}), encoding="utf-8")
            subprocess.run(["node", str(SKILL / "scripts" / "behavior_matrix_generate.js"), "--inventory", str(inventory), "--out", str(out)], check=True)
            rows = {row["interaction_id"]: row for row in json.loads(out.read_text(encoding="utf-8"))["interactions"]}
            self.assertEqual([step["action"] for step in rows["menu:close-escape"]["sequence"]], ["click", "escape"])
            self.assertEqual([step["action"] for step in rows["menu:close-outside"]["sequence"]], ["click", "outside-click"])

    def test_liveness_compare_rejects_wrong_motion_timing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            sys.path.insert(0, str(SKILL / "scripts"))
            from PIL import Image
            for name in ("o.png", "c.png"):
                Image.new("RGBA", (4, 4), (255, 0, 0, 255)).save(root / name)
            inventory = {"surfaces": [{"surface_id": "s1", "kind": "css-transition", "triggers": ["hover"]}]}
            (root / "inventory.json").write_text(json.dumps(inventory), encoding="utf-8")
            original = {"trace_id": "s1@hover", "surface_id": "s1", "kind": "css-transition", "samples": [{"t_ms": 0, "screenshot": "o.png", "computed": {"transform": "none"}, "canvas": None}], "errors": []}
            candidate = {**original, "samples": [{"t_ms": 100, "screenshot": "c.png", "computed": {"transform": "none"}, "canvas": None}]}
            (root / "original.jsonl").write_text(json.dumps(original) + "\n", encoding="utf-8")
            (root / "candidate.jsonl").write_text(json.dumps(candidate) + "\n", encoding="utf-8")
            completed = subprocess.run([sys.executable, str(SKILL / "scripts" / "liveness_compare_traces.py"), "--original", str(root / "original.jsonl"), "--candidate", str(root / "candidate.jsonl"), "--inventory", str(root / "inventory.json"), "--original-root", str(root), "--candidate-root", str(root), "--out", str(root / "out.json")])
            self.assertEqual(completed.returncode, 2)
            self.assertEqual(json.loads((root / "out.json").read_text(encoding="utf-8"))["result"], "fail")


if __name__ == "__main__":
    unittest.main()
