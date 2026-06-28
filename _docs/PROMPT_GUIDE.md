# Prompt Guide — Project Tracker

Dokumentasi prompt untuk vibe-coding. Copy-paste, isi field `[...]`, kirim ke Claude Code.
Setiap prompt sudah include skill yang tepat. Jangan ubah urutan skill invocation.

---

## 1. Session Baru (Resume)

Pakai ini setiap kali buka session baru Claude Code.

```
/goal resume Project Tracker vibe-code.

Context:
- Project root: D:/Ibrahim/Projects/project_tracker
- Working one menu at a time

Do:
1. claude-mem:recall — get latest decisions, current menu, approved designs
2. Read _docs/PROGRESS.md
3. git status + git branch
4. graphify check (absolute path)
5. Report: active menu, last slice done, dirty files, next safest task
6. Ask: continue current menu or switch?
```

---

## 2. Mulai / Lanjut Menu

Pakai ini untuk mulai kerja di satu menu atau lanjut dari terakhir.

```
/goal lanjut [NAMA_MENU] sampai sesuai ekspektasi gw.

Context:
- Current menu: [NAMA_MENU]
- Target sekarang: [APA YANG MAU DICAPAI]
- Visual ref: _reference/ HTML prototype
- Important preference: [PREFERENCE KALAU ADA, HAPUS KALAU TIDAK]

Skills:
- /frontend-design (for design work)
- /context7-mcp (for Svelte/Vite/Tailwind docs)
- Read _docs/DESIGN_RULES.md for design system

Rules:
- Satu menu only
- Design mockup dulu, gw approve baru code
- graphify first from D:/Ibrahim/Projects/project_tracker
- Update _docs/PROGRESS.md after each slice
- Generate manual checklist setelah code
- Report: changed files, tests run, not tested, next slice
```

---

## 3. Ubah Desain (Design Change)

Pakai ini kalau desain yang sudah di-code perlu diubah (warna, layout, spacing, dll).

```
/goal ubah desain [NAMA_MENU].

Perubahan yang gw mau:
[JELASKAN PERUBAHAN SPESIFIK — warna, layout, spacing, posisi, ukuran, dll]

Context:
- Menu: [NAMA_MENU]
- Yang harus tetap: [BAGIAN YANG JANGAN DIUBAH]

Skills:
- /frontend-design
- Read _docs/DESIGN_RULES.md

Rules:
- Buat branch: design/[menu]-[desc]
- Tunjukkan mockup/preview dulu sebelum ubah code
- Kalau element ini shared → update di semua menu yang pakai
- List semua menu yang terdampak
- Generate checklist untuk semua menu terdampak
```

---

## 4. Fix Issue / Bug

Pakai ini kalau ketemu bug atau error.

```
/goal fix error di [NAMA_MENU].

Apa yang gw lakukan sebelum error:
[LANGKAH YANG GW LAKUKAN]

Yang gw harapkan:
[EXPECTED RESULT]

Yang terjadi:
[ACTUAL RESULT / ERROR MESSAGE — paste exact error]

Skills:
- /superpowers:systematic-debugging

Rules:
- Buat branch: fix/[menu]-[desc]
- Jangan tebak — reproduce atau locate failing path dulu
- graphify first from D:/Ibrahim/Projects/project_tracker
- Find root cause → smallest fix → verify
- Jangan weaken tests
- Generate checklist setelah fix
- Update _docs/PROGRESS.md kalau status/risk berubah
```

---

## 5. Tambah Fitur Baru

Pakai ini untuk menambah fitur yang belum ada.

