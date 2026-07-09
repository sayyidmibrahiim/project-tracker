<script lang="ts">
  /**
   * Piece D v2 — CICD Workbench (top-level page).
   * Link-only clone flow: user pastes a Bitbucket URL, backend derives/creates
   * the appcode and clones branch `cicd`. VSCode-like workbench, Red-Binder skin:
   * Explorer (repos + tree) · Editor (CodeMirror) · Source Control (git actions).
   * All path/appcode/git safety lives in the backend; this is presentation only.
   */
  import { onMount } from "svelte";
  import { isPywebviewReady } from "../bridge";
  import {
    cicdPreviewLink,
    cicdCloneFromLink,
    cicdJob,
    cicdWorkspace,
    cicdRepoStatus,
    cicdListFiles,
    cicdFileRead,
    cicdFileSave,
    cicdGitAction,
    callBridge,
    type CicdLinkPreview,
    type CicdWorkspace,
    type CicdWorkspaceRepo,
    type CicdRepoStatus,
    type CicdChange,
    type CicdFileNode,
  } from "../bridge";
  import { addToast } from "../stores/toastStore";
  import ConfirmModal from "./ConfirmModal.svelte";
  import CICDCodeEditor from "./CICDCodeEditor.svelte";

  type GitStatus = { installed: boolean; version: string | null };

  let git: GitStatus = $state({ installed: false, version: null });
  let gitChecked = $state(false);
  let checking = $state(true);

  // ── workspace ──
  let appcodes: { name: string; display_name: string }[] = $state([]);
  let appcode = $state("");
  let repos: CicdWorkspaceRepo[] = $state([]);
  let workspaceLoading = $state(false);
  let selectedRepo: CicdWorkspaceRepo | null = $state(null);

  // ── clone bar ──
  let cloneUrl = $state("");
  let cloneUrlTouched = $state(false);
  let preview: CicdLinkPreview | null = $state(null);
  let previewLoading = $state(false);
  let previewError = $state("");
  let appcodeOverride = $state("");
  let cloning = $state(false);
  let confirmCreate: { url: string; appcode: string } | null = $state(null);
  let previewTimer: ReturnType<typeof setTimeout> | undefined;

  // ── file tree + editor ──
  let tree: CicdFileNode[] = $state([]);
  let treeLoading = $state(false);
  let openPath = $state("");
  let openName = $state("");
  let editorContent = $state("");
  let editorHash = $state("");
  let editorDirty = $state(false);
  let editorReadonly = $state(false);
  let readonlyReason = $state("");
  let stale = $state(false);
  let saving = $state(false);
  let loadingFile = $state(false);

  // ── source control ──
  let repoStatus = $state<CicdRepoStatus | null>(null);
  let statusLoading = $state(false);
  let commitMsg = $state("");
  let selectedChanges: Record<string, boolean> = $state({});
  let output = $state("");
  let actionBusy = $state(false);
  let confirmPush = $state(false);

  // ── mobile tabs ──
  let mobileTab: "clone" | "explorer" | "editor" | "git" = $state("explorer");

  const urlValid = $derived(/^https?:\/\/[^\s/]+\/[^\s]+/i.test(cloneUrl.trim()));
  const showUrlError = $derived(cloneUrlTouched && cloneUrl.trim().length > 0 && !urlValid);
  const onCicd = $derived(repoStatus?.branch === "cicd");
  const canCommit = $derived(
    onCicd && commitMsg.trim().length > 0 && Object.values(selectedChanges).some(Boolean) && !actionBusy,
  );

  async function checkGit() {
    checking = true;
    if (!isPywebviewReady()) { checking = false; gitChecked = true; return; }
    const resp = await callBridge<GitStatus>("cicd_git_status");
    if (resp.ok) git = resp.data ?? { installed: false, version: null };
    checking = false;
    gitChecked = true;
  }

  async function loadWorkspace(keepSelection = false) {
    if (!isPywebviewReady()) return;
    workspaceLoading = true;
    const resp = await cicdWorkspace(appcode);
    workspaceLoading = false;
    if (!resp.ok) { addToast(resp.error.message, "error"); return; }
    const ws: CicdWorkspace = resp.data!;
    appcodes = ws.appcodes ?? [];
    if (!appcode) appcode = ws.selected_appcode ?? "";
    repos = ws.repos ?? [];
    if (keepSelection && selectedRepo) {
      const fresh = repos.find((r) => r.repo_id === selectedRepo!.repo_id);
      if (fresh) selectedRepo = fresh;
    }
    if (selectedRepo && !repos.some((r) => r.repo_id === selectedRepo!.repo_id)) {
      clearRepoSelection();
    }
  }

  function clearRepoSelection() {
    selectedRepo = null;
    tree = [];
    repoStatus = null;
    closeFile();
  }

  async function onAppcodeChange() {
    clearRepoSelection();
    await loadWorkspace();
  }

  // ── clone flow ──
  function onUrlInput() {
    preview = null;
    previewError = "";
    if (previewTimer) clearTimeout(previewTimer);
    if (!urlValid) return;
    previewTimer = setTimeout(runPreview, 450);
  }

  async function runPreview() {
    if (!urlValid || !isPywebviewReady()) return;
    previewLoading = true;
    previewError = "";
    const resp = await cicdPreviewLink(cloneUrl.trim());
    previewLoading = false;
    if (!resp.ok) { preview = null; previewError = resp.error.message; return; }
    preview = resp.data!;
    appcodeOverride = preview.needs_confirmation ? preview.appcode_candidate : "";
  }

  async function onCloneClick() {
    if (!preview) { await runPreview(); if (!preview) return; }
    if (preview!.needs_confirmation) {
      confirmCreate = { url: cloneUrl.trim(), appcode: (appcodeOverride || preview!.appcode_candidate).trim() };
      return;
    }
    await doClone(false);
  }

  async function doClone(confirmCreateFlag: boolean) {
    cloning = true;
    const override = preview?.needs_confirmation ? appcodeOverride.trim() : "";
    const resp = await cicdCloneFromLink(cloneUrl.trim(), override, confirmCreateFlag);
    if (!resp.ok) { cloning = false; addToast(resp.error.message, "error", 7000); return; }
    const result = resp.data!;
    if (result.status === "exists") {
      cloning = false;
      addToast(`Repository already cloned: ${result.repo_name}`, "info");
      await afterClone(result.appcode, result.repo_id);
      return;
    }
    pollJob(result.job_id, result.appcode, result.repo_id, result.repo_name);
  }

  async function pollJob(jobId: string, targetAppcode: string, repoId: string, repoName: string) {
    const resp = await cicdJob(jobId);
    if (!resp.ok) { cloning = false; addToast(resp.error.message, "error", 7000); return; }
    const state = resp.data!.state;
    if (state === "cloning") { setTimeout(() => pollJob(jobId, targetAppcode, repoId, repoName), 1200); return; }
    cloning = false;
    if (state === "done") {
      addToast(`Cloned ${repoName} (branch: cicd)`, "success");
      cloneUrl = "";
      cloneUrlTouched = false;
      preview = null;
      await afterClone(targetAppcode, repoId);
    } else {
      addToast(resp.data!.stderr_tail || "Clone failed", "error", 8000);
    }
  }

  async function afterClone(targetAppcode: string, repoId: string) {
    appcode = targetAppcode;
    await loadWorkspace();
    const fresh = repos.find((r) => r.repo_id === repoId);
    if (fresh) await selectRepo(fresh);
  }

  // ── explorer ──
  async function selectRepo(repo: CicdWorkspaceRepo) {
    selectedRepo = repo;
    closeFile();
    treeLoading = true;
    tree = [];
    const [filesResp] = await Promise.all([cicdListFiles(repo.path), refreshStatus(repo)]);
    treeLoading = false;
    if (filesResp.ok) tree = filesResp.data ?? [];
    else addToast(filesResp.error.message, "error");
    mobileTab = "explorer";
  }

  async function refreshStatus(repo: CicdWorkspaceRepo | null = selectedRepo) {
    if (!repo) return;
    statusLoading = true;
    const resp = await cicdRepoStatus(repo.repo_id);
    statusLoading = false;
    if (resp.ok) {
      repoStatus = resp.data!;
      const next: Record<string, boolean> = {};
      for (const c of repoStatus.changes) next[c.rel_path] = selectedChanges[c.rel_path] ?? true;
      selectedChanges = next;
    } else {
      repoStatus = null; // reading is allowed even when status fails; UI shows a banner
    }
  }

  // ── file editor ──
  function relPath(repo: CicdWorkspaceRepo, nodePath: string): string {
    let rel = nodePath.startsWith(repo.path) ? nodePath.slice(repo.path.length) : nodePath;
    return rel.replace(/^[\\/]+/, "").replace(/\\/g, "/");
  }

  async function openFile(node: CicdFileNode) {
    if (node.type !== "file" || !selectedRepo) return;
    const rel = relPath(selectedRepo, node.path);
    loadingFile = true;
    stale = false;
    const resp = await cicdFileRead(selectedRepo.repo_id, rel);
    loadingFile = false;
    if (!resp.ok) {
      // Binary/large/unsupported → read-only card with Open External.
      editorReadonly = true;
      readonlyReason = resp.error.message;
      openPath = rel;
      openName = node.name;
      editorContent = "";
      editorDirty = false;
      mobileTab = "editor";
      return;
    }
    const data = resp.data!;
    openPath = rel;
    openName = node.name;
    editorContent = data.content;
    editorHash = data.hash;
    editorReadonly = false;
    readonlyReason = "";
    editorDirty = false;
    mobileTab = "editor";
  }

  function onEditorChange(next: string) {
    editorContent = next;
    editorDirty = true;
  }

  async function saveFile() {
    if (!selectedRepo || !openPath || editorReadonly || saving) return;
    if (!onCicd) { addToast("Editing allowed only on branch cicd.", "warning"); return; }
    saving = true;
    const resp = await cicdFileSave(selectedRepo.repo_id, openPath, editorContent, editorHash);
    saving = false;
    if (!resp.ok) {
      if (resp.error.code === "STALE_FILE") { stale = true; return; }
      addToast(resp.error.message, "error", 6000);
      return;
    }
    editorHash = resp.data!.hash;
    editorDirty = false;
    stale = false;
    addToast(`Saved ${openName}`, "success", 2500);
    await refreshStatus();
  }

  async function reloadFile() {
    if (!selectedRepo || !openPath) return;
    const resp = await cicdFileRead(selectedRepo.repo_id, openPath);
    if (!resp.ok) { addToast(resp.error.message, "error"); return; }
    editorContent = resp.data!.content;
    editorHash = resp.data!.hash;
    editorDirty = false;
    stale = false;
  }

  async function openExternal() {
    if (!selectedRepo || !openPath) return;
    const abs = `${selectedRepo.path}\\${openPath.replace(/\//g, "\\")}`;
    const resp = await callBridge("file_open", abs);
    if (!resp.ok) addToast("Cannot open file", "error");
  }

  function closeFile() {
    openPath = "";
    openName = "";
    editorContent = "";
    editorHash = "";
    editorDirty = false;
    editorReadonly = false;
    readonlyReason = "";
    stale = false;
  }

  // ── source control ──
  async function runAction(action: string, payload: Record<string, unknown> = {}) {
    if (!selectedRepo) return;
    actionBusy = true;
    output = "";
    const resp = await cicdGitAction(selectedRepo.repo_id, action, payload);
    actionBusy = false;
    if (!resp.ok) { output = resp.error.message; addToast(resp.error.message, "error", 6000); return; }
    output = resp.data?.status === "clean" ? "Already up to date." : `${action}: ok`;
    await refreshStatus();
    await selectRepoTreeRefresh();
  }

  async function selectRepoTreeRefresh() {
    if (!selectedRepo) return;
    const resp = await cicdListFiles(selectedRepo.path);
    if (resp.ok) tree = resp.data ?? [];
  }

  function selectedPaths(): string[] {
    return Object.entries(selectedChanges).filter(([, v]) => v).map(([k]) => k);
  }

  function commit() {
    if (!canCommit) return;
    runAction("commit_selected", { paths: selectedPaths(), message: commitMsg.trim() });
    commitMsg = "";
  }

  function pull() { runAction("pull_ff_only"); }
  function sync() { runAction("sync"); }
  function doPush() { confirmPush = false; runAction("push"); }

  function statusSummary(s: { modified: number; untracked: number; staged: number; clean: boolean }): string {
    if (s.clean) return "clean";
    const parts: string[] = [];
    if (s.modified) parts.push(`${s.modified} modified`);
    if (s.staged) parts.push(`${s.staged} staged`);
    if (s.untracked) parts.push(`${s.untracked} new`);
    return parts.join(" · ") || "clean";
  }

  function changeBadge(status: string): { letter: string; cls: string } {
    if (status === "modified") return { letter: "M", cls: "badge-mod" };
    if (status === "staged") return { letter: "S", cls: "badge-staged" };
    if (status === "untracked") return { letter: "U", cls: "badge-new" };
    if (status === "deleted") return { letter: "D", cls: "badge-del" };
    if (status === "conflict") return { letter: "!", cls: "badge-conflict" };
    return { letter: "•", cls: "badge-clean" };
  }

  function fileBadge(gitStatus: string): { letter: string; cls: string } | null {
    if (!gitStatus) return null;
    return changeBadge(gitStatus);
  }

  onMount(async () => {
    await checkGit();
    if (git.installed) await loadWorkspace();
  });
