# Penjelasan Teknis Implementasi Tiptap, Paste Gambar, Autosave, dan Export DOCX

## 1. Tujuan Implementasi

Fitur rich text editor di aplikasi harus memenuhi kebutuhan berikut:

1. Editor tetap menggunakan Tiptap yang sudah ada di project.
2. User dapat menulis dan memformat teks.
3. User dapat membuat serta mengedit tabel.
4. User dapat memasukkan gambar dari file.
5. User dapat melakukan screenshot menggunakan `Win + Shift + S`, lalu langsung menekan `Ctrl + V` di editor.
6. Dokumen otomatis tersimpan tanpa membebani CPU, RAM, disk, atau membuat UI tersendat.
7. File keluaran utama dapat berupa `.docx`.
8. Tampilan DOCX harus sedekat mungkin dengan tampilan dokumen di Tiptap.
9. Kegagalan export DOCX tidak boleh menyebabkan konten editor hilang.
10. Implementasi harus mengikuti struktur project yang sudah ada, bukan membuat arsitektur paralel yang tumpang tindih.

## Project saat ini sudah memiliki frontend Svelte, `NotesEditor.svelte`, `bridge.ts`, custom extension `FontSize.ts`, backend `web/js_api.py`, folder `services`, serta test untuk bridge dan notes persistence. Agent perlu memeriksa implementasi yang sudah berjalan sebelum menambah file, method, atau dependency baru.

## 2. Prinsip Utama Arsitektur

Penyimpanan source editor dan pembuatan DOCX harus dipisahkan.

Flow dasarnya:

```text
Tiptap Editor
    ↓
Tiptap JSON
    ↓
Autosave source document
    ↓
DOCX export dijalankan secara terjadwal
    ↓
File temporary
    ↓
Atomic replace
    ↓
File DOCX final
```

Tiptap JSON menjadi sumber data utama karena mempertahankan struktur node, marks, atribut tabel, ukuran gambar, alignment, dan atribut custom dengan lebih baik dibanding hanya menyimpan HTML.

HTML boleh tetap dihasilkan untuk preview, debugging, clipboard, atau fallback conversion, tetapi bukan satu-satunya source of truth.

Struktur data minimum:

```json
{
  "document_id": "project-123",
  "revision": 17,
  "content": {
    "type": "doc",
    "content": []
  },
  "document_settings": {
    "page_format": "A4",
    "margin_top_mm": 20,
    "margin_right_mm": 20,
    "margin_bottom_mm": 20,
    "margin_left_mm": 20,
    "default_font_family": "Arial",
    "default_font_size_pt": 11,
    "line_height": 1.15
  }
}
```

---

## 3. Audit Existing Code Sebelum Implementasi

Sebelum mengubah code, agent perlu memeriksa:

```text
frontend/package.json
frontend/src/lib/components/NotesEditor.svelte
frontend/src/lib/bridge.ts
frontend/src/lib/extensions/FontSize.ts
frontend/src/lib/types.ts
frontend/src/styles.css
web/js_api.py
app_web.py
services/
tests/test_bridge_contract_guard.py
tests/test_phase_e_notes_persistence.py
frontend/tests/bridge.test.ts
frontend/tests/as-is-prototype-parity.test.mjs
```

Hal yang perlu diidentifikasi:

```text
- Versi Tiptap yang sedang dipakai.
- Extension Tiptap yang sudah didaftarkan.
- Bentuk data notes yang sekarang disimpan.
- Apakah notes saat ini disimpan sebagai HTML, Markdown, plain text, atau JSON.
- Kontrak yang sudah digunakan antara bridge.ts dan js_api.py.
- Mekanisme debounce yang mungkin sudah ada.
- Lokasi penyimpanan project dan notes.
- Cara aplikasi menangani shutdown.
- Pola service dan dependency injection yang sudah dipakai.
- Test yang sudah mengunci kontrak lama.
```

Jangan langsung mengganti seluruh `NotesEditor.svelte`. Pertahankan behavior yang sudah ada dan lakukan perubahan secara bertahap.

---

## 4. Konfigurasi Tiptap

Editor tetap menggunakan Tiptap.

Extension minimum yang dibutuhkan:

```text
StarterKit
TextStyle
FontFamily
FontSize atau custom FontSize yang sudah ada
Color
Highlight
TextAlign
Underline
Image
FileHandler
TableKit
Link
```

