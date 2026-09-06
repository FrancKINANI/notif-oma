# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository reorganization (modular `src/` structure)
- Python package `omaping` with proper entry points
- Pyproject.toml with build config, ruff, mypy
- Package.json with prettier for JS/QML formatting
- EditorConfig, Prettier config, .gitignore
- CONTRIBUTING.md, CHANGELOG.md
- Documentation updates for new name "Omaping"

### Changed
- Renamed from "Omapager" to "Omaping"
- Plugin ID: `njpatel.omapager` → `franckinani.omaping`
- IPC targets: `omapager` → `omaping`, `omapager.panel` → `omaping.panel`
- State paths: `~/.local/state/omarchy/omapager/` → `~/.local/state/omarchy/omaping/`
- Config paths: `~/.config/omarchy/omapager/` → `~/.config/omarchy/omaping/`
- Binary names: `omapager-*` → `omaping-*`

### Removed
- Flat file structure in repository root
- Legacy `bin/` directory (replaced by `src/python/scripts/`)

## [0.1.0] - 2024-09-06

### Added
- Notification daemon for Omarchy (Quickshell)
- Stacking deck with per-source grouping
- Content detection: verification codes, links, meetings, phone numbers
- Sender action buttons (Reply, Mark as read, etc.)
- Inline phone reply via KDE Connect
- Smart window routing (focus existing window or open new)
- Per-source snooze with configurable durations
- Silence mode with history panel
- Verification code bypass for quiet modes
- Multi-source icon resolution (config → theme → desktop → web)
- History persistence (7 days / 200 entries)
- Demo script with multiple scenes

### Fixed
- Icon resolution for web apps (Slack, WhatsApp, etc.)
- Grouping by source key instead of app name
- Animation stalls from binding loops
- Reply field stability while typing

---

## Release Notes Template

### Added
- New features

### Changed
- Changes in existing functionality

### Deprecated
- Soon-to-be removed features

### Removed
- Removed features

### Fixed
- Bug fixes

### Security
- Vulnerability fixes