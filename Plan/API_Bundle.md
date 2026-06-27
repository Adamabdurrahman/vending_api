# API BUNDLE — Daftar API untuk Diimplementasikan ke Android Capstone

> **Panduan membaca file ini:**
> - File ini dibaca oleh AI setelah membaca `PROMPT_API_to_Capstone.md`
> - Setiap section = satu fitur di menu **"module"** Android
> - `[CONNECT]` = UI sudah ada di Android, tinggal sambungkan ke API
> - `[CRUD]` = harus build dari nol seperti Management Variant
> - `[EXIST]` = endpoint lama yang juga perlu diimplementasikan

---

## ══════════════════════════════════════
## BAGIAN 1 — KONTEKS EKSEKUSI
## ══════════════════════════════════════

**Target Menu di Android:**
- Masuk ke menu: **"module"**
- Tambahkan sub menu baru sejajar dengan sub menu **"Management Variant"** yang sudah ada
- Setiap section di bawah = 1 sub menu baru

**Yang sudah ada (jangan disentuh):**
- Sub menu "Management Variant" → sudah terhubung ke endpoint `/api/v1/variants`

---

## ══════════════════════════════════════
## BAGIAN 2 — API YANG SUDAH ADA (vending_api existing)
## ══════════════════════════════════════

> Endpoint-endpoint ini sudah ada di vending_api versi lama.
> Implementasikan ke Android sesuai prioritas yang ditetapkan di bawah.

---

### [EXIST] 📊 Dashboard Summary
**Target Android:** Sub menu "Dashboard" di menu "module"

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/dashboard/metrics` | `start_date`, `end_date`, `shift_id` (opsional, default ALL) | 4 kartu metrik utama: Taken, Failed, Restock, Taken Today |
| GET | `/api/v1/dashboard/consumption-chart` | `start_date`, `end_date`, `shift_id` | Data line chart konsumsi harian |
| GET | `/api/v1/dashboard/sales-analytics` | `start_date`, `end_date`, `shift_id` | Proporsi per varian (untuk chart donut/pie) |
| GET | `/api/v1/dashboard/latest-transactions` | `start_date`, `end_date`, `shift_id` | 10 transaksi terbaru |

**Catatan implementasi:**
- `shift_id` bisa diisi dari data master shift atau cukup "ALL" sebagai default
- `start_date` dan `end_date` format: `YYYY-MM-DD`
- Tampilkan 4 kartu metrik di bagian atas, diikuti list transaksi terbaru

---

### [EXIST] 🔔 Notifikasi Sistem
**Target Android:** Sub menu "Notifikasi" di menu "module"

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/notifications` | `unread_only` (bool), `limit` (int, default 50), `notif_type` (opsional) | Ambil daftar notifikasi |
| PUT | `/api/v1/notifications/{notif_id}/read` | `notif_id` di path | Tandai satu notif sudah dibaca |
| PUT | `/api/v1/notifications/read-all` | - | Tandai semua notif sudah dibaca |

**Response notifikasi:**
```json
{
  "unread_count": 3,
  "notifications": [
    {
      "id": 1,
      "created_at": "...",
      "notif_type": "ETL",
      "severity": "SUCCESS",
      "title": "...",
      "message": "...",
      "is_read": false,
      "related_month": "2026-01",
      "related_quarter": null
    }
  ]
}
```

---

### [EXIST] 📅 Kalender Operasional
**Target Android:** Sub menu "Kalender" di menu "module"

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/calendar` | `year` (int, default 2026) | Ambil seluruh data kalender 1 tahun |
| POST | `/api/v1/calendar/day` | Body JSON | Update status 1 hari tertentu |
| POST | `/api/v1/calendar/generate` | Body: `{"year": int}` | Generate kalender untuk 1 tahun baru |
| DELETE | `/api/v1/calendar/year/{year}` | `year` di path | Hapus seluruh kalender 1 tahun |

**Request body `POST /api/v1/calendar/day`:**
```json
{
  "date": "2026-03-15",
  "day_category": "Kerja Normal",
  "is_working_day": true,
  "is_ramadan": false,
  "is_shutdown": false
}
```

---

### [EXIST] 📂 Manual Insert Data
**Target Android:** Sub menu "Upload Data" di menu "module"

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/manual-insert/template` | - | Download file template Excel |
| POST | `/api/v1/manual-insert/upload` | File multipart `.xlsx` | Upload file Excel berisi data demand |

**Catatan implementasi:**
- Endpoint download template mengembalikan file `.xlsx` langsung
- Endpoint upload menggunakan `multipart/form-data`
- Response upload berisi: `inserted_count`, `duplicated_count`, `invalid_rows_skipped`

---