```
/goal tambah fitur [NAMA_FITUR] di [NAMA_MENU].

Deskripsi fitur:
[JELASKAN FITUR — apa yang dilakukan, trigger apa, output apa]

User flow:
1. [LANGKAH 1]
2. [LANGKAH 2]
3. [LANGKAH 3]

Context:
- Menu: [NAMA_MENU]
- Related existing features: [FITUR YANG BERHUBUNGAN KALAU ADA]

Skills:
- /superpowers:writing-plans (if complex)
- /frontend-design (if has UI)
- /context7-mcp (if using new library API)
- /fullstack-dev-skills:python-pro (if backend logic)

Rules:
- Buat branch: feat/[menu]-[desc]
- Check PRD.md — fitur ini sudah ada di PRD atau baru?
- Kalau baru dan mengubah product behavior → update PRD.md juga
- Design mockup dulu kalau ada UI → gw approve → baru code
- graphify first — cari existing code yang bisa di-reuse
- Generate checklist setelah code
```

---

## 6. Ubah / Update Fitur yang Sudah Ada

Pakai ini untuk mengubah perilaku fitur yang sudah jalan.

```
/goal ubah fitur [NAMA_FITUR] di [NAMA_MENU].

Perilaku lama:
[CARA KERJA SEKARANG]

Perilaku baru yang gw mau:
[CARA KERJA YANG DIINGINKAN]

Alasan perubahan:
[KENAPA HARUS BERUBAH]

Skills:
- /frontend-design (if UI changes)
- /fullstack-dev-skills:python-pro (if backend changes)
- /context7-mcp (if library API involved)

Rules:
- Buat branch: feat/[menu]-[desc]
- Compare dengan PRD.md — ini mengubah product rules?
- Kalau ya → update PRD.md setelah implementation
- Kalau ada shared element yang berubah → update semua menu
- Generate checklist + list affected areas
```

---

## 7. Tambah Logic / Rules Aplikasi

Pakai ini untuk menambah business logic, validation, state machine rules, etc.

```
/goal tambah rules [DESKRIPSI SINGKAT].

Rules yang mau ditambah:
[JELASKAN LOGIC / RULE — kapan trigger, kondisi apa, output apa]

Contoh case:
- Input: [CONTOH INPUT]
- Expected: [CONTOH OUTPUT]
- Edge case: [CONTOH EDGE CASE]

Skills:
- /fullstack-dev-skills:python-pro
- /superpowers:test-driven-development (if complex logic)

Rules:
- Buat branch: feat/[scope]-[desc]
- Logic harus di Python services/core layer, bukan di Svelte
- Tulis test untuk logic ini
- Update PRD.md kalau ini product rule baru
- Generate checklist
```

---

## 8. Polish / Finalize Menu

Pakai ini setelah menu sudah fungsional, mau polish detail terakhir.

```
/goal polish [NAMA_MENU] — final pass.

Yang perlu di-polish:
- [ ] [ITEM 1 — misal: spacing terlalu lebar]
- [ ] [ITEM 2 — misal: hover state belum ada]
- [ ] [ITEM 3 — misal: loading state belum ada]

Skills:
- /frontend-polish
- /simplify (if code needs cleanup)
- /code-review (final review before merge)

Rules:
- Buat branch: refactor/[menu]-polish
- Jangan tambah fitur baru — polish only
- Generate final checklist
- Setelah gw approve → siap merge ke main
```

---

## 9. Review Sebelum Pindah Menu

Pakai ini sebelum pindah ke menu selanjutnya.

```
/goal final review [NAMA_MENU] sebelum pindah menu.

Skills:
- /code-review
- /superpowers:verification-before-completion

Rules:
- Compare vs PRD behavior
- Compare vs _reference/ visual reference
- Run relevant tests + build
- List: DONE / NOT DONE / USER CHECK NEEDED / RISK / NEXT MENU READY
- Update _docs/PROGRESS.md
- Save memory: approved design decisions for this menu
```

---

## 10. Pivot / Ubah Arah

Pakai ini kalau mau mengubah arah pengerjaan (bukan fix bug, tapi perubahan konsep).