Untuk tabel, gunakan extension resmi Tiptap `TableKit`. Extension tabel mendukung pembuatan tabel, row, cell, header, serta column resizing ketika dikonfigurasi.

Contoh konseptual:

```ts
const editor = new Editor({
  extensions: [
    StarterKit,
    TextStyle,
    FontFamily,
    FontSize,
    Color,
    Highlight,
    TextAlign.configure({
      types: ['heading', 'paragraph'],
    }),
    Underline,
    Image.configure({
      allowBase64: false,
      resize: {
        enabled: true,
        minWidth: 50,
        minHeight: 50,
        alwaysPreserveAspectRatio: true,
      },
    }),
    FileHandler.configure({
      allowedMimeTypes: [
        'image/png',
        'image/jpeg',
        'image/webp',
        'image/gif',
      ],
    }),
    TableKit.configure({
      table: {
        resizable: true,
      },
    }),
  ],
})
```

`Image` hanya bertanggung jawab menampilkan node gambar. Extension tersebut tidak mengunggah atau menyimpan file. Tiptap menyediakan `FileHandler` untuk menangkap paste dan drop, tetapi upload tetap menjadi tanggung jawab aplikasi.

---

## 5. Flow Screenshot dan Ctrl+V

User experience yang diinginkan:

```text
Win + Shift + S
    ↓
User memilih area screenshot
    ↓
Clipboard berisi image/png
    ↓
User fokus ke editor
    ↓
Ctrl + V
    ↓
FileHandler menangkap file
    ↓
Frontend mengirim file ke Python
    ↓
Python menyimpan file ke folder assets
    ↓
Python mengembalikan asset URL atau asset ID
    ↓
Tiptap memasukkan image node di posisi cursor
```

`FileHandler` memiliki event `onPaste`, `onDrop`, filter MIME type, dan opsi `consumePasteEvent` untuk mencegah konten diproses dua kali.

Gambar tidak boleh disimpan permanen sebagai Base64 di dalam JSON.

Base64 hanya boleh dipakai sementara ketika mengirim clipboard image dari JavaScript ke Python apabila bridge saat ini belum mendukung binary transfer.

Setelah backend menerima gambar:

```text
Base64 atau binary
    ↓
Decode satu kali
    ↓
Validasi MIME dan ukuran
    ↓
Generate nama file unik
    ↓
Atomic save
    ↓
Return asset_id dan URL
```

Contoh struktur asset:

```text
project-data/
└── documents/
    └── project-123/
        ├── source.json
        ├── output.docx
        └── assets/
            ├── 8c91d620.png
            └── f23ab841.jpg
```

Node gambar di Tiptap sebaiknya menyimpan:

```json
{
  "type": "image",
  "attrs": {
    "assetId": "8c91d620",
    "src": "asset://8c91d620.png",
    "alt": "Screenshot",
    "title": null,
    "width": 720,
    "height": 405
  }
}
```

Gunakan `assetId` sebagai identitas stabil. Jangan bergantung pada absolute path Windows di JSON.

Hindari format seperti:

```text
D:\Users\Ibrahim\Pictures\screenshot.png
```

Absolute path membuat dokumen mudah rusak ketika folder project dipindahkan atau aplikasi dijalankan dari komputer lain.

---

## 6. Penyimpanan Source Document

Tiptap memiliki event `update` yang dipanggil ketika konten berubah. Event ini digunakan untuk menandai dokumen sebagai dirty dan menjadwalkan autosave, bukan untuk membuat DOCX pada setiap perubahan.

Flow autosave source:

```text
Tiptap onUpdate
    ↓
dirty = true
    ↓
revision bertambah
    ↓
restart debounce timer
    ↓
user berhenti mengetik 750–1.500 ms
    ↓
editor.getJSON()
    ↓
bridge.saveDocumentSource(...)
    ↓
Python menyimpan source.json
```

Konfigurasi awal yang disarankan:

```text
Autosave JSON debounce: 1.000 ms
```

Autosave JSON relatif ringan karena hanya melakukan serialisasi dan menulis file teks.

Jangan melakukan ini:

```text
Setiap keystroke
    ↓
Generate DOCX
```

Flow tersebut akan menambah CPU usage, disk I/O, garbage collection, dan kemungkinan UI freeze.

---

## 7. Source of Truth dan Derived Output

