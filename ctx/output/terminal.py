"""Rich terminal output renderer — the beautiful ctx output."""

from __future__ import annotations

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ctx.analyzers.architecture import ArchitectureResult
from ctx.scanner.env import EnvResult
from ctx.scanner.filesystem import FilesystemResult
from ctx.scanner.git_info import GitResult
from ctx.scanner.packages import PackageResult

console = Console(highlight=False)


def _header(title: str) -> Text:
    """Create a styled section header."""
    return Text(title, style="bold cyan")


def render_scan(
    fs: FilesystemResult,
    git: GitResult,
    pkg: PackageResult,
    env: EnvResult,
    arch: ArchitectureResult,
) -> None:
    """Render the full scan result to the terminal."""

    # ── Project Overview ──
    overview_lines: list[str] = []

    project_name = pkg.project_name or fs.root.name
    overview_lines.append(f"[bold white]{project_name}[/]")

    if arch.project_type:
        overview_lines.append(f"[dim]{arch.project_type}[/]")

    if git.remote_url:
        url = git.remote_url.replace(".git", "")
        overview_lines.append(f"[dim blue]{url}[/]")

    console.print()
    console.print(
        Panel(
            "\n".join(overview_lines),
            title="[bold bright_cyan]ctx[/]",
            subtitle=f"[dim]{fs.total_files} files | {fs.total_lines:,} lines[/]",
            border_style="bright_cyan",
            padding=(1, 3),
        )
    )

    # ── Quick Facts ──
    table = Table(
        show_header=False,
        box=None,
        padding=(0, 2),
        expand=False,
    )
    table.add_column("key", style="bold bright_cyan", min_width=18)
    table.add_column("value", style="white")

    if pkg.language:
        table.add_row("Language", pkg.language)
    if pkg.framework:
        ver = f" {pkg.framework_version}" if pkg.framework_version else ""
        table.add_row("Framework", f"{pkg.framework}{ver}")
    if pkg.package_manager:
        table.add_row("Package Manager", pkg.package_manager)
    if git.branch:
        table.add_row("Branch", git.branch)
    if git.total_commits:
        table.add_row("Commits", str(git.total_commits) + ("+  " if git.total_commits >= 100 else ""))
    if git.contributors:
        table.add_row("Contributors", str(len(git.contributors)))

    console.print()
    console.print(table)

    # ── Directory Structure ──
    if fs.main_folders:
        console.print()
        console.print(_header("  Directory Structure"))
        console.print()

        from ctx.analyzers.architecture import DIR_PURPOSES
        for folder in fs.main_folders:
            dirname = folder.rstrip("/")
            purpose = DIR_PURPOSES.get(dirname, "")
            if purpose:
                console.print(f"  [bold yellow]  {folder:<20}[/] [dim]{purpose}[/]")
            else:
                console.print(f"  [bold yellow]  {folder}[/]")

    # ── Important Files ──
    if fs.important_files:
        console.print()
        console.print(_header("  Important Files"))
        console.print()
        for f in fs.important_files[:15]:
            console.print(f"  [green]  {f}[/]")

    # ── Entrypoints ──
    if arch.entrypoints:
        console.print()
        console.print(_header("  Entrypoints"))
        console.print()
        for ep in arch.entrypoints:
            console.print(f"  [bright_magenta]>[/] [white]{ep}[/]")

    # ── Dependencies ──
    if pkg.dependencies:
        console.print()
        dep_count = len(pkg.dependencies)
        dev_count = len(pkg.dev_dependencies)
        label = f"  Dependencies ({dep_count}"
        if dev_count:
            label += f" + {dev_count} dev"
        label += ")"
        console.print(_header(label))
        console.print()

        # Show top dependencies (not all)
        shown = list(pkg.dependencies.keys())[:20]
        dep_text = "  " + "  ".join(
            f"[white]{d}[/]" for d in shown
        )
        if len(pkg.dependencies) > 20:
            dep_text += f"  [dim]... +{len(pkg.dependencies) - 20} more[/]"
        console.print(dep_text)

    # ── Environment Variables ──
    if env.variables:
        console.print()
        console.print(_header(f"  Environment Variables ({len(env.variables)})"))
        console.print()
        for var in env.variables[:15]:
            console.print(f"  [bright_yellow]  {var}[/]")
        if len(env.variables) > 15:
            console.print(f"  [dim]  ... +{len(env.variables) - 15} more[/]")

    # ── Architecture Summary ──
    if arch.summary_points:
        console.print()
        console.print(_header("  Summary"))
        console.print()
        for point in arch.summary_points:
            console.print(f"  [white]  *[/] {point}")

    # ── Architecture Layers ──
    if arch.architecture_layers:
        console.print()
        console.print(_header("  Architecture"))
        console.print()
        layers_display = "  " + "  ->  ".join(
            f"[bold bright_cyan]{layer}[/]" for layer in arch.architecture_layers
        )
        console.print(layers_display)

    console.print()
    console.print("  [dim]⭐ Enjoying ctx? Give us a star on GitHub: [link=https://github.com/Biya-dev/ctx]https://github.com/Biya-dev/ctx[/link][/]")
    console.print()


