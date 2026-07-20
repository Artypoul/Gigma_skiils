from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = PLUGIN_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fetch_comments = load_module(
    "codex_toolkit_fetch_comments",
    "skills/gh-address-comments/scripts/fetch_comments.py",
)
inspect_pr_checks = load_module(
    "codex_toolkit_inspect_pr_checks",
    "skills/gh-fix-ci/scripts/inspect_pr_checks.py",
)
community_maintainers = load_module(
    "codex_toolkit_community_maintainers",
    "skills/security-ownership-map/scripts/community_maintainers.py",
)
run_ownership_map = load_module(
    "codex_toolkit_run_ownership_map",
    "skills/security-ownership-map/scripts/run_ownership_map.py",
)
translation_bounds = load_module(
    "codex_toolkit_translation_bounds",
    "skills/pixel-mask-move/scripts/translation_bounds.py",
)
background_remove = load_module(
    "codex_toolkit_background_remove",
    "skills/background-remove/scripts/background_remove.py",
)


class FetchCommentsRegressionTests(unittest.TestCase):
    def test_cross_repository_pr_uses_base_repository_from_url(self) -> None:
        payload = {
            "number": 42,
            "url": "https://github.com/base-owner/base-repo/pull/42",
        }
        with patch.object(fetch_comments, "gh_pr_view_json", return_value=payload):
            self.assertEqual(
                fetch_comments.get_current_pr_ref(),
                ("base-owner", "base-repo", 42),
            )

    def test_exhausted_connections_are_not_appended_again(self) -> None:
        calls: list[dict[str, object]] = []

        def connection(nodes, *, has_next=False, cursor=None):
            return {
                "nodes": nodes,
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            }

        def fake_graphql(**kwargs):
            calls.append(kwargs)
            second_page = kwargs.get("comments_cursor") == "comments-page-2"
            comments = connection(
                [{"id": "comment-2"}] if second_page else [{"id": "comment-1"}],
                has_next=not second_page,
                cursor=None if second_page else "comments-page-2",
            )
            return {
                "data": {
                    "repository": {
                        "pullRequest": {
                            "number": 7,
                            "url": "https://github.com/base/repo/pull/7",
                            "title": "PR",
                            "state": "OPEN",
                            "comments": comments,
                            "reviews": connection([{"id": "review-1"}]),
                            "reviewThreads": connection([{"id": "thread-1"}]),
                        }
                    }
                }
            }

        with patch.object(fetch_comments, "gh_api_graphql", side_effect=fake_graphql):
            result = fetch_comments.fetch_all("base", "repo", 7)

        self.assertEqual([item["id"] for item in result["conversation_comments"]], ["comment-1", "comment-2"])
        self.assertEqual([item["id"] for item in result["reviews"]], ["review-1"])
        self.assertEqual([item["id"] for item in result["review_threads"]], ["thread-1"])
        self.assertEqual(len(calls), 2)

    def test_review_thread_comments_are_paginated(self) -> None:
        def connection(nodes, has_next=False, cursor=None):
            return {
                "nodes": nodes,
                "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            }

        first_page = {
            "data": {
                "repository": {
                    "pullRequest": {
                        "number": 7,
                        "url": "https://github.com/base/repo/pull/7",
                        "title": "PR",
                        "state": "OPEN",
                        "comments": connection([]),
                        "reviews": connection([]),
                        "reviewThreads": connection([
                            {
                                "id": "thread-1",
                                "comments": connection([{"id": "reply-1"}], True, "reply-page-2"),
                            }
                        ]),
                    }
                }
            }
        }
        second_page = {
            "data": {
                "node": {
                    "comments": connection([{"id": "reply-2"}]),
                }
            }
        }
        with (
            patch.object(fetch_comments, "gh_api_graphql", return_value=first_page),
            patch.object(fetch_comments, "gh_api_thread_comments", return_value=second_page) as nested,
        ):
            result = fetch_comments.fetch_all("base", "repo", 7)
        replies = result["review_threads"][0]["comments"]["nodes"]
        self.assertEqual([reply["id"] for reply in replies], ["reply-1", "reply-2"])
        nested.assert_called_once_with("thread-1", "reply-page-2")


class PlaywrightWrapperRegressionTests(unittest.TestCase):
    def test_session_flag_matches_upstream_cli(self) -> None:
        skill_root = PLUGIN_ROOT / "skills/playwright"
        wrapper = (skill_root / "scripts/playwright_cli.sh").read_text(encoding="utf-8")
        docs = "\n".join(
            (skill_root / relative).read_text(encoding="utf-8")
            for relative in ("references/cli.md", "references/workflows.md")
        )
        self.assertIn('-s|-s=*)', wrapper)
        self.assertIn('cmd+=("-s=${PLAYWRIGHT_CLI_SESSION}")', wrapper)
        self.assertNotIn("--session", wrapper + docs)

    def test_wrapper_is_executable_in_git_index(self) -> None:
        repo_root = PLUGIN_ROOT.parents[1]
        targets = (
            "plugins/codex-toolkit/skills/playwright/scripts/playwright_cli.sh",
            ".codex/skills/playwright/scripts/playwright_cli.sh",
        )
        for target in targets:
            output = subprocess.check_output(
                ["git", "-C", str(repo_root), "ls-files", "--stage", target],
                text=True,
            )
            self.assertTrue(output.startswith("100755 "), f"{target}: {output}")


class ImageWorkflowRegressionTests(unittest.TestCase):
    def test_rembg_failure_does_not_silently_change_method(self) -> None:
        unavailable = {"error": "rembg not installed"}
        with (
            patch.object(background_remove, "remove_background_rembg", return_value=unavailable),
            patch.object(background_remove, "remove_background_builtin") as builtin,
        ):
            self.assertEqual(background_remove.remove_background("photo.png"), unavailable)
        builtin.assert_not_called()

    def test_background_remove_docs_resolve_from_loaded_skill_directory(self) -> None:
        text = (PLUGIN_ROOT / "skills/background-remove/SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("${SKILL_PATH}/skills/background-remove", text)
        self.assertIn("<absolute loaded background-remove skill directory>/scripts/background_remove.py", text)
        self.assertNotIn("automatically fall back", text)

    def test_rgb_watermarks_apply_requested_opacity(self) -> None:
        source = (PLUGIN_ROOT / "skills/image-utils/references/code-examples/image_utils.py").read_text(encoding="utf-8")
        start = source.index("    def add_image_watermark(")
        end = source.index("    # ==================== Adjustments", start)
        function = source[start:end]
        self.assertNotIn('if wm.mode == "RGBA"', function)
        conversion = 'wm = ImageUtils.resize(watermark, width=wm_width).convert("RGBA")'
        self.assertIn(conversion, function)
        self.assertLess(function.index(conversion), function.index("wm.split()"))
        self.assertIn("opacity must be between 0 and 1", function)

    def test_github_skill_agent_metadata_has_balanced_description_quotes(self) -> None:
        text = (PLUGIN_ROOT / "skills/gh-address-comments/agents/openai.yaml").read_text(encoding="utf-8")
        self.assertIn('short_description: "Address comments in a GitHub PR review"', text)


class CheckInspectionRegressionTests(unittest.TestCase):
    def test_nonzero_gh_checks_exit_still_parses_valid_json(self) -> None:
        response = inspect_pr_checks.GhResult(
            1,
            '[{"name":"tests","bucket":"fail"}]',
            "",
        )
        with patch.object(inspect_pr_checks, "run_gh_command", return_value=response):
            checks = inspect_pr_checks.fetch_checks("34", Path("."))
        self.assertEqual(checks, [{"name": "tests", "bucket": "fail"}])

    def test_job_log_is_requested_before_full_run_log(self) -> None:
        with (
            patch.object(inspect_pr_checks, "fetch_job_log", return_value=("job log", "")) as job_log,
            patch.object(inspect_pr_checks, "fetch_run_log") as run_log,
        ):
            result = inspect_pr_checks.fetch_check_log("run-1", "job-2", Path("."))
        self.assertEqual(result, ("job log", "", "ok"))
        job_log.assert_called_once_with("run-1", "job-2", Path("."))
        run_log.assert_not_called()


class OwnershipRegressionTests(unittest.TestCase):
    def test_recency_weight_uses_a_real_half_life(self) -> None:
        self.assertAlmostEqual(community_maintainers.recency_weight(180, 180), 0.5)
        self.assertAlmostEqual(community_maintainers.recency_weight(360, 180), 0.25)

    def test_documented_script_paths_exist_from_skill_root(self) -> None:
        skill_root = PLUGIN_ROOT / "skills/security-ownership-map"
        text = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        self.assertNotIn("skills/skills/", text)
        targets = set(re.findall(r"python scripts/([A-Za-z0-9_]+\.py)", text))
        self.assertTrue(targets)
        for target in targets:
            self.assertTrue((skill_root / "scripts" / target).is_file(), target)

    def test_networkx_is_optional_when_graph_outputs_are_disabled(self) -> None:
        real_import = __import__

        def import_without_networkx(name, *args, **kwargs):
            if name == "networkx" or name.startswith("networkx."):
                raise ImportError("networkx intentionally unavailable")
            return real_import(name, *args, **kwargs)

        argv = ["run_ownership_map.py", "--no-communities", "--no-cochange"]
        with (
            patch.object(sys, "argv", argv),
            patch("builtins.__import__", side_effect=import_without_networkx),
            patch.object(
                run_ownership_map.subprocess,
                "run",
                return_value=SimpleNamespace(returncode=0),
            ) as run,
        ):
            self.assertEqual(run_ownership_map.main(), 0)
        command = run.call_args.args[0]
        self.assertIn("--no-communities", command)
        self.assertIn("--no-cochange", command)

    def test_networkx_is_still_required_for_default_community_output(self) -> None:
        real_import = __import__

        def import_without_networkx(name, *args, **kwargs):
            if name == "networkx" or name.startswith("networkx."):
                raise ImportError("networkx intentionally unavailable")
            return real_import(name, *args, **kwargs)

        with (
            patch.object(sys, "argv", ["run_ownership_map.py"]),
            patch("builtins.__import__", side_effect=import_without_networkx),
            patch.object(run_ownership_map.subprocess, "run") as run,
        ):
            self.assertEqual(run_ownership_map.main(), 2)
        run.assert_not_called()


class SegmentAnythingRegressionTests(unittest.TestCase):
    def test_documented_onnx_exporter_exists_and_help_is_dependency_free(self) -> None:
        skill_root = PLUGIN_ROOT / "skills/segment-anything-model"
        script = skill_root / "scripts/export_onnx_model.py"
        self.assertTrue(script.is_file())
        result = subprocess.run(
            [sys.executable, str(script), "--help"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--checkpoint", result.stdout)
        self.assertIn("--model-type", result.stdout)
        self.assertIn("--output", result.stdout)


class PixelTranslationRegressionTests(unittest.TestCase):
    def test_visible_selection_must_remain_inside_canvas(self) -> None:
        with self.assertRaisesRegex(ValueError, "clip visible selected pixels"):
            translation_bounds.ensure_translation_fits(
                bounds=(2, 2, 5, 5),
                canvas_size=(10, 10),
                dx=-3,
                dy=0,
            )
        translation_bounds.ensure_translation_fits(
            bounds=(2, 2, 5, 5),
            canvas_size=(10, 10),
            dx=5,
            dy=5,
        )

    def test_move_script_enforces_translation_bounds(self) -> None:
        source = (
            PLUGIN_ROOT / "skills/pixel-mask-move/scripts/move_masked_layer.py"
        ).read_text(encoding="utf-8")
        self.assertIn("from translation_bounds import ensure_translation_fits", source)
        self.assertIn("ensure_translation_fits(", source)


if __name__ == "__main__":
    unittest.main()
