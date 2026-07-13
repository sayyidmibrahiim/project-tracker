<aside>
🎯

Dokumen ini adalah source of truth untuk pematangan menu Automations pada Project Tracker. Implementasi harus goal-centric, seamless untuk penggunaan normal, tetapi tetap menyediakan opsi advanced yang dapat dikustomisasi.

</aside>

## 1. Tujuan Produk

Menu **Automations** adalah sistem automation general yang dapat digunakan untuk kebutuhan CR maupun non-CR.

Channel/capability yang didukung:

- **Outlook Classic** melalui `pywin32` dan COM session akun aktif, tanpa credential/API/password.
- **Microsoft Teams** melalui deeplink.
- **Reminder** internal aplikasi.

CR bukan pusat seluruh automation. CR merupakan salah satu scope, sumber data, condition, placeholder, dan target action yang dapat digunakan oleh rule.

### Prinsip produk

1. **Goal-centric:** field dan behavior editor berubah sesuai goal yang dipilih.
2. **Seamless by default:** default aman dan mudah digunakan.
3. **Customizable when needed:** opsi advanced tersedia tanpa memenuhi UI utama.
4. **Separate channel settings:** Outlook, Teams, dan Reminder mempunyai setting sendiri.
5. **Global rule management:** seluruh rule dapat dicari dan dipantau dari Rules Engine global.
6. **No silent failure:** kondisi Outlook, COM, scheduler, dan hasil execution harus terlihat oleh user.
7. **Evidence before state mutation:** perubahan status CR/Drone dari email hanya dilakukan setelah email bukti ditemukan dan berhasil disimpan.

## 2. Batas Teknis

### Outlook

- Full automation hanya ditujukan untuk **Outlook Classic for Windows**.
- COM digunakan untuk mengambil Outlook session aktif, mencari email, membuat draft, Reply/Reply All, mengirim email, dan menyimpan `.msg`.
- Jika Outlook Classic tertutup saat scheduled auto-send, aplikasi mencoba membukanya secara otomatis.
- New Outlook tidak dianggap kompatibel dengan COM. UI harus menampilkan status unsupported, bukan melakukan fallback palsu.
- Ketika laptop mati/sleep, worker lokal tidak berjalan. Missed schedule ditangani ketika aplikasi hidup kembali.

### Teams

- Integrasi menggunakan deeplink.
- Jangan menjanjikan background auto-send jika capability deeplink hanya dapat membuka Teams/compose target.
- Flow default bersifat preview/open-first dan transparan kepada user.

### Reminder

- Reminder berjalan di dalam aplikasi dan dapat memunculkan Windows/app notification sesuai capability yang tersedia.

## 3. Information Architecture

### Top-level Automations

```
Automations
├── Outlook
│   ├── Connection status & metrics
│   ├── Templates
│   └── Outlook settings
├── Teams
│   ├── Teams templates
│   ├── Saved Teams automations
│   └── Teams/deeplink settings
├── Reminder
│   ├── Reminder entries
│   ├── Reminder presets
│   └── Reminder settings
├── Rules Engine
│   ├── All rules
│   ├── Filters by channel/goal/status
│   ├── Goal-centric rule builder
│   └── Per-rule execution history
└── Logs
```

Subtab **Downloaded Emails dihapus**. Fitur download/check email tetap tersedia sebagai goal rule. Hasilnya diakses melalui log dan folder CR.

### Hybrid management model

- Template dikelola di channel masing-masing.
- Setting channel tidak dicampur.
- Rules Engine menjadi pusat global untuk CRUD, search, filter, duplicate, enable/disable, run, dan monitoring seluruh rule.
- Editor rule hanya menampilkan field yang relevan dengan channel dan goal terpilih.

## 4. Dua Level Automations

### Level 1 — Project Details Automation Control Panel

Control panel kontekstual untuk CR/Non-CR yang sedang dibuka.

Grup utama:

- **Outlook Automation**
- **CR Automation**
- **Teams Automation**

