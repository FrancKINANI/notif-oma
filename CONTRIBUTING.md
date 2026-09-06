# Contributing to Omaping

Thank you for considering a contribution! Here's how to help.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/yourname/omaping.git`
3. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   npm install
   ```
4. Make your changes
5. Run tests and linting:
   ```bash
   pytest tests/python/
   npm run format:check
   npm run lint
   ```
6. Submit a pull request

## Code Style

- **Python**: Ruff (configured in `pyproject.toml`) — 4-space indent, 100-char lines
- **JavaScript/QML**: Prettier (configured in `.prettierrc`) — 2-space indent, single quotes
- **EditorConfig**: Enforces basics across editors (`.editorconfig`)

## Architecture Overview

| Layer | Location | Responsibility |
|-------|----------|----------------|
| Daemon | `src/qml/services/Service.qml` | DBus service, state, animation clock |
| UI Cards | `src/qml/components/Toast.qml` | Single notification card |
| Actions | `src/qml/components/DeedButton.qml` | Action buttons (copy, open, reply) |
| Bar/Panel | `src/qml/widgets/Widget.qml` | Bar indicator + history panel |
| Detection | `src/js/core/Detect.js` | Code/link/phone extraction |
| Layout | `src/js/core/Layout.js` | Deck positioning math |
| Markup | `src/js/core/Markup.js` | HTML sanitization, source detection |
| Persistence | `src/js/core/Store.js` | Snapshot, normalize, store API |
| Store CLI | `src/python/omaping/store.py` | File-based notification store |
| Icons | `src/python/omaping/icon.py` | Multi-source icon resolution |
| KDE Connect | `src/python/omaping/kdeconnect.py` | Phone reply bridge |

## Testing

- **Unit tests**: `tests/python/` — test pure functions in isolation
- **Integration tests**: `tests/integration/` — test CLI commands end-to-end
- Run with: `pytest tests/`

## Pull Request Guidelines

- Keep changes focused — one logical change per PR
- Update docs/README if user-facing behavior changes
- Add tests for new functionality
- Follow the existing code style (run formatters before committing)
- Write clear commit messages

## Reporting Issues

- Search existing issues first
- Include: Omarchy version, Quickshell version, steps to reproduce
- For crashes: include relevant log output from `journalctl --user -u omarchy-shell`

## License

By contributing, you agree that your contributions will be licensed under the Apache-2.0 license.