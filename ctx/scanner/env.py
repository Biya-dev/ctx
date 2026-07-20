"""Environment variable scanner — finds .env files, references in code."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from ctx.scanner.ignore import load_ignore_patterns


@dataclass
class EnvResult:
    env_files: list[str] = field(default_factory=list)
    variables: list[str] = field(default_factory=list)
    has_env_example: bool = False


# Patterns to find env var references in source code
ENV_PATTERNS = [
    re.compile(r'process\.env\.([A-Z][A-Z0-9_]+)'),
    re.compile(r'os\.environ\[[\"\']([A-Z][A-Z0-9_]+)[\"\']\]'),
    re.compile(r'os\.environ\.get\([\"\']([A-Z][A-Z0-9_]+)[\"\']'),
    re.compile(r'os\.getenv\([\"\']([A-Z][A-Z0-9_]+)[\"\']'),
    re.compile(r'env\([\"\']([A-Z][A-Z0-9_]+)[\"\']'),
    re.compile(r'getenv\([\"\']([A-Z][A-Z0-9_]+)[\"\']'),
    re.compile(r'Environment\.GetEnvironmentVariable\([\"\']([A-Z][A-Z0-9_]+)[\"\']'),
    re.compile(r'std::env::var\([\"\']([A-Z][A-Z0-9_]+)[\"\']'),
]

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".rb",
    ".php", ".java", ".cs", ".env", ".env.example", ".env.sample",
}


def _parse_env_file(path: Path) -> list[str]:
    """Extract variable names from a .env file."""
    variables: list[str] = []
    try:
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key = line.split("=", 1)[0].strip()
                if key and re.match(r'^[A-Z][A-Z0-9_]*$', key):
                    variables.append(key)
    except OSError:
        pass
    return variables


def scan_env(root: Path, files: list | None = None) -> EnvResult:
    """Scan for environment variables.

    Args:
        root: Project root directory.
        files: Optional list of FileInfo objects from filesystem scan.

    Returns:
        EnvResult with discovered environment variables.
    """
    result = EnvResult()
    env_vars: set[str] = set()

    # Find .env files
    for name in [".env", ".env.example", ".env.sample", ".env.template",
                 ".env.local", ".env.development", ".env.production"]:
        path = root / name
        if path.exists():
            result.env_files.append(name)
            if "example" in name or "sample" in name or "template" in name:
                result.has_env_example = True
                env_vars.update(_parse_env_file(path))

    # If we have an env example file, use its vars; otherwise scan source
    if not env_vars:
        # Parse any .env file for variable names (not values)
        for env_file in result.env_files:
            path = root / env_file
            env_vars.update(_parse_env_file(path))

    # Scan source files for env var references (limited scan)
    if files:
        for finfo in files[:500]:  # Cap to avoid slow scans
            if finfo.extension in SOURCE_EXTENSIONS:
                try:
                    content = finfo.path.read_text(encoding="utf-8", errors="ignore")
                    for pattern in ENV_PATTERNS:
                        env_vars.update(pattern.findall(content))
                except OSError:
                    pass

    # Filter out common non-useful vars
    noise = {"NODE_ENV", "PATH", "HOME", "USER", "SHELL", "TERM", "PWD"}
    env_vars -= noise

    result.variables = sorted(env_vars)
    return result
