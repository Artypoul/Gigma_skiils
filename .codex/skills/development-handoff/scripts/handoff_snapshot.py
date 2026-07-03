#!/usr/bin/env python3
"""Print a read-only development handoff snapshot for a git repository."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.dont_write_bytecode = True


def run(cmd: list[str], cwd: Path, timeout: int = 20) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(cwd),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        return {
            "cmd": " ".join(cmd),
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:  # pragma: no cover - defensive CLI output
        return {
            "cmd": " ".join(cmd),
            "ok": False,
            "code": None,
            "stdout": "",
            "stderr": str(exc),
        }


def add_git_snapshot(snapshot: dict[str, Any], repo: Path, show_paths: bool) -> None:
    commands = {
        "branch": ["git", "branch", "--show-current"],
        "status": ["git", "status", "--short", "--branch"],
        "last_commit": ["git", "log", "-1", "--oneline", "--decorate"],
        "branches": ["git", "branch", "-vv"],
        "remotes": ["git", "remote"],
        "diff_stat": ["git", "diff", "--stat"],
        "staged_diff_stat": ["git", "diff", "--cached", "--stat"],
    }
    if show_paths:
        commands["root"] = ["git", "rev-parse", "--show-toplevel"]
        commands["remote_urls"] = ["git", "remote", "-v"]
    snapshot["git"] = {name: run(cmd, repo) for name, cmd in commands.items()}

    upstream = run(["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], repo)
    snapshot["git"]["upstream"] = upstream
    if upstream["ok"] and upstream["stdout"]:
        snapshot["git"]["ahead_behind"] = run(
            ["git", "rev-list", "--left-right", "--count", f"{upstream['stdout']}...HEAD"],
            repo,
        )


def add_pr_snapshot(
    snapshot: dict[str, Any],
    repo: Path,
    pr: str | None,
    include_comment_bodies: bool,
) -> None:
    if not shutil.which("gh"):
        snapshot["github"] = {"available": False, "reason": "gh CLI not found"}
        return

    fields = "url,state,mergedAt,mergeCommit,headRefName,baseRefName,statusCheckRollup,reviewDecision"
    if include_comment_bodies:
        fields += ",comments,reviews"
    cmd = ["gh", "pr", "view"]
    if pr:
        cmd.append(pr)
    cmd.extend(["--json", fields])
    snapshot["github"] = {"available": True, "pr": run(cmd, repo, timeout=30)}


def print_text(snapshot: dict[str, Any]) -> None:
    git = snapshot.get("git", {})
    gh = snapshot.get("github", {})

    print("HANDOFF SNAPSHOT")
    print(f"repo: {snapshot['repo']}")
    if snapshot.get("repo_path"):
        print(f"repo_path: {snapshot['repo_path']}")
    for key in (
        "branch",
        "last_commit",
        "status",
        "upstream",
        "ahead_behind",
        "remotes",
        "remote_urls",
    ):
        item = git.get(key)
        if not item:
            continue
        value = item.get("stdout") or item.get("stderr") or "<empty>"
        print(f"\n[{key}]")
        print(value)

    for key in ("diff_stat", "staged_diff_stat"):
        value = git.get(key, {}).get("stdout")
        if value:
            print(f"\n[{key}]")
            print(value)

    pr_result = gh.get("pr") if gh.get("available") else None
    if pr_result:
        print("\n[pr]")
        if pr_result["ok"]:
            print(pr_result["stdout"])
        else:
            print(pr_result["stderr"] or pr_result["stdout"] or "gh pr view failed")
    elif gh:
        print(f"\n[github]\n{gh.get('reason')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print read-only git/GitHub handoff snapshot.")
    parser.add_argument("--repo", default=".", help="Repository path.")
    parser.add_argument("--pr", help="Pull request number or URL for gh pr view.")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of text.")
    parser.add_argument(
        "--show-paths",
        action="store_true",
        help=(
            "Include absolute local paths and remote URLs. Use only for local diagnostics; "
            "do not paste unredacted output into chat, docs or PR comments."
        ),
    )
    parser.add_argument(
        "--include-comment-bodies",
        action="store_true",
        help=(
            "Include raw PR comment/review bodies. Use only for local review work; "
            "do not paste unredacted output into chat, docs or PR comments."
        ),
    )
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    snapshot: dict[str, Any] = {"repo": repo.name}
    if args.show_paths:
        snapshot["repo_path"] = str(repo)
    add_git_snapshot(snapshot, repo, args.show_paths)
    add_pr_snapshot(snapshot, repo, args.pr, args.include_comment_bodies)

    if args.json:
        print(json.dumps(snapshot, ensure_ascii=False, indent=2))
    else:
        print_text(snapshot)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
