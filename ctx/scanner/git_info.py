"""Git metadata scanner."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GitResult:
    is_git_repo: bool = False
    branch: str = ""
    remote_url: str = ""
    total_commits: int = 0
    recent_commits: list[dict[str, str]] = field(default_factory=list)
    contributors: list[str] = field(default_factory=list)
    last_commit_date: str = ""
    repo_age_days: int = 0


def scan_git(root: Path) -> GitResult:
    """Extract Git metadata from a repository."""
    result = GitResult()
    try:
        from git import Repo
    except ImportError:
        return result

    try:
        repo = Repo(root, search_parent_directories=True)
    except Exception:
        return result

    result.is_git_repo = True

    try:
        result.branch = repo.active_branch.name
    except (TypeError, ValueError):
        result.branch = "detached HEAD"

    try:
        if repo.remotes:
            result.remote_url = repo.remotes.origin.url
    except (AttributeError, IndexError):
        pass

    try:
        commits = list(repo.iter_commits(max_count=100))
        result.total_commits = len(commits)

        for commit in commits[:5]:
            msg = commit.message
            if isinstance(msg, bytes):
                msg = msg.decode("utf-8", errors="replace")
            result.recent_commits.append({
                "hash": commit.hexsha[:8],
                "message": msg.strip().split("\n")[0][:80],
                "author": str(commit.author),
                "date": commit.committed_datetime.strftime("%Y-%m-%d"),
            })

        if commits:
            result.last_commit_date = commits[0].committed_datetime.strftime("%Y-%m-%d")
            from datetime import datetime, timezone
            age = datetime.now(timezone.utc) - commits[-1].committed_datetime
            result.repo_age_days = age.days

        authors = {str(c.author) for c in commits}
        result.contributors = sorted(authors)[:10]
    except Exception:
        pass

    return result