File harus dibedakan menjadi dua kategori.

### Source of truth

```text
source.json
```

Isinya:

```text
- Tiptap JSON
- Revision
- Document settings
- Asset references
- Schema version
- Last saved timestamp
```

### Derived output

```text
output.docx
```

DOCX dapat dibuat ulang dari `source.json`.

Apabila DOCX gagal dibuat, konten user tetap aman karena source JSON sudah tersimpan.

Apabila format exporter diubah pada masa depan, semua DOCX lama dapat diregenerasi dari source JSON terbaru.

---

## 8. Trigger Pembuatan DOCX

DOCX tidak boleh dibuat pada setiap `onUpdate`.

Trigger yang disarankan:

```text
1. User menekan Ctrl+S.
2. User menekan tombol Save.
3. User berhenti mengedit selama 15–30 detik.
4. User berpindah dari dokumen, apabila export terakhir belum sesuai revision terbaru.
5. Aplikasi akan ditutup dan dokumen masih dirty.
6. User memilih Export DOCX.
```

Konfigurasi awal:

```text
Autosave source JSON : debounce 1 detik
Idle DOCX export     : 20 detik
Manual save          : langsung dijadwalkan
Application close    : final export jika dirty
```

Untuk dokumen besar atau banyak gambar:

```text
Idle DOCX export : 30–60 detik
```

Tidak perlu membuat DOCX ketika:

```text
- Cursor hanya berpindah.
- Selection berubah.
- User menekan Save tetapi hash tidak berubah.
- Revision sudah pernah diekspor.
- Dokumen baru dibuka tanpa perubahan.
```

---

## 9. Hash dan Revision

Setiap save harus memiliki revision yang meningkat.

Contoh:

```json
{
  "document_id": "project-123",
  "revision": 42,
  "content_hash": "sha256..."
}
```

Gunakan hash dari canonical JSON:

```python
json.dumps(
    content,
    ensure_ascii=False,
    sort_keys=True,
    separators=(",", ":"),
)
```

Flow:

```text
Current hash == last saved hash
    ↓
Skip source save

Current hash == last exported hash
    ↓
Skip DOCX export
```

Hash mencegah proses ulang yang tidak diperlukan.

Revision mencegah file versi lama menimpa versi baru.

---

## 10. Export Coordinator

Hanya boleh ada satu export DOCX aktif untuk satu aplikasi atau satu dokumen pada saat yang sama.

Aturan:

```text
- Maksimal satu export aktif.
- Request export baru tidak langsung membuat job paralel.
- Selama export berlangsung, simpan revision terbaru sebagai pending.
- Setelah job selesai, cek apakah ada revision lebih baru.
- Kalau ada, export hanya revision terbaru.
- Revision di tengah dibuang.
```

Contoh kondisi:

```text
Revision 10 mulai export
Revision 11 masuk
Revision 12 masuk
Revision 13 masuk
Revision 10 selesai
    ↓
Langsung export revision 13
```

Jangan melakukan:

```text
Revision 10, 11, 12, dan 13 diekspor bersamaan
```

Pola ini disebut latest revision wins.

Tujuannya:

```text
- CPU tidak melonjak.
- Disk tidak dipukul banyak proses.
- Tidak ada race condition.
- File lama tidak menimpa file baru.
- Memori lebih stabil.
```

---

## 11. Background Processing

Pembuatan DOCX tidak boleh menghalangi UI thread.

Untuk exporter Python, gunakan satu worker:

```python
ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="docx-export",
)
```

`ThreadPoolExecutor` menjalankan callable secara asynchronous menggunakan sejumlah thread maksimal sesuai `max_workers`. Satu worker cukup untuk mencegah export paralel dan mengendalikan penggunaan resource.

Gunakan `ProcessPoolExecutor(max_workers=1)` hanya apabila profiling membuktikan bahwa:

```text
- Export memakan CPU tinggi.
- UI tetap tersendat meskipun memakai thread.
- Dokumen sangat panjang.
- Banyak gambar resolusi tinggi.
- Banyak tabel kompleks.
```

Jangan langsung memakai multiprocessing tanpa pengukuran karena proses baru di Windows memiliki overhead startup dan komunikasi tambahan.

Untuk exporter yang berjalan di browser, gunakan state frontend:

```text
exportRunning
pendingRevision
lastExportedRevision
```