Capability:

- Melihat rule yang cocok dengan data CR/Non-CR saat ini.
- Menjalankan `Send`, `Draft`, `Run`, `Force Check Now`, atau action manual lain.
- Mengubah mode Draft/Send Direct untuk execution saat itu.
- Melihat status dot: ready, waiting, failed, disabled, completed.
- Membuka setting rule.
- Deep-link ke `Create matching rule`.
- Membuka logs.
- Master toggle ON/OFF.
- Master toggle dipaksa OFF ketika CR `FINISHED`, `POSTPONED`, atau `CANCELED`.

Project Details menjalankan **rule**, bukan template. Template melekat pada rule.

Hanya rule yang seluruh condition-nya cocok yang ditampilkan/diaktifkan. Jika tidak ada:

```
No matching rules
Belum ada rule aktif yang cocok dengan data CR ini.
[Create matching rule]
```

`Create matching rule` membuka Rules Engine dengan sample context CR dan suggested conditions yang masih editable. Rule tidak dibuat otomatis.

### Level 2 — Top-level Automations

Pusat konfigurasi global untuk template, rule, scheduler, health, logs, dan channel settings.

## 5. Domain Model

### Template

- `id`
- `channel`: outlook | teams | reminder
- `category`
- `name`
- `description`
- `tags[]`
- `built_in`
- `content_html`
- Goal-specific fields
- `created_at`
- `updated_at`
- `usage_count`

### Rule

- `id`
- `name`
- `description`
- `channel`
- `goal`
- `scope`: general | cr_related
- `enabled`
- `tags[]`
- `template_id` jika goal memerlukan template
- `trigger_type`
- `conditions`
- `actions[]` berurutan
- `execution_mode`
- `error_policy`
- `schedule_config`
- `created_at`
- `updated_at`

### Execution

- `execution_id`
- `rule_id`
- `context_id`/CR ID jika ada
- `status`
- `started_at`
- `completed_at`
- `steps[]`
- `result`
- `error_code`
- `error_message`

### Processed Outlook Item

- `rule_id`
- `outlook_entry_id`
- `conversation_id`
- `status`: draft_pending | completed | discarded | failed
- `draft_entry_id`
- `sent_entry_id`
- `processed_at`

## 6. Global Rule Builder

Flow:

```
New Rule
→ Choose Channel
→ Choose Goal
→ Rule Info
→ Trigger/Availability
→ Conditions
→ Goal-specific Settings
→ Ordered Actions
→ Review & Test
→ Save inactive / Save and activate
```

Rule editor wajib sectioned:

1. Rule Info
2. Trigger/Availability
3. Conditions
4. Goal Settings
5. Actions
6. Execution & Error Policy
7. Review

Duplicate rule:

- Nama awal `Copy of …`.
- Selalu dibuat dalam status OFF.
- Langsung dibuka dalam edit mode.

## 7. CR Condition Builder

`On CR Condition` pada flow manual bukan auto-send. Condition berfungsi sebagai eligibility filter agar rule hanya muncul di Project Details ketika cocok.

Condition yang dapat dipertimbangkan:

- CR/Non-CR
- Appcode
- CR name/title pattern
- CR Type
- Project Type
- CR Status
- Drone Status
- UAT Sign-off attachment exists/missing
- PROD LV attachment exists/missing
- Field data CR lain yang memang tersedia

Behavior:

- Semua condition aktif memakai **Match ALL** secara default.
- Condition yang tidak diaktifkan tidak ikut dinilai.
- Pattern kosong berarti tidak membatasi CR berdasarkan pattern tersebut.
- Text operators: exact, contains, starts with, ends with, does not contain.
- Default case-sensitive OFF.
- Regex tersedia di Advanced.
- Advanced mode dapat menyediakan ALL/ANY groups jika dibutuhkan.

## 8. Outlook Templates

### Kategori

1. `New Email`
2. `Reply Email`

`Reply` versus `Reply All` ditentukan di rule Reply Email, bukan kategori template.

