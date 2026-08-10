from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SKILL = Path(__file__).resolve().parents[1] / "skills" / "h2d-pixel-perfect-transfer"


def playwright_available() -> bool:
    return subprocess.run(["node", "-e", "require('playwright')"], cwd=SKILL, capture_output=True).returncode == 0


class DesignSystemGateTests(unittest.TestCase):
    def test_component_repeat_floor_is_bundled_and_includes_pairs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            decoded = root / "decoded.json"
            out = root / "design_system.json"
            repeated = {
                "tag": "article",
                "width": 200,
                "height": 100,
                "styles": {"display": "block", "color": "rgb(6, 7, 10)"},
                "children": [{"tag": "span", "text": "Card", "styles": {"color": "rgb(6, 7, 10)", "fontFamily": "Arial", "fontSize": "16px", "fontWeight": "400", "lineHeight": "20px"}, "children": []}],
            }
            decoded.write_text(json.dumps({"width": 800, "frame": {"tag": "main", "width": 800, "height": 600, "styles": {"color": "rgb(6, 7, 10)"}, "children": [repeated, repeated]}}), encoding="utf-8")
            subprocess.run([sys.executable, str(SKILL / "scripts" / "extract_design_system.py"), "--decoded", str(decoded), "--out", str(out)], check=True, cwd=SKILL)
            report = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(report["min_component_repeats"], 2)
            self.assertTrue(any(component["count"] == 2 for component in report["components"]))
            bypass = subprocess.run([sys.executable, str(SKILL / "scripts" / "extract_design_system.py"), "--decoded", str(decoded), "--min-component-repeats", "1000", "--out", str(out)], cwd=SKILL, capture_output=True, text=True)
            self.assertNotEqual(bypass.returncode, 0)

    def test_token_gate_requires_definition_usage_and_rejects_scattered_literals(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "tokens.css").write_text(":root{--color-ink:#06070a}", encoding="utf-8")
            (root / "Card.svelte").write_text("<article style='color:var(--color-ink)'>ok</article>", encoding="utf-8")
            design = root / "design.json"
            token_map = root / "token_map.json"
            out = root / "token_reuse.json"
            design.write_text(json.dumps({"tokens": {"colors": [{"value": "rgb(6, 7, 10)", "count": 20}]}}), encoding="utf-8")
            token_map.write_text(json.dumps({"colors": {"rgb(6, 7, 10)": {"definition": "tokens.css", "token": "--color-ink", "usage": "var(--color-ink)"}}}), encoding="utf-8")
            command = [sys.executable, str(SKILL / "scripts" / "validate_token_reuse.py"), "--design-system", str(design), "--candidate-root", str(root), "--token-map", str(token_map), "--out", str(out)]
            subprocess.run(command, check=True, cwd=SKILL)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["result"], "pass")
            (root / "one.css").write_text(".one{color:#06070a}", encoding="utf-8")
            (root / "two.css").write_text(".two{background:#06070a}", encoding="utf-8")
            failed = subprocess.run(command, cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["result"], "fail")

    @unittest.skipUnless(playwright_available(), "playwright is installed by the H2D CI job")
    def test_component_map_must_match_donor_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            candidate = root / "candidate.html"
            definition = root / "Card.svelte"
            other_definition = root / "Other.svelte"
            design = root / "design.json"
            component_map = root / "component_map.json"
            out = root / "component_reuse.json"
            candidate.write_text("<!doctype html><article class='card'><h2>A</h2><p>x</p></article><article class='card'><h2>B</h2><p>y</p></article><div class='other'><span>x</span></div><div class='other'><span>y</span></div>", encoding="utf-8")
            definition.write_text('<article class="card"><h2>{title}</h2><p>{copy}</p></article>', encoding="utf-8")
            other_definition.write_text('<div class="other"><span>{copy}</span></div>', encoding="utf-8")
            donor_signature = "article.Card[h2,p]"
            donor_hash = hashlib.sha256(donor_signature.encode()).hexdigest()
            design.write_text(json.dumps({"min_component_repeats": 2, "components": [{"signature": donor_signature, "signature_sha256": donor_hash, "structure_signature": "article[h2,p]", "count": 2, "viewport": 800}]}), encoding="utf-8")
            base = ["node", str(SKILL / "scripts" / "validate_component_reuse.js"), "--candidate", str(candidate), "--candidate-root", str(root), "--design-system", str(design), "--component-map", str(component_map), "--out", str(out)]
            component_map.write_text(json.dumps({"components": {"card": {"selector": ".card", "definition": "Card.svelte", "donor_signature_sha256": donor_hash}}}), encoding="utf-8")
            subprocess.run(base, check=True, cwd=SKILL)
            component_map.write_text(json.dumps({"components": {"card": {"selector": ".other", "definition": "Other.svelte", "donor_signature_sha256": donor_hash}}}), encoding="utf-8")
            failed = subprocess.run(base, cwd=SKILL, capture_output=True, text=True)
            self.assertEqual(failed.returncode, 2)
            self.assertTrue(any("structure differs" in issue.get("issue", "") for issue in json.loads(out.read_text(encoding="utf-8"))["issues"]))


if __name__ == "__main__":
    unittest.main()