Jangan memanggil exporter browser beberapa kali secara paralel.

---

## 12. Pilihan Mesin Export DOCX

Ada dua jalur implementasi.

# Jalur A: Fidelity Tertinggi

Gunakan stack resmi:

```text
Tiptap Pro ExportDocx
Tiptap Pages
PagesTableKit
ConvertKit
```

`ExportDocx` resmi membaca Tiptap JSON secara langsung dan mempertahankan atribut editor seperti ukuran gambar, lebar kolom melalui `colwidth`, `rowspan`, alignment, paragraph spacing, indentation, serta beberapa atribut formatting lain. Export dapat berjalan langsung di browser dan menghasilkan `Blob`.

`Pages` menambahkan layout halaman, ukuran kertas, margin, header, footer, page break, dan zoom sehingga editor lebih menyerupai word processor.

Untuk tabel di editor paginated, gunakan `PagesTableKit`, bukan table extension open-source biasa. Dokumentasi Tiptap menyebutkan bahwa Pages memerlukan table stack khusus agar tabel dapat dipisahkan dan dirender dengan benar lintas halaman.

Flow:

```text
Tiptap JSON
    ↓
ExportDocx
    ↓
Blob DOCX
    ↓
Bridge atau local HTTP endpoint
    ↓
Python menerima binary
    ↓
Atomic save
```

DOCX Blob sebaiknya dikirim sebagai binary melalui endpoint lokal apabila arsitektur aplikasi mendukungnya.

Hindari Base64 untuk file DOCX besar karena payload menjadi lebih besar dan memerlukan encode/decode tambahan.

Jalur ini adalah pilihan utama apabila requirement “hasil DOCX harus sedekat mungkin dengan tampilan editor” benar-benar wajib.

Keterbatasan tetap ada. Dokumentasi resmi menyatakan export ditujukan agar visualnya faithful untuk fitur yang didukung, tetapi pixel-perfect parity dengan rendering engine Microsoft Word tidak dijamin.

# Jalur B: Gratis dan Dikontrol Python

Gunakan:

```text
Tiptap JSON
    ↓
Custom JSON-to-DOCX mapper
    ↓
python-docx
    ↓
DOCX
```

Mapper membaca setiap node dan mark:

```text
paragraph        → Word paragraph
heading          → Word heading
bold             → run.bold
italic           → run.italic
underline        → run.underline
text color       → font color
highlight        → character shading
font family      → run font
font size        → run size
text alignment   → paragraph alignment
bullet list      → Word numbering
ordered list     → Word numbering
image            → inline picture
table            → Word table
tableCell        → Word cell
rowspan          → vertical merge XML
colspan          → grid span XML
pageBreak        → Word page break
```

Jalur gratis dapat menghasilkan output yang rapi dan konsisten untuk fitur yang memang dipetakan.

Namun hasilnya tidak otomatis identik dengan tampilan browser. Semua fitur yang ingin dipertahankan harus memiliki mapping eksplisit.

Jangan memakai HTML-to-DOCX generik sebagai jalur utama apabila requirement fidelity tinggi. HTML converter cocok sebagai fallback atau MVP, tetapi CSS browser tidak memiliki padanan langsung untuk seluruh fitur Word.

---

## 13. Rekomendasi Pilihan Exporter

Prioritas:

```text
1. Tiptap Pro ExportDocx + Pages + PagesTableKit
   Untuk fidelity tertinggi dan layout print-like.

2. Custom Tiptap JSON → python-docx
   Untuk solusi gratis, deterministic, dan dikontrol penuh.

3. Tiptap HTML → Pandoc
   Untuk dokumen laporan yang rapi tetapi tidak benar-benar as-is.

4. HTML converter sederhana
   Hanya untuk MVP atau dokumen dengan styling minimal.
```

Apabila target “as-is” merupakan requirement keras, jalur pertama paling sesuai.

Apabila tidak ada budget, jalur kedua lebih benar dibanding mengandalkan converter HTML generik.

---

## 14. Menyamakan Tampilan Editor dan DOCX

Editor dan exporter harus menggunakan satu document style manifest yang sama.

Contoh:

