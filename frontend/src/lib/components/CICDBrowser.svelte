<script lang="ts">
  /**
   * Piece D — CICD Bitbucket browser (top-level page).
   * Appcode dropdown → clone URL + Clone → repo list → recursive file tree.
   * Hardened: git-check gate (no empty-state flash), per-region loading,
   * clone-URL validation, native folder picker for shared root, guarded
   * config switch, keyboard focus states, responsive stack at 3 sizes.
   */
  import { onMount } from "svelte";
  import { callBridge, isPywebviewReady } from "../bridge";
  import { addToast } from "../stores/toastStore";

  type GitStatus = { installed: boolean; version: string | null };
  type AppCode = { name: string; path: string; display_name: string; cicd_location: string; cicd_shared_path: string | null };
  type RepoStatus = { modified: number; untracked: number; staged: number; clean: boolean };
  type Repo = { name: string; path: string; status: RepoStatus };
  type FileNode = { name: string; path: string; type: "file" | "dir"; git_status: string; children: FileNode[] };

  let git: GitStatus = $state({ installed: false, version: null });
  let gitChecked = $state(false); // gate: don't render install-steps until the first check resolves
  let checking = $state(true);

  let appcodes: AppCode[] = $state([]);
  let appcode: string = $state("");
  let repos: Repo[] = $state([]);
  let reposLoading = $state(false);
  let selectedRepo: string = $state("");
  let tree: FileNode[] = $state([]);
  let treeLoading = $state(false);

  let cloneUrl: string = $state("");
  let cloneUrlTouched = $state(false);
  let cloning: boolean = $state(false);
  let errorMsg: string = $state("");

  // Config editing (guarded — a shared_root is only persisted once a path exists).
  let locOverride: string = $state(""); // "" = follow the saved config
  let sharedDraft: string = $state("");
  let browsing = $state(false);

  let currentConfig = $derived(appcodes.find((a) => a.name === appcode));
  let effectiveLoc = $derived(locOverride || currentConfig?.cicd_location || "per_appcode");
  // Lenient Bitbucket HTTP(S) clone-URL shape: scheme + host + a path segment.
  let urlValid = $derived(/^https?:\/\/[^\s/]+\/[^\s]+/i.test(cloneUrl.trim()));
  let showUrlError = $derived(cloneUrlTouched && cloneUrl.trim().length > 0 && !urlValid);
  let canClone = $derived(!cloning && !!appcode && urlValid);

  async function checkGit() {
    checking = true;
    if (!isPywebviewReady()) { checking = false; gitChecked = true; return; }
    const resp = await callBridge<GitStatus>("cicd_git_status");
    if (resp.ok) git = resp.data ?? { installed: false, version: null };
    checking = false;
    gitChecked = true;
  }

  async function loadAppcodes() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<AppCode[]>("appcode_list");
    if (resp.ok) {
      appcodes = resp.data ?? [];
      if (!appcode && appcodes.length) appcode = appcodes[0].name;
    }
  }

  async function loadRepos() {
    if (!appcode || !isPywebviewReady()) { repos = []; return; }
    reposLoading = true;
    errorMsg = "";
    const resp = await callBridge<Repo[]>("cicd_list_repos", appcode);
    reposLoading = false;
    if (!resp.ok) { errorMsg = resp.error.message; repos = []; return; }
    repos = resp.data ?? [];
    if (selectedRepo && !repos.some((r) => r.name === selectedRepo)) {
      selectedRepo = "";
      tree = [];
    }
  }

  async function selectRepo(repo: Repo) {
    if (selectedRepo === repo.name && tree.length) return;
    selectedRepo = repo.name;
    treeLoading = true;
    tree = [];
    const resp = await callBridge<FileNode[]>("cicd_list_files", repo.path);
    treeLoading = false;
    if (resp.ok) tree = resp.data ?? [];
    else { errorMsg = resp.error.message; }
  }

  async function startClone() {
    if (!canClone) return;
    const url = cloneUrl.trim();
    cloning = true;
    const resp = await callBridge<{ repo_name: string }>("cicd_clone", appcode, url);
    if (!resp.ok) { cloning = false; addToast(resp.error.message, "error", 6000); return; }
    pollClone(resp.data!.repo_name);
  }

  async function pollClone(repoName: string) {
    const resp = await callBridge<{ status: string; error: string }>("cicd_clone_status", repoName);
    if (!resp.ok) { cloning = false; addToast(resp.error.message, "error", 6000); return; }
    const { status, error } = resp.data!;
    if (status === "cloning") { setTimeout(() => pollClone(repoName), 1200); return; }
    cloning = false;
    if (status === "done") {
      addToast(`Cloned ${repoName} (branch: cicd)`, "success");
      cloneUrl = "";
      cloneUrlTouched = false;
      await loadRepos();
      const fresh = repos.find((r) => r.name === repoName);
      if (fresh) await selectRepo(fresh); // auto-open the repo we just cloned
    } else {
      addToast(error || "Clone failed", "error", 8000);
    }
  }

  async function openFile(node: FileNode) {
    if (node.type !== "file") return;
    const resp = await callBridge("file_open", node.path);
    if (!resp.ok) addToast("Cannot open file", "error");
  }

  async function onAppcodeChange() {
    selectedRepo = "";
    tree = [];
    locOverride = "";
    sharedDraft = "";
    await loadRepos();
  }

  // ── config (guarded) ────────────────────────────────────────────────
  function pickPerAppcode() {
    locOverride = "";
    if (currentConfig?.cicd_location === "per_appcode") return; // already saved
    saveConfig("per_appcode", "");
  }

  function pickSharedRoot() {
    locOverride = "shared_root";
    sharedDraft = currentConfig?.cicd_shared_path ?? "";
  }

  async function browseShared() {
    if (!isPywebviewReady()) { addToast("Folder picker needs the desktop app — type the path.", "warning"); return; }
    browsing = true;
    const resp = await callBridge<{ path: string | null }>("util_choose_folder");
    browsing = false;
    if (resp.ok && resp.data?.path) sharedDraft = resp.data.path;
  }

  function applyShared() {
    const path = sharedDraft.trim();
    if (!path) { addToast("Choose a shared CICD folder first.", "warning"); return; }
    saveConfig("shared_root", path);
  }

  async function saveConfig(location: string, sharedPath: string) {
    if (!appcode) return;
    const resp = await callBridge<AppCode>("appcode_update_config", appcode, {
      cicd_location: location,
      cicd_shared_path: sharedPath,
    });
    if (resp.ok) {
      appcodes = appcodes.map((a) => (a.name === appcode ? (resp.data as AppCode) : a));
      locOverride = "";
      addToast("CICD folder updated", "success");
      await loadRepos();
    } else {
      addToast(resp.error.message, "error");
    }
  }

  // Letter badge (not color-only) for per-file git status.
  function fileBadge(gitStatus: string): { letter: string; cls: string } | null {
    if (gitStatus === "modified") return { letter: "M", cls: "badge-mod" };
    if (gitStatus === "untracked") return { letter: "U", cls: "badge-new" };
    if (gitStatus === "staged") return { letter: "S", cls: "badge-staged" };
    return null;
  }

  function statusSummary(s: RepoStatus): string {
    if (s.clean) return "clean";
    const parts: string[] = [];
    if (s.modified) parts.push(`modified: ${s.modified}`);
    if (s.untracked) parts.push(`untracked: ${s.untracked}`);
    if (s.staged) parts.push(`staged: ${s.staged}`);
    return parts.join(", ") || "clean";
  }

  onMount(async () => {
    await checkGit();
    if (git.installed) {
      await loadAppcodes();
      await loadRepos();
    }
  });