### New Email Template

Field:

- Template name
- Tags
- To
- CC
- BCC
- Subject
- Body
- Attachments
- Placeholders

### Reply Email Template

Mengikuti behavior Outlook:

- Tidak mempunyai To/CC/BCC.
- Tidak menyusun recipient secara manual.
- Body template
- Placeholder
- Attachment tambahan jika dibutuhkan
- Subject/original thread mengikuti Reply/Reply All Outlook.

### Editor

Mode:

- **Visual:** email-oriented RTE.
- **HTML:** source editor dengan validation/sanitization.
- **Import HTML:** upload `.html`, lalu hasilnya tetap editable.

Tidak ada in-app preview.

Button:

- `Save`
- `Preview in Outlook`
- `Create rule`

### Preview in Outlook

- Membuat unsent MailItem melalui COM.
- Memasukkan To/CC/BCC, Subject, HTML body, dan attachment sesuai template.
- Membuka compose window Outlook Classic.
- Tidak dihitung sebagai rule execution.
- Jika terdapat placeholder CR, user memilih sample CR/Non-CR terlebih dahulu.
- Jika tidak ada placeholder CR, preview langsung dibuka.

### Recipient autocomplete untuk New Email

- Recipient ditampilkan sebagai chips.
- Suggestion berasal dari alamat yang pernah dipakai pada template/history aplikasi dan sumber Outlook yang aman diakses.
- Mendukung keyboard navigation, Enter, Tab, dan deduplication.
- User dapat menghapus recipient history.

### Template list

Search/filter berdasarkan:

- Name
- Category
- Tags
- Built-in/user-created
- Attached/unattached to rules
- Last updated/last used

Status keterkaitan rule harus terlihat tanpa bergantung pada hover. Built-in template tidak dapat dihapus, tetapi dapat diduplikasi.

## 9. Outlook Goal — Send New Email

Template `New Email` wajib melekat pada rule.

### Trigger/availability

#### Manual Trigger

- Rule general dijalankan dari Rules Engine.
- Rule CR-related muncul di Project Details hanya ketika condition cocok.

#### Schedule

- General; tidak terkait CR/Non-CR.
- Mendukung Once dan recurring schedule yang sangat customizable.

#### Available When CR Matches

- Rule muncul di Project Details ketika seluruh condition cocok.
- Tidak berjalan otomatis.
- User tetap menekan Run/Send/Draft.

### Execution mode

- `Draft first` — default.
- `Send directly`.
- Mode dapat diubah dari Project Details untuk execution saat itu.
- Rule sensitif dapat dikunci ke Draft-only jika kelak dibutuhkan.

Setelah email benar-benar terkirim:

- Tombol Send/Submit disabled.
- Status `Sent` + timestamp.
- Tampilkan rule/template yang digunakan.
- Resend hanya melalui action eksplisit dengan confirmation.
- Resend dibuat sebagai execution baru.

### Follow-up actions

Registry action dapat berisi:

- Show notification
- Open URL
- Create Reminder
- Open file/folder
- Open app page
- Run another rule
- Pause/disable current rule
- Capability aman lain yang memang dimiliki aplikasi

Jangan menyediakan arbitrary PowerShell, executable, Python, atau shell command.

## 10. Scheduler Specification

### Recurrence builder

- Once: tanggal dan waktu tertentu.
- Every N minutes/hours.
- Every N days pada waktu tertentu.
- Every N weeks pada satu/beberapa weekday dan waktu.
- Every N months pada satu/beberapa day/time slot.
- Start date/time.
- Timezone.
- Multiple execution slots dalam satu rule.
- Next-run preview.

### End condition

- Never ends — default.
- End on date.
- End after N successful executions.

### Scheduled Draft

Ketika due:

- Tampilkan popup berisi rule, template, waktu, dan status Outlook.
- Button `Open draft`.
- Klik button menutup popup dan membuka draft Outlook.
- User bebas edit/send/close.