```json
{
  "page": {
    "format": "A4",
    "width_mm": 210,
    "height_mm": 297,
    "margin_top_mm": 20,
    "margin_right_mm": 20,
    "margin_bottom_mm": 20,
    "margin_left_mm": 20
  },
  "body": {
    "font_family": "Arial",
    "font_size_pt": 11,
    "line_height": 1.15,
    "color": "#000000"
  },
  "paragraph": {
    "spacing_before_pt": 0,
    "spacing_after_pt": 8
  },
  "table": {
    "border_width_pt": 0.5,
    "cell_padding_pt": 5,
    "header_background": "#E7E6E6"
  }
}
```

Manifest ini dipakai oleh:

```text
Frontend CSS
DOCX exporter
Template DOCX
Page preview
Table styling
```

Jangan membuat style editor dan style exporter terpisah tanpa sumber konfigurasi bersama.

---

## 15. Editor Harus Menyerupai Kertas

Apabila editor selebar monitor sedangkan DOCX memakai ukuran A4, line wrapping tidak akan sama.

Contoh CSS non-paginated:

```css
.document-page {
  width: 210mm;
  min-height: 297mm;
  padding: 20mm;
  box-sizing: border-box;
  background: #ffffff;
}

.document-page .ProseMirror {
  width: 170mm;
  min-height: 257mm;
  font-family: Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.15;
}
```

CSS A4 saja hanya menyamakan lebar content area. CSS tersebut tidak otomatis membagi konten ke halaman secara akurat.

Untuk pagination yang benar, gunakan Pages atau implementasi page layout khusus.

---

## 16. Fitur yang Aman untuk Fidelity

Batasi toolbar pada fitur yang memiliki padanan Word yang jelas.

Fitur yang relatif aman:

```text
- Paragraph
- Heading
- Bold
- Italic
- Underline
- Strike
- Font family
- Font size
- Text color
- Highlight
- Left, center, right, justify
- Ordered list
- Bullet list
- Paragraph spacing
- Proportional line height
- Inline image
- Image width dan height
- Table
- Header row
- Rowspan
- Colspan
- Column width
- Page break
```

Fitur yang perlu dibatasi:

```text
- Absolute positioning
- Floating image bebas
- CSS flex
- CSS grid
- Gradient
- Transform
- Complex box shadow
- Arbitrary HTML
- Fixed pixel line-height
- Table yang lebih lebar dari halaman
- Font yang tidak tersedia di komputer atau tidak di-embed
```

---

## 17. Penyimpanan Gambar yang Efisien

Gambar disimpan satu kali.

Autosave JSON berikutnya hanya menyimpan asset reference.

Jangan lakukan:

```text
- Menyimpan Base64 permanen di source JSON.
- Mengirim ulang seluruh gambar setiap autosave.
- Resize ulang gambar setiap export.
- Compress ulang gambar setiap export.
- Menyalin gambar berulang kali ke folder berbeda.
```

Lakukan:

```text
- Simpan gambar saat paste/upload.
- Generate asset ID.
- Simpan ukuran tampilan di atribut node.
- Gunakan asset yang sama pada setiap export.
- Cache intrinsic width dan height.
```

Opsional:

```text
- Batasi gambar maksimal 10–15 MB.
- Validasi MIME dari byte signature, bukan nama file saja.
- Generate thumbnail hanya untuk preview bila gambar sangat besar.
- Jangan menurunkan kualitas original kecuali user memilih compress.
```

---

## 18. Atomic Save

Jangan menulis langsung ke file final.

Flow:

```text
Generate DOCX
    ↓
Tulis ke output.docx.tmp
    ↓
Flush
    ↓
Validasi file
    ↓
Backup file lama, bila diperlukan
    ↓
os.replace(tmp, output.docx)
```

`os.replace()` mengganti file tujuan dan merupakan primitive yang tepat untuk mengganti hasil sementara dengan file final setelah proses selesai.

Contoh struktur:

```text
output.docx
output.docx.tmp
output.docx.backup
```

File final hanya diganti setelah export benar-benar selesai.

---

## 19. Struktur Service yang Disarankan

Agent perlu menyesuaikan dengan pola service yang sudah ada.

Tambahan konseptual:

```text
services/
├── document_autosave_service.py
├── document_export_service.py
└── document_asset_service.py

infrastructure/
├── document_source_store.py
├── document_asset_store.py
├── docx_writer.py
└── atomic_file_writer.py
```

Namun nama dan lokasi akhir harus mengikuti pola project existing.