### [EXIST] 🤖 Prediction Dashboard
**Target Android:** Sub menu "Prediksi" di menu "module"

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/prediction/summary` | `year`, `quarter` | Ringkasan akurasi & prediksi per quarter |
| GET | `/api/v1/prediction/variant-errors` | `year`, `quarter` | Error per varian per bulan |
| GET | `/api/v1/prediction/shift-errors` | `year`, `quarter` | Error per shift per bulan |
| GET | `/api/v1/prediction/daily-logs` | `year`, `quarter` | 30 log harian aktual vs prediksi |
| GET | `/api/v1/prediction/chart-data` | `year`, `quarter` | Dataset chart 27 deret data |

---

### [EXIST] 📋 Retrain Logs
**Target Android:** Sub menu "Log Retraining" di menu "module"

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/retrain/logs` | `limit` (default 100), `offset` (default 0) | Riwayat retraining model ML |

**Catatan implementasi:**
- Response berisi: `quarter_label`, `calculated_year`, `mape`, `mae`, `rmse`, `status`
- Tampilkan sebagai list/tabel dengan badge status (SUCCESS/FAILED)

---

### [EXIST] ⚙️ Manajemen User (Admin Only)
**Target Android:** Sub menu "User Management" di menu "module"
**Akses:** Hanya level_user tertentu (cek `level_user` dari SharedPreferences)

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/admin/users` | - | Ambil semua user |
| GET | `/api/v1/admin/pending-users` | - | Ambil user yang menunggu approval |
| POST | `/api/v1/admin/approve-user` | Body: `target_user_id`, `admin_id` | Setujui user baru |
| PUT | `/api/v1/admin/users/{userId}/update-role-password` | Body: `level_user`, `new_password` | Update role/password user |
| DELETE | `/api/v1/admin/users/{userId}` | `userId` di path | Nonaktifkan/tolak user |

**Catatan implementasi:**
- `admin_id` diambil dari SharedPreferences (field `Id`)
- Tampilkan tombol approve hanya jika `level_user` dari SharedPreferences adalah admin (level 1 atau sesuai yang terdeteksi di project)

---

## ══════════════════════════════════════
## BAGIAN 3 — API BARU (dari branch belvatabitha-patch-1)
## ══════════════════════════════════════

> Bagian ini sudah diisi berdasarkan analisa branch `belvatabitha-patch-1`.
> Semua endpoint di bawah sudah diverifikasi dari kode sumber.

---

### [NEW] ⚙️ Variant Management (Refactor)
**Target Android:** Sub menu "Management Variant" — **UPDATE path lama!**
**PENTING:** Path berubah dari `/api/v1/variants` → `/api/v1/variant` (singular)

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/variant` | `status` (int opsional: 0/1) | List semua varian |
| GET | `/api/v1/variant/{variant_id}` | `variant_id` di path | Detail varian |
| GET | `/api/v1/variant/active` | - | Hanya varian aktif (status=1) |
| POST | `/api/v1/variant` | Body JSON | Buat varian baru |
| PUT | `/api/v1/variant/{variant_id}` | `variant_id` + Body | Update varian |
| DELETE | `/api/v1/variant/{variant_id}` | `variant_id` di path | Hapus varian |

**Request body POST/PUT:**
```json
{
  "nama_variant": "Coklat",
  "image_url": null,
  "status": 1
}
```

**Response:**
```json
{
  "id_recnum_variant": 1,
  "nama_variant": "Coklat",
  "image_url": null,
  "status": 1,
  "created_at": "2026-01-01T00:00:00",
  "updated_at": "2026-01-01T00:00:00"
}
```

---

### [CRUD] 💦 Restock Management
**Target Android:** Sub menu "Restock Management" di menu "module"
**Tabel DB:** `dbo.manage_restok`

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/restock` | `status` (int opsional: 0/1) | List semua restock |
| GET | `/api/v1/restock/{restock_id}` | `restock_id` di path | Detail restock |
| GET | `/api/v1/restock/vm/{vm_id}` | `vm_id` di path | Semua restock aktif untuk 1 VM |
| POST | `/api/v1/restock` | Body JSON | Buat/update slot (upsert) |
| PUT | `/api/v1/restock/{restock_id}` | `restock_id` + Body | Update restock |
| DELETE | `/api/v1/restock/{restock_id}` | `restock_id` di path | Hapus restock |
| PUT | `/api/v1/restock/vm/{vm_id}/slot/{slot_number}` | path + `stok_qty` + `user` query | Shortcut update qty slot |
| GET | `/api/v1/restock/alerts/low-stock` | `threshold` (int, default 10) | Alert stok rendah |

**Request body POST:**
```json
{
  "id_recnum_mav": 1,
  "stok_qty": 50,
  "slot_number": "A1",
  "user_input": "admin",
  "status_restok": 1
}
```

**Catatan penting:** POST bersifat **upsert** — jika slot sudah ada untuk VM tersebut, akan di-UPDATE, bukan INSERT baru.

---

### [CRUD] 🏭 Manage Alat VM
**Target Android:** Sub menu "Manage Alat VM" di menu "module"
**Tabel DB:** `dbo.master_alat_vm`

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/machine` | - | List semua mesin |
| GET | `/api/v1/machine/{machine_id}` | `machine_id` di path | Detail mesin |
| POST | `/api/v1/machine` | Body JSON | Tambah mesin baru |
| PUT | `/api/v1/machine/{machine_id}` | `machine_id` + Body | Update mesin |
| DELETE | `/api/v1/machine/{machine_id}` | `machine_id` di path | Hapus mesin |

