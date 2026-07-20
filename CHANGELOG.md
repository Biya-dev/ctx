# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-20

### Added
- **Core CLI**: `ctx .` command for 1-second codebase scanning and architecture summary.
- **AI Context Generation**: `ctx export . --[chatgpt|claude|gemini|cursor]` for instant prompt creation.
- **Architecture Analysis**: Deep detection of frameworks, languages, databases, auth, and state management.
- **Dependency Graph**: `ctx deps` command to visualize package relationships and execution flows.
- **Codebase Q&A**: `ctx ask` command with offline heuristic search and optional LLM integration.
- **Interactive TUI**: `ctx tui` powered by Textual for browsing project context locally.
- **Utilities**: 
  - `ctx docs` for scaffolding README/CONTRIBUTING files.
  - `ctx security` for detecting leaked secrets and outdated packages.
  - `ctx diagram` for Mermaid JS generation.
  - `ctx pr` and `ctx onboard` for collaborative workflows.

### Changed
- Complete overhaul of product positioning to focus on codebase understanding and AI context generation.

### Fixed
- Addressed Windows CP1252 rendering crashes by standardizing ASCII fallback rendering.
- Fixed strict type hint checking and missing stubs.