Jika draft occurrence sebelumnya masih pending:

- `Open previous draft`
- `Create new draft anyway`
- `Skip this occurrence`

Jangan replace/delete draft lama otomatis.

### Scheduled Auto-send preflight

Periksa:

- Automation worker aktif
- Outlook Classic terpasang
- Outlook dapat dibuka
- COM session ready
- Account tersedia
- Template valid
- Recipient valid
- Placeholder resolved
- Koneksi/kondisi yang diperlukan tersedia

Jika Outlook tertutup, aplikasi mencoba membukanya. Gunakan timeout dan bounded retry. Jika tetap gagal, beri status Waiting/Failed dan notifikasi.

### Laptop mati/sleep dan missed schedule

- Schedule disimpan persisten.
- Default grace period: 30 menit, editable per rule.
- Dalam grace period: lanjutkan otomatis sesuai mode.
- Di luar grace period: minta keputusan `Send now`, `Open as draft`, atau `Skip`.
- Job harus idempotent dan tidak boleh dieksekusi dua kali.

## 11. Outlook Goal — Reply Email

Template `Reply Email` wajib melekat pada rule.

### Reply behavior

- Rule memilih `Reply` atau `Reply All`.
- Outlook menentukan recipient berdasarkan email asli.
- Aplikasi tidak memanipulasi To/CC/BCC secara manual.

### Target email query

#### Search location

- Minimal satu Outlook folder.
- Boleh memilih beberapa folder.
- Include subfolders ON/OFF.

#### Pattern

- From
- To
- CC
- Subject
- Body
- Has attachment
- Attachment filename
- Placeholder seperti `CRNUMBER`
- Exact/contains/starts/ends/regex
- Case-sensitive ON/OFF

#### State filter

- Any
- Unread only
- Read only
- Flagged only
- Has attachment
- Not previously processed by this rule

#### Time filter

- Anytime
- Today
- Last N hours
- Last N days
- After date/time
- Since CR created untuk rule CR-related

#### Selection strategy

- Newest matching — default
- Oldest matching
- Newest unread
- Ask me every time

`Ask me every time` hanya boleh untuk manual/Draft execution, bukan background schedule.

### Deduplication

- Gunakan `Rule ID + Outlook Entry ID`.
- Email yang sama tidak boleh diproses dua kali secara otomatis oleh rule yang sama.
- Rule lain boleh memproses email tersebut.
- `Reply again` merupakan action manual dengan confirmation.

### Draft lifecycle

- `Draft pending`: draft dibuat, belum selesai.
- Jangan buat duplicate draft selama draft masih tersedia.
- `Completed`: reply terdeteksi di Sent Items.
- `Draft discarded`: draft dihapus; rule dapat dijalankan kembali.
- `Failed`: create/send gagal.

### Non-disableable loop protection

- Jangan reply ke email milik akun user sendiri.
- Abaikan automatic reply/out-of-office.
- Abaikan `noreply` secara default.
- Jangan memproses email yang dibuat oleh automation yang sama.
- Batasi reply per conversation/window waktu.
- Safety inti tidak dapat dimatikan.

## 12. Outlook Goal — Check/Download Email & Auto Update CR/Drone

Goal ini mencari bukti email di Outlook. Send/Reply Email tidak langsung mengubah aktivitas/status CR.

### Rule settings

- Target entity: CR Status, Drone Status, atau keduanya.
- `From status` dan `To status` untuk setiap status action.
- Search folders: minimal satu, boleh beberapa, selalu ditentukan per rule.
- Polling interval: default 10 menit, customizable.
- From matcher
- To matcher
- Subject matcher
- Body matcher—opsional
- Attachment existence/name matcher—opsional
- `CRNUMBER` wajib ada pada Subject atau Body.
- Minimal salah satu dari From atau To wajib diisi.
- Default operator Contains, case-sensitive OFF; operator customizable per field.

### Monitoring flow

