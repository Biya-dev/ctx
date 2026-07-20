"""Filesystem scanner — builds the directory tree and identifies important files."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from ctx.scanner.ignore import load_ignore_patterns, should_ignore


@dataclass
class FileInfo:
    """Information about a single file."""
    path: Path
    relative: str
    size: int
    extension: str
    lines: int = 0


@dataclass
class DirInfo:
    """Information about a directory."""
    path: Path
    relative: str
    file_count: int = 0
    children: list[str] = field(default_factory=list)


@dataclass
class FilesystemResult:
    """Complete filesystem scan result."""
    root: Path
    files: list[FileInfo] = field(default_factory=list)
    directories: list[DirInfo] = field(default_factory=list)
    total_files: int = 0
    total_dirs: int = 0
    total_lines: int = 0
    extension_counts: dict[str, int] = field(default_factory=dict)
    main_folders: list[str] = field(default_factory=list)
    important_files: list[str] = field(default_factory=list)


# Files that are almost always important for understanding a project
IMPORTANT_FILE_NAMES: set[str] = {
    # Config & project definition
    "package.json",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "composer.json",
    "Gemfile",
    "mix.exs",
    # App config
    "next.config.js",
    "next.config.ts",
    "next.config.mjs",
    "vite.config.ts",
    "vite.config.js",
    "webpack.config.js",
    "tsconfig.json",
    "tailwind.config.js",
    "tailwind.config.ts",
    "nuxt.config.ts",
    "astro.config.mjs",
    "svelte.config.js",
    "angular.json",
    # Docker & infra
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Makefile",
    "Procfile",
    "serverless.yml",
    "terraform.tf",
    # CI/CD
    ".github/workflows",
    "Jenkinsfile",
    ".gitlab-ci.yml",
    # Documentation
    "README.md",
    "README.rst",
    "CONTRIBUTING.md",
    "CHANGELOG.md",
    # Auth & middleware
    "middleware.ts",
    "middleware.js",
    "auth.ts",
    "auth.js",
    # Database
    "schema.prisma",
    "drizzle.config.ts",
    "alembic.ini",
    "knexfile.js",
    # Entry points
    "main.py",
    "app.py",
    "manage.py",
    "index.ts",
    "index.js",
    "server.ts",
    "server.js",
    "main.go",
    "main.rs",
    "Main.java",
    "Program.cs",
    # Environment
    ".env.example",
    ".env.sample",
    ".env.template",
    ".env.local.example",
}

# Patterns for important files (checked via fnmatch-style)
IMPORTANT_FILE_PATTERNS: list[str] = [
    "*.config.js",
    "*.config.ts",
    "*.config.mjs",
]


_SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".java", ".go", ".rs",
    ".rb", ".php", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift",
    ".kt", ".scala", ".ex", ".exs", ".vue", ".svelte", ".astro",
    ".md", ".mdx", ".yaml", ".yml", ".toml", ".json", ".xml",
    ".html", ".css", ".scss", ".sass", ".less",
    ".sql", ".graphql", ".proto", ".tf", ".hcl",
    ".sh", ".bash", ".zsh", ".fish", ".ps1",
    ".r", ".R", ".jl", ".lua", ".dart", ".zig",
}

# Average bytes per line — used for fast estimation on large repos
_AVG_BYTES_PER_LINE = 40


def _estimate_lines(size: int) -> int:
    """Estimate line count from file size (fast, no I/O)."""
    return max(1, size // _AVG_BYTES_PER_LINE) if size > 0 else 0


def scan_filesystem(root: Path, max_depth: int = 8) -> FilesystemResult:
    """Scan the filesystem starting from root.

    Args:
        root: The root directory to scan.
        max_depth: Maximum directory depth to traverse.

    Returns:
        A FilesystemResult containing all discovered files and directories.
    """
    result = FilesystemResult(root=root)
    ignore_patterns = load_ignore_patterns(root)
    extension_counts: dict[str, int] = {}
    important_files: list[str] = []
    top_level_dirs: list[str] = []

    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        current = Path(dirpath)
        depth = len(current.relative_to(root).parts)

        if depth > max_depth:
            dirnames.clear()
            continue

        # Filter out ignored directories (modifying in-place for os.walk)
        dirnames[:] = sorted(
            d for d in dirnames
            if not should_ignore(current / d, root, ignore_patterns)
        )

        # Track top-level directories
        if depth == 0:
            top_level_dirs = list(dirnames)

        # Track directories
        rel_dir = current.relative_to(root).as_posix()
        if rel_dir != ".":
            dir_info = DirInfo(
                path=current,
                relative=rel_dir,
                file_count=len(filenames),
                children=[d for d in dirnames],
            )
            result.directories.append(dir_info)
            result.total_dirs += 1

        # Process files
        for fname in sorted(filenames):
            fpath = current / fname
            if should_ignore(fpath, root, ignore_patterns):
                continue

            rel_path = fpath.relative_to(root).as_posix()
            ext = fpath.suffix.lower()

            # Get file size
            try:
                fsize = fpath.stat().st_size
            except OSError:
                fsize = 0

            # Estimate lines for source files (fast, no I/O)
            lines = _estimate_lines(fsize) if ext in _SOURCE_EXTENSIONS else 0

            file_info = FileInfo(
                path=fpath,
                relative=rel_path,
                size=fsize,
                extension=ext,
                lines=lines,
            )
            result.files.append(file_info)
            result.total_files += 1
            result.total_lines += lines

            # Track extension counts
            if ext:
                extension_counts[ext] = extension_counts.get(ext, 0) + 1

            # Check if file is important
            # Skip entry-point style files (main.py, app.py) if deeply nested in tests/docs
            is_entry = fname in {
                "main.py", "app.py", "index.ts", "index.js",
                "server.ts", "server.js", "main.go", "main.rs",
            }
            depth_here = len(rel_path.split("/"))

            if fname in IMPORTANT_FILE_NAMES:
                # For entry-point-style files, only include if near root (depth <= 3)
                if is_entry and depth_here > 3:
                    pass  # Skip deeply nested entry files
                else:
                    important_files.append(rel_path)
            else:
                import fnmatch
                for pattern in IMPORTANT_FILE_PATTERNS:
                    if fnmatch.fnmatch(fname, pattern):
                        important_files.append(rel_path)
                        break

    result.extension_counts = dict(
        sorted(extension_counts.items(), key=lambda x: x[1], reverse=True)
    )
    result.main_folders = [f"{d}/" for d in top_level_dirs]
    result.important_files = important_files

    return result
