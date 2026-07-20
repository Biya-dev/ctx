"""Interactive Terminal User Interface for ctx."""

from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Input, ListItem, ListView, Log, Markdown, Static

from ctx.analyzers.architecture import (
    analyze_architecture,
    analyze_detailed_architecture,
)
from ctx.analyzers.ask import ask_codebase
from ctx.analyzers.deps import analyze_dependencies
from ctx.scanner.env import scan_env
from ctx.scanner.filesystem import scan_filesystem
from ctx.scanner.git_info import scan_git
from ctx.scanner.packages import scan_packages


class CtxApp(App):
    """A Textual app to navigate codebase context."""

    CSS = """
    Screen {
        background: $surface;
    }

    #sidebar {
        width: 25;
        height: 100%;
        dock: left;
        background: $panel;
        border-right: vkey $primary;
    }

    #main-content {
        height: 100%;
        padding: 1 2;
        overflow: auto;
    }

    ListItem {
        padding: 1 2;
    }
    
    #ask-input {
        dock: bottom;
        margin: 1;
    }
    
    #ask-log {
        height: 100%;
        border: solid $primary;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("d", "toggle_dark", "Toggle dark mode", show=True),
    ]

    def __init__(self, root: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.root = root
        # Pre-scan the project
        self.fs = scan_filesystem(root)
        self.git = scan_git(root)
        self.pkg = scan_packages(root)
        self.env = scan_env(root, self.fs.files)
        self.arch = analyze_architecture(self.fs, self.pkg, root)

        self.overview_md = self._build_overview()
        self.architecture_md = self._build_architecture()
        self.deps_md = self._build_deps()

    def _build_overview(self) -> str:
        project_name = self.pkg.project_name or self.root.name
        md = f"# {project_name}\n\n"
        md += f"**Type:** {self.arch.project_type}\n"
        md += f"**Language:** {self.pkg.language}\n"
        md += f"**Framework:** {self.pkg.framework}\n"
        md += f"**Package Manager:** {self.pkg.package_manager}\n\n"

        if self.fs.main_folders:
            md += "## Directory Structure\n"
            for f in self.fs.main_folders:
                md += f"- `{f}`\n"

        if self.fs.important_files:
            md += "\n## Important Files\n"
            for f in self.fs.important_files[:10]:
                md += f"- `{f}`\n"

        return md

    def _build_architecture(self) -> str:
        details = analyze_detailed_architecture(self.fs, self.pkg, self.arch, self.root)
        md = "# Architecture\n\n"
        md += f"- **API Style:** {details.api_style}\n"
        md += f"- **Database:** {details.database_tech}\n"
        md += f"- **Auth:** {details.auth_tech}\n"
        md += f"- **State:** {details.state_tech}\n\n"

        if details.layers:
            md += "## Layers\n"
            for layer, paths in details.layers.items():
                md += f"### {layer}\n"
                for p in paths:
                    md += f"- `{p}`\n"
        return md

    def _build_deps(self) -> str:
        deps = analyze_dependencies(self.fs, self.pkg, self.root)
        md = "# Dependencies & Flows\n\n"

        if deps.chain_summary:
            md += "## Flow Chains\n"
            for c in deps.chain_summary:
                md += f"- {c}\n"

        if deps.categorized_deps:
            md += "\n## Package Categories\n"
            for cat, items in deps.categorized_deps.items():
                md += f"### {cat}\n"
                md += f"{', '.join(items)}\n"
        return md

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()

        with Horizontal():
            with ListView(id="sidebar"):
                yield ListItem(Static("Overview", classes="menu-item"), id="menu-overview")
                yield ListItem(Static("Architecture", classes="menu-item"), id="menu-arch")
                yield ListItem(Static("Dependencies", classes="menu-item"), id="menu-deps")
                yield ListItem(Static("Q&A (Ask)", classes="menu-item"), id="menu-ask")

            with Vertical(id="main-content"):
                yield Markdown(self.overview_md, id="markdown-view")
                yield Vertical(
                    Log(id="ask-log"),
                    Input(placeholder="Ask a question about the codebase...", id="ask-input"),
                    id="ask-view"
                )

        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#ask-view").display = False

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle menu selection."""
        md_view = self.query_one("#markdown-view", Markdown)
        ask_view = self.query_one("#ask-view")

        if event.item.id == "menu-overview":
            md_view.display = True
            ask_view.display = False
            md_view.update(self.overview_md)
        elif event.item.id == "menu-arch":
            md_view.display = True
            ask_view.display = False
            md_view.update(self.architecture_md)
        elif event.item.id == "menu-deps":
            md_view.display = True
            ask_view.display = False
            md_view.update(self.deps_md)
        elif event.item.id == "menu-ask":
            md_view.display = False
            ask_view.display = True
            self.query_one("#ask-input").focus()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Q&A input."""
        if not event.value.strip():
            return

        log = self.query_one("#ask-log", Log)
        input_widget = self.query_one("#ask-input", Input)

        question = event.value
        input_widget.value = ""

        log.write_line(f"\n[bold cyan]Q: {question}[/]")

        # Ask question
        result = ask_codebase(question, self.fs, self.pkg, self.arch, self.root)

        log.write_line("[bold green]Answer:[/]")
        log.write_line(result.answer)
        if result.matches:
            log.write_line("\n[dim]Relevant Snippets:[/]")
            for m in result.matches[:3]:
                log.write_line(f"  {m.file_path}:{m.line_number} - {m.snippet.strip()}")


def run_tui(root: Path) -> None:
    """Run the TUI."""
    app = CtxApp(root)
    app.run()