```
/goal pivot [NAMA_MENU].

Arah baru:
[PERUBAHAN KONSEP / ARAH]

Context:
- Arah lama: [APA YANG SEBELUMNYA]
- Ekspektasi baru: [APA YANG DIINGINKAN]
- Yang tetap: [YANG JANGAN DIUBAH]
- Yang berubah: [YANG BOLEH DIUBAH]

Skills:
- /superpowers:brainstorming (if direction unclear)
- /superpowers:writing-plans (if complex)

Rules:
- Stop old path first
- Compare new direction vs PRD.md, _docs/PROGRESS.md, current code
- If product behavior changes → update PRD.md + _docs/PROGRESS.md
- If only visual changes → update _docs/PROGRESS.md
- Keep change bounded to [NAMA_MENU]
- graphify first → smart-explore
```

---

## 11. Cleanup / Housekeeping

Pakai ini untuk bersih-bersih tanpa feature work.

```
/goal clean project hygiene. No feature work.

Skills:
- /project-cleanup (if available)

Rules:
- Inspect: git status, worktrees, untracked files, graphify health
- Remove only: stale clean agent worktrees, temp folders
- Do NOT delete: source files, graphify-out, _reference/, active branches
- Do NOT change product behavior
- Report: removed items, kept risky items, remaining dirty files
```

---

## 12. Wrap Up Session

Pakai ini di akhir session.

```
/goal wrap up session.

Context:
- Menu dikerjakan: [NAMA_MENU]
- Yang selesai: [YANG SELESAI SESSION INI]
- Known gaps: [YANG BELUM SELESAI]

Rules:
- Update _docs/PROGRESS.md
- claude-mem:remember — save stable decisions
- Refresh graphify if available
- Jangan commit/stash kecuali gw bilang
- Report: branch, dirty files, tests run, not tested, next prompt
```

---

## Quick Reference — Skill Cheat Sheet

| Mau ngapain    | Skill yang dipakai                            |
| -------------- | --------------------------------------------- |
| Desain UI      | `/frontend-design` + `_docs/DESIGN_RULES.md`  |
| Polish UI      | `/frontend-polish`                            |
| Code Svelte    | `/context7-mcp` (resolve svelte → query)      |
| Code Python    | `/fullstack-dev-skills:python-pro`            |
| Fix bug        | `/superpowers:systematic-debugging`           |
| Plan complex   | `/superpowers:writing-plans`                  |
| Brainstorm     | `/superpowers:brainstorming`                  |
| Review code    | `/code-review` atau `/ponytail-review`        |
| Test-first     | `/superpowers:test-driven-development`        |
| Simplify       | `/simplify`                                   |
| Commit         | `/caveman:caveman-commit`                     |
| Memory save    | `claude-mem:remember`                        |
| Memory load    | `claude-mem:recall`                          |
| Codebase query | `/graphify`                                   |
| Verify done    | `/superpowers:verification-before-completion` |
| Run app        | `/verify` atau `/run`                         |
| Security check | `/fullstack-dev-skills:security-reviewer`     |

---

## Quick Reference — Integrations

| Need               | Use           | Catatan Windows                                         |
| ------------------ | ------------- | ------------------------------------------------------- |
| Style ringkas      | caveman ultra | Session-level; normal mode untuk teks stakeholder       |
| Output tool besar  | context-mode  | Plugin otomatis; jangan bikin hook kompresi sendiri     |
| Memory lintas sesi | claude-mem    | claude-mem is the one active tool                       |
| Blast radius code  | graphify      | `graphify query`, bukan `/graphify .` di PowerShell     |
| CLI verbose manual | RTK           | `rtk ...` manual-only; auto-rewrite cuma WSL/Unix shell |

---

## Tips Hemat Token

1. **Pakai prompt yang spesifik** — "ubah warna sidebar jadi lebih gelap" > "improve the design"
2. **Paste error exact** — jangan describe error, paste langsung
3. **Approve desain cepat** — kalau 80% ok, approve + list yang perlu diubah. Jangan minta redesign total.
4. **Satu menu per session** — context switching = token waste
5. **Jangan minta explain** kecuali beneran bingung — code speaks louder
6. **Bilang "lanjut" / "ok"** kalau setuju — jangan elaborate agreement
