"""Package & dependency scanner — detects package managers and dependencies."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore
    except ImportError:
        tomllib = None  # type: ignore[assignment]


@dataclass
class PackageResult:
    package_manager: str = ""
    language: str = ""
    framework: str = ""
    framework_version: str = ""
    dependencies: dict[str, str] = field(default_factory=dict)
    dev_dependencies: dict[str, str] = field(default_factory=dict)
    scripts: dict[str, str] = field(default_factory=dict)
    project_name: str = ""
    project_version: str = ""


def _detect_package_manager(root: Path) -> str:
    """Detect which package manager is used."""
    if (root / "pnpm-lock.yaml").exists():
        return "pnpm"
    if (root / "yarn.lock").exists():
        return "yarn"
    if (root / "bun.lockb").exists():
        return "bun"
    if (root / "package-lock.json").exists():
        return "npm"
    if (root / "poetry.lock").exists():
        return "poetry"
    if (root / "Pipfile.lock").exists():
        return "pipenv"
    if (root / "uv.lock").exists():
        return "uv"
    if (root / "requirements.txt").exists():
        return "pip"
    if (root / "Cargo.lock").exists():
        return "cargo"
    if (root / "go.sum").exists():
        return "go modules"
    if (root / "Gemfile.lock").exists():
        return "bundler"
    if (root / "composer.lock").exists():
        return "composer"
    if (root / "mix.lock").exists():
        return "mix"

    # Fallback to manifest files
    if (root / "package.json").exists():
        return "npm"
    if (root / "pyproject.toml").exists():
        return "pip"
    if (root / "Cargo.toml").exists():
        return "cargo"
    if (root / "go.mod").exists():
        return "go modules"
    return ""


def _scan_node(root: Path, result: PackageResult) -> None:
    """Scan Node.js package.json."""
    pkg_path = root / "package.json"
    if not pkg_path.exists():
        return

    try:
        data = json.loads(pkg_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    result.project_name = data.get("name", "")
    result.project_version = data.get("version", "")

    deps = data.get("dependencies", {})
    dev_deps = data.get("devDependencies", {})
    result.dependencies = dict(deps)
    result.dev_dependencies = dict(dev_deps)
    result.scripts = dict(data.get("scripts", {}))

    all_deps = {**deps, **dev_deps}

    # Detect framework
    frameworks = [
        ("next", "Next.js"),
        ("nuxt", "Nuxt"),
        ("@angular/core", "Angular"),
        ("svelte", "SvelteKit" if "@sveltejs/kit" in all_deps else "Svelte"),
        ("vue", "Vue.js"),
        ("react", "React"),
        ("express", "Express"),
        ("fastify", "Fastify"),
        ("hono", "Hono"),
        ("@remix-run/react", "Remix"),
        ("astro", "Astro"),
        ("gatsby", "Gatsby"),
        ("electron", "Electron"),
    ]
    for pkg, name in frameworks:
        if pkg in all_deps:
            result.framework = name
            result.framework_version = all_deps[pkg].lstrip("^~>=<")
            break


def _scan_python(root: Path, result: PackageResult) -> None:
    """Scan Python project files."""
    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists() and tomllib:
        try:
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            project = data.get("project", {})
            result.project_name = project.get("name", "")
            result.project_version = project.get("version", "")
            for dep in project.get("dependencies", []):
                name = dep.split(">=")[0].split("<=")[0].split("==")[0].split("<")[0].split(">")[0]
                name = name.split("[")[0].split(";")[0].strip()
                result.dependencies[name] = dep
        except Exception:
            pass

    # requirements.txt fallback
    req = root / "requirements.txt"
    if req.exists() and not result.dependencies:
        try:
            for line in req.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and not line.startswith("-"):
                    name = line.split(">=")[0].split("==")[0].split("<")[0].split(">")[0]
                    name = name.split("[")[0].strip()
                    if name:
                        result.dependencies[name] = line
        except OSError:
            pass

    # Detect framework — first check if the project itself IS a framework
    name_to_framework = {
        "django": "Django",
        "flask": "Flask",
        "fastapi": "FastAPI",
        "starlette": "Starlette",
        "tornado": "Tornado",
        "sanic": "Sanic",
        "streamlit": "Streamlit",
        "gradio": "Gradio",
    }
    proj_name_lower = result.project_name.lower().replace("-", "").replace("_", "")
    if proj_name_lower in name_to_framework:
        result.framework = name_to_framework[proj_name_lower]
        return

    # Otherwise detect from dependencies
    all_deps = set(result.dependencies.keys())
    frameworks = [
        ({"django"}, "Django"),
        ({"flask"}, "Flask"),
        ({"fastapi"}, "FastAPI"),
        ({"starlette"}, "Starlette"),
        ({"tornado"}, "Tornado"),
        ({"sanic"}, "Sanic"),
        ({"streamlit"}, "Streamlit"),
        ({"gradio"}, "Gradio"),
        ({"typer"}, "Typer CLI"),
        ({"click"}, "Click CLI"),
    ]
    for pkgs, name in frameworks:
        if pkgs & all_deps:
            result.framework = name
            break


def _scan_rust(root: Path, result: PackageResult) -> None:
    """Scan Cargo.toml for Rust projects."""
    cargo = root / "Cargo.toml"
    if not cargo.exists() or not tomllib:
        return
    try:
        data = tomllib.loads(cargo.read_text(encoding="utf-8"))
        pkg = data.get("package", {})
        result.project_name = pkg.get("name", "")
        result.project_version = pkg.get("version", "")
        for name, ver in data.get("dependencies", {}).items():
            if isinstance(ver, str):
                result.dependencies[name] = ver
            elif isinstance(ver, dict):
                result.dependencies[name] = ver.get("version", "")
    except Exception:
        pass


def _scan_go(root: Path, result: PackageResult) -> None:
    """Scan go.mod for Go projects."""
    gomod = root / "go.mod"
    if not gomod.exists():
        return
    try:
        content = gomod.read_text(encoding="utf-8")
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("module "):
                result.project_name = line.split("module ", 1)[1].strip()
            if line.startswith("go "):
                result.project_version = line.split("go ", 1)[1].strip()
    except OSError:
        pass


def scan_packages(root: Path) -> PackageResult:
    """Detect and scan package manager and dependencies."""
    result = PackageResult()
    result.package_manager = _detect_package_manager(root)

    # Detect language from files
    lang_indicators = [
        ("package.json", "TypeScript" if (root / "tsconfig.json").exists() else "JavaScript"),
        ("pyproject.toml", "Python"),
        ("requirements.txt", "Python"),
        ("setup.py", "Python"),
        ("Cargo.toml", "Rust"),
        ("go.mod", "Go"),
        ("pom.xml", "Java"),
        ("build.gradle", "Java"),
        ("build.gradle.kts", "Kotlin"),
        ("Gemfile", "Ruby"),
        ("composer.json", "PHP"),
        ("mix.exs", "Elixir"),
        ("pubspec.yaml", "Dart"),
        ("Package.swift", "Swift"),
    ]

    for filename, lang in lang_indicators:
        if (root / filename).exists():
            result.language = lang
            break

    # Run language-specific scanner
    if result.language in ("JavaScript", "TypeScript"):
        _scan_node(root, result)
    elif result.language == "Python":
        _scan_python(root, result)
    elif result.language == "Rust":
        _scan_rust(root, result)
    elif result.language == "Go":
        _scan_go(root, result)

    return result
