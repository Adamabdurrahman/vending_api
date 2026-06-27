# PROMPT: FROM API (vending_api) → CAPSTONE (Android)

> **Cara pakai file ini:**
> 1. Isi bagian `[FILL: ...]` di Section 0 (root path) sebelum diberikan ke AI
> 2. Semua bagian lain sudah terisi lengkap — tidak perlu diubah
> 3. Berikan seluruh isi file ini sebagai system prompt / context awal ke AI Agent
> 4. Baca juga file pendamping: `Plan/API_Bundle.md`

---

## ════════════════════════════════════════
## SECTION 0 — ROOT PATH DECLARATION
## ════════════════════════════════════════

> **WAJIB diisi sebelum prompt diberikan ke AI.**

```
PROJECT A — vending_api (FastAPI Python)
Root Path : [FILL: contoh → C:\Users\namauser\Documents\vending_api]
C:\Users\isyaa\OneDrive\Documents\Web and Code\vending_api

PROJECT B — Capstone (Android Studio Java)
Root Path : [FILL: contoh → C:\Users\namauser\AndroidStudioProjects\CapstoneApp]
C:\Users\isyaa\AndroidStudioProjects\CapstoneProject
```

---

## ════════════════════════════════════════
## SECTION 1 — RINGKASAN SWAGGER BARU (sudah terisi)
## ════════════════════════════════════════

Project A memiliki **18 swagger group, 71 endpoint**. Berikut 5 swagger yang BARU
ditambahkan (yang perlu diimplementasikan ke Project B):

```
Tag: "Restock Management"   (8 endpoint)
  GET    /api/v1/restock                           → list semua restock
  GET    /api/v1/restock/alerts/low-stock          → alert stok rendah
  GET    /api/v1/restock/vm/{vm_id}                → restock per VM
  GET    /api/v1/restock/{restock_id}              → detail by ID
  POST   /api/v1/restock                           → buat/update slot (upsert)
  PUT    /api/v1/restock/vm/{vm_id}/slot/{slot}    → update qty cepat
  PUT    /api/v1/restock/{restock_id}              → update by ID
  DELETE /api/v1/restock/{restock_id}              → hapus

Tag: "Slot Number"   (5 endpoint)
  GET    /api/v1/slot?vm_id={id}                   → slot per VM
  GET    /api/v1/slot/{slot_id}                    → detail
  POST   /api/v1/slot                              → buat slot baru
  PUT    /api/v1/slot/{slot_id}                    → update
  DELETE /api/v1/slot/{slot_id}                    → hapus

Tag: "Manage Alat VM"   (5 endpoint)
  GET    /api/v1/machine                           → list semua mesin
  GET    /api/v1/machine/{machine_id}              → detail
  POST   /api/v1/machine                           → tambah mesin
  PUT    /api/v1/machine/{machine_id}              → update
  DELETE /api/v1/machine/{machine_id}              → hapus

Tag: "Shift Management"   (5 endpoint)
  GET    /api/v1/shift                             → list semua shift
  GET    /api/v1/shift/{shift_id}                  → detail
  POST   /api/v1/shift                             → buat shift
  PUT    /api/v1/shift/{shift_id}                  → update
  DELETE /api/v1/shift/{shift_id}                  → hapus

Tag: "Inventory Dashboard"   (3 endpoint)
  GET    /api/v1/inventory/dashboard               → dashboard utama + DSS
  GET    /api/v1/inventory/movements               → riwayat pergerakan stok (paginated)
  POST   /api/v1/inventory/stock-in                → input stok masuk dari supplier
```

**PENTING — Dua jenis pekerjaan berbeda di Project B:**
- `Restock Management`, `Slot Number`, `Manage Alat VM`, `Shift Management`
  → **Build CRUD dari nol** (Activity + XML + API call)
- `Inventory Dashboard`
  → **UI sudah ada di Android**, tinggal **sambungkan ke 3 API endpoint** di atas

---

## ════════════════════════════════════════
## SECTION 2 — INSTRUKSI UNTUK AI: PELAJARI PROJECT A
## ════════════════════════════════════════

Kamu adalah AI agent yang akan membantu mengintegrasikan dua project:
- **Project A**: Backend API berbasis **FastAPI (Python)** — sudah berjalan & tested
- **Project B**: Aplikasi Android berbasis **Java + XML (Activity-based)** — akan diintegrasikan

### LANGKAH 1 — Pelajari Project A (vending_api)

Baca file-file berikut dari Project A secara berurutan:

**Core:**
1. `database.py` → koneksi SQL Server, cara session dibuat
2. `models.py` → ORM models: User, Variant, Restock, SlotNumber, Machine, Shift
3. `schemas.py` → semua Pydantic request/response schemas
4. `main.py` → seluruh 71 endpoint beserta tag Swagger-nya

