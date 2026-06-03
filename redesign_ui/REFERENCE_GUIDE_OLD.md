# REFERENCE_GUIDE_OLD.md

> Historical reference only. This file is not active Claude Code instruction. Root `../CLAUDE.md` and `../PRD.md` are authoritative.

This file previously provided guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

`redesign_ui/` adalah **UI design laboratory** untuk HTML/Tailwind frontend yang diintegrasikan via pywebview.

File `.py` PyQt6 yang ada = **referensi UX/userflow ONLY**. Jangan generate PyQt6 code baru di sini.
Frontend baru = HTML files dengan Tailwind CDN.

**Parent project context:** See `../CLAUDE.md` for full project documentation, environment constraints, and implementation phases.

## Directory Purpose

This directory serves as a **UI design laboratory** where:

- HTML screens di-prototype dengan Tailwind CDN
- Data contract antara JS dan Python API ditentukan
- User flow ditest sebelum wire ke backend services

**Key constraint:** File `.py` lama = referensi UX/userflow ONLY. Jangan jadikan basis generate code baru.

## File Descriptions

| File                          | Purpose                                                                          |
| ----------------------------- | -------------------------------------------------------------------------------- |
| `project_tracker_clean.py`    | Main dashboard UI prototype with project list, inline editing, state transitions |
| `project_details_redesign.py` | Project details split-pane layout with CR/drone ticket inline editing            |
| `settings_redesign.py`        | Settings screen prototype with theme toggle, display name, folder path config    |
| `report_redesign.py`          | Report generation UI with filters, export options, date range selection          |
| `second_brain_redesign.py`    | Second Brain notes editor with rich text, tagging, search                        |
| `automations_redesign.py`     | Automation rules UI with email/Teams trigger configuration                       |

## Running Redesign Files

Each file is a standalone PyQt6 application. Run directly:

```bash
# From redesign_ui/ directory
python project_tracker_clean.py
python project_details_redesign.py
# etc.
```

**Linux preview:** ✅ Allowed. PyQt6 runs on Linux. Windows-only integrations (Outlook, Teams, send2trash) are stubbed/skipped.

**Windows testing:** Manual testing on Windows laptop required for final verification.

## Design Patterns Used

### Color Palette (Catppuccin Mocha)

- `C_ORANGE = "#BC6C2C"` — Primary action color
- `C_DARK = "#2D3D34"` — Dark backgrounds
- `C_LIGHT = "#D0D4D2"` — Light text/backgrounds
- `C_SAGE = "#ADB9B2"` — Secondary accents
- `C_OLIVE = "#949A89"` — Tertiary accents

All colors defined at module top level. No inline hex colors in production code.

### Animations

- `QPropertyAnimation` for smooth transitions
- `QEasingCurve` for easing functions
- `QVariantAnimation` for custom property animations
- Sidebar collapse/expand, theme toggle, hover effects

### Inline Editing Components

- `InlineEditLabel` — Click-to-edit text fields
- `StateBadgeCombo` — State selector with badge styling
- Used in Dashboard and Project Details for CR/drone ticket/state editing

### Theme System

- Catppuccin Mocha (dark) and Latte (light) themes
- QSS stylesheets for centralized styling
- Theme toggle button in sidebar
- Dynamic color switching without restart

## Integration into Main App

When an HTML prototype is finalized:

1. Copy HTML/JS ke `../frontend/`
2. Wire ke `AppAPI` method di pywebview entry point
3. Connect ke `../project_tracker/services/` via js_api bridge
4. Terapkan threading rule untuk semua COM calls (lihat `../CLAUDE.md`)

**Frontend baru = HTML only. Jangan integrate PyQt6 code.**

## Testing Redesigns

### Linux (Pop!\_OS)

```bash
# Run individual redesign file
python project_tracker_clean.py

# Verify:
# - UI renders without errors
# - Animations smooth
# - Inline editing works
# - Theme toggle works
# - No crashes on interaction
```

### Windows (Manual)

- Visual verification of colors, fonts, spacing
- Unicode symbols render correctly (☀, 🌙, ☰, 📁, 🗑)
- Outlook/Teams stubs don't crash
- Performance acceptable

## Key Rules

- **No production imports:** Don't import from `../project_tracker/` directly. Keep redesigns self-contained.
- **Platform guards:** Use `if sys.platform == "win32":` for Windows-only code (Outlook, Teams, send2trash).
- **QSS centralization:** All colors/fonts in QSS stylesheets, not inline.
- **No database:** Use mock data only. No SQLite, no file I/O to app config.
- **Feature documentation maintenance:** Update `UI_FEATURE_DOCUMENTATION.md` in the same work session whenever any UI feature, user flow, action, tab, panel, empty state, search behavior, file handling behavior, or responsive behavior is added, changed, renamed, or removed.
- **Atomic testing:** Each file runs standalone. No dependencies on other redesigns.

## Common Commands

```bash
# Run a redesign file
python project_tracker_clean.py

# Check for syntax errors
python -m py_compile project_tracker_clean.py

# Format code (if using black)
black project_tracker_clean.py

# From parent directory, run all tests (Phase A-B only, not redesigns)
rtk /home/sayyidmibrahim/Development/projects/project_tracker_dbs/.venv/bin/python -m pytest tests/ -v
```

## Related Documentation

- `../PRD.md` — Full product requirements
- `../PROJECT_STATUS.md` — Current implementation status
- `../CLAUDE.md` — Main project guidance (RTK, environment constraints, phases)
- `../project_tracker/` — Production application code
- `UI_FEATURE_DOCUMENTATION.md` — User-facing redesign UI feature and flow documentation; keep updated when UI behavior changes

<!-- rtk-instructions v2 -->

# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:

```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)

```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)

```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)

```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
#rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)

```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)

```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)

```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)

```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)

```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)

```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands

```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category         | Commands                       | Typical Savings |
| ---------------- | ------------------------------ | --------------- |
| Tests            | vitest, playwright, cargo test | 90-99%          |
| Build            | next, tsc, lint, prettier      | 70-87%          |
| Git              | status, log, diff, add, commit | 59-80%          |
| GitHub           | gh pr, gh run, gh issue        | 26-87%          |
| Package Managers | pnpm, npm, npx                 | 70-90%          |
| Files            | ls, read, grep, find           | 60-75%          |
| Infrastructure   | docker, kubectl                | 85%             |
| Network          | curl, wget                     | 65-70%          |

Overall average: **60-90% token reduction** on common development operations.

<!-- /rtk-instructions -->