1. CR memasuki `From status` yang relevan.
2. Monitoring dimulai dan menyimpan `monitoring_started_at`.
3. Worker memeriksa folder terpilih sesuai interval.
4. Pemeriksaan otomatis memproses email sejak CR dibuat.
5. Cocokkan seluruh condition aktif.
6. Deduplicate menggunakan Outlook Entry ID.
7. Simpan email sebagai `.msg`.
8. Setelah penyimpanan berhasil, jalankan ordered status actions.
9. Tampilkan notifikasi dan tulis log.
10. Stop monitoring jika target tercapai atau status diubah manual sehingga rule tidak relevan.

### Force Check Now

- Mencari sejak CR dibuat.
- Tidak mencari email sebelum CR ada.
- Menggunakan folder dan matcher milik rule.
- Hasil dan alasan no-match masuk log.

### File storage

File disimpan ke folder tree CR yang sudah dibangun aplikasi:

```
C:\Users\Azzahra\Documents\Project Tracker\SSID\2026\CR\UAT_PREPARE\SOP CR\_cr-docs
```

Ketentuan:

- Format `.msg` saja.
- Attachment tidak diekstrak terpisah.
- Nama dasar file mengikuti subject asli yang disanitasi untuk Windows.
- Jika nama sudah ada, tambahkan timestamp.
- Jika save `.msg` gagal, jangan update status.
- Referensi file harus tetap valid jika aplikasi memindahkan folder CR ketika status berubah.

### Ordered status actions

Satu rule dapat mengubah CR dan Drone sekaligus:

```
1. Save matched email as .msg
2. Update CR: UAT_PREPARE → APPROVED
3. Update Drone: OPEN → COMPLETED
4. Show notification
5. Stop monitoring
```

- User memilih action dan urutannya secara manual.
- Default error policy: halt on failure.
- Jika `From status` tidak lagi cocok akibat perubahan manual, jangan memaksa update.

## 13. Teams Automation

Teams tetap merupakan channel terpisah dengan templates, saved automations, setting, dan logs sendiri.

### Goals awal

- Open chat with prepared message
- Open channel with prepared message
- CR follow-up acknowledgement
- CR approval follow-up
- General scheduled/manual message preparation

### Template

- Name
- Purpose
- Target person/chat/channel deeplink
- Message body
- Tags
- Placeholders

### Behavior

- Preview/open-first sebagai default.
- Aplikasi resolve placeholder dan membuka Teams melalui deeplink.
- Jangan menyatakan message sudah terkirim hanya karena deeplink berhasil dibuka.
- Status yang valid: Prepared, Teams opened, User-confirmed sent, Failed.
- Jika aplikasi tidak dapat memverifikasi send, tampilkan status secara jujur.
- Tambahkan Saved Automations list dan cancelable countdown hanya jika auto-open memang digunakan.

### CR-related Teams rules

- Rule dapat memakai CR condition builder yang sama.
- Hanya rule cocok yang muncul di Project Details.
- User menjalankan action secara manual dari control panel.

## 14. Reminder Automation

Reminder merupakan channel dan goal tersendiri.

### Reminder types

- One-time
- Recurring dengan recurrence builder bersama
- Follow-up reminder
- Rule failure reminder
- CR-related reminder

### Fields

- Name/title
- Description
- Due date/time
- Timezone
- Recurrence
- Priority
- Related CR/Non-CR—opsional
- Actions on click
- Snooze options
- End condition

### State

- Scheduled
- Due
- Snoozed
- Completed
- Missed
- Paused
- Canceled

### Actions

- Open Project Details
- Open URL
- Open file/folder
- Run eligible rule
- Snooze
- Mark completed

Reminder KPI:

- Due Soon
- Overdue
- Paused
- Total Entries

## 15. Rules List UX

Toolbar:

- Search
- Filter by channel
- Filter by goal
- Filter by status
- Tags
- Add rule
- Global logs

Rule card/row:

