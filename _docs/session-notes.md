# Session Notes

> Brief recovery ledger. Do not paste transcripts or secrets.
> - **DECISIONS.md** → permanent ADRs (why)
> - **PROGRESS.md** → tracking (what's done, what's next)
> - **session-notes.md** → what's active NOW

---

**Now:** Config cleanup — rapihin settings & docs system (branch: `chore/config-cleanup`)
- Hapus agentmemory dari semua routing docs
- CLAUDE.md: tambah Session vs Turn section
- WORKFLOW.md: tambah chore/ branch, fix sidebar→bottom dock
- FILE_ROUTING.md: bersihin stale references (notes.md, tree.txt)
- DECISIONS.md: tambah D-0004 untuk config cleanup

**Next:** User review & merge approval for config cleanup branch

**Blocked:** None

**active_menu:** Config/docs cleanup (non-product)

---

## 2026-06-27

Branch aktif: `chore/bootstrap-tooling`  
File diubah: bootstrap tooling/config docs only  
Design approved: none  
Keputusan teknis: context-mode owns tool-output compression; claude-mem owns cross-session recall; agentmemory disabled to avoid duplicate capture/injection; graphify is on-demand graph; RTK manual-only on native Windows.  
Next step: memory switch committed; start first approved design menu.  
Smoke: plugin list OK; graphify query degraded/noisy but executable; RTK OK.  
Blocked: Windows manual product verification remains separate from bootstrap.
