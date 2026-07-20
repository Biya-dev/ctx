"""Extra analyzers for Phase 4, 5, and 6 features."""

from dataclasses import dataclass
from pathlib import Path

from ctx.analyzers.architecture import ArchitectureResult
from ctx.analyzers.deps import DependencyGraphResult
from ctx.scanner.filesystem import FilesystemResult
from ctx.scanner.packages import PackageResult


@dataclass
class SecurityResult:
    secrets_found: list[str]
    outdated_packages: list[str]
    warnings: list[str]


def analyze_security(fs: FilesystemResult, pkg: PackageResult, root: Path) -> SecurityResult:
    """Basic security heuristic check."""
    secrets = []
    warnings = []

    # Check for hardcoded secrets heuristics
    if (root / ".env").exists() and not (root / ".gitignore").exists():
        warnings.append(".env exists but no .gitignore found - secrets may be committed!")

    for f in fs.files:
        if f.relative.endswith((".pem", ".key", ".p8")):
            secrets.append(f"Suspicious key file: {f.relative}")

    # Check for typical outdated or vulnerable packages (dummy logic for now)
    outdated = []
    if "requests" in pkg.dependencies:
        outdated.append("requests (consider updating to latest version)")

    return SecurityResult(secrets, outdated, warnings)


def generate_docs(arch: ArchitectureResult, pkg: PackageResult, root: Path) -> dict[str, str]:
    """Generate boilerplate docs."""
    project_name = pkg.project_name or root.name
    readme = f"# {project_name}\n\nProject generated or documented by ctx.\n\n"
    readme += f"## Architecture\n- **Framework:** {pkg.framework}\n- **Language:** {pkg.language}\n"

    contributing = f"# Contributing to {project_name}\n\n1. Fork the repo\n2. Create a branch\n3. Submit a PR\n"

    return {
        "README.md": readme,
        "CONTRIBUTING.md": contributing
    }


def analyze_tests(fs: FilesystemResult) -> dict[str, int]:
    """Basic heuristic to find test gaps."""
    src_files = [f for f in fs.files if not f.relative.startswith("tests/") and "test_" not in f.relative]
    test_files = [f for f in fs.files if f.relative.startswith("tests/") or "test_" in f.relative]

    return {
        "source_files_count": len(src_files),
        "test_files_count": len(test_files),
        "ratio_percent": int((len(test_files) / (len(src_files) or 1)) * 100)
    }


def generate_diagram(deps: DependencyGraphResult) -> str:
    """Generate Mermaid diagram of dependency flow chains."""
    lines = ["graph TD;"]
    for chain in deps.chain_summary:
        parts = chain.split(" -> ")
        for i in range(len(parts) - 1):
            source = parts[i].replace(" ", "_")
            target = parts[i+1].replace(" ", "_")
            lines.append(f"    {source}-->{target};")

    if len(lines) == 1:
        lines.append("    App-->Logic;")

    return "\n".join(lines)


def generate_pr_template(fs: FilesystemResult, pkg: PackageResult) -> str:
    """Generate a PR description template."""
    return f"""## Description
    
Describe your changes here.

## Type of change
- [ ] Bug fix
- [ ] New feature
- [ ] Refactoring

## Architecture Impact
This changes the {pkg.project_name or 'project'} architecture in the following way:
...
"""

def generate_onboard_guide(arch: ArchitectureResult, fs: FilesystemResult, root: Path) -> str:
    """Generate an onboarding guide."""
    return f"""# Welcome to the project!

## Getting Started
1. Run setup commands.
2. Entrypoints are located at:
{chr(10).join(f' - {ep}' for ep in arch.entrypoints)}

## Structure
Key folders:
{chr(10).join(f' - {f}' for f in fs.main_folders[:5])}
"""