- Name
- Channel + goal
- Scope
- Trigger/availability summary
- Template
- Tags
- ON/OFF
- Health
- Last run
- Next run
- Success/failure count
- Run
- Logs
- Duplicate
- Edit
- Delete

Status:

- Active
- Paused
- Invalid
- Needs attention
- Unsupported
- Archived

## 16. Logging

Display format wajib:

```
01 January 2025, 14:32:15.128 [INFO] Message
```

Level:

- DEBUG
- INFO
- SUCCESS
- WARNING
- ERROR
- CRITICAL

Structured log fields:

- ISO timestamp + timezone
- Level
- Event code
- Channel
- Rule ID
- Execution ID
- Context/CR ID
- Step
- Human-readable message
- Duration
- Structured error/context

Execution status:

- Queued
- Waiting
- Running
- Succeeded
- Partially succeeded
- Failed
- Skipped
- Canceled
- Missed

Global log drawer dan per-rule log memakai komponen yang sama. Per-rule drawer otomatis difilter ke rule terkait. Jangan menyimpan body email penuh atau attachment content di log biasa.

## 17. Outlook Health & Diagnostics

Status panel:

- Outlook edition detected
- Outlook process state
- COM session state
- Active account
- Automation worker state
- Last successful check
- Last error
- `Run diagnostics`
- `Open Outlook`

Possible states:

- Ready
- Outlook closed
- Starting Outlook
- COM unavailable
- New Outlook unsupported
- Account unavailable
- Offline
- Permission blocked

Semua failure harus menghasilkan actionable message, bukan hanya stack trace.

## 18. Safety, Validation, dan Idempotency

- Draft-first sebagai default untuk rule email baru.
- Direct send merupakan pilihan eksplisit.
- Resend membutuhkan confirmation.
- Duplicate rule selalu OFF.
- Scheduled jobs mempunyai unique occurrence key.
- Outlook email processing menggunakan Entry ID/conversation identity.
- Placeholder wajib di-resolve sebelum Send Direct.
- Automatic CR status update wajib menyimpan `.msg` terlebih dahulu.
- Bounded retry + timeout; tidak ada infinite retry.
- Arbitrary code/script execution tidak didukung.
- Sensitive email content tidak masuk log default.

## 19. Placeholder System

Placeholder registry harus typed dan dapat dicari dari editor.

Contoh domain:

- CR Number
- CR Name
- Appcode
- CR Type
- Project Type
- CR Status
- Drone Status
- UAT/PROD dates
- Project folder/path
- Current date/time

Setiap placeholder mempunyai:

- Key
- Display label
- Source
- Data type
- Example
- Required flag
- Fallback
- Formatter

Jika placeholder wajib tidak dapat di-resolve:

- Draft/manual: tampilkan error dan izinkan user memperbaiki.
- Send Direct/background: hentikan execution dan beri notifikasi.

## 20. Implementation Phases

### Phase 1 — Foundation & parity

- Finalize domain models.
- Full sectioned Rule Editor.
- Global latest execution log.
- Shared recurrence builder.
- Health/diagnostics service.
- Idempotency and execution state machine.

### Phase 2 — Outlook Templates

- Goal-specific template editor.
- Visual/HTML/Import HTML.
- Preview in Outlook.
- Placeholder registry/resolver.
- Recipient autocomplete.
- Search/filter/tags/rule attachment status.

### Phase 3 — Send New Email

- Manual and CR-eligible rules.
- Draft/Send Direct modes.
- Sent-state detection.
- Resend confirmation.
- Follow-up action registry.

### Phase 4 — Scheduler

- Custom recurrence builder.
- Multiple slots.
- End conditions.
- Preflight, auto-launch Outlook, grace period, missed-run UX.
- Pending draft handling.

### Phase 5 — Reply Email

- Folder picker and email query builder.
- Reply/Reply All through Outlook.
- Selection strategy.
- Draft lifecycle.
- Deduplication and loop protection.

### Phase 6 — Check Email & Status Update