</script>

{#snippet fileTree(nodes: FileNode[])}
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
          <button class="cicd-file" onclick={() => openFile(node)} title={node.git_status ? `${node.name} — ${node.git_status}` : node.name}>
            {#if badge}<span class="cicd-badge {badge.cls}">{badge.letter}</span>{:else}<span class="cicd-badge badge-clean" aria-hidden="true"></span>{/if}
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
      <h2 class="page-header-title">CICD</h2>
    </div>
    {#if gitChecked && git.installed}
      <div class="page-header-actions">
        <button class="sb-tab" onclick={loadRepos} disabled={reposLoading} aria-label="Refresh repositories">
          {#if reposLoading}<span class="spin" aria-hidden="true"></span> Loading…{:else}↻ Refresh{/if}
        </button>
      </div>
    {/if}
  </div>

  <div class="page-stack active">
    {#if checking || !gitChecked}
      <div class="cicd-center" role="status" aria-busy="true">
        <span class="spin spin-lg" aria-hidden="true"></span>
        <p>Checking Git…</p>
      </div>
    {:else if !git.installed}
      <div class="panel-card cicd-empty">
        <p class="cicd-empty-title">Git CLI is not installed</p>
        <p class="cicd-empty-sub">CICD needs the git command-line tool to clone and read repositories.</p>
        <ol class="cicd-steps">
          <li>Press <kbd>Windows</kbd> + <kbd>R</kbd></li>
          <li>Copy-paste: <code>softwarecenter:softwareid=scopeid_a28b0b90-3c76-4954-b83a-985d0626645a/application_436aff6_de9b_4071_8725_982c241b719d</code></li>
          <li>Press Enter → Company Software Center opens → click <strong>Install</strong></li>
          <li>Login with your 1Bank account if prompted</li>
        </ol>
        <button class="btn-primary" onclick={checkGit} disabled={checking}>
          {#if checking}<span class="spin" aria-hidden="true"></span> Checking…{:else}Recheck Git Status{/if}
        </button>
      </div>
    {:else}
      <div class="panel-card cicd-controls">
        <label class="field cicd-appcode">
          <span>Appcode</span>
          <select class="input" bind:value={appcode} onchange={onAppcodeChange}>
            {#each appcodes as a}<option value={a.name}>{a.display_name}</option>{/each}
          </select>
        </label>
        <div class="field cicd-url">
          <span>Bitbucket clone URL <em>(branch: cicd)</em></span>
          <input
            class="input"
            class:invalid={showUrlError}
            bind:value={cloneUrl}
            onblur={() => (cloneUrlTouched = true)}
            placeholder="https://bitbucket.sgp.dbs.com:8443/scm/…/myapp.git"
            aria-invalid={showUrlError}
            aria-describedby="cicd-url-hint"
          />
          {#if showUrlError}<span class="cicd-url-hint err" id="cicd-url-hint">Enter a full HTTP(S) clone URL.</span>{/if}
        </div>
        <button class="btn-primary cicd-clone-btn" onclick={startClone} disabled={!canClone}>
          {#if cloning}<span class="spin" aria-hidden="true"></span> Cloning…{:else}Clone{/if}
        </button>
      </div>

      {#if currentConfig}
        <fieldset class="panel-card cicd-config">
          <legend>CICD folder location</legend>
          <label class="cicd-radio">
            <input type="radio" name="cicd-loc" checked={effectiveLoc !== "shared_root"} onchange={pickPerAppcode} />
            <span>Per appcode <code>{appcode}/CICD</code></span>
          </label>
          <label class="cicd-radio">
            <input type="radio" name="cicd-loc" checked={effectiveLoc === "shared_root"} onchange={pickSharedRoot} />
            <span>Shared root folder</span>
          </label>
          {#if effectiveLoc === "shared_root"}
            <div class="cicd-shared-row">
              <input class="input" bind:value={sharedDraft} placeholder="C:\shared\CICD" aria-label="Shared CICD folder path" />
              <button class="btn-secondary" onclick={browseShared} disabled={browsing}>{browsing ? "…" : "Browse"}</button>
              <button class="btn-primary btn-tiny" onclick={applyShared} disabled={!sharedDraft.trim()}>Apply</button>
            </div>
            {#if locOverride === "shared_root"}<span class="cicd-config-hint">Choose a folder and click Apply to switch.</span>{/if}
          {/if}
        </fieldset>
      {/if}

      {#if errorMsg}
        <div class="dashboard-banner banner-error" role="alert"><span class="banner-icon">⚠</span><span>{errorMsg}</span></div>
      {/if}

      <div class="cicd-body">
        <div class="panel-card cicd-repos">
          <div class="panel-title-row"><span class="panel-title">REPOS</span>{#if repos.length}<span class="cicd-count">{repos.length}</span>{/if}</div>
          {#if reposLoading}
            <p class="cicd-hint" role="status"><span class="spin" aria-hidden="true"></span> Loading repos…</p>
          {:else if repos.length === 0}
            <div class="cicd-empty-inline">
              <p class="cicd-empty-inline-title">No repositories cloned yet</p>
              <ol class="cicd-steps">
                <li>Open <code>bitbucket.sgp.dbs.com:8443/dcifgit/projects/dcif_binary</code></li>
                <li>Pick the appcode repo → branch <code>cicd</code> → Clone → copy the HTTP URL</li>
                <li>Paste it above and click <strong>Clone</strong></li>
              </ol>
            </div>
          {:else}
            <ul class="cicd-repo-list">
              {#each repos as repo}
                <li>
                  <button class="cicd-repo-row" class:selected={selectedRepo === repo.name} onclick={() => selectRepo(repo)} title={repo.name}>
                    <span class="cicd-name cicd-repo-name">{repo.name}</span>
                    <span class="cicd-repo-status" class:clean={repo.status.clean}>{statusSummary(repo.status)}</span>
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>

        <div class="panel-card cicd-files">
          <div class="panel-title-row"><span class="panel-title">FILES</span>{#if selectedRepo}<span class="panel-subtitle">{selectedRepo}</span>{/if}</div>
          {#if treeLoading}
            <p class="cicd-hint" role="status"><span class="spin" aria-hidden="true"></span> Reading files…</p>
          {:else if selectedRepo && tree.length}
            <div class="cicd-tree-wrap">{@render fileTree(tree)}</div>
          {:else if selectedRepo}
            <p class="cicd-hint">This repository has no files to show.</p>
          {:else}
            <p class="cicd-hint">Select a repository to browse its files. Click a file to open it in your default app.</p>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</section>

<style>
  /* ── controls row ─────────────────────────────────────────────────── */
  .cicd-controls { display: flex; gap: 12px; align-items: flex-end; flex-wrap: wrap; }
  .cicd-controls .field { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
  .cicd-controls .field > span { font-size: 9px; font-weight: 900; color: var(--color-muted); text-transform: uppercase; letter-spacing: 0.3px; }
  .cicd-controls .field > span em { font-style: normal; color: var(--text-muted); font-weight: 800; }
  .cicd-appcode { flex: 0 0 auto; min-width: 150px; }
  .cicd-url { flex: 1 1 320px; }
  .cicd-controls .input { padding: 5px 9px; font-size: 12px; border: 1px solid var(--input-border); border-radius: 5px; background: #fff; color: var(--color-ink); height: 30px; }
  .cicd-controls .input.invalid { border-color: var(--primary-red); }
  .cicd-controls .input:focus-visible { outline: 2px solid var(--active-red); outline-offset: 1px; border-color: var(--primary-red); }
  .cicd-url-hint.err { font-size: 10px; font-weight: 700; color: var(--primary-red); }
  .cicd-clone-btn { height: 30px; flex: 0 0 auto; }

  /* ── config fieldset ──────────────────────────────────────────────── */
  .cicd-config { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; border: 1px solid var(--input-border); }
  .cicd-config legend { font-size: 9px; font-weight: 900; color: var(--color-muted); text-transform: uppercase; letter-spacing: 0.3px; padding: 0 4px; }
  .cicd-radio { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--color-ink); cursor: pointer; }
  .cicd-radio input { accent-color: var(--primary-red); }
  .cicd-radio code, .cicd-config code { font-size: 10px; font-family: monospace; background: #f3f4f6; padding: 1px 5px; border-radius: 3px; }
  .cicd-shared-row { display: flex; align-items: center; gap: 6px; flex: 1 1 260px; min-width: 0; }
  .cicd-shared-row .input { flex: 1 1 auto; min-width: 0; padding: 4px 8px; font-size: 11px; border: 1px solid var(--input-border); border-radius: 5px; height: 28px; }
  .cicd-shared-row .input:focus-visible { outline: 2px solid var(--active-red); outline-offset: 1px; }
  .cicd-config-hint { font-size: 10px; color: var(--text-muted); font-weight: 700; flex-basis: 100%; }

  /* ── body: repos + files ──────────────────────────────────────────── */
  .cicd-body { display: flex; gap: 12px; flex: 1; min-height: 0; }
  .cicd-repos { flex: 0 0 288px; min-width: 0; overflow: auto; }
  .cicd-files { flex: 1 1 auto; min-width: 0; overflow: auto; }
  .cicd-count { margin-left: auto; font-size: 10px; font-weight: 800; color: var(--text-muted); }

  .cicd-repo-list, .cicd-tree { list-style: none; margin: 0; padding: 0; }
  .cicd-repo-row { display: flex; flex-direction: column; gap: 1px; align-items: flex-start; width: 100%; text-align: left; padding: 7px 10px; border: none; background: none; border-radius: 5px; cursor: pointer; transition: background 120ms ease-out; }
  .cicd-repo-row:hover { background: #fff1f4; }
  .cicd-repo-row.selected { background: #fff1f4; box-shadow: inset 2px 0 0 var(--primary-red); }
  .cicd-repo-row:focus-visible { outline: 2px solid var(--active-red); outline-offset: -2px; }
  .cicd-repo-name { font-size: 12px; font-weight: 700; color: var(--color-ink); max-width: 100%; }
  .cicd-repo-status { font-size: 10px; color: var(--text-secondary); max-width: 100%; }
  .cicd-repo-status.clean { color: #15803d; }

  /* ── file tree ────────────────────────────────────────────────────── */
  .cicd-tree { padding-left: 13px; }
  .cicd-dir { display: flex; align-items: center; gap: 5px; cursor: pointer; padding: 2px 4px; border-radius: 4px; font-size: 12px; font-weight: 700; color: var(--color-ink); list-style: none; }
  .cicd-dir::-webkit-details-marker { display: none; }
  .cicd-dir:hover { background: #f3f4f6; }
  .cicd-dir:focus-visible { outline: 2px solid var(--active-red); outline-offset: -2px; }
  .cicd-caret { width: 0; height: 0; border-left: 4px solid var(--text-secondary); border-top: 3px solid transparent; border-bottom: 3px solid transparent; transition: transform 120ms ease-out; flex: none; }
  details[open] > .cicd-dir .cicd-caret { transform: rotate(90deg); }
  .cicd-file { display: flex; align-items: center; gap: 7px; width: 100%; border: none; background: none; cursor: pointer; padding: 2px 4px; border-radius: 4px; font-size: 12px; color: var(--color-ink); font-family: monospace; text-align: left; transition: background 120ms ease-out; }
  .cicd-file:hover { background: #f3f4f6; }
  .cicd-file:focus-visible { outline: 2px solid var(--active-red); outline-offset: -2px; }
  .cicd-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-width: 0; }
  .cicd-badge { flex: none; width: 14px; height: 14px; border-radius: 3px; font-size: 9px; font-weight: 900; font-family: Inter, sans-serif; display: inline-flex; align-items: center; justify-content: center; color: #fff; }
  .badge-mod { background: #b45309; }      /* modified */
  .badge-new { background: #15803d; }      /* untracked */
  .badge-staged { background: #15803d; }   /* staged */
  .badge-clean { background: transparent; }

  /* ── empty / loading states ───────────────────────────────────────── */
  .cicd-center { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; padding: 60px 20px; color: var(--text-secondary); font-size: 12px; font-weight: 700; }
  .cicd-empty { text-align: center; padding: 28px 24px; }
  .cicd-empty-title { font-weight: 900; font-size: 15px; color: var(--color-ink); }
  .cicd-empty-sub { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }
  .cicd-steps { text-align: left; max-width: 620px; margin: 12px auto 16px; font-size: 12px; line-height: 1.7; color: var(--color-ink); padding-left: 20px; }
  .cicd-steps code { font-size: 10px; word-break: break-all; background: #f3f4f6; padding: 1px 4px; border-radius: 3px; }
  .cicd-empty-inline { font-size: 12px; color: var(--text-secondary); padding: 4px 2px; }
  .cicd-empty-inline-title { font-weight: 800; color: var(--color-ink); margin-bottom: 6px; }
  .cicd-hint { font-size: 11px; font-weight: 700; color: var(--text-secondary); padding: 16px; text-align: center; display: flex; align-items: center; justify-content: center; gap: 6px; }

  /* ── spinner (reduced-motion safe) ────────────────────────────────── */
  .spin { display: inline-block; width: 11px; height: 11px; border: 2px solid var(--input-border); border-top-color: var(--primary-red); border-radius: 50%; animation: cicd-spin 0.6s linear infinite; vertical-align: -1px; }
  .spin-lg { width: 22px; height: 22px; border-width: 3px; }
  @keyframes cicd-spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    .spin { animation: none; border-top-color: var(--input-border); }
    .cicd-repo-row, .cicd-file, .cicd-dir, .cicd-caret { transition: none; }
  }

  /* ── responsive: stack the browser on narrow windows ──────────────── */
  @media (max-width: 900px) {
    .cicd-body { flex-direction: column; }
    .cicd-repos { flex: 0 0 auto; max-height: 220px; }
    .cicd-files { flex: 1 1 auto; }
  }
  @media (max-width: 560px) {
    .cicd-controls { flex-direction: column; align-items: stretch; }
    .cicd-appcode, .cicd-url, .cicd-clone-btn { flex: 1 1 auto; width: 100%; }
    .cicd-shared-row { flex-wrap: wrap; }
  }
</style>