def render_deps(deps_result) -> None:
    """Render dependency graph and categorization."""
    console.print()
    console.print(Panel("[bold white]Dependency & Architecture Graph[/]", border_style="bright_cyan"))

    if deps_result.chain_summary:
        console.print()
        console.print(_header("  Dependency Flow Chains"))
        console.print()
        for chain in deps_result.chain_summary:
            console.print(f"  [bright_cyan]>[/] [bold white]{chain}[/]")

    if deps_result.flows:
        console.print()
        console.print(_header("  Internal Layer Connections"))
        console.print()
        for flow in deps_result.flows:
            console.print(f"  [yellow]{flow.from_layer}[/] [dim]----([/][white]{flow.description}[/][dim])--->[/] [green]{flow.to_layer}[/]")

    if deps_result.categorized_deps:
        console.print()
        console.print(_header("  Categorized Package Dependencies"))
        console.print()
        for cat, items in deps_result.categorized_deps.items():
            item_str = ", ".join(items[:10])
            if len(items) > 10:
                item_str += f" (+{len(items)-10} more)"
            console.print(f"  [bold bright_cyan]{cat:<22}[/] [white]{item_str}[/]")

    console.print()


def render_ask(ask_result) -> None:
    """Render ctx ask Q&A output."""
    console.print()
    subtitle = f"AI Provider: {ask_result.ai_provider}" if ask_result.used_ai else "Offline Heuristic Search"
    console.print(Panel(f"[bold bright_cyan]Q:[/] [white]{ask_result.query}[/]", title="[bold bright_cyan]ctx ask[/]", subtitle=subtitle, border_style="bright_cyan"))

    console.print()
    console.print(_header("  Answer"))
    console.print()
    for line in ask_result.answer.splitlines():
        console.print(f"  {line}")

    if ask_result.matches:
        console.print()
        console.print(_header("  Relevant Code Snippets"))
        console.print()
        for m in ask_result.matches[:5]:
            console.print(f"  [bold green]{m.file_path}:{m.line_number}[/] [dim]({m.reason})[/]")
            console.print(f"    [dim white]{m.snippet}[/]")
            console.print()

    console.print()


def render_architecture_detailed(details) -> None:
    """Render detailed architecture breakdown for ctx architecture."""
    console.print()
    console.print(Panel(
        f"[bold white]{details.project_name}[/]\n"
        f"[dim]{details.project_type} | Language: {details.language} | Framework: {details.framework}[/]",
        title="[bold bright_cyan]ctx architecture[/]",
        border_style="bright_cyan",
        padding=(1, 3),
    ))

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("key", style="bold bright_cyan", min_width=20)
    table.add_column("value", style="white")

    table.add_row("API Style", details.api_style)
    table.add_row("Database Tech", details.database_tech)
    table.add_row("Auth Tech", details.auth_tech)
    table.add_row("State/Validation", details.state_tech)
    table.add_row("Package Manager", details.package_manager)

    console.print()
    console.print(table)

    if details.layers:
        console.print()
        console.print(_header("  Architectural Layers & Directories"))
        console.print()
        for layer_name, paths in details.layers.items():
            path_str = ", ".join(paths[:6])
            console.print(f"  [bold yellow]{layer_name:<24}[/] [white]{path_str}[/]")

    if details.key_directories:
        console.print()
        console.print(_header("  Directory Responsibilities"))
        console.print()
        for dpath, purpose in details.key_directories[:8]:
            console.print(f"  [bold green]{dpath:<22}[/] [dim]{purpose}[/]")

    if details.recommendations:
        console.print()
        console.print(_header("  Architecture Recommendations"))
        console.print()
        for rec in details.recommendations:
            console.print(f"  [bold magenta]*[/] {rec}")

    console.print()