- Polling worker.
- Force Check Now.
- `.msg` persistence in `_cr-docs`.
- CR/Drone ordered status actions.
- Stop conditions and manual override handling.

### Phase 7 — Teams

- Templates and Saved Automations.
- Deeplink target builder.
- Honest delivery-state model.
- Project Details integration.

### Phase 8 — Reminder

- CRUD + recurrence.
- Due Soon/Overdue KPI.
- Notifications, snooze, completion, contextual actions.

### Phase 9 — Hardening

- Recovery after restart/crash.
- Migration of existing seeded rules/templates.
- Performance tests for Outlook folder scanning.
- Error simulation.
- Accessibility and keyboard navigation.
- User verification.

## 21. Existing Implementation Gap Checklist

Before coding, compare this source of truth against:

- `PRD.md` §16
- `_docs/specs/automations-parity-matrix.md`
- `_docs/specs/superpowers/specs/2026-07-08-automation-system-design.md`
- Existing `ProjectDetails.svelte` automation panel
- Existing Outlook, TeamsActions, SchedulerActions, RulesActions, and logs implementation

Known gaps to verify:

- Full sectioned goal-centric Rule Editor.
- Teams Saved Automations list.
- Reminder Due Soon/Overdue based on real next-run timestamp.
- Global latest execution log.
- Outlook template editor behavior in this document.
- Removal of Downloaded Emails subtab.
- New scheduler recurrence and recovery behavior.
- Outlook Reply Email query/dedup lifecycle.
- Auto Update CR/Drone evidence workflow.

## 22. Acceptance Criteria Utama

1. User dapat membuat template Outlook New Email dan Reply Email dengan editor yang sesuai goal.
2. Preview selalu dibuka di Outlook Classic, bukan preview tiruan aplikasi.
3. Project Details hanya menampilkan rule CR-related yang cocok.
4. On CR Condition tidak mengirim otomatis; user tetap menjalankan action.
5. Scheduled Auto-send tidak silent-fail ketika Outlook/laptop bermasalah.
6. Missed schedule ditangani dengan grace period dan confirmation.
7. Reply/Reply All menggunakan email asli dan behavior Outlook.
8. Email yang sama tidak diproses dua kali oleh rule yang sama.
9. Auto Update CR/Drone membutuhkan `CRNUMBER`, sender/recipient guard, dan bukti `.msg`.
10. `.msg` masuk ke `_cr-docs` dengan subject asli + timestamp jika duplikat.
11. Manual status change menghentikan monitoring yang tidak lagi relevan.
12. Teams delivery state tidak mengklaim sent jika hanya membuka deeplink.
13. Semua execution memiliki structured log dan human-readable timeline.
14. UI mengikuti design tokens dan shared components Project Tracker yang sudah ada; jangan membuat design system baru.

## 23. Instruksi untuk AI Coding Agent

1. Baca source of truth dan dokumen referensi sebelum mengubah kode.
2. Audit implementasi existing; jangan rewrite bagian yang sudah benar.
3. Catat setiap keputusan/perubahan arah di `_docs/DECISIONS.md` secara append-only.
4. Update `_docs/PROGRESS.md` setelah setiap slice.
5. Implementasikan per phase/slice kecil.
6. Jalankan scoped tests untuk area yang berubah; full suite hanya saat explicit full check atau pre-release.
7. Jangan mengubah schema/payload tanpa migration dan backward compatibility.
8. Pertahankan dark minimal UI, existing tokens, shared components, dan bottom-dock navigation.
9. Semua automation operation harus observable, cancelable bila relevan, idempotent, dan recoverable setelah restart.
10. Jangan mengklaim capability Outlook/Teams yang tidak dapat diverifikasi oleh implementasi nyata.

<aside>
✅

Dokumen ini menggantikan asumsi lama yang bertentangan: Project Details menjalankan rules, bukan templates; CR conditions bersifat eligibility untuk flow manual; Downloaded Emails subtab dihapus; update status CR/Drone berasal dari bukti email yang ditemukan dan disimpan.

</aside>