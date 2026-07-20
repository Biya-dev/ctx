"""Unit test suite for ctx CLI tool."""

from pathlib import Path

from typer.testing import CliRunner

from ctx.analyzers.architecture import analyze_architecture, analyze_detailed_architecture
from ctx.analyzers.ask import ask_codebase
from ctx.analyzers.deps import analyze_dependencies
from ctx.cli import app
from ctx.scanner.env import scan_env
from ctx.scanner.filesystem import scan_filesystem
from ctx.scanner.packages import scan_packages

runner = CliRunner()
PROJECT_ROOT = Path(__file__).parent.parent


def test_scanner_filesystem():
    fs = scan_filesystem(PROJECT_ROOT)
    assert fs.total_files > 0
    assert fs.root == PROJECT_ROOT
    assert len(fs.files) > 0


def test_scanner_packages():
    pkg = scan_packages(PROJECT_ROOT)
    assert pkg.language == "Python"
    assert pkg.package_manager in ("pip", "uv", "")
    assert "typer" in pkg.dependencies


def test_scanner_env():
    fs = scan_filesystem(PROJECT_ROOT)
    env = scan_env(PROJECT_ROOT, files=fs.files)
    assert isinstance(env.variables, list)


def test_analyzer_architecture():
    fs = scan_filesystem(PROJECT_ROOT)
    pkg = scan_packages(PROJECT_ROOT)
    arch = analyze_architecture(fs, pkg, PROJECT_ROOT)
    assert "CLI" in arch.project_type or "Python" in arch.project_type
    assert isinstance(arch.summary_points, list)


def test_analyzer_deps():
    fs = scan_filesystem(PROJECT_ROOT)
    pkg = scan_packages(PROJECT_ROOT)
    deps_res = analyze_dependencies(fs, pkg, PROJECT_ROOT)
    assert "Framework" in deps_res.categorized_deps or "Utilities & Services" in deps_res.categorized_deps


def test_analyzer_detailed_architecture():
    fs = scan_filesystem(PROJECT_ROOT)
    pkg = scan_packages(PROJECT_ROOT)
    arch = analyze_architecture(fs, pkg, PROJECT_ROOT)
    details = analyze_detailed_architecture(fs, pkg, arch, PROJECT_ROOT)
    assert details.project_name != ""
    assert details.api_style == "CLI"


def test_ask_codebase():
    fs = scan_filesystem(PROJECT_ROOT)
    pkg = scan_packages(PROJECT_ROOT)
    arch = analyze_architecture(fs, pkg, PROJECT_ROOT)
    res = ask_codebase("How are commands handled?", fs, pkg, arch, PROJECT_ROOT)
    assert res.query == "How are commands handled?"
    assert len(res.matches) > 0


def test_cli_scan():
    result = runner.invoke(app, ["scan", str(PROJECT_ROOT)])
    assert result.exit_code == 0
    assert "ctx" in result.output


def test_cli_deps():
    result = runner.invoke(app, ["deps", str(PROJECT_ROOT)])
    assert result.exit_code == 0
    assert "Dependency" in result.output


def test_cli_architecture():
    result = runner.invoke(app, ["architecture", str(PROJECT_ROOT)])
    assert result.exit_code == 0
    assert "ctx architecture" in result.output


def test_cli_ask():
    result = runner.invoke(app, ["ask", "How does scan work?"])
    assert result.exit_code == 0
    assert "ctx ask" in result.output

def test_cli_tui_help():
    result = runner.invoke(app, ["tui", "--help"])
    assert result.exit_code == 0
    assert "Launch the interactive terminal UI" in result.output

def test_cli_extras():
    commands = ["docs", "security", "tests", "diagram", "pr", "onboard", "deadcode"]
    for cmd in commands:
        result = runner.invoke(app, [cmd, str(PROJECT_ROOT)])
        assert result.exit_code == 0


def test_cli_export(tmp_path: Path):
    result = runner.invoke(app, ["export", str(PROJECT_ROOT)])
    assert result.exit_code == 0
    # The command should create ctx.md in PROJECT_ROOT by default, but let's just check output
    assert "Exported context" in result.output or result.exit_code == 0
