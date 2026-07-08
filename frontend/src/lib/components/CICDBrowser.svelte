<script lang="ts">
  /**
   * Piece D — CICD Bitbucket browser (top-level page).
   * Appcode dropdown → clone URL + Clone → repo list → recursive file tree.
   * Empty states: git not installed (install steps + Recheck), no repos
   * (Bitbucket steps + clone URL). Config row switches per_appcode/shared_root.
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
  let appcodes: AppCode[] = $state([]);
  let appcode: string = $state("");
  let repos: Repo[] = $state([]);
  let selectedRepo: string = $state("");
  let tree: FileNode[] = $state([]);
  let cloneUrl: string = $state("");
  let cloning: boolean = $state(false);
  let loading: boolean = $state(false);
  let errorMsg: string = $state("");

  let currentConfig = $derived(appcodes.find((a) => a.name === appcode));

  async function checkGit() {
    if (!isPywebviewReady()) return;
    const resp = await callBridge<GitStatus>("cicd_git_status");
    if (resp.ok) git = resp.data ?? { installed: false, version: null };
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
    loading = true;
    errorMsg = "";
    const resp = await callBridge<Repo[]>("cicd_list_repos", appcode);
    loading = false;
    if (!resp.ok) { errorMsg = resp.error.message; return; }
    repos = resp.data ?? [];
    if (selectedRepo && !repos.some((r) => r.name === selectedRepo)) {
      selectedRepo = "";
      tree = [];
    }
  }

  async function selectRepo(repo: Repo) {
    selectedRepo = repo.name;
    const resp = await callBridge<FileNode[]>("cicd_list_files", repo.path);
    tree = resp.ok ? (resp.data ?? []) : [];
    if (!resp.ok) errorMsg = resp.error.message;
  }

  async function startClone() {
    const url = cloneUrl.trim();
    if (!url) { addToast("Paste a Bitbucket clone URL first.", "warning"); return; }
    if (!appcode) { addToast("Select an appcode first.", "warning"); return; }
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
      await loadRepos();
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
    await loadRepos();
  }

  async function saveConfig(location: string, sharedPath: string) {
    if (!appcode) return;
    const resp = await callBridge<AppCode>("appcode_update_config", appcode, {
      cicd_location: location,
      cicd_shared_path: sharedPath,
    });
    if (resp.ok) {
      appcodes = appcodes.map((a) => (a.name === appcode ? (resp.data as AppCode) : a));
      addToast("CICD location updated", "success");
      await loadRepos();
    } else {
      addToast(resp.error.message, "error");
    }
  }

  function dotClass(gitStatus: string): string {
    if (gitStatus === "modified") return "dot-waiting";
    if (gitStatus === "untracked" || gitStatus === "staged") return "dot-done";
    return "";
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
    await loadAppcodes();
    await loadRepos();
  });
</script>

{#snippet fileTree(nodes: FileNode[])}
  <ul class="cicd-tree">
    {#each nodes as node}
      <li>
        {#if node.type === "dir"}
          <details open>
            <summary class="cicd-dir">📁 {node.name}</summary>
            {@render fileTree(node.children)}
          </details>
        {:else}
          <button class="cicd-file" onclick={() => openFile(node)}>
            <span class="cicd-dot {dotClass(node.git_status)}"></span>
            {node.name}
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
    <div class="page-header-actions">
      <button class="sb-tab" onclick={loadRepos} disabled={loading}>{loading ? "◌ Loading…" : "↻ Refresh"}</button>
    </div>
  </div>

  <div class="page-stack active">
    {#if !git.installed}
      <div class="panel-card accent cicd-empty">
        <p class="cicd-empty-title">Git CLI is not installed</p>
        <ol class="cicd-steps">
          <li>Press <kbd>Windows</kbd> + <kbd>R</kbd></li>
          <li>Copy-paste: <code>softwarecenter:softwareid=scopeid_a28b0b90-3c76-4954-b83a-985d0626645a/application_436aff6_de9b_4071_8725_982c241b719d</code></li>
          <li>Press Enter → Company Software Center opens → click Install</li>
          <li>Login with your 1Bank account if prompted</li>
        </ol>
        <button class="btn-primary" onclick={checkGit}>Recheck Git Status</button>
      </div>
    {:else}
      <div class="panel-card accent cicd-controls">
        <label class="field">
          <span>Appcode</span>
          <select class="input" bind:value={appcode} onchange={onAppcodeChange}>
            {#each appcodes as a}<option value={a.name}>{a.display_name}</option>{/each}
          </select>
        </label>
        <label class="field cicd-url">
          <span>Bitbucket clone URL (branch: cicd)</span>
          <input class="input" bind:value={cloneUrl} placeholder="https://bitbucket.sgp.dbs.com:8443/scm/…/myapp.git" />
        </label>
        <button class="btn-primary" onclick={startClone} disabled={cloning}>{cloning ? "◌ Cloning…" : "Clone"}</button>
      </div>

      {#if currentConfig}
        <div class="panel-card cicd-config">
          <span class="cicd-config-label">CICD folder:</span>
          <label><input type="radio" checked={currentConfig.cicd_location !== "shared_root"} onchange={() => saveConfig("per_appcode", currentConfig?.cicd_shared_path ?? "")} /> Per appcode ({appcode}/CICD)</label>
          <label><input type="radio" checked={currentConfig.cicd_location === "shared_root"} onchange={() => saveConfig("shared_root", currentConfig?.cicd_shared_path ?? "")} /> Shared root</label>
          {#if currentConfig.cicd_location === "shared_root"}
            <input class="input cicd-shared" value={currentConfig.cicd_shared_path ?? ""} placeholder="C:\shared\CICD" onchange={(e) => saveConfig("shared_root", e.currentTarget.value)} />
          {/if}
        </div>
      {/if}

      {#if errorMsg}
        <div class="dashboard-banner banner-error"><span class="banner-icon">⚠</span><span>{errorMsg}</span></div>
      {/if}

      <div class="cicd-body">
        <div class="panel-card cicd-repos">
          <div class="panel-title-row"><span class="panel-title">REPOS</span></div>
          {#if repos.length === 0}
            <div class="cicd-empty-inline">
              <p>No repos cloned yet. To clone:</p>
              <ol class="cicd-steps">
                <li>Open <code>https://bitbucket.sgp.dbs.com:8443/dcifgit/projects/dcif_binary</code></li>
                <li>Select the appcode repo → branch <code>cicd</code> → Clone → copy HTTP URL</li>
                <li>Paste above and click Clone</li>
              </ol>
            </div>
          {:else}
            {#each repos as repo}
              <button class="cicd-repo-row" class:selected={selectedRepo === repo.name} onclick={() => selectRepo(repo)}>
                <strong>{repo.name}</strong>
                <span class="cicd-repo-status">({statusSummary(repo.status)})</span>
              </button>
            {/each}
          {/if}
        </div>

        <div class="panel-card cicd-files">
          <div class="panel-title-row"><span class="panel-title">FILES</span><span class="panel-subtitle">{selectedRepo || "select a repo"}</span></div>
          {#if selectedRepo && tree.length}
            {@render fileTree(tree)}
          {:else}
            <p class="cicd-hint">Select a repo to browse its files. Click a file to open it in the default app.</p>
          {/if}
        </div>
      </div>
    {/if}
  </div>
</section>

<style>
  .cicd-controls { display:flex; gap:12px; align-items:flex-end; flex-wrap:wrap; }
  .cicd-controls .field { display:flex; flex-direction:column; gap:4px; font-size:9px; font-weight:800; color:var(--color-muted); text-transform:uppercase; letter-spacing:0.3px; }
  .cicd-controls .cicd-url { flex:1; min-width:280px; }
  .cicd-controls .input { padding:6px 8px; font-size:11px; border:1px solid #D7DCE2; border-radius:5px; background:#fff; color:var(--color-ink); text-transform:none; letter-spacing:normal; }
  .cicd-config { display:flex; gap:14px; align-items:center; font-size:11px; flex-wrap:wrap; }
  .cicd-config-label { font-weight:800; color:var(--color-muted); text-transform:uppercase; font-size:9px; }
  .cicd-config label { display:flex; gap:4px; align-items:center; }
  .cicd-shared { padding:4px 8px; font-size:11px; border:1px solid #D7DCE2; border-radius:5px; }
  .cicd-body { display:flex; gap:12px; flex:1; min-height:0; }
  .cicd-repos { width:280px; overflow:auto; }
  .cicd-files { flex:1; overflow:auto; }
  .cicd-repo-row { display:flex; gap:8px; align-items:baseline; width:100%; text-align:left; padding:7px 10px; border:none; background:none; border-radius:5px; cursor:pointer; font-size:12px; }
  .cicd-repo-row:hover { background:#f3f4f6; }
  .cicd-repo-row.selected { background:#EEF2FF; }
  .cicd-repo-status { font-size:10px; color:var(--color-muted); }
  .cicd-tree { list-style:none; margin:0; padding-left:12px; font-size:12px; }
  .cicd-tree summary.cicd-dir { cursor:pointer; padding:2px 0; font-weight:700; }
  .cicd-file { display:flex; gap:6px; align-items:center; border:none; background:none; cursor:pointer; padding:2px 0; font-size:12px; color:var(--color-ink); font-family:monospace; }
  .cicd-file:hover { text-decoration:underline; }
  .cicd-dot { width:8px; height:8px; border-radius:50%; display:inline-block; flex:none; }
  .cicd-dot.dot-waiting { background:#C77700; }
  .cicd-dot.dot-done { background:#17803d; }
  .cicd-empty { text-align:center; padding:24px; }
  .cicd-empty-title { font-weight:800; font-size:14px; margin-bottom:10px; }
  .cicd-steps { text-align:left; max-width:640px; margin:8px auto 14px; font-size:11px; line-height:1.7; }
  .cicd-steps code { font-size:9px; word-break:break-all; background:#f3f4f6; padding:1px 4px; border-radius:3px; }
  .cicd-empty-inline { font-size:11px; color:var(--color-muted); }
  .cicd-hint { font-size:11px; color:var(--color-muted); padding:14px; text-align:center; }
</style>
