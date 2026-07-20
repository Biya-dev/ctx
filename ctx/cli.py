"""ctx CLI -- Understand any codebase in 10 seconds."""

from __future__ import annotations

import sys
import time
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from ctx import __version__

app = typer.Typer(
    name="ctx",
    help="Understand any codebase in 10 seconds.",
    no_args_is_help=False,
    add_completion=False,
    rich_markup_mode="rich",
    invoke_without_command=True,
)
console = Console(highlight=False)


def _run_scan(root: Path):
    """Execute the full scan pipeline and return results."""
    from ctx.analyzers.architecture import analyze_architecture
    from ctx.scanner.env import scan_env
    from ctx.scanner.filesystem import scan_filesystem
    from ctx.scanner.git_info import scan_git
    from ctx.scanner.packages import scan_packages

    with Progress(
        SpinnerColumn(style="bright_cyan"),
        TextColumn("[bright_cyan]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Scanning filesystem...", total=None)
        fs = scan_filesystem(root)

        progress.update(task, description="Reading git metadata...")
        git = scan_git(root)

        progress.update(task, description="Analyzing packages...")
        pkg = scan_packages(root)

        progress.update(task, description="Scanning environment...")
        env = scan_env(root, files=fs.files)

        progress.update(task, description="Analyzing architecture...")
        arch = analyze_architecture(fs, pkg, root)

    return fs, git, pkg, env, arch


def _do_scan(path: str) -> None:
    """Execute a scan and render output."""
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[bold red]Error:[/] {root} is not a directory.")
        raise typer.Exit(code=1)

    start = time.perf_counter()
    fs, git, pkg, env, arch = _run_scan(root)
    elapsed = time.perf_counter() - start

    from ctx.output.terminal import render_scan
    render_scan(fs, git, pkg, env, arch)

    console.print(f"  [dim]Scanned in {elapsed:.1f}s[/]")
    console.print()


@app.callback()
def main(
    version: bool = typer.Option(
        False, "--version", "-v",
        help="Show version and exit.",
    ),
):
    """Understand any codebase in 10 seconds.

    Run [bold cyan]ctx scan .[/] to scan a codebase.

    Run [bold cyan]ctx export . --claude[/] to export AI context.
    """
    if version:
        console.print(f"[bold bright_cyan]ctx[/] v{__version__}")
        raise typer.Exit()


@app.command()
def scan(
    path: str = typer.Argument(".", help="Path to the project directory."),
):
    """Scan a codebase and display architecture summary.

    Examples:
        ctx scan
        ctx scan .
        ctx scan /path/to/project
    """
    _do_scan(path)


@app.command()
def export(
    path: str = typer.Argument(".", help="Path to the project directory."),
    target: str = typer.Option(
        "generic",
        "--target", "-t",
        help="Target AI: generic, chatgpt, claude, gemini, cursor, codex.",
    ),
    output: str | None = typer.Option(
        None,
        "--output", "-o",
        help="Output file path (defaults to ctx.md in project root).",
    ),
    chatgpt: bool = typer.Option(False, "--chatgpt", help="Optimize for ChatGPT."),
    claude: bool = typer.Option(False, "--claude", help="Optimize for Claude."),
    gemini: bool = typer.Option(False, "--gemini", help="Optimize for Gemini."),
    cursor: bool = typer.Option(False, "--cursor", help="Optimize for Cursor."),
    codex: bool = typer.Option(False, "--codex", help="Optimize for Codex."),
):
    """Export AI-ready context file (ctx.md).

    Creates a comprehensive markdown file perfect for pasting into
    ChatGPT, Claude, Gemini, Cursor, or Codex.

    Examples:
        ctx export .
        ctx export . --claude
        ctx export . --chatgpt -o context.md
    """
    root = Path(path).resolve()

    if not root.is_dir():
        console.print(f"[bold red]Error:[/] {root} is not a directory.")
        raise typer.Exit(code=1)

    # Resolve target from shorthand flags
    if chatgpt:
        target = "chatgpt"
    elif claude:
        target = "claude"
    elif gemini:
        target = "gemini"
    elif cursor:
        target = "cursor"
    elif codex:
        target = "codex"

    fs, git, pkg, env, arch = _run_scan(root)

    from ctx.output.export import export_context

    output_path = Path(output) if output else None
    result_path = export_context(fs, pkg, env, arch, output_path=output_path, target=target)

    console.print()
    console.print(f"  [bold green]OK[/] Exported to [bold]{result_path}[/]")
    console.print(f"  [dim]Target: {target}[/]")
    console.print(f"  [dim]Optimized for: {_target_label(target)}[/]")
    console.print()
    console.print("  [dim]* Enjoying ctx? Give us a star on GitHub: [link=https://github.com/Biya-dev/ctx]https://github.com/Biya-dev/ctx[/link][/]")
    console.print()


@app.command()
def ask(
    question: str = typer.Argument(..., help="Question to ask about the codebase."),
    path: str = typer.Option(".", "--path", "-p", help="Path to the project directory."),
):
    """Ask AI or heuristic search any question about the codebase.

    Examples:
        ctx ask "Where is authentication?"
        ctx ask "How does line counting work?"
    """
    root = Path(path).resolve()
    if not root.is_dir():
        console.print(f"[bold red]Error:[/] {root} is not a directory.")
        raise typer.Exit(code=1)

    fs, git, pkg, env, arch = _run_scan(root)

    from ctx.analyzers.ask import ask_codebase
    from ctx.output.terminal import render_ask

    ask_result = ask_codebase(question, fs, pkg, arch, root)
    render_ask(ask_result)


@app.command()
def deps(
    path: str = typer.Argument(".", help="Path to the project directory."),
):
    """Analyze and display codebase dependency graph and flows.

    Examples:
        ctx deps
        ctx deps .
    """
    root = Path(path).resolve()
    if not root.is_dir():
        console.print(f"[bold red]Error:[/] {root} is not a directory.")
        raise typer.Exit(code=1)

    fs, git, pkg, env, arch = _run_scan(root)

    from ctx.analyzers.deps import analyze_dependencies
    from ctx.output.terminal import render_deps

    deps_result = analyze_dependencies(fs, pkg, root)
    render_deps(deps_result)


@app.command(name="architecture")
def architecture(
    path: str = typer.Argument(".", help="Path to the project directory."),
):
    """Display deep architectural summary and layer breakdown.

    Examples:
        ctx architecture
        ctx arch
    """
    root = Path(path).resolve()
    if not root.is_dir():
        console.print(f"[bold red]Error:[/] {root} is not a directory.")
        raise typer.Exit(code=1)

    fs, git, pkg, env, arch = _run_scan(root)

    from ctx.analyzers.architecture import analyze_detailed_architecture
    from ctx.output.terminal import render_architecture_detailed

    details = analyze_detailed_architecture(fs, pkg, arch, root)
    render_architecture_detailed(details)


@app.command(name="arch", hidden=True)
def arch_alias(
    path: str = typer.Argument(".", help="Path to the project directory."),
):
    """Alias for `ctx architecture`."""
    architecture(path)


@app.command(name="tui")
def tui(
    path: str = typer.Argument(".", help="Path to the project directory."),
):
    """Launch the interactive terminal UI (TUI).

    Examples:
        ctx tui
        ctx ui
    """
    root = Path(path).resolve()
    if not root.is_dir():
        console.print(f"[bold red]Error:[/] {root} is not a directory.")
        raise typer.Exit(code=1)

    try:
        from ctx.tui import run_tui
        run_tui(root)
    except ImportError:
        console.print("[bold red]Error:[/] textual is not installed. Please install with `pip install textual`.")
        raise typer.Exit(code=1)


@app.command(name="ui", hidden=True)
def ui_alias(
    path: str = typer.Argument(".", help="Path to the project directory."),
):
    """Alias for `ctx tui`."""
    tui(path)


@app.command()
def docs(path: str = typer.Argument(".")):
    """Auto-generate boilerplate documentation (Phase 4)."""
    root = Path(path).resolve()
    fs, git, pkg, env, arch = _run_scan(root)
    from ctx.analyzers.extras import generate_docs
    res = generate_docs(arch, pkg, root)
    for name, content in res.items():
        console.print(f"[bold bright_cyan]{name}[/]")
        console.print(content)

@app.command()
def security(path: str = typer.Argument(".")):
    """Check for basic security risks (Phase 4)."""
    root = Path(path).resolve()
    fs, git, pkg, env, arch = _run_scan(root)
    from ctx.analyzers.extras import analyze_security
    res = analyze_security(fs, pkg, root)
    console.print("[bold red]Security Report[/]")
    for w in res.warnings:
        console.print(f"[yellow]Warning: {w}[/]")
    for s in res.secrets_found:
        console.print(f"[red]Secret: {s}[/]")

@app.command()
def deadcode(path: str = typer.Argument(".")):
    """Find unused files/exports (Phase 4 placeholder)."""
    console.print("[yellow]deadcode command is a placeholder for Phase 4.[/]")

@app.command()
def tests(path: str = typer.Argument(".")):
    """Check test coverage heuristics (Phase 4)."""
    root = Path(path).resolve()
    fs, git, pkg, env, arch = _run_scan(root)
    from ctx.analyzers.extras import analyze_tests
    res = analyze_tests(fs)
    console.print("[bold bright_cyan]Tests Analysis[/]")
    console.print(f"Source files: {res['source_files_count']}")
    console.print(f"Test files: {res['test_files_count']}")

@app.command()
def diagram(path: str = typer.Argument(".")):
    """Generate Mermaid diagram (Phase 5)."""
    root = Path(path).resolve()
    fs, git, pkg, env, arch = _run_scan(root)
    from ctx.analyzers.deps import analyze_dependencies
    from ctx.analyzers.extras import generate_diagram
    deps = analyze_dependencies(fs, pkg, root)
    res = generate_diagram(deps)
    console.print("[bold bright_cyan]Mermaid Diagram[/]")
    console.print(res)

@app.command()
def pr(path: str = typer.Argument(".")):
    """Generate PR template (Phase 5)."""
    root = Path(path).resolve()
    fs, git, pkg, env, arch = _run_scan(root)
    from ctx.analyzers.extras import generate_pr_template
    res = generate_pr_template(fs, pkg)
    console.print(res)

@app.command()
def onboard(path: str = typer.Argument(".")):
    """Generate onboarding guide (Phase 5)."""
    root = Path(path).resolve()
    fs, git, pkg, env, arch = _run_scan(root)
    from ctx.analyzers.extras import generate_onboard_guide
    res = generate_onboard_guide(arch, fs, root)
    console.print(res)

def _target_label(target: str) -> str:
    """Get human-friendly label for export target."""
    labels = {
        "generic": "All AI assistants",
        "chatgpt": "ChatGPT (OpenAI)",
        "claude": "Claude (Anthropic)",
        "gemini": "Gemini (Google)",
        "cursor": "Cursor IDE",
        "codex": "Codex CLI",
    }
    return labels.get(target, target)


def _cli_entry() -> None:
    """Entry point that intercepts bare `ctx` and `ctx .` to run scan."""
    args = sys.argv[1:]

    # If no args or if the first arg looks like a path (not a subcommand),
    # insert "scan" to route to the scan command
    known_commands = {
        "scan", "export", "ask", "deps", "architecture", "arch",
        "tui", "ui", "docs", "security", "deadcode", "tests", "diagram", "pr", "onboard",
        "--help", "-h", "--version", "-v"
    }
    if not args:
        sys.argv.insert(1, "scan")
    elif args[0] not in known_commands and not args[0].startswith("-"):
        sys.argv.insert(1, "scan")

    app()


if __name__ == "__main__":
    _cli_entry()