**Request body POST:**
```json
{
  "nama_vm": "VM Lantai 1",
  "no_ref": "VM-001",
  "ip_address": "192.168.1.10",
  "user_input": "admin"
}
```

---

### [CRUD] ⏰ Shift Management
**Target Android:** Sub menu "Shift Management" di menu "module"
**Tabel DB:** `dbo.master_settime`

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/shift` | - | List semua shift |
| GET | `/api/v1/shift/{shift_id}` | `shift_id` di path | Detail shift |
| POST | `/api/v1/shift` | Body JSON | Buat shift baru |
| PUT | `/api/v1/shift/{shift_id}` | `shift_id` + Body | Update shift |
| DELETE | `/api/v1/shift/{shift_id}` | `shift_id` di path | Hapus shift |

**Request body POST:**
```json
{
  "nama_shift": "SHIFT1",
  "nama_bagian": "Produksi",
  "jam_mulai": "07:00",
  "jam_akhir": "15:00",
  "status_active": 1,
  "user_input": "admin"
}
```

---

### [CRUD] 📂️ Slot Number
**Target Android:** Sub menu "Slot Number" di menu "module"
**Tabel DB:** `dbo.manage_map_slot_number`

| Method | Endpoint | Parameter | Keterangan |
|--------|----------|-----------|------------|
| GET | `/api/v1/slot` | `vm_id` (int, wajib) | Slot untuk 1 VM |
| GET | `/api/v1/slot/{slot_id}` | `slot_id` di path | Detail slot |
| POST | `/api/v1/slot` | Body JSON | Buat konfigurasi slot baru |
| PUT | `/api/v1/slot/{slot_id}` | `slot_id` + Body | Update slot |
| DELETE | `/api/v1/slot/{slot_id}` | `slot_id` di path | Hapus slot |

**Request body POST:**
```json
{
  "id_recnum_mav": 1,
  "slot_name": "A",
  "slot_number_max": 10,
  "id_recnum_variant": 1,
  "user_input": "admin"
}
```

---

### [CONNECT] 📊 Inventory Dashboard
**Target Android:** Activity Inventory Dashboard yang sudah ada
**Status UI:** SUDAH DIIMPLEMENTASI di Android — hanya perlu disambungkan ke API
**Tabel DB:** `dbo.warehouse_stock`, `dbo.ForecastResults_Layer1`, `dbo.manage_restok`

---

#### ENDPOINT A — `GET /api/v1/inventory/dashboard`

| Parameter | Tipe | Default | Keterangan |
|-----------|------|---------|------------|
| `year` | int | tahun sekarang | Tahun kuartal yang dilihat |
| `quarter` | int | kuartal berikutnya | 1–4 |

**Struktur response yang penting:**
```json
{
  "year": 2026,
  "quarter": 3,
  "quarter_label": "Q3 2026 (Jul - Agu - Sep)",
  "has_prediction_data": true,
  "available_quarters": [{"year": 2026, "quarter": 1, "label": "Q1 2026"}, ...],
  "summary": {
    "total_predicted_demand": 137345,
    "total_warehouse_stock": 0,
    "total_vm_stock": 2233,
    "total_available": 2233,
    "total_to_purchase": 135112
  },
  "variants": [
    {
      "variant_name": "Coklat",
      "predicted_demand": 68188,
      "warehouse_stock": 0,
      "vm_stock": 1200,
      "total_available": 1200,
      "to_purchase": 66988,
      "purchase_percentage": 49.6,
      "monthly": [
        {"month_name": "Juli", "month_number": 7, "predicted": 22500}
      ]
    }
  ],
  "history_summary": null,
  "decision_support": {
    "recommended_purchase_total": 135112,
    "top_variant": "Coklat",
    "top_variant_qty": 66988,
    "notes": ["Rekomendasi pembelian utama: Coklat...", ...]
  },
  "auto_sync_info": {
    "processed_variants": 0,
    "total_out_qty": 0,
    "note": "Tidak ada event stocking baru..."
  }
}
```

**Catatan penting:**
- Jika `has_prediction_data = false` → tampilkan pesan "Data prediksi belum tersedia" + arahkan ke `available_quarters`
- `warehouse_stock` bisa negatif → tampilkan warna merah sebagai warning
- `auto_sync_info` diproses server otomatis, Android tidak perlu melakukan apapun
- Gunakan `available_quarters` untuk dropdown pemilih kuartal
- Jika `history_summary != null` → kuartal sudah lewat, tampilkan section histori

---

#### ENDPOINT B — `GET /api/v1/inventory/movements`

| Parameter | Tipe | Default | Keterangan |
|-----------|------|---------|------------|
| `page` | int | 1 | Halaman |
| `per_page` | int | 10 (max 50) | Item per halaman |
| `variant` | string | null (semua) | Filter nama variant |
| `type` | string | null (semua) | Filter: `IN` atau `OUT` |

**Response item:**
```json
{
  "id": 1,
  "date": "2026-01-01",
  "date_string": "01 Jan 2026",
  "time_string": "08:00",
  "variant_name": "Coklat",
  "movement_type": "IN",
  "qty": 500,
  "balance_after": 500,
  "note": "Pembelian Q1",
  "created_by": "admin"
}
```

---

#### ENDPOINT C — `POST /api/v1/inventory/stock-in`

**Kapan dipanggil:** Saat admin klik FAB / tombol "Tambah Stok Masuk"

**Request body:**
```json
{
  "items": [
    {"variant_name": "Coklat",           "qty": 500},
    {"variant_name": "Strawberry",       "qty": 300},
    {"variant_name": "Moca",             "qty": 0},
    {"variant_name": "Original (Putih)", "qty": 200}
  ],
  "note": "Pembelian dari supplier Juni 2026"
}
```

**Aturan:**
- `qty = 0` untuk variant yang tidak dibeli — akan otomatis diskip server
- Minimal 1 variant harus qty > 0, jika tidak → server return 400
- Field `note` opsional

**Response sukses (201):**
```json
{
  "success": true,
  "message": "3 varian berhasil ditambahkan ke gudang.",
  "entry_date": "2026-06-19",
  "total_added": 1000,
  "results": [
    {
      "variant_name": "Coklat",
      "qty_added": 500,
      "previous_balance": 0,
      "new_balance": 500
    }
  ]
}
```

**UX yang diharapkan:**
- Form menampilkan 4 field qty (1 per variant)
- Di bawah setiap field: tampilkan saldo gudang saat ini (`warehouse_stock` dari dashboard)
- Placeholder/hint qty = nilai `to_purchase` dari DSS (rekomendasi beli)
- Setelah berhasil: tutup form, refresh dashboard otomatis

> Jika ada endpoint tambahan lagi di kemudian hari, tambahkan section baru di sini mengikuti format yang sama.

---

## ══════════════════════════════════════
## BAGIAN 4 — URUTAN PRIORITAS EKSEKUSI
## ══════════════════════════════════════

> AI harus mengeksekusi dalam urutan berikut. Selesaikan satu nomor sebelum lanjut.

```
TIPE 1 — CONNECT (UI sudah ada, sambungkan ke API):
  1. Inventory Dashboard  ← sambungkan 3 endpoint ke UI yang sudah ada

