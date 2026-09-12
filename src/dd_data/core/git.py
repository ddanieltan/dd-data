"""Git automation utilities for checking diffs and committing updates."""

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
from typing import Optional

from dd_data.core.logger import log_error, log_info, log_success, log_warning


def write_target_file(repo_dir: Path, rel_path: str, content: str) -> Path:
    """Writes formatted content to the target file inside the repository."""
    full_path = repo_dir / rel_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")
    log_info(f"Updated file at {full_path}")
    return full_path


def run_git(repo_dir: Path, *args: str) -> subprocess.CompletedProcess:
    """Executes a git command inside the repo directory with clean environment."""
    env = os.environ.copy()
    # Avoid local gitconfig leakage in sandbox/CI if needed
    if "GIT_CONFIG_GLOBAL" not in env and not os.path.exists(os.path.expanduser("~/.gitconfig")):
        env["GIT_CONFIG_GLOBAL"] = "/dev/null"

    cmd = ["git", "-C", str(repo_dir)] + list(args)
    return subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)


def has_git_changes(repo_dir: Path, rel_path: Optional[str] = None) -> bool:
    """Checks whether there are uncommitted changes in the repository."""
    cmd = ["status", "--porcelain"]
    if rel_path:
        cmd.append(rel_path)
    result = run_git(repo_dir, *cmd)
    return bool(result.stdout.strip())


def commit_and_push(
    repo_dir: Path,
    rel_path: str,
    commit_msg: Optional[str] = None,
    branch: str = "main",
) -> bool:
    """Stages, commits, and pushes changes if diff exists.

    Returns True if a commit was made and pushed, False if no changes existed.
    """
    if not has_git_changes(repo_dir, rel_path):
        log_info(f"No changes detected in {rel_path}. Skipping commit.")
        return False

    if not commit_msg:
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        commit_msg = f"Automated data update: {now_utc}"

    try:
        run_git(repo_dir, "add", rel_path)
        run_git(repo_dir, "commit", "-m", commit_msg)
        log_info(f"Committed changes: {commit_msg}")

        run_git(repo_dir, "push", "origin", branch)
        log_success(f"Pushed commit to origin/{branch} successfully.")
        return True
    except subprocess.CalledProcessError as e:
        log_error(f"Git operation failed:\nStdout: {e.stdout}\nStderr: {e.stderr}")
        raise
