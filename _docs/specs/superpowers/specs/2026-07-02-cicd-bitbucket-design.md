# Piece D Design — CICD Bitbucket Integration

**Date:** 2026-07-02
**Author:** Sayyid M. Ibrahim
**Branch:** `general/cicd-bitbucket` (branch from `main` after Piece A merge)
**Status:** Approved (pending implementation)
**Dependencies:** Piece A (appcode concept + CICD/ folder created empty + appcode.json config)

---

## Context

Piece A created `CICD/` as an empty folder inside each appcode (or shared root). Piece D adds the Bitbucket clone helper, git CLI detection, and in-app repo file browser.

## Scope

1. Git CLI detection + install guidance
2. Bitbucket clone helper (paste HTTP URL -> app clones `cicd` branch)
3. In-app repo file browser (VSCode-like tree with git status)
4. Click file -> open in VSCode/Notepad++/default Windows app
5. CICD folder management (per-appcode or shared root, already in appcode.json)

## Section 1: Git CLI Detection

### Detection

On opening CICD folder view, app checks if `git` CLI is installed:
```python
def check_git_installed() -> bool:
    """Check if git is available on PATH."""
    import shutil
    return shutil.which("git") is not None
```

### If NOT installed — empty state notification

Show in-app notification (English, professional tone):

> "Git CLI is not installed. To install:
> 1. Press Windows + R
> 2. Copy-paste: `softwarecenter:softwareid=scopeid_a28b0b90-3c76-4954-b83a-985d0626645a/application_436aff6_de9b_4071_8725_982c241b719d`
> 3. Press Enter
> 4. Company Software Center will open — click Install
> 5. Login with your 1Bank account if prompted"

Plus a **"Recheck Git Status"** button that re-runs `check_git_installed()`.

### If installed but CICD folder empty

> "CICD folder is empty. No remote repos have been cloned yet.
> To clone a repo:
> 1. Go to https://bitbucket.sgp.dbs.com:8443/dcifgit/projects/dcif_binary
> 2. Select the appcode repo you want to clone
> 3. Select branch: `cicd`
> 4. Click the Clone icon
> 5. Copy the HTTP URL
> 6. Paste it in the field below and click Clone"

Plus an input field for the HTTP clone URL + "Clone" button.

## Section 2: Bitbucket Clone Helper

### Clone flow

1. User pastes Bitbucket HTTP clone URL (e.g. `https://bitbucket.sgp.dbs.com:8443/scm/dcifbinary/myapp.git`)
2. App parses URL → extracts repo name
3. App runs: `git clone -b cicd <url> <CICD_FOLDER>/<repo_name>`
4. Clone runs in background thread (don't block UI)
5. Progress shown: "Cloning myapp (branch: cicd)..."
6. On success: repo appears in file browser
7. On failure: error toast with git stderr

### Bridge methods

```python
def check_git_status(self) -> object:
    """Return {installed: bool, version: str|None}."""

def clone_repo(self, appcode: str, clone_url: str) -> object:
    """Clone repo with branch=cicd into CICD folder. Returns {repo_name, path}."""

def list_cicd_repos(self, appcode: str) -> object:
    """List cloned repos in CICD folder. Returns [{name, path, git_status}]."""
```

### Multiple repos per appcode

User can clone multiple repos. Each repo is a subfolder inside `CICD/`:
```
{appcode}/CICD/
  myapp.git/          <- cloned repo 1
  anotherapp.git/     <- cloned repo 2
```

## Section 3: In-App Repo File Browser

### File tree (VSCode-like)

- Tree view of repo files/folders (expand/collapse)
- Git status indicators per file:
  - Modified (M) — orange dot
  - Untracked (U) — green dot
  - Staged (S) — green check
  - Clean — no indicator
- Git status obtained via `git status --porcelain` in the repo folder

### Click file -> open externally

When user clicks a file name:
- Opens in default Windows application (VSCode if installed, Notepad++, or OS default)
- Uses `os.startfile(filepath)` (existing pattern)

### Bridge methods

```python
def list_repo_files(self, repo_path: str) -> object:
    """Return file tree with git status. [{name, path, type: 'file'|'dir', git_status, children}]"""

def open_repo_file(self, file_path: str) -> object:
    """Open file in default OS application."""
```

### Frontend

- New component: `CICDBrowser.svelte` (or section in Settings/ProjectDetails)
- Tree component for file listing (reuse existing tree patterns if any)
- Git status badges (colored dots)
- Clone URL input + Clone button
- Empty states (git not installed / no repos)

## Section 4: CICD Folder Configuration

Already in Piece A's `appcode.json`:
- `cicd_location: "per_appcode" | "shared_root"`
- `cicd_shared_path: Path | None`

Piece D adds UI in Settings to switch between per-appcode and shared root, and shows which folder is active.

## Section 5: Error Handling

| Edge case | Handling |
|-----------|----------|
| Git not installed | Empty state with install instructions + recheck button |
| Clone URL invalid | Error: "Invalid URL format" |
| Clone fails (auth) | Error toast with git stderr (may contain auth instructions) |
| Clone fails (network) | Error toast "Cannot reach Bitbucket. Check VPN/connection." |
| Repo folder deleted externally | Repo disappears from list on next refresh |
| Git status fails (not a git repo) | Show files without status indicators |
| File open fails | Error toast "Cannot open file" |

## Section 6: Testing

- `tests/test_git_detection.py` — check_git_installed (mock shutil.which)
- `tests/test_clone_repo.py` — clone flow (mock subprocess)
- `tests/test_repo_file_browser.py` — file tree + git status parsing

Manual: open CICD folder -> verify git detection -> paste clone URL -> verify clone -> verify file tree -> click file -> verify opens externally.

## Out of Scope

- Approval automation (Piece C)
- _cr-docs editable files (Piece B — already done)
- Git operations beyond clone (no pull/commit/push — user does that externally)
