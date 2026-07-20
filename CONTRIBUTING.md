# Contributing to ctx

First off, thank you for considering contributing to `ctx`! 

Our goal is to build the definitive tool for understanding codebases and generating AI context. We welcome contributions of all kinds: bug reports, feature requests, documentation improvements, and code.

## Getting Started

1. Fork the repository and clone it locally.
2. Install the package in editable mode with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
   *(Note: if using a virtual environment, activate it first!)*
3. Run the test suite to ensure everything is working:
   ```bash
   pytest
   ```

## Development Workflow

1. Create a branch for your feature or bugfix (`git checkout -b feature/my-new-feature`).
2. Make your changes.
3. Ensure your code passes linting and type-checking:
   ```bash
   ruff check .
   mypy ctx tests
   ```
4. Write tests for your changes. We aim to keep coverage high.
5. Commit your changes with a clear, descriptive message.
6. Push to your fork and submit a Pull Request.

## Issues and Feature Requests

Please check the issue tracker before opening a new issue to avoid duplicates.

If you are proposing a new feature, especially a new `ctx` command, please open an issue first to discuss the design and ensure it aligns with the project's goals.

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in your interactions with other contributors.