Jangan menambahkan folder baru apabila fungsi yang sama sudah tersedia di module lain.

Tanggung jawab:

### DocumentAssetService

```text
- Validasi gambar.
- Menyimpan gambar.
- Generate asset ID.
- Resolve asset path.
- Menghapus orphan asset secara aman.
```

### DocumentAutosaveService

```text
- Menyimpan source JSON.
- Menangani revision.
- Menghitung hash.
- Menolak stale revision.
```

### DocumentExportService

```text
- Membaca revision terbaru.
- Menjalankan exporter.
- Resolve asset.
- Menulis file temporary.
- Atomic replace.
- Menyimpan last exported hash dan revision.
```

### ExportCoordinator

```text
- Menjaga satu export aktif.
- Menyimpan pending revision terbaru.
- Membuang request lama.
- Menangani retry dan error.
```

---

## 20. Kontrak Bridge

Tambahan kontrak perlu mengikuti style yang sudah dipakai oleh `bridge.ts` dan `web/js_api.py`.

Method konseptual:

```ts
saveDocumentSource(payload)
saveEditorImage(payload)
requestDocumentExport(documentId, revision)
getDocumentSaveStatus(documentId)
```

Backend:

```python
def save_document_source(self, payload: dict) -> dict:
    ...

def save_editor_image(self, payload: dict) -> dict:
    ...

def request_document_export(
    self,
    document_id: str,
    revision: int,
) -> dict:
    ...

def get_document_save_status(
    self,
    document_id: str,
) -> dict:
    ...
```

Response harus konsisten:

```json
{
  "success": true,
  "status": "saved",
  "revision": 42,
  "error": null
}
```

Export request tidak perlu menunggu seluruh export selesai.

Response awal:

```json
{
  "success": true,
  "status": "queued",
  "revision": 42
}
```

UI dapat menampilkan:

```text
Saving…
Saved
Exporting DOCX…
DOCX saved
Export failed, source is safe
```

---

## 21. Shutdown Flow

Ketika aplikasi ditutup:

```text
Check dirty source
    ↓
Save JSON synchronously atau tunggu save aktif selesai
    ↓
Check exported revision
    ↓
Jika DOCX tertinggal, request final export
    ↓
Tunggu dengan timeout yang wajar
    ↓
Close application
```

Source JSON harus selalu diprioritaskan.

Apabila final DOCX export gagal atau timeout:

```text
- Jangan membatalkan shutdown tanpa alasan.
- Source JSON tetap aman.
- Tandai export_pending.
- Regenerate DOCX ketika dokumen dibuka kembali.
```

---

## 22. Error Handling

Contoh error yang harus ditangani:

```text
- Clipboard bukan gambar.
- Format gambar tidak didukung.
- File gambar terlalu besar.
- Folder project read-only.
- DOCX sedang dibuka di Microsoft Word sehingga terkunci.
- Disk penuh.
- Asset hilang.
- JSON invalid.
- Schema version tidak kompatibel.
- Exporter gagal.
- Aplikasi ditutup saat export.
```

Apabila DOCX sedang terbuka dan tidak dapat diganti:

```text
- Jangan menghapus file lama.
- Simpan source JSON.
- Simpan hasil export ke temporary file.
- Tampilkan status bahwa DOCX belum diperbarui.
- Retry ketika memungkinkan.
```

---

## 23. Performance Guardrails

Implementasi dianggap sehat apabila memenuhi aturan berikut:

```text
- onUpdate hanya menandai dirty dan menjadwalkan debounce.
- Tidak ada DOCX export per keystroke.
- Maksimal satu export worker.
- Latest revision wins.
- JSON save memakai debounce.
- DOCX export memakai idle delay.
- Hash digunakan untuk skip pekerjaan identik.
- Gambar disimpan sekali.
- Base64 tidak disimpan permanen.
- Binary DOCX tidak dikirim berulang kali.
- UI thread tidak menunggu export.
- Editor tidak dirender ulang penuh pada setiap event.
- Extension yang tidak dibutuhkan tidak dimuat.
```

Hindari polling sangat cepat.

Status export cukup diperbarui melalui:

```text
- callback,
- event queue,
- existing event mechanism,
- atau polling lambat 500–1.000 ms hanya selama export aktif.
```

---

## 24. Testing Minimum

Tambahkan test tanpa merusak contract test yang sudah ada.

### Frontend tests