</script>

{#snippet fileTree(nodes: CicdFileNode[])}
  <ul class="cicd-tree">
    {#each nodes as node}
      <li>
        {#if node.type === "dir"}
          <details open>
            <summary class="cicd-dir"><span class="cicd-caret" aria-hidden="true"></span><span class="cicd-name">{node.name}</span></summary>
            {@render fileTree(node.children)}
          </details>
        {:else}
          {@const badge = fileBadge(node.git_status)}
          <button class="cicd-file" class:active={selectedRepo && openPath === relPath(selectedRepo, node.path)} onclick={() => openFile(node)} title={node.git_status ? `${node.name} — ${node.git_status}` : node.name}>
            {#if badge}<span class="cicd-badge {badge.cls}">{badge.letter}</span>{:else}<span class="cicd-badge badge-none" aria-hidden="true"></span>{/if}
            <span class="cicd-name">{node.name}</span>
          </button>
        {/if}
      </li>
    {/each}
  </ul>
{/snippet}

<section class="screen active" id="screen-cicd">
  <div class="page-header">
    <div class="page-header-left">
      <span class="page-header-icon">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><line x1="6" y1="3" x2="6" y2="15"/><circle cx="18" cy="6" r="3"/><circle cx="6" cy="18" r="3"/><path d="M18 9a9 9 0 0 1-9 9"/></svg>
      </span>
      <h2 class="page-header-title">CICD Workspace</h2>
    </div>
    {#if gitChecked && git.installed}
      <div class="page-header-actions cicd-header-meta">
        {#if git.version}<span class="cicd-git-ver">{git.version.replace("git version ", "git ")}</span>{/if}
        <button class="sb-tab" onclick={() => loadWorkspace(true)} disabled={workspaceLoading} aria-label="Refresh workspace">
          {#if workspaceLoading}<span class="spin" aria-hidden="true"></span> Loading…{:else}↻ Refresh{/if}
        </button>
      </div>
    {/if}
  </div>

  <div class="page-stack active cicd-page">
    {#if checking || !gitChecked}
      <div class="cicd-center" role="status" aria-busy="true"><span class="spin spin-lg" aria-hidden="true"></span><p>Checking Git…</p></div>
    {:else if !git.installed}
      <div class="panel-card cicd-empty">
        <p class="cicd-empty-title">Git CLI is not installed</p>
        <p class="cicd-empty-sub">CICD needs the git command-line tool to clone and read repositories.</p>
        <ol class="cicd-steps">
          <li>Press <kbd>Windows</kbd> + <kbd>R</kbd></li>
          <li>Copy-paste: <code>softwarecenter:softwareid=scopeid_a28b0b90-3c76-4954-b83a-985d0626645a/application_436aff6_de9b_4071_8725_982c241b719d</code></li>
          <li>Press Enter → Company Software Center → click <strong>Install</strong></li>
          <li>Login with your 1Bank account if prompted</li>
        </ol>
        <button class="btn-primary" onclick={checkGit} disabled={checking}>
          {#if checking}<span class="spin" aria-hidden="true"></span> Checking…{:else}Recheck Git Status{/if}
        </button>
      </div>
    {:else}
      <!-- Clone bar (link-only) -->
      <div class="panel-card cicd-clonebar" data-tab="clone" class:tab-active={mobileTab === "clone"}>
        <div class="cicd-clone-input">
          <input
            class="input"
            class:invalid={showUrlError}
            bind:value={cloneUrl}
            oninput={onUrlInput}
            onblur={() => (cloneUrlTouched = true)}
            placeholder="Paste a Bitbucket clone link (branch: cicd)…"
            aria-label="Bitbucket clone URL"
            aria-invalid={showUrlError}
          />
          <button class="btn-primary cicd-clone-btn" onclick={onCloneClick} disabled={cloning || !urlValid}>
            {#if cloning}<span class="spin" aria-hidden="true"></span> Cloning…{:else}Clone{/if}
          </button>
        </div>
        {#if showUrlError}<span class="cicd-hint err">Enter a full HTTP(S) clone URL.</span>{/if}
        {#if previewLoading}
          <span class="cicd-hint" role="status"><span class="spin" aria-hidden="true"></span> Resolving target…</span>
        {:else if previewError}
          <span class="cicd-hint err" role="alert">⚠ {previewError}</span>
        {:else if preview}
          <div class="cicd-preview">
            <div class="cicd-preview-row">
              <span class="cicd-chip">repo <b>{preview.repo_name}</b></span>
              {#if preview.appcode_exists}
                <span class="cicd-chip ok">appcode <b>{preview.matched_appcode}</b> · exists</span>
              {:else}
                <span class="cicd-chip warn">appcode will be created</span>
              {/if}
            </div>
            <div class="cicd-preview-path" title={preview.target_repo_path}>{preview.target_repo_path}</div>
            {#if preview.needs_confirmation}
              <label class="cicd-override">
                <span>Appcode name</span>
                <input class="input" bind:value={appcodeOverride} aria-label="Appcode name to create" />
              </label>
            {/if}
            {#each preview.warnings as w}<span class="cicd-hint warn">⚠ {w}</span>{/each}
          </div>
        {/if}
      </div>

      <!-- Workbench -->
      <div class="cicd-workbench">
        <!-- Explorer -->
        <aside class="panel-card cicd-explorer" data-tab="explorer" class:tab-active={mobileTab === "explorer"}>
          <label class="field cicd-appcode">
            <span>Appcode</span>
            <select class="input" bind:value={appcode} onchange={onAppcodeChange}>
              {#each appcodes as a}<option value={a.name}>{a.display_name || a.name}</option>{/each}
            </select>
          </label>

          <div class="panel-title-row"><span class="panel-title">REPOS</span>{#if repos.length}<span class="cicd-count">{repos.length}</span>{/if}</div>
          {#if workspaceLoading}
            <p class="cicd-hint" role="status"><span class="spin" aria-hidden="true"></span> Loading…</p>
          {:else if repos.length === 0}
            <div class="cicd-empty-inline"><p class="cicd-empty-inline-title">No repositories yet</p><p>Paste a Bitbucket clone link above to start.</p></div>
          {:else}
            <ul class="cicd-repo-list">
              {#each repos as repo}
                <li>
                  <button class="cicd-repo-row" class:selected={selectedRepo?.repo_id === repo.repo_id} onclick={() => selectRepo(repo)} title={repo.name}>
                    <span class="cicd-name cicd-repo-name">{repo.name}</span>
                    <span class="cicd-repo-status" class:clean={repo.status.clean}>{statusSummary(repo.status)}</span>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}

          {#if selectedRepo}
            <div class="panel-title-row cicd-tree-head"><span class="panel-title">FILES</span><span class="panel-subtitle">{selectedRepo.name}</span></div>
            {#if treeLoading}
              <p class="cicd-hint" role="status"><span class="spin" aria-hidden="true"></span> Reading files…</p>
            {:else if tree.length}
              <div class="cicd-tree-wrap">{@render fileTree(tree)}</div>
            {:else}
              <p class="cicd-hint">This repository has no files.</p>
            {/if}
          {/if}
        </aside>

        <!-- Editor -->
        <main class="panel-card cicd-editor-pane" data-tab="editor" class:tab-active={mobileTab === "editor"}>
          {#if !selectedRepo}
            <div class="cicd-pane-empty">Select a repository, then a file to edit.</div>
          {:else if !openPath}
            <div class="cicd-pane-empty">Select a file from the Explorer to open it here.</div>
          {:else}
            <div class="cicd-editor-tabbar">
              <span class="cicd-editor-file">{openName}{#if editorDirty}<span class="cicd-dot-dirty" title="Unsaved changes" aria-label="Unsaved changes"></span>{/if}</span>
              <div class="cicd-editor-actions">
                {#if !editorReadonly}
                  <button class="btn-tiny" onclick={saveFile} disabled={saving || !editorDirty || !onCicd} title={onCicd ? "Save (Ctrl+S)" : "Editing allowed only on branch cicd"}>
                    {#if saving}<span class="spin" aria-hidden="true"></span>{/if} Save
                  </button>
                  <button class="btn-tiny ghost" onclick={reloadFile} disabled={saving}>Reload</button>
                {/if}
                <button class="btn-tiny ghost" onclick={openExternal}>Open External</button>
                <button class="btn-tiny ghost" onclick={closeFile}>Close</button>
              </div>
            </div>
            {#if !onCicd && !editorReadonly}
              <div class="cicd-banner warn">Read-only: this repo is on branch <b>{repoStatus?.branch || "?"}</b>. Switch to <b>cicd</b> to edit.</div>
            {/if}
            {#if stale}
              <div class="cicd-banner err">File changed outside the app. <button class="linklike" onclick={reloadFile}>Reload</button> or <button class="linklike" onclick={openExternal}>Open External</button>.</div>
            {/if}
            {#if loadingFile}
              <div class="cicd-pane-empty"><span class="spin" aria-hidden="true"></span> Opening…</div>
            {:else if editorReadonly}
              <div class="cicd-readonly-card">
                <p class="cicd-readonly-title">Cannot edit this file here</p>
                <p class="cicd-readonly-sub">{readonlyReason}</p>
                <button class="btn-secondary" onclick={openExternal}>Open External</button>
              </div>
            {:else}
              <div class="cicd-editor-host">
                <CICDCodeEditor content={editorContent} fileName={openName} readonly={!onCicd} onChange={onEditorChange} onSave={saveFile} />
              </div>
            {/if}
          {/if}
        </main>

        <!-- Source Control -->
        <aside class="panel-card cicd-scm" data-tab="git" class:tab-active={mobileTab === "git"}>
          <div class="panel-title-row"><span class="panel-title">SOURCE CONTROL</span></div>
          {#if !selectedRepo}
            <p class="cicd-hint">Select a repository to see git status.</p>
          {:else}
            <div class="cicd-branch">
              <span class="cicd-branch-pill" class:off={!onCicd}>{repoStatus?.branch || "?"}</span>
              {#if repoStatus}
                <span class="cicd-ab" title="ahead / behind">↑{repoStatus.ahead} ↓{repoStatus.behind}</span>
                {#if repoStatus.conflicted}<span class="cicd-chip warn">conflict</span>{/if}
              {/if}
              <button class="btn-tiny ghost" onclick={() => refreshStatus()} disabled={statusLoading} aria-label="Refresh status">{#if statusLoading}<span class="spin" aria-hidden="true"></span>{:else}↻{/if}</button>
            </div>
            {#if !onCicd}
              <div class="cicd-banner warn small">Git actions run only on branch <b>cicd</b>.</div>
            {/if}

            {#if repoStatus && repoStatus.changes.length}
              <ul class="cicd-changes">
                {#each repoStatus.changes as c}
                  {@const badge = changeBadge(c.status)}
                  <li class="cicd-change">
                    <label class="cicd-change-label" title={c.rel_path}>
                      <input type="checkbox" bind:checked={selectedChanges[c.rel_path]} disabled={!onCicd} />
                      <span class="cicd-badge {badge.cls}">{badge.letter}</span>
                      <span class="cicd-name">{c.rel_path}</span>
                    </label>
                  </li>
                {/each}
              </ul>
              <textarea class="input cicd-commit-msg" bind:value={commitMsg} placeholder="Commit message" rows="2" disabled={!onCicd}></textarea>
              <div class="cicd-scm-buttons">
                <button class="btn-primary btn-tiny" onclick={commit} disabled={!canCommit}>Commit</button>
                <button class="btn-secondary btn-tiny" onclick={() => (confirmPush = true)} disabled={actionBusy || !onCicd || (repoStatus?.ahead ?? 0) === 0}>Push</button>
                <button class="btn-secondary btn-tiny" onclick={pull} disabled={actionBusy || !onCicd || repoStatus.dirty || (repoStatus?.behind ?? 0) === 0}>Pull</button>
                <button class="btn-secondary btn-tiny" onclick={sync} disabled={actionBusy || !onCicd}>Sync</button>
              </div>
            {:else if repoStatus}
              <p class="cicd-hint">Working tree clean.</p>
              <div class="cicd-scm-buttons">
                <button class="btn-secondary btn-tiny" onclick={sync} disabled={actionBusy || !onCicd}>Sync</button>
              </div>
            {:else}
              <p class="cicd-hint err">Could not read git status for this folder.</p>
            {/if}

            {#if output}<pre class="cicd-output">{output}</pre>{/if}
          {/if}
        </aside>
      </div>

      <!-- Mobile tab bar -->
      <nav class="cicd-mobile-tabs" aria-label="CICD panels">
        <button class:active={mobileTab === "clone"} onclick={() => (mobileTab = "clone")}>Clone</button>
        <button class:active={mobileTab === "explorer"} onclick={() => (mobileTab = "explorer")}>Explorer</button>
        <button class:active={mobileTab === "editor"} onclick={() => (mobileTab = "editor")}>Editor</button>
        <button class:active={mobileTab === "git"} onclick={() => (mobileTab = "git")}>Git</button>
      </nav>
    {/if}
  </div>
</section>

{#if confirmCreate}
  <ConfirmModal
    title="Create appcode folder"
    actionLabel="Create & Clone"
    targetName={`Create appcode "${confirmCreate.appcode}" (with CICD + year folders) and clone branch cicd?`}
    reversible={false}
    onConfirm={() => { const c = confirmCreate!; confirmCreate = null; doClone(true); }}
    onCancel={() => (confirmCreate = null)}
  />
{/if}

{#if confirmPush}
  <ConfirmModal
    title="Push to origin"
    actionLabel="Push"
    targetName={`Push branch cicd of ${selectedRepo?.name ?? ""} to origin?`}
    reversible={false}
    onConfirm={doPush}
    onCancel={() => (confirmPush = false)}
  />
{/if}

<style>
  .cicd-page { display: flex; flex-direction: column; gap: 10px; min-height: 0; }

  /* ── header meta ── */
  .cicd-header-meta { display: flex; align-items: center; gap: 10px; }
  .cicd-git-ver { font-size: 10px; font-weight: 800; color: var(--text-muted); font-family: monospace; }

  /* ── clone bar ── */
  .cicd-clonebar { display: flex; flex-direction: column; gap: 7px; }
  .cicd-clone-input { display: flex; gap: 8px; }
  .cicd-clone-input .input { flex: 1 1 auto; min-width: 0; padding: 6px 10px; font-size: 12px; border: 1px solid var(--input-border); border-radius: 5px; height: 32px; background: #fff; color: var(--color-ink); }
  .cicd-clone-input .input.invalid { border-color: var(--primary-red); }
  .cicd-clone-input .input:focus-visible { outline: 2px solid var(--active-red); outline-offset: 1px; border-color: var(--primary-red); }
  .cicd-clone-btn { height: 32px; flex: 0 0 auto; min-width: 92px; }

  .cicd-preview { display: flex; flex-direction: column; gap: 5px; padding: 8px 10px; background: var(--row-alt); border: 1px solid var(--light-border); border-radius: 6px; }
  .cicd-preview-row { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .cicd-chip { font-size: 10px; font-weight: 800; color: var(--text-secondary); background: #fff; border: 1px solid var(--light-border); border-radius: 4px; padding: 2px 7px; }
  .cicd-chip b { color: var(--color-ink); }
  .cicd-chip.ok { border-color: #bbf7d0; color: #166534; background: #ecfdf3; }
  .cicd-chip.warn { border-color: var(--soft-pink-border); color: var(--primary-red); background: var(--soft-pink-surface); }
  .cicd-preview-path { font-size: 10px; font-family: monospace; color: var(--text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .cicd-override { display: flex; flex-direction: column; gap: 3px; margin-top: 2px; }
  .cicd-override span { font-size: 9px; font-weight: 900; color: var(--color-muted); text-transform: uppercase; }
  .cicd-override .input { padding: 4px 8px; font-size: 11px; border: 1px solid var(--input-border); border-radius: 5px; height: 28px; max-width: 220px; }
  .cicd-override .input:focus-visible { outline: 2px solid var(--active-red); outline-offset: 1px; }

  /* ── workbench grid ── */
  .cicd-workbench { display: grid; grid-template-columns: 288px minmax(0, 1fr) 300px; gap: 10px; flex: 1; min-height: 0; }
  .cicd-explorer, .cicd-scm { display: flex; flex-direction: column; gap: 8px; min-height: 0; overflow: auto; }
  .cicd-editor-pane { display: flex; flex-direction: column; min-height: 0; padding: 0; overflow: hidden; }

  .cicd-appcode { display: flex; flex-direction: column; gap: 4px; }
  .cicd-appcode > span { font-size: 9px; font-weight: 900; color: var(--color-muted); text-transform: uppercase; letter-spacing: 0.3px; }
  .cicd-appcode .input { padding: 5px 9px; font-size: 12px; border: 1px solid var(--input-border); border-radius: 5px; background: #fff; color: var(--color-ink); height: 30px; }
  .cicd-appcode .input:focus-visible { outline: 2px solid var(--active-red); outline-offset: 1px; }

  .cicd-count { margin-left: auto; font-size: 10px; font-weight: 800; color: var(--text-muted); }
  .cicd-tree-head { margin-top: 4px; border-top: 1px solid var(--light-border); padding-top: 8px; }

  .cicd-repo-list, .cicd-tree { list-style: none; margin: 0; padding: 0; }
  .cicd-repo-row { display: flex; flex-direction: column; gap: 1px; align-items: flex-start; width: 100%; text-align: left; padding: 7px 10px; border: none; background: none; border-radius: 5px; cursor: pointer; transition: background 120ms ease-out; }
  .cicd-repo-row:hover { background: var(--soft-pink-surface); }
  .cicd-repo-row.selected { background: var(--soft-pink-surface); box-shadow: inset 2px 0 0 var(--primary-red); }
  .cicd-repo-row:focus-visible { outline: 2px solid var(--active-red); outline-offset: -2px; }
  .cicd-repo-name { font-size: 12px; font-weight: 700; color: var(--color-ink); max-width: 100%; }
  .cicd-repo-status { font-size: 10px; color: var(--text-secondary); max-width: 100%; }
  .cicd-repo-status.clean { color: #15803d; }

  .cicd-tree-wrap { min-height: 0; }
  .cicd-tree { padding-left: 12px; }
  .cicd-dir { display: flex; align-items: center; gap: 5px; cursor: pointer; padding: 2px 4px; border-radius: 4px; font-size: 12px; font-weight: 700; color: var(--color-ink); list-style: none; }
  .cicd-dir::-webkit-details-marker { display: none; }
  .cicd-dir:hover { background: #f3f4f6; }
  .cicd-dir:focus-visible { outline: 2px solid var(--active-red); outline-offset: -2px; }
  .cicd-caret { width: 0; height: 0; border-left: 4px solid var(--text-secondary); border-top: 3px solid transparent; border-bottom: 3px solid transparent; transition: transform 120ms ease-out; flex: none; }
  details[open] > .cicd-dir .cicd-caret { transform: rotate(90deg); }
  .cicd-file { display: flex; align-items: center; gap: 7px; width: 100%; border: none; background: none; cursor: pointer; padding: 2px 4px; border-radius: 4px; font-size: 12px; color: var(--color-ink); font-family: monospace; text-align: left; transition: background 120ms ease-out; }
  .cicd-file:hover { background: #f3f4f6; }
  .cicd-file.active { background: var(--soft-pink-surface); }
  .cicd-file:focus-visible { outline: 2px solid var(--active-red); outline-offset: -2px; }
  .cicd-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }

  .cicd-badge { flex: none; width: 14px; height: 14px; border-radius: 3px; font-size: 9px; font-weight: 900; font-family: Inter, sans-serif; display: inline-flex; align-items: center; justify-content: center; color: #fff; }
  .badge-mod { background: #b45309; }
  .badge-staged { background: #15803d; }
  .badge-new { background: #15803d; }
  .badge-del { background: #6b7280; }
  .badge-conflict { background: var(--primary-red); }
  .badge-clean, .badge-none { background: transparent; }

  /* ── editor pane ── */
  .cicd-editor-tabbar { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 7px 10px; border-bottom: 1px solid var(--light-border); background: var(--row-alt); }
  .cicd-editor-file { font-size: 12px; font-weight: 800; color: var(--color-ink); font-family: monospace; display: inline-flex; align-items: center; gap: 6px; }
  .cicd-dot-dirty { width: 7px; height: 7px; border-radius: 50%; background: var(--primary-red); display: inline-block; }
  .cicd-editor-actions { display: flex; gap: 5px; }
  .cicd-editor-host { flex: 1; min-height: 0; }

  .cicd-readonly-card { padding: 24px; text-align: center; display: flex; flex-direction: column; gap: 8px; align-items: center; }
  .cicd-readonly-title { font-weight: 900; font-size: 13px; color: var(--color-ink); }
  .cicd-readonly-sub { font-size: 11px; color: var(--text-secondary); max-width: 360px; }

  .cicd-pane-empty { flex: 1; display: flex; align-items: center; justify-content: center; gap: 8px; color: var(--text-secondary); font-size: 12px; font-weight: 600; padding: 40px 20px; text-align: center; }

  .cicd-banner { font-size: 11px; font-weight: 700; padding: 6px 10px; display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }
  .cicd-banner.warn { background: var(--soft-pink-surface); color: var(--primary-red); border-bottom: 1px solid var(--soft-pink-border); }
  .cicd-banner.err { background: #fef2f2; color: var(--primary-red); border-bottom: 1px solid #fecaca; }
  .cicd-banner.small { border: 1px solid var(--soft-pink-border); border-radius: 5px; }
  .linklike { background: none; border: none; color: var(--primary-red); font-weight: 800; cursor: pointer; padding: 0; text-decoration: underline; font-size: 11px; }

  /* ── source control ── */
  .cicd-branch { display: flex; align-items: center; gap: 7px; }
  .cicd-branch-pill { font-size: 11px; font-weight: 900; color: #fff; background: var(--color-ink); border-radius: 4px; padding: 2px 9px; font-family: monospace; }
  .cicd-branch-pill.off { background: var(--text-muted); }
  .cicd-ab { font-size: 11px; font-weight: 800; color: var(--text-secondary); font-family: monospace; }
  .cicd-changes { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 1px; max-height: 40vh; overflow: auto; }
  .cicd-change-label { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--color-ink); font-family: monospace; cursor: pointer; padding: 2px 2px; }
  .cicd-change-label input { accent-color: var(--primary-red); }
  .cicd-commit-msg { resize: vertical; padding: 6px 8px; font-size: 11px; border: 1px solid var(--input-border); border-radius: 5px; background: #fff; color: var(--color-ink); font-family: inherit; }
  .cicd-commit-msg:focus-visible { outline: 2px solid var(--active-red); outline-offset: 1px; }
  .cicd-scm-buttons { display: flex; gap: 5px; flex-wrap: wrap; }
  .cicd-output { font-size: 10px; font-family: monospace; color: var(--text-secondary); background: var(--row-alt); border: 1px solid var(--light-border); border-radius: 5px; padding: 6px 8px; white-space: pre-wrap; word-break: break-word; margin: 0; max-height: 120px; overflow: auto; }

  /* ── shared buttons ── */
  .btn-tiny { height: 24px; padding: 0 10px; font-size: 10px; font-weight: 800; border-radius: 4px; border: 1px solid var(--input-border); background: #fff; color: var(--color-ink); cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
  .btn-tiny:hover:not(:disabled) { background: #f3f4f6; }
  .btn-tiny.ghost { background: none; }
  .btn-tiny:disabled { opacity: 0.5; cursor: not-allowed; }
  .btn-tiny:focus-visible { outline: 2px solid var(--active-red); outline-offset: 1px; }

  /* ── empty / loading / hints ── */
  .cicd-center { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 60px 20px; color: var(--text-secondary); font-size: 12px; font-weight: 700; }
  .cicd-empty { text-align: center; padding: 28px 24px; }
  .cicd-empty-title { font-weight: 900; font-size: 15px; color: var(--color-ink); }
  .cicd-empty-sub { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
  .cicd-steps { text-align: left; max-width: 620px; margin: 12px auto 16px; font-size: 12px; line-height: 1.7; color: var(--color-ink); padding-left: 20px; }
  .cicd-steps code { font-size: 10px; word-break: break-all; background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }
  .cicd-empty-inline { font-size: 11px; color: var(--text-secondary); padding: 4px 2px; }
  .cicd-empty-inline-title { font-weight: 800; color: var(--color-ink); margin-bottom: 4px; }
  .cicd-hint { font-size: 11px; font-weight: 700; color: var(--text-secondary); padding: 8px 2px; display: flex; align-items: center; gap: 6px; }
  .cicd-hint.err { color: var(--primary-red); }
  .cicd-hint.warn { color: var(--red-hover); }

  /* ── spinner ── */
  .spin { display: inline-block; width: 11px; height: 11px; border: 2px solid var(--input-border); border-top-color: var(--primary-red); border-radius: 50%; animation: cicd-spin 0.6s linear infinite; vertical-align: -1px; }
  .spin-lg { width: 22px; height: 22px; border-width: 3px; }
  @keyframes cicd-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    .spin { animation: none; border-top-color: var(--input-border); }
    .cicd-repo-row, .cicd-file, .cicd-dir, .cicd-caret { transition: none; }
  }

  /* ── mobile tabs (hidden on desktop) ── */
  .cicd-mobile-tabs { display: none; }

  /* ── responsive ── */
  @media (max-width: 1359px) {
    .cicd-workbench { grid-template-columns: 260px minmax(0, 1fr); grid-template-rows: minmax(0, 1fr); }
    .cicd-scm { grid-column: 2; grid-row: 2; max-height: 260px; }
    .cicd-editor-pane { grid-column: 2; grid-row: 1; }
    .cicd-explorer { grid-row: 1 / span 2; }
  }
  @media (max-width: 959px) {
    .cicd-workbench { display: block; flex: 1; overflow: auto; }
    .cicd-mobile-tabs { display: flex; gap: 4px; padding: 6px; background: var(--surface-dark); border-radius: 6px; position: sticky; bottom: 0; }
    .cicd-mobile-tabs button { flex: 1; height: 30px; font-size: 11px; font-weight: 800; border: none; border-radius: 4px; background: transparent; color: var(--inactive-nav-text); cursor: pointer; }
    .cicd-mobile-tabs button.active { background: var(--primary-red); color: #fff; }
    .cicd-clonebar[data-tab], .cicd-explorer[data-tab], .cicd-editor-pane[data-tab], .cicd-scm[data-tab] { display: none; }
    .cicd-clonebar.tab-active, .cicd-explorer.tab-active, .cicd-editor-pane.tab-active, .cicd-scm.tab-active { display: flex; }
    .cicd-editor-pane { min-height: 60vh; }
    .cicd-explorer, .cicd-scm { max-height: none; }
  }
  @media (min-width: 960px) {
    .cicd-clonebar, .cicd-explorer, .cicd-editor-pane, .cicd-scm { display: flex; }
  }
</style>
