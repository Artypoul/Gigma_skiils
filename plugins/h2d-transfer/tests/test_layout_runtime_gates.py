from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "h2d-pixel-perfect-transfer"
sys.path.insert(0, str(SKILL / "scripts"))

from evidence_integrity import EvidenceError, reject_candidate_reference_code_overlap
from run_all_gates import add_layout_integrity_checks


def playwright_available() -> bool:
    return subprocess.run(["node", "-e", "require('playwright')"], cwd=SKILL, capture_output=True).returncode == 0


class LayoutRuntimeGateTests(unittest.TestCase):
    def test_rect_targets_include_ancestors_and_bind_current_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tree = root / "h2d_tree_index.json"
            out = root / "rect_targets.json"
            rows = [
                {"h2d_path_guess": "0", "viewport": 390, "tag": "body", "rect": {"x": 0, "y": 0, "width": 390, "height": 900}, "box_style": {"display": "block"}},
                {"h2d_path_guess": "0.0", "viewport": 390, "tag": "main", "rect": {"x": 0, "y": 50, "width": 390, "height": 700}, "box_style": {"display": "block"}},
                {"h2d_path_guess": "0.0.2", "viewport": 390, "tag": "section", "rect": {"x": 20, "y": 100, "width": 350, "height": 300}, "box_style": {"display": "flex"}},
                {"h2d_path_guess": "0.0.2.0", "viewport": 390, "tag": "h1", "rect": {"x": 20, "y": 100, "width": 300, "height": 80}},
            ]
            tree.write_text(json.dumps(rows), encoding="utf-8")
            subprocess.run([sys.executable, str(SKILL / "scripts" / "extract_rect_targets.py"), "--tree-index", str(tree), "--scope", "hero", "--root-map", '{"390":"0.0.2"}', "--out", str(out)], check=True, cwd=SKILL)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(report["includes_ancestors"])
            self.assertEqual(report["source_tree_sha256"], hashlib.sha256(tree.read_bytes()).hexdigest())
            self.assertEqual([target["relation_to_scope"] for target in report["viewports"][0]["targets"]], ["scope-ancestor", "scope-ancestor", "scope-root", "scope-descendant"])
            self.assertEqual(report["viewports"][0]["ancestor_target_count"], 2)

    def test_final_layout_integrity_rejects_scope_only_or_incomplete_measurement(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tree = root / "h2d_tree_index.json"; tree.write_text("[]", encoding="utf-8")
            rect = {
                "coverage_mode": "complete-ancestor-chain", "includes_ancestors": True,
                "source_tree_sha256": hashlib.sha256(tree.read_bytes()).hexdigest(),
                "generator_sha256": hashlib.sha256((SKILL / "scripts" / "extract_rect_targets.py").read_bytes()).hexdigest(),
                "root_map": {"390": "0.0"},
                "viewports": [{"viewport": 390, "root_path": "0.0", "target_count": 2, "ancestor_target_count": 1, "layout_target_count": 1, "targets": [
                    {"data_h2d_path": "0", "relation_to_scope": "scope-ancestor", "box_style": {"display": "block"}},
                    {"data_h2d_path": "0.0", "relation_to_scope": "scope-root"},
                ]}],
            }
            node = {"lenient_box_style": False, "selector_map_injective": True, "viewports": [{"viewport": 390, "checked": 2, "missing": []}]}
            checks: list[dict[str, str]] = []
            add_layout_integrity_checks(checks, rect, node, tree)
            self.assertEqual(checks[-1]["result"], "pass")
            rect["coverage_mode"] = "scope-only"
            add_layout_integrity_checks(checks, rect, node, tree)
            self.assertEqual(checks[-1]["result"], "fail")

    def test_substantial_authored_code_overlap_is_not_an_independent_reference(self) -> None:
        closure = {"files": [{"path": "src/App.svelte", "size": 1000, "sha256": "a" * 64}, {"path": "src/util.ts", "size": 50, "sha256": "b" * 64}]}
        reference = {"donor_closure": [{"path": "app.js", "size": 1000, "sha256": "a" * 64}]}
        with self.assertRaises(EvidenceError):
            reject_candidate_reference_code_overlap(closure, reference)

    @unittest.skipUnless(playwright_available(), "playwright is installed by the H2D CI job")
    def test_selector_map_must_be_injective(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            html = root / "candidate.html"; targets = root / "targets.json"; selectors = root / "selectors.json"; out = root / "node.json"
            html.write_text("<!doctype html><div class='same'></div>", encoding="utf-8")
            target_rows = []
            for path_value in ("0", "0.0"):
                target_rows.append({"key": f"390::{path_value}", "data_h2d_path": path_value, "parent_path": None if path_value == "0" else "0", "relation_to_scope": "scope-root" if path_value == "0" else "scope-descendant", "rect": {"x": 8, "y": 8, "width": 0, "height": 0}})
            targets.write_text(json.dumps({"scope": "test", "coordinate_space": "page", "coverage_mode": "complete-ancestor-chain", "includes_ancestors": True, "root_map": {"390": "0"}, "source_tree_sha256": "0" * 64, "generator_sha256": "0" * 64, "viewports": [{"viewport": 390, "root_path": "0", "target_count": 2, "ancestor_target_count": 0, "layout_target_count": 0, "targets": target_rows}], "total_targets": 2}), encoding="utf-8")
            selectors.write_text(json.dumps({"390": {"0": ".same", "0.0": ".same"}}), encoding="utf-8")
            completed = subprocess.run(["node", str(SKILL / "scripts" / "validate_active_viewport.js"), "--candidate", str(html), "--rect-targets", str(targets), "--selector-map", str(selectors), "--viewports", "390", "--out", str(out)], cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(completed.returncode, 2)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(report["selector_map_injective"])


if __name__ == "__main__":
    unittest.main()