TIPE 2 — CRUD dari nol (seperti Management Variant):
  2. Restock Management   ← 8 endpoint, ada fitur upsert & low-stock alert
  3. Manage Alat VM       ← 5 endpoint, CRUD standar
  4. Shift Management     ← 5 endpoint, perhatikan format jam HH:MM
  5. Slot Number          ← 5 endpoint, CRUD standar
```

---

## ══════════════════════════════════════
## BAGIAN 5 — CATATAN TEKNIS GLOBAL
## ══════════════════════════════════════

- **Base URL**: Gunakan konstanta yang sudah ada di Project B (jangan hardcode baru)
- **Auth header**: Saat ini API tidak menggunakan Bearer token — cukup kirim parameter yang dibutuhkan
- **Error handling**: Semua API bisa return HTTP 400/404/403 — tangani dengan pesan yang ramah ke user
- **Format tanggal**: Selalu gunakan format `YYYY-MM-DD` untuk parameter tanggal
- **SharedPreferences keys** yang tersedia dari session login:
  - `id_recnum_mur` → ID numerik user (Integer)
  - `Id` → ID string user (misal: "adam_abdurrahman_9")
  - `username` → nama tampilan user
  - `email_primary` → email utama
  - `level_user` → level/role user (Integer)
  - `status_active` → status akun ("1" = aktif)
  - `photo_url` → path foto profil (bisa null)
