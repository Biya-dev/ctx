"""Load and apply ignore patterns (.gitignore, .ctxignore, defaults)."""

from __future__ import annotations

import fnmatch
from pathlib import Path

# Directories and patterns that are always ignored
DEFAULT_IGNORE_DIRS: set[str] = {
    ".git",
    ".svn",
    ".hg",
    "__pycache__",
    "node_modules",
    ".next",
    ".nuxt",
    "dist",
    "build",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "venv",
    ".venv",
    "env",
    ".env",
    ".idea",
    ".vscode",
    "vendor",
    "target",
    "out",
    ".gradle",
    ".cache",
    "coverage",
    ".nyc_output",
    ".turbo",
    ".parcel-cache",
    "egg-info",
    ".eggs",
    "__pypackages__",
    "bower_components",
    ".terraform",
}

DEFAULT_IGNORE_FILES: set[str] = {
    ".DS_Store",
    "Thumbs.db",
    "*.pyc",
    "*.pyo",
    "*.class",
    "*.o",
    "*.so",
    "*.dll",
    "*.exe",
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "Cargo.lock",
    "poetry.lock",
    "composer.lock",
    "Gemfile.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
    "*.ico",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.webp",
    "*.mp4",
    "*.webm",
    "*.mp3",
    "*.wav",
    "*.pdf",
    "*.zip",
    "*.tar.gz",
    "*.jar",
}

BINARY_EXTENSIONS: set[str] = {
    ".pyc", ".pyo", ".class", ".o", ".so", ".dll", ".exe",
    ".woff", ".woff2", ".ttf", ".eot",
    ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico",
    ".mp4", ".webm", ".mp3", ".wav",
    ".pdf", ".zip", ".tar", ".gz", ".jar",
    ".db", ".sqlite", ".sqlite3",
}


def load_ignore_patterns(root: Path) -> set[str]:
    """Load ignore patterns from .gitignore and .ctxignore files."""
    patterns: set[str] = set()

    for ignore_file in (".gitignore", ".ctxignore"):
        path = root / ignore_file
        if path.is_file():
            try:
                for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
                    line = line.strip()
                    if line and not line.startswith("#"):
                        patterns.add(line)
            except OSError:
                pass

    return patterns


def should_ignore(
    path: Path,
    root: Path,
    ignore_patterns: set[str],
) -> bool:
    """Check if a path should be ignored."""
    name = path.name
    rel = path.relative_to(root).as_posix()

    # Check default directory ignores
    if path.is_dir() and name in DEFAULT_IGNORE_DIRS:
        return True

    # Check if any parent directory is ignored
    for part in path.relative_to(root).parts[:-1]:
        if part in DEFAULT_IGNORE_DIRS:
            return True

    # Check default file pattern ignores
    if path.is_file():
        for pattern in DEFAULT_IGNORE_FILES:
            if fnmatch.fnmatch(name, pattern):
                return True
        # Check binary extensions
        if path.suffix.lower() in BINARY_EXTENSIONS:
            return True

    # Check custom ignore patterns
    for pattern in ignore_patterns:
        # Handle directory patterns (ending with /)
        if pattern.endswith("/"):
            dir_pattern = pattern.rstrip("/")
            if path.is_dir() and fnmatch.fnmatch(name, dir_pattern):
                return True
            if any(fnmatch.fnmatch(p, dir_pattern) for p in path.relative_to(root).parts):
                return True
        else:
            if fnmatch.fnmatch(name, pattern) or fnmatch.fnmatch(rel, pattern):
                return True

    return False