**Service layer (baca sesuai kebutuhan endpoint yang akan diimplementasi):**
5. `restock_service.py` → CRUD stok slot VM
6. `slot_service.py` → CRUD konfigurasi slot mesin
7. `machine_service.py` → CRUD data mesin vending
8. `shift_service.py` → CRUD jam shift kerja
9. `inventory_service.py` → Inventory Dashboard + DSS + warehouse stock
10. `dashboard_service.py` → data dashboard monitoring
11. `user_auth_service.py` → autentikasi dan manajemen user
12. `calendar_service.py` → kalender operasional
13. `notif_service.py` → sistem notifikasi

**Dokumen desain Inventory Dashboard (WAJIB dibaca sebelum mengerjakan Inventory):**
14. `Plan/InventoryDashboard/01_database_design.md`
15. `Plan/InventoryDashboard/02_flow_logic.md`
16. `Plan/InventoryDashboard/03_data_response.md`
17. `Plan/InventoryDashboard/04_endpoint_ui_design.md` ← desain UI Android ada di sini

Setelah membaca, kamu harus memahami:
- Tabel DB yang digunakan setiap endpoint
- Schema request/response dari setiap endpoint
- Alur: DB → Service → API → Response

### LANGKAH 2 — Baca File API Bundle

Setelah mempelajari Project A, baca:
```
Plan/API_Bundle.md
```
File ini berisi spesifikasi lengkap semua API yang harus diimplementasikan ke Project B,
termasuk request body, response format, dan catatan khusus per fitur.

---

## ════════════════════════════════════════
## SECTION 3 — INSTRUKSI UNTUK AI: PELAJARI PROJECT B
## ════════════════════════════════════════

### LANGKAH 3 — Pelajari Project B (Android Capstone)

Sebelum menulis satu baris kode pun, lakukan analisa berikut:

#### 3A — Deteksi Library HTTP
Baca file `build.gradle` (app level) dan temukan library jaringan yang digunakan.
Gunakan library yang SUDAH ADA — jangan menambahkan dependency baru tanpa alasan kuat.

#### 3B — Pahami Struktur Navigasi
- Baca file menu XML di `res/menu/`
- Cari menu bernama **"module"** dan sub menu **"Management Variant"**
- Semua fitur CRUD baru ditambahkan di menu "module", sejajar "Management Variant"
- Inventory Dashboard sudah ada di project — cari Activity-nya terlebih dahulu

#### 3C — Pahami Pattern Kode yang Ada
Baca 2-3 Activity yang sudah ada untuk memahami:
- Cara Activity memanggil API
- Cara response ditampilkan ke UI
- Cara data session dibaca dari SharedPreferences

> **Session User (SharedPreferences):**
> Login menyimpan: `id_recnum_mur`, `Id`, `username`, `email_primary`,
> `level_user`, `status_active`, `photo_url`
> Gunakan mekanisme yang SAMA untuk semua endpoint yang butuh data user.

#### 3D — Temukan Base URL
Cari konstanta IP/URL server (hardcode). Catat lokasinya, jangan ubah nilainya.

#### 3E — Inventory Dashboard Activity
Cari Activity yang sudah ada untuk Inventory Dashboard. Baca:
- Variabel/field yang sudah dideklarasikan
- Layout XML yang digunakan
- Komponen UI yang sudah ada (CardView, RecyclerView, FAB, dll)
Kamu hanya perlu **menambahkan pemanggilan API**, bukan membuat ulang UI.

---

## ════════════════════════════════════════
## SECTION 4 — INSTRUKSI EKSEKUSI
## ════════════════════════════════════════

### LANGKAH 4 — Eksekusi ke Project B

**Aturan Umum:**
1. Ikuti pattern kode yang sudah ada — jangan ubah arsitektur
2. Gunakan library HTTP yang terdeteksi di LANGKAH 3A
3. Gunakan SharedPreferences untuk data session user
4. Tangani error response — minimal Toast atau AlertDialog
5. Jangan hardcode string — gunakan `strings.xml`

---

### TIPE 1 — CRUD dari Nol (Restock, Slot, Machine, Shift)

Referensi: lihat cara "Management Variant" diimplementasikan, lakukan hal yang sama.

**Setiap fitur CRUD minimal terdiri dari:**
- 1 file Activity Java (`NamaFeatureActivity.java`)
- 1 file layout XML (`activity_nama_feature.xml`)
- 1 file item layout XML (`item_nama_feature.xml`) jika pakai RecyclerView
- Pendaftaran di `AndroidManifest.xml`
- Tambahan menu item di menu "module"