```text
- onUpdate memakai debounce.
- Ctrl+V image memanggil upload satu kali.
- Duplicate paste tidak membuat dua image node.
- Upload sukses memasukkan node di posisi benar.
- Upload gagal tidak membuat broken image.
- Save status berubah dengan benar.
- Export request tidak dipanggil pada selection change.
```

### Backend tests

```text
- Source JSON tersimpan secara atomic.
- Revision lama ditolak.
- Hash yang sama tidak menulis ulang file.
- MIME image invalid ditolak.
- Asset ID aman dari path traversal.
- Export hanya berjalan satu kali.
- Latest revision wins.
- DOCX temporary tidak mengganti final ketika export gagal.
- Atomic replace berjalan setelah export sukses.
- File lama tetap ada ketika target terkunci.
```

### Integration tests

```text
- Teks, formatting, gambar, dan tabel dapat dibuka kembali.
- Screenshot Ctrl+V tersimpan dan tampil kembali.
- DOCX berisi gambar yang sama.
- Ukuran gambar mendekati editor.
- Lebar tabel dan kolom terjaga.
- Rowspan dan colspan terjaga.
- Page format dan margin sesuai.
- Closing app menyimpan revision terakhir.
```

### Performance tests

```text
- Mengetik cepat selama 30 detik hanya menghasilkan beberapa JSON save.
- Mengetik cepat tidak menghasilkan puluhan DOCX export.
- Banyak export request hanya menghasilkan revision awal dan revision terbaru.
- UI tetap responsif ketika export berlangsung.
- Memory tidak terus meningkat setelah export berulang.
```

---

## 25. Acceptance Criteria

Implementasi dianggap selesai apabila:

```text
1. User dapat mengetik dan memformat dokumen di Tiptap.
2. User dapat membuat dan mengedit tabel.
3. User dapat paste screenshot langsung dengan Ctrl+V.
4. Gambar tersimpan sebagai asset, bukan Base64 permanen.
5. Source JSON otomatis tersimpan setelah user berhenti mengetik.
6. DOCX tidak dibuat pada setiap keystroke.
7. DOCX dibuat saat Ctrl+S, tombol Save, idle, dan closing.
8. Hanya satu export berjalan pada satu waktu.
9. Revision lama tidak dapat menimpa revision baru.
10. Export failure tidak menghilangkan konten.
11. DOCX ditulis melalui temporary file dan atomic replace.
12. Font, ukuran, warna, alignment, list, gambar, dan tabel terlihat sedekat mungkin dengan editor.
13. Editor menggunakan ukuran halaman dan margin yang sama dengan DOCX.
14. Tidak ada UI freeze yang terasa pada penggunaan normal.
15. Test lama tetap lolos.
16. Test baru untuk paste image, autosave, export queue, dan atomic save ikut lolos.
```

---

## 26. Keputusan Arsitektur Final

Flow final yang direkomendasikan:

```text
Tiptap onUpdate
    ↓
Set dirty flag
    ↓
Debounce 1 detik
    ↓
Save Tiptap JSON
    ↓
Reset idle export timer
    ↓
20 detik tidak ada perubahan
    ↓
Check hash dan revision
    ↓
Queue satu export
    ↓
Generate DOCX di luar UI thread
    ↓
Write output.docx.tmp
    ↓
Atomic replace output.docx
```

Flow paste gambar:

```text
Screenshot
    ↓
Ctrl+V
    ↓
Tiptap FileHandler
    ↓
Python asset storage
    ↓
Return asset ID
    ↓
Insert Image node
    ↓
Autosave JSON
    ↓
Image ikut masuk ke DOCX pada export berikutnya
```

Pilihan fidelity:

```text
Fidelity tertinggi:
Tiptap Pro ExportDocx + Pages + PagesTableKit

Gratis:
Custom Tiptap JSON → python-docx
```

Kesimpulan teknis:

```text
Autosave source boleh sering.
DOCX export harus jarang, terkoordinasi, dan asynchronous.
Tiptap JSON harus menjadi source of truth.
Gambar harus menjadi reusable assets.
Editor dan DOCX harus memakai document style manifest yang sama.
Pixel-perfect absolut tidak dapat dijamin, tetapi visual fidelity tinggi dapat dicapai dengan membatasi fitur dan menggunakan exporter yang memahami atribut Tiptap.
```