**Pattern CRUD standar yang harus diimplementasi:**
- Tampilkan list data dari GET endpoint
- Tombol/FAB untuk Create (buka dialog atau Activity baru)
- Swipe/Long press atau tombol Edit untuk Update
- Konfirmasi dialog sebelum Delete
- Refresh list setelah operasi Create/Update/Delete

---

### TIPE 2 — Sambungkan UI ke API (Inventory Dashboard)

UI sudah ada. Yang perlu dilakukan:

**A. Sambungkan `GET /api/v1/inventory/dashboard`**
- Panggil saat Activity dibuka (dan saat refresh)
- Tampilkan data ke komponen UI yang sudah ada:
  - Summary cards: `total_predicted_demand`, `total_warehouse_stock`, `total_vm_stock`, `total_to_purchase`
  - List per variant: `variant_name`, `predicted_demand`, `warehouse_stock`, `vm_stock`, `to_purchase`, `purchase_percentage`
  - Decision support notes: tampilkan array `decision_support.notes` sebagai list teks
  - Quarter selector: gunakan `available_quarters` untuk dropdown/spinner
  - History summary: tampilkan jika `history_summary != null` (kuartal lalu)
- Parameter: `year` dan `quarter` (opsional, default kuartal berikutnya)

**B. Sambungkan `GET /api/v1/inventory/movements`**
- Tampilkan di tab/section riwayat pergerakan stok
- Implementasi paginasi (load more atau paging)
- Filter by `variant` dan `type` (IN/OUT)
- Setiap item: tanggal, nama variant, tipe gerakan, qty, balance_after, keterangan

**C. Sambungkan `POST /api/v1/inventory/stock-in`**
- Dipanggil dari FAB "Tambah Stok Masuk" → buka StockInActivity/Dialog
- Form: 4 field qty (satu per variant), field catatan opsional
- Placeholder qty = nilai `to_purchase` dari DSS (rekomendasi beli)
- Tampilkan saldo gudang saat ini di bawah setiap field
- Setelah berhasil: refresh dashboard
- Request body:
  ```json
  {
    "items": [
      {"variant_name": "Coklat", "qty": 0},
      {"variant_name": "Strawberry", "qty": 0},
      {"variant_name": "Moca", "qty": 0},
      {"variant_name": "Original (Putih)", "qty": 0}
    ],
    "note": "keterangan opsional"
  }
  ```

---

### Urutan Prioritas Eksekusi

Ikuti urutan ini, selesaikan satu sebelum lanjut ke berikutnya:

```
1. Inventory Dashboard   ← sambungkan UI yang sudah ada ke 3 API
2. Restock Management    ← build CRUD dari nol
3. Manage Alat VM        ← build CRUD dari nol
4. Shift Management      ← build CRUD dari nol
5. Slot Number           ← build CRUD dari nol
```

---

## ════════════════════════════════════════
## SECTION 5 — CATATAN TEKNIS PENTING
## ════════════════════════════════════════

**Tentang Restock:**
- `status_restok` adalah **VARCHAR** di DB, bukan integer → kirim sebagai string `"1"` atau `"0"`
- `POST /api/v1/restock` bersifat **UPSERT** — jika slot sudah ada untuk VM tersebut,
  data akan di-UPDATE, bukan INSERT baru. Komunikasikan ini ke user di UI.

**Tentang Shift:**
- `jam_mulai` dan `jam_akhir` dikirim sebagai string format `"HH:MM"` (contoh: `"07:00"`)
- `status_active` adalah **VARCHAR** → kirim sebagai `"1"` (aktif) atau `"0"` (nonaktif)

**Tentang Inventory Dashboard:**
- Setiap kali endpoint `GET /dashboard` dipanggil, server otomatis menjalankan
  auto-sync stocking events — ini normal, tidak perlu aksi khusus dari Android
- Jika `has_prediction_data = false` → tampilkan pesan bahwa data prediksi belum tersedia
  untuk kuartal ini, dan arahkan user ke kuartal yang tersedia di `available_quarters`
- `warehouse_stock` bisa bernilai negatif jika stok gudang belum pernah diisi.
  Tampilkan indikator visual (warna merah) untuk nilai negatif

**Tentang Auth:**
- API tidak menggunakan Bearer token — tidak perlu Authorization header
- Format tanggal selalu `YYYY-MM-DD`

**Jika ada masalah:**
- File tidak ditemukan → tanya user, jangan berasumsi
- Endpoint tidak ada di API → tandai `[SKIP]` dan lanjut
- Konflik pattern Android vs instruksi di atas → utamakan pattern Android
- Setelah selesai semua → buat summary: berhasil, skip, perlu perhatian
